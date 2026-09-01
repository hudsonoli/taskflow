"""Testes de app/core/sla_resolver.py (Fase 2G.6C) — resolução determinística, sem cálculo de
prazo (isso é test_calculadora_expediente.py) e sem integração com Demanda (2G.6D).

As `SlaRegra` usadas aqui são criadas diretamente via ORM (não via API `/slas`) para ter
controle explícito sobre `prioridade_regra`/`created_at`/`id` — necessário pros testes de
precedência/desempate."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.sla_resolver import resolver_sla
from app.models.cliente import Cliente
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.sla_regra import SlaRegra


def _sla_regra(
    db: Session,
    empresa: Empresa,
    *,
    sla_regra_id: str | None = None,
    nome: str | None = None,
    status: str = "ativo",
    prioridade_alvo: str | None = None,
    departamento_id: str | None = None,
    cliente_id: str | None = None,
    prioridade_regra: int = 100,
    created_at: datetime | None = None,
) -> SlaRegra:
    sufixo = uuid.uuid4().hex[:8]
    agora = created_at or datetime.now(timezone.utc)
    regra = SlaRegra(
        id=sla_regra_id or str(uuid.uuid4()),
        empresa_id=empresa.id,
        nome=nome or f"SLA {sufixo}",
        nome_normalizado=(nome or f"sla {sufixo}").lower(),
        descricao=None,
        prioridade_alvo=prioridade_alvo,
        departamento_id=departamento_id,
        cliente_id=cliente_id,
        prioridade_regra=prioridade_regra,
        prazo_primeira_resposta_quantidade=4,
        prazo_primeira_resposta_unidade="horas",
        prazo_resolucao_quantidade=48,
        prazo_resolucao_unidade="horas",
        considerar_apenas_expediente=True,
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(regra)
    db.flush()
    return regra


def _departamento(db: Session, empresa: Empresa) -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Departamento {sufixo}",
        nome_normalizado=f"departamento {sufixo}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _cliente(db: Session, empresa: Empresa) -> Cliente:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    cliente = Cliente(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"cli-{sufixo}",
        codigo_referencia=f"C26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Cliente {sufixo}",
        nome_normalizado=f"cliente {sufixo}",
        tipo_documento="cnpj",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(cliente)
    db.flush()
    return cliente


# --------------------------------------------------------------------------------------
# A-B: sem regra / default
# --------------------------------------------------------------------------------------


def test_a_nenhuma_regra_retorna_none(db_session: Session, empresa: Empresa) -> None:
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    assert resultado is None


def test_b_default_combina_com_qualquer_criterio(db_session: Session, empresa: Empresa) -> None:
    default = _sla_regra(db_session, empresa)
    resultado = resolver_sla(
        db_session, empresa_id=empresa.id, prioridade="baixa", departamento_id=str(uuid.uuid4()), cliente_id=str(uuid.uuid4())
    )
    assert resultado is not None
    assert resultado.id == default.id


# --------------------------------------------------------------------------------------
# C-F: critérios específicos
# --------------------------------------------------------------------------------------


def test_c_prioridade_especifica_vence_por_precedencia(db_session: Session, empresa: Empresa) -> None:
    _sla_regra(db_session, empresa, prioridade_regra=100)  # default, menos prioritária
    especifica = _sla_regra(db_session, empresa, prioridade_alvo="alta", prioridade_regra=10)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    assert resultado.id == especifica.id


def test_d_departamento_especifico(db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    _sla_regra(db_session, empresa, prioridade_regra=100)
    especifica = _sla_regra(db_session, empresa, departamento_id=departamento.id, prioridade_regra=10)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="media", departamento_id=departamento.id)
    assert resultado.id == especifica.id


def test_e_cliente_especifico(db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    _sla_regra(db_session, empresa, prioridade_regra=100)
    especifica = _sla_regra(db_session, empresa, cliente_id=cliente.id, prioridade_regra=10)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="media", cliente_id=cliente.id)
    assert resultado.id == especifica.id


def test_f_combinacao_cliente_departamento_prioridade(db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    cliente = _cliente(db_session, empresa)
    _sla_regra(db_session, empresa, prioridade_regra=100)
    _sla_regra(db_session, empresa, prioridade_alvo="alta", prioridade_regra=10)
    tripla = _sla_regra(
        db_session,
        empresa,
        prioridade_alvo="alta",
        departamento_id=departamento.id,
        cliente_id=cliente.id,
        prioridade_regra=10,
    )
    resultado = resolver_sla(
        db_session,
        empresa_id=empresa.id,
        prioridade="alta",
        departamento_id=departamento.id,
        cliente_id=cliente.id,
    )
    assert resultado.id == tripla.id


# --------------------------------------------------------------------------------------
# G-J: precedência/desempate
# --------------------------------------------------------------------------------------


def test_g_prioridade_regra_menor_vence_mesmo_menos_especifica(db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    generica_prioritaria = _sla_regra(db_session, empresa, prioridade_regra=1)
    especifica_menos_prioritaria = _sla_regra(db_session, empresa, cliente_id=cliente.id, prioridade_regra=50)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta", cliente_id=cliente.id)
    assert resultado.id == generica_prioritaria.id
    assert resultado.id != especifica_menos_prioritaria.id


def test_h_mesma_prioridade_regra_maior_especificidade_vence(db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    generica = _sla_regra(db_session, empresa, prioridade_regra=10)
    mais_especifica = _sla_regra(
        db_session, empresa, cliente_id=cliente.id, prioridade_alvo="alta", prioridade_regra=10
    )
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta", cliente_id=cliente.id)
    assert resultado.id == mais_especifica.id


def test_i_empate_especificidade_created_at_mais_antigo_vence(db_session: Session, empresa: Empresa) -> None:
    agora = datetime.now(timezone.utc)
    mais_antiga = _sla_regra(db_session, empresa, prioridade_regra=10, created_at=agora - timedelta(days=1))
    mais_nova = _sla_regra(db_session, empresa, prioridade_regra=10, created_at=agora)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    assert resultado.id == mais_antiga.id
    assert resultado.id != mais_nova.id


def test_j_empate_created_at_desempate_por_id(db_session: Session, empresa: Empresa) -> None:
    agora = datetime.now(timezone.utc)
    id_menor = "00000000-0000-0000-0000-000000000001"
    id_maior = "00000000-0000-0000-0000-000000000002"
    _sla_regra(db_session, empresa, sla_regra_id=id_maior, prioridade_regra=10, created_at=agora)
    _sla_regra(db_session, empresa, sla_regra_id=id_menor, prioridade_regra=10, created_at=agora)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    assert resultado.id == id_menor


# --------------------------------------------------------------------------------------
# K-M: lifecycle e tenant
# --------------------------------------------------------------------------------------


def test_k_regra_inativa_e_ignorada(db_session: Session, empresa: Empresa) -> None:
    _sla_regra(db_session, empresa, status="inativo", prioridade_regra=1)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    assert resultado is None


def test_l_regra_arquivada_e_ignorada(db_session: Session, empresa: Empresa) -> None:
    _sla_regra(db_session, empresa, status="arquivado", prioridade_regra=1)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    assert resultado is None


def test_m_regra_de_outra_empresa_e_ignorada(db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    _sla_regra(db_session, outra_empresa, prioridade_regra=1)
    resultado = resolver_sla(db_session, empresa_id=empresa.id, prioridade="alta")
    assert resultado is None
