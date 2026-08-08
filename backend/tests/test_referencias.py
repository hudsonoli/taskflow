"""Infraestrutura de códigos de referência — ver app/core/referencias.py."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.referencias import (
    PREFIXOS_REFERENCIA,
    TipoEntidadeNaoSuportadoError,
    formatar_codigo_referencia,
    gerar_proxima_referencia,
)
from app.models.empresa import Empresa


def _criar_empresa(db: Session) -> Empresa:
    agora = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid.uuid4()),
        nome="Empresa Sequencia",
        documento=None,
        codigo_interno=f"SEQ-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db.add(empresa)
    db.flush()
    return empresa


# --------------------------------------------------------------------------------------
# Formato e lista fechada
# --------------------------------------------------------------------------------------

def test_lista_executavel_cobre_apenas_dominios_ja_migrados() -> None:
    """A lista é FECHADA: cada domínio entra junto da própria migração, nunca antes.

    departamento e equipe entraram na Fase 2A; cliente na 2B; fornecedor na 2C. Tarefa fica
    fora por causa do conflito com a numeração #AA0000 do iClips (pendência da Fase 2E);
    usuario e projeto entram nas fases correspondentes.
    """
    assert PREFIXOS_REFERENCIA == {
        "departamento": "D",
        "equipe": "E",
        "cliente": "C",
        "fornecedor": "F",
    }


def test_formato_do_codigo_de_cliente() -> None:
    assert formatar_codigo_referencia("cliente", 2026, 1) == "C26000001"


def test_formato_do_codigo_de_fornecedor() -> None:
    assert formatar_codigo_referencia("fornecedor", 2026, 1) == "F26000001"


def test_tipo_entidade_fora_da_lista_levanta_erro(db_session: Session, empresa) -> None:
    with pytest.raises(TipoEntidadeNaoSuportadoError):
        gerar_proxima_referencia(db_session, empresa_id=empresa.id, tipo_entidade="tarefa")


def test_formato_do_codigo() -> None:
    assert formatar_codigo_referencia("departamento", 2026, 1) == "D26000001"
    assert formatar_codigo_referencia("equipe", 2026, 1) == "E26000001"
    assert formatar_codigo_referencia("departamento", 2026, 999999) == "D26999999"


# --------------------------------------------------------------------------------------
# Sequência
# --------------------------------------------------------------------------------------

def test_primeiro_e_segundo_departamento_do_ano(db_session: Session, empresa) -> None:
    primeiro = gerar_proxima_referencia(
        db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2026
    )
    segundo = gerar_proxima_referencia(
        db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2026
    )
    assert primeiro.codigo_referencia == "D26000001"
    assert primeiro.sequencial_referencia == 1
    assert primeiro.ano_referencia == 2026
    assert segundo.codigo_referencia == "D26000002"


def test_primeira_equipe_do_ano(db_session: Session, empresa) -> None:
    referencia = gerar_proxima_referencia(
        db_session, empresa_id=empresa.id, tipo_entidade="equipe", ano=2026
    )
    assert referencia.codigo_referencia == "E26000001"


def test_departamento_e_equipe_tem_sequencias_independentes(db_session: Session, empresa) -> None:
    gerar_proxima_referencia(db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2026)
    gerar_proxima_referencia(db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2026)
    equipe = gerar_proxima_referencia(db_session, empresa_id=empresa.id, tipo_entidade="equipe", ano=2026)
    # A equipe começa do 1 mesmo com dois departamentos já emitidos.
    assert equipe.codigo_referencia == "E26000001"


def test_empresas_diferentes_podem_ter_o_mesmo_codigo(db_session: Session, empresa) -> None:
    outra = _criar_empresa(db_session)
    a = gerar_proxima_referencia(db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2026)
    b = gerar_proxima_referencia(db_session, empresa_id=outra.id, tipo_entidade="departamento", ano=2026)
    assert a.codigo_referencia == b.codigo_referencia == "D26000001"


def test_virada_de_ano_reinicia_em_um_e_preserva_o_ano_anterior(db_session: Session, empresa) -> None:
    de_2026 = gerar_proxima_referencia(
        db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2026
    )
    gerar_proxima_referencia(db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2026)
    de_2027 = gerar_proxima_referencia(
        db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2027
    )

    assert de_2026.codigo_referencia == "D26000001"
    assert de_2027.codigo_referencia == "D27000001"

    # A linha de 2026 continua intacta (sem reset destrutivo) — o contador do ano anterior
    # permanece disponível para auditoria.
    ultimo_2026 = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_referencia "
            "WHERE empresa_id = :e AND tipo_entidade = 'departamento' AND ano = 2026"
        ),
        {"e": empresa.id},
    ).scalar_one()
    assert ultimo_2026 == 2


def test_ano_omitido_usa_o_relogio_da_aplicacao(db_session: Session, empresa) -> None:
    from app.core.relogio import ano_corrente

    referencia = gerar_proxima_referencia(db_session, empresa_id=empresa.id, tipo_entidade="departamento")
    assert referencia.ano_referencia == ano_corrente()


# --------------------------------------------------------------------------------------
# Transação: a função não commita e o contador acompanha o rollback
# --------------------------------------------------------------------------------------

def test_nao_faz_commit_proprio(db_session: Session, empresa) -> None:
    """A reserva fica pendente na transação do chamador — quem commita é o service."""
    gerar_proxima_referencia(db_session, empresa_id=empresa.id, tipo_entidade="departamento", ano=2026)
    assert db_session.in_transaction()


def test_rollback_desfaz_o_incremento_sem_queimar_numero(test_engine, empresa) -> None:
    """Se a criação da entidade falhar, o número reservado volta a ficar disponível.

    Usa conexão própria (fora do savepoint do db_session) para conseguir observar o efeito
    real de um rollback completo.
    """
    from sqlalchemy.orm import Session as SessionRaw

    empresa_id = empresa.id
    # A empresa vive na transação do teste; recria uma isolada para esta conexão própria.
    with SessionRaw(bind=test_engine) as sessao_setup:
        nova_empresa = _criar_empresa(sessao_setup)
        empresa_id = nova_empresa.id
        sessao_setup.commit()

    try:
        with SessionRaw(bind=test_engine) as sessao:
            gerar_proxima_referencia(sessao, empresa_id=empresa_id, tipo_entidade="departamento", ano=2026)
            sessao.rollback()

        with SessionRaw(bind=test_engine) as sessao:
            depois = gerar_proxima_referencia(
                sessao, empresa_id=empresa_id, tipo_entidade="departamento", ano=2026
            )
            sessao.commit()

        # O primeiro número foi desfeito pelo rollback, então o próximo ainda é o 1.
        assert depois.sequencial_referencia == 1
    finally:
        with SessionRaw(bind=test_engine) as limpeza:
            limpeza.execute(
                text("DELETE FROM sequencias_referencia WHERE empresa_id = :e"), {"e": empresa_id}
            )
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
            limpeza.commit()


def test_concorrencia_nao_gera_codigo_duplicado(test_engine, empresa) -> None:
    """Duas transações concorrentes no mesmo escopo têm de receber números distintos.

    Concorrência real contra o Postgres de teste: threads com conexões próprias, cada uma
    commitando. O ON CONFLICT ... DO UPDATE serializa pelo lock da linha do contador.
    """
    from sqlalchemy.orm import Session as SessionRaw

    with SessionRaw(bind=test_engine) as sessao_setup:
        nova_empresa = _criar_empresa(sessao_setup)
        empresa_id = nova_empresa.id
        sessao_setup.commit()

    total = 8
    obtidos: list[int] = []
    trava = threading.Lock()
    barreira = threading.Barrier(total)

    def reservar() -> None:
        with SessionRaw(bind=test_engine) as sessao:
            barreira.wait()  # maximiza a chance de colisão real
            referencia = gerar_proxima_referencia(
                sessao, empresa_id=empresa_id, tipo_entidade="departamento", ano=2026
            )
            sessao.commit()
        with trava:
            obtidos.append(referencia.sequencial_referencia)

    threads = [threading.Thread(target=reservar) for _ in range(total)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sorted(obtidos) == list(range(1, total + 1)), f"sequenciais duplicados/faltando: {obtidos}"
    finally:
        with SessionRaw(bind=test_engine) as limpeza:
            limpeza.execute(
                text("DELETE FROM sequencias_referencia WHERE empresa_id = :e"), {"e": empresa_id}
            )
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
            limpeza.commit()
