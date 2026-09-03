"""Integração SLA ↔ Demanda (Fase 2G.6D1) — resolução na criação, snapshot imutável,
deadlines persistidos. Não cobre resolução/cálculo em si (ver test_sla_resolver.py e
test_calculadora_expediente.py) nem nada de primeira resposta/resolução real (2G.6D2).

Decisão registrada nesta fase: `departamento_id` NUNCA é usado como critério de resolução —
`Demanda` pode ter zero, um ou vários `DemandaDepartamento` vinculados, sem conceito de
"principal" (ver docstring de app/models/demanda.py). O grupo "departamento" abaixo prova
isso nos três cenários (zero/um/múltiplos vínculos)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.calculadora_expediente import SlaExpedienteSemJanelaUtilError
from app.models.cliente import Cliente
from app.models.demanda import Demanda
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.sla_regra import SlaRegra
from app.schemas.demanda import DemandaCreate
from app.services.demanda_service import DemandaService
from app.services.regra_expediente_service import RegraExpedienteService

# --------------------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------------------


def _payload(**extra) -> dict:
    return {"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra}


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json=_payload(**extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


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


def _sla_regra(db: Session, empresa: Empresa, **overrides) -> SlaRegra:
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    base = dict(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        nome=f"SLA {sufixo}",
        nome_normalizado=f"sla {sufixo}",
        descricao=None,
        prioridade_alvo=None,
        departamento_id=None,
        cliente_id=None,
        prioridade_regra=100,
        prazo_primeira_resposta_quantidade=4,
        prazo_primeira_resposta_unidade="horas",
        prazo_resolucao_quantidade=48,
        prazo_resolucao_unidade="horas",
        # False por padrão nos testes de integração: deixa os deadlines com matemática
        # trivial (inicio + N), decidindo o SLA sem reabrir a lógica de janela/expediente já
        # coberta em test_calculadora_expediente.py.
        considerar_apenas_expediente=False,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    base.update(overrides)
    regra = SlaRegra(**base)
    db.add(regra)
    db.flush()
    return regra


def _quebrar_regra_expediente(db: Session, empresa: Empresa) -> None:
    """Deixa a RegraExpediente da Empresa sem nenhum dia ativo — configuração impossível
    usada pelos testes O/P (proteção contra loop já teria disparado no nível da
    calculadora; aqui confirmamos que a criação de Demanda propaga esse erro)."""
    service = RegraExpedienteService()
    regra = service.get_ou_criar(db, empresa_id=empresa.id)
    for dia in service.repository.list_dias(db, regra.id):
        dia.ativo = False
        service.repository.update_dia(db, dia)


def _parse(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


# --------------------------------------------------------------------------------------
# A-D: resolução básica
# --------------------------------------------------------------------------------------


def test_a_sem_regra_sla_criacao_sucesso_campos_null(client_admin: TestClient) -> None:
    criada = _criar_demanda(client_admin)
    assert criada["id"]
    for campo in (
        "slaRegraId",
        "slaRegraNomeSnapshot",
        "slaPrazoPrimeiraRespostaQuantidadeSnapshot",
        "slaPrazoPrimeiraRespostaUnidadeSnapshot",
        "slaPrazoResolucaoQuantidadeSnapshot",
        "slaPrazoResolucaoUnidadeSnapshot",
        "slaConsiderarExpedienteSnapshot",
        "slaResolvidoAt",
        "slaPrimeiraRespostaLimiteEm",
        "slaResolucaoLimiteEm",
    ):
        assert criada[campo] is None, campo


def test_b_regra_default_snapshot_correto(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    default = _sla_regra(db_session, empresa)
    criada = _criar_demanda(client_admin)
    assert criada["slaRegraId"] == default.id
    assert criada["slaRegraNomeSnapshot"] == default.nome
    assert criada["slaPrazoPrimeiraRespostaQuantidadeSnapshot"] == default.prazo_primeira_resposta_quantidade
    assert criada["slaPrazoPrimeiraRespostaUnidadeSnapshot"] == default.prazo_primeira_resposta_unidade
    assert criada["slaPrazoResolucaoQuantidadeSnapshot"] == default.prazo_resolucao_quantidade
    assert criada["slaPrazoResolucaoUnidadeSnapshot"] == default.prazo_resolucao_unidade
    assert criada["slaConsiderarExpedienteSnapshot"] == default.considerar_apenas_expediente
    assert criada["slaResolvidoAt"] is not None
    assert criada["slaPrimeiraRespostaLimiteEm"] is not None
    assert criada["slaResolucaoLimiteEm"] is not None


def test_c_regra_especifica_por_prioridade_vence(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _sla_regra(db_session, empresa, prioridade_regra=100)
    especifica = _sla_regra(db_session, empresa, prioridade_alvo="alta", prioridade_regra=10)
    criada = _criar_demanda(client_admin, prioridade="alta")
    assert criada["slaRegraId"] == especifica.id


def test_regra_especifica_por_cliente_vence(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    _sla_regra(db_session, empresa, prioridade_regra=100)
    especifica = _sla_regra(db_session, empresa, cliente_id=cliente.id, prioridade_regra=10)
    criada = _criar_demanda(client_admin, clienteId=str(cliente.id))
    assert criada["slaRegraId"] == especifica.id


def test_d_deadlines_iguais_ao_calculo_esperado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    regra = _sla_regra(
        db_session,
        empresa,
        prazo_primeira_resposta_quantidade=4,
        prazo_primeira_resposta_unidade="horas",
        prazo_resolucao_quantidade=48,
        prazo_resolucao_unidade="horas",
    )
    criada = _criar_demanda(client_admin)

    resolvido_at = _parse(criada["slaResolvidoAt"])
    created_at = _parse(criada["createdAt"])
    assert resolvido_at == created_at

    assert _parse(criada["slaPrimeiraRespostaLimiteEm"]) == created_at + timedelta(
        hours=regra.prazo_primeira_resposta_quantidade
    )
    assert _parse(criada["slaResolucaoLimiteEm"]) == created_at + timedelta(hours=regra.prazo_resolucao_quantidade)


# --------------------------------------------------------------------------------------
# Departamento — decisão da 2G.6D1: nunca usado como critério
# --------------------------------------------------------------------------------------


def test_departamento_sem_vinculo_default_ainda_combina(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    default = _sla_regra(db_session, empresa)
    criada = _criar_demanda(client_admin)
    assert criada["departamentoResponsavelIds"] == []
    assert criada["slaRegraId"] == default.id


def test_departamento_unico_regra_especifica_nao_combina(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    especifica_por_departamento = _sla_regra(
        db_session, empresa, departamento_id=departamento.id, prioridade_regra=1
    )
    criada = _criar_demanda(client_admin, departamentoResponsavelIds=[str(departamento.id)])
    assert criada["departamentoResponsavelIds"] == [str(departamento.id)]
    assert criada["slaRegraId"] is None
    assert criada["slaRegraId"] != especifica_por_departamento.id


def test_departamento_multiplos_regra_especifica_nao_combina(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    dep_a = _departamento(db_session, empresa)
    dep_b = _departamento(db_session, empresa)
    _sla_regra(db_session, empresa, departamento_id=dep_a.id, prioridade_regra=1)
    criada = _criar_demanda(
        client_admin, departamentoResponsavelIds=[str(dep_a.id), str(dep_b.id)]
    )
    assert len(criada["departamentoResponsavelIds"]) == 2
    assert criada["slaRegraId"] is None


def test_departamento_regra_generica_continua_combinando_com_departamento_vinculado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    _sla_regra(db_session, empresa, departamento_id=departamento.id, prioridade_regra=1)
    generica = _sla_regra(db_session, empresa, prioridade_regra=50)
    criada = _criar_demanda(client_admin, departamentoResponsavelIds=[str(departamento.id)])
    assert criada["slaRegraId"] == generica.id


# --------------------------------------------------------------------------------------
# E-G: imutabilidade do snapshot
# --------------------------------------------------------------------------------------


def test_e_snapshot_nome_preservado_apos_rename_da_regra(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    regra = _sla_regra(db_session, empresa, nome="Nome Original")
    criada = _criar_demanda(client_admin)
    assert criada["slaRegraNomeSnapshot"] == "Nome Original"

    regra.nome = "Nome Renomeado"
    regra.nome_normalizado = "nome renomeado"
    db_session.add(regra)
    db_session.flush()

    relida = client_admin.get(f"/demandas/{criada['id']}")
    assert relida.status_code == 200, relida.text
    assert relida.json()["slaRegraNomeSnapshot"] == "Nome Original"


def test_f_snapshot_prazo_preservado_apos_editar_regra(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    regra = _sla_regra(db_session, empresa, prazo_resolucao_quantidade=48, prazo_resolucao_unidade="horas")
    criada = _criar_demanda(client_admin)
    assert criada["slaPrazoResolucaoQuantidadeSnapshot"] == 48

    regra.prazo_resolucao_quantidade = 5
    regra.prazo_resolucao_unidade = "dias_uteis"
    db_session.add(regra)
    db_session.flush()

    relida = client_admin.get(f"/demandas/{criada['id']}")
    assert relida.json()["slaPrazoResolucaoQuantidadeSnapshot"] == 48
    assert relida.json()["slaPrazoResolucaoUnidadeSnapshot"] == "horas"


def test_g_arquivar_regra_nao_muda_demanda(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    regra = _sla_regra(db_session, empresa)
    criada = _criar_demanda(client_admin)

    regra.status = "arquivado"
    db_session.add(regra)
    db_session.flush()

    relida = client_admin.get(f"/demandas/{criada['id']}")
    assert relida.status_code == 200, relida.text
    corpo = relida.json()
    assert corpo["slaRegraId"] == regra.id
    assert corpo["slaRegraNomeSnapshot"] == criada["slaRegraNomeSnapshot"]
    assert corpo["slaPrimeiraRespostaLimiteEm"] == criada["slaPrimeiraRespostaLimiteEm"]
    assert corpo["slaResolucaoLimiteEm"] == criada["slaResolucaoLimiteEm"]


# --------------------------------------------------------------------------------------
# H-J: PATCH não recalcula
# --------------------------------------------------------------------------------------


def test_h_patch_prioridade_nao_recalcula(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _sla_regra(db_session, empresa, prioridade_regra=100)
    especifica_alta = _sla_regra(db_session, empresa, prioridade_alvo="alta", prioridade_regra=1)
    criada = _criar_demanda(client_admin, prioridade="baixa")
    assert criada["slaRegraId"] != especifica_alta.id

    editada = client_admin.patch(f"/demandas/{criada['id']}", json={"prioridade": "alta"})
    assert editada.status_code == 200, editada.text
    corpo = editada.json()
    assert corpo["prioridade"] == "alta"
    assert corpo["slaRegraId"] == criada["slaRegraId"]
    assert corpo["slaPrimeiraRespostaLimiteEm"] == criada["slaPrimeiraRespostaLimiteEm"]


def test_i_patch_cliente_nao_recalcula(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    _sla_regra(db_session, empresa, prioridade_regra=100)
    especifica_cliente = _sla_regra(db_session, empresa, cliente_id=cliente.id, prioridade_regra=1)
    criada = _criar_demanda(client_admin)
    assert criada["slaRegraId"] != especifica_cliente.id

    editada = client_admin.patch(f"/demandas/{criada['id']}", json={"clienteId": str(cliente.id)})
    assert editada.status_code == 200, editada.text
    corpo = editada.json()
    assert corpo["clienteId"] == str(cliente.id)
    assert corpo["slaRegraId"] == criada["slaRegraId"]


def test_j_patch_departamento_nao_recalcula(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    default = _sla_regra(db_session, empresa)
    criada = _criar_demanda(client_admin)
    assert criada["slaRegraId"] == default.id

    editada = client_admin.patch(
        f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": [str(departamento.id)]}
    )
    assert editada.status_code == 200, editada.text
    corpo = editada.json()
    assert corpo["departamentoResponsavelIds"] == [str(departamento.id)]
    assert corpo["slaRegraId"] == default.id
    assert corpo["slaPrimeiraRespostaLimiteEm"] == criada["slaPrimeiraRespostaLimiteEm"]


# --------------------------------------------------------------------------------------
# K: proteção de payload
# --------------------------------------------------------------------------------------


def test_k_payload_create_com_campo_sla_rejeitado_422(client_admin: TestClient) -> None:
    resposta = client_admin.post(
        "/demandas", json={**_payload(), "slaRegraId": str(uuid.uuid4())}
    )
    assert resposta.status_code == 422, resposta.text


def test_k_payload_update_com_campo_sla_rejeitado_422(client_admin: TestClient) -> None:
    criada = _criar_demanda(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"slaResolucaoLimiteEm": "2030-01-01T00:00:00Z"}
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# L-N: tenant e lifecycle
# --------------------------------------------------------------------------------------


def test_l_cross_tenant_nunca_resolve_regra_de_outra_empresa(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    _sla_regra(db_session, outra_empresa, prioridade_regra=1)
    criada = _criar_demanda(client_admin)
    assert criada["slaRegraId"] is None


def test_m_regra_inativa_ignorada(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _sla_regra(db_session, empresa, status="inativo", prioridade_regra=1)
    criada = _criar_demanda(client_admin)
    assert criada["slaRegraId"] is None


def test_n_regra_arquivada_ignorada_na_resolucao(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    _sla_regra(db_session, empresa, status="arquivado", prioridade_regra=1)
    criada = _criar_demanda(client_admin)
    assert criada["slaRegraId"] is None


# --------------------------------------------------------------------------------------
# O-P: erro de configuração vs. ausência de regra
# --------------------------------------------------------------------------------------


def test_o_configuracao_expediente_invalida_criacao_atomica_falha(
    db_session: Session, empresa: Empresa
) -> None:
    _sla_regra(db_session, empresa, considerar_apenas_expediente=True, prioridade_regra=1)
    _quebrar_regra_expediente(db_session, empresa)

    contagem_antes = db_session.query(Demanda).filter(Demanda.empresa_id == empresa.id).count()

    with pytest.raises(SlaExpedienteSemJanelaUtilError):
        DemandaService().create_demanda(
            db_session, DemandaCreate(nome="Falha de configuracao de SLA"), empresa_id=empresa.id
        )

    contagem_depois = db_session.query(Demanda).filter(Demanda.empresa_id == empresa.id).count()
    assert contagem_depois == contagem_antes


def test_p_sem_regra_nao_calcula_expediente_mesmo_com_configuracao_quebrada(
    db_session: Session, empresa: Empresa
) -> None:
    """Sem nenhuma SlaRegra combinando, `resolver_sla` devolve `None` e a criação nunca chega
    a chamar a calculadora/RegraExpediente — confirmado deixando a RegraExpediente da
    Empresa propositalmente quebrada e provando que isso não impede a criação."""
    _quebrar_regra_expediente(db_session, empresa)

    demanda = DemandaService().create_demanda(
        db_session, DemandaCreate(nome="Sem SLA, expediente quebrado"), empresa_id=empresa.id
    )

    assert demanda.sla_regra_id is None
    assert demanda.sla_primeira_resposta_limite_em is None
