"""Primeira resposta do SLA via primeiro comentário da equipe (Fase 2G.6D2B).

Definição V1 aprovada no relatório da 2G.6D2A: primeiro comentário da equipe (não visível ao
cliente — essa distinção não existe no domínio ainda). Cobre fixação idempotente,
concorrência, indicador derivado `slaPrimeiraRespostaDentroPrazo`, atomicidade e ausência de
backfill. Não cobre resolução (`sla_resolvido_em`) nem pausa — fora do escopo desta fase."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_comentario import DemandaComentario
from app.models.empresa import Empresa
from app.models.sla_regra import SlaRegra
from app.repositories.demanda_repository import DemandaRepository
from app.services.demanda_comentario_service import DemandaComentarioService

# --------------------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------------------


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_comentario(client: TestClient, demanda_id: str, texto: str = "Primeira resposta da equipe") -> dict:
    resposta = client.post(f"/demandas/{demanda_id}/comentarios", json={"texto": texto})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _ler_demanda(client: TestClient, demanda_id: str) -> dict:
    resposta = client.get(f"/demandas/{demanda_id}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


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


def _parse(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


# --------------------------------------------------------------------------------------
# A-C: idempotência
# --------------------------------------------------------------------------------------


def test_a_primeiro_comentario_fixa_primeira_resposta(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    assert demanda["slaPrimeiraRespostaEm"] is None

    antes = datetime.now(timezone.utc)
    _criar_comentario(client_admin, demanda["id"])
    depois = datetime.now(timezone.utc)

    lida = _ler_demanda(client_admin, demanda["id"])
    assert lida["slaPrimeiraRespostaEm"] is not None
    assert antes <= _parse(lida["slaPrimeiraRespostaEm"]) <= depois


def test_b_segundo_comentario_nao_sobrescreve(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _criar_comentario(client_admin, demanda["id"], "Primeiro")
    primeira = _ler_demanda(client_admin, demanda["id"])["slaPrimeiraRespostaEm"]

    _criar_comentario(client_admin, demanda["id"], "Segundo")
    depois_do_segundo = _ler_demanda(client_admin, demanda["id"])["slaPrimeiraRespostaEm"]

    assert depois_do_segundo == primeira


def test_c_terceiro_comentario_nao_sobrescreve(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _criar_comentario(client_admin, demanda["id"], "Primeiro")
    primeira = _ler_demanda(client_admin, demanda["id"])["slaPrimeiraRespostaEm"]
    _criar_comentario(client_admin, demanda["id"], "Segundo")
    _criar_comentario(client_admin, demanda["id"], "Terceiro")

    final = _ler_demanda(client_admin, demanda["id"])["slaPrimeiraRespostaEm"]
    assert final == primeira


# --------------------------------------------------------------------------------------
# D-H: indicador derivado slaPrimeiraRespostaDentroPrazo
# --------------------------------------------------------------------------------------


def test_d_antes_do_prazo_e_dentro(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    demanda_dict = _criar_demanda(client_admin)
    demanda = db_session.get(Demanda, demanda_dict["id"])
    demanda.sla_primeira_resposta_limite_em = datetime.now(timezone.utc) + timedelta(hours=10)
    db_session.add(demanda)
    db_session.flush()

    _criar_comentario(client_admin, demanda_dict["id"])
    lida = _ler_demanda(client_admin, demanda_dict["id"])
    assert lida["slaPrimeiraRespostaDentroPrazo"] is True


def test_e_exatamente_no_limite_e_dentro(client_admin: TestClient, db_session: Session) -> None:
    demanda_dict = _criar_demanda(client_admin)
    _criar_comentario(client_admin, demanda_dict["id"])
    primeira_resposta_em = _parse(_ler_demanda(client_admin, demanda_dict["id"])["slaPrimeiraRespostaEm"])

    demanda = db_session.get(Demanda, demanda_dict["id"])
    demanda.sla_primeira_resposta_limite_em = primeira_resposta_em
    db_session.add(demanda)
    db_session.flush()

    lida = _ler_demanda(client_admin, demanda_dict["id"])
    assert lida["slaPrimeiraRespostaDentroPrazo"] is True


def test_f_depois_do_prazo_e_fora(client_admin: TestClient, db_session: Session) -> None:
    demanda_dict = _criar_demanda(client_admin)
    demanda = db_session.get(Demanda, demanda_dict["id"])
    demanda.sla_primeira_resposta_limite_em = datetime.now(timezone.utc) - timedelta(hours=10)
    db_session.add(demanda)
    db_session.flush()

    _criar_comentario(client_admin, demanda_dict["id"])
    lida = _ler_demanda(client_admin, demanda_dict["id"])
    assert lida["slaPrimeiraRespostaDentroPrazo"] is False


def test_g_sem_limite_e_indeterminado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)  # sem SlaRegra -> limite fica None
    _criar_comentario(client_admin, demanda["id"])
    lida = _ler_demanda(client_admin, demanda["id"])
    assert lida["slaPrimeiraRespostaLimiteEm"] is None
    assert lida["slaPrimeiraRespostaEm"] is not None
    assert lida["slaPrimeiraRespostaDentroPrazo"] is None


def test_h_sem_primeira_resposta_e_indeterminado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    lida = _ler_demanda(client_admin, demanda["id"])
    assert lida["slaPrimeiraRespostaEm"] is None
    assert lida["slaPrimeiraRespostaDentroPrazo"] is None


# --------------------------------------------------------------------------------------
# I-J: sem SLA / Demanda antiga
# --------------------------------------------------------------------------------------


def test_i_demanda_sem_sla_grava_primeira_resposta_mesmo_assim(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    assert demanda["slaRegraId"] is None
    _criar_comentario(client_admin, demanda["id"])
    lida = _ler_demanda(client_admin, demanda["id"])
    assert lida["slaPrimeiraRespostaEm"] is not None


def test_j_demanda_antiga_sem_nenhum_campo_sla_grava_normalmente(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Simula uma Demanda anterior à 2G.6D1/2G.6D2B: inserida direto via ORM, todos os campos
    de SLA NULL (como uma linha que já existia antes das migrations resolverem qualquer
    coisa)."""
    agora = datetime.now(timezone.utc)
    demanda_antiga = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_referencia=f"T99{uuid.uuid4().hex[:6]}",
        ano_referencia=99,
        sequencial_referencia=1,
        numero_operacional=999901,
        nome="Demanda antiga",
        status="rascunho",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(demanda_antiga)
    db_session.flush()

    resposta = client_admin.post(
        f"/demandas/{demanda_antiga.id}/comentarios", json={"texto": "Primeiro comentário pós-deploy"}
    )
    assert resposta.status_code == 201, resposta.text

    lida = _ler_demanda(client_admin, demanda_antiga.id)
    assert lida["slaPrimeiraRespostaEm"] is not None
    assert lida["slaPrimeiraRespostaDentroPrazo"] is None


# --------------------------------------------------------------------------------------
# K-L: imutabilidade após regra alterada/arquivada
# --------------------------------------------------------------------------------------


def test_k_regra_alterada_depois_nao_muda_primeira_resposta(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    regra = _sla_regra(db_session, empresa)
    demanda = _criar_demanda(client_admin)
    _criar_comentario(client_admin, demanda["id"])
    primeira_resposta_antes = _ler_demanda(client_admin, demanda["id"])["slaPrimeiraRespostaEm"]

    regra.prazo_resolucao_quantidade = 999
    db_session.add(regra)
    db_session.flush()

    depois = _ler_demanda(client_admin, demanda["id"])
    assert depois["slaPrimeiraRespostaEm"] == primeira_resposta_antes


def test_l_regra_arquivada_depois_nao_muda_primeira_resposta(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    regra = _sla_regra(db_session, empresa)
    demanda = _criar_demanda(client_admin)
    _criar_comentario(client_admin, demanda["id"])
    primeira_resposta_antes = _ler_demanda(client_admin, demanda["id"])["slaPrimeiraRespostaEm"]

    regra.status = "arquivado"
    db_session.add(regra)
    db_session.flush()

    depois = _ler_demanda(client_admin, demanda["id"])
    assert depois["slaPrimeiraRespostaEm"] == primeira_resposta_antes


# --------------------------------------------------------------------------------------
# M-N: PATCH e write protection
# --------------------------------------------------------------------------------------


def test_m_patch_nao_altera_primeira_resposta(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin, prioridade="baixa")
    _criar_comentario(client_admin, demanda["id"])
    antes = _ler_demanda(client_admin, demanda["id"])["slaPrimeiraRespostaEm"]

    editada = client_admin.patch(f"/demandas/{demanda['id']}", json={"prioridade": "alta"})
    assert editada.status_code == 200, editada.text
    assert editada.json()["slaPrimeiraRespostaEm"] == antes


def test_n_payload_create_com_primeira_resposta_rejeitado_422(client_admin: TestClient) -> None:
    resposta = client_admin.post(
        "/demandas",
        json={"nome": "x", "slaPrimeiraRespostaEm": "2030-01-01T00:00:00Z"},
    )
    assert resposta.status_code == 422, resposta.text


def test_n_payload_update_com_dentro_prazo_rejeitado_422(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}", json={"slaPrimeiraRespostaDentroPrazo": True}
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# O: cross-tenant
# --------------------------------------------------------------------------------------


def test_o_comentario_de_outra_empresa_nao_e_aceito(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    agora = datetime.now(timezone.utc)
    demanda_outra = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_referencia=f"T98{uuid.uuid4().hex[:6]}",
        ano_referencia=98,
        sequencial_referencia=1,
        numero_operacional=999902,
        nome="Demanda de outra empresa",
        status="rascunho",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(demanda_outra)
    db_session.flush()

    resposta = client_admin.post(
        f"/demandas/{demanda_outra.id}/comentarios", json={"texto": "não deveria funcionar"}
    )
    assert resposta.status_code == 404, resposta.text


def test_o_update_condicional_repository_respeita_empresa_id(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    """Defesa em profundidade: mesmo chamado diretamente com o `empresa_id` errado, o
    `UPDATE` condicional nunca toca a linha (WHERE inclui empresa_id, não só o id)."""
    agora = datetime.now(timezone.utc)
    demanda = Demanda(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"T97{uuid.uuid4().hex[:6]}",
        ano_referencia=97, sequencial_referencia=1, numero_operacional=999903, nome="Demanda",
        status="rascunho", prioridade="media", created_at=agora, updated_at=agora,
    )
    db_session.add(demanda)
    db_session.flush()

    fixou = DemandaRepository().fixar_primeira_resposta_se_vazia(
        db_session, demanda_id=demanda.id, empresa_id=outra_empresa.id, timestamp=agora
    )
    assert fixou is False
    db_session.refresh(demanda)
    assert demanda.sla_primeira_resposta_em is None


# --------------------------------------------------------------------------------------
# P: rollback atômico
# --------------------------------------------------------------------------------------


def test_p_falha_apos_fixar_reverte_comentario_e_primeira_resposta(
    db_session: Session, empresa: Empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.schemas.demanda_comentario import DemandaComentarioCreate
    from tests.fixtures.usuarios import _criar_usuario_com_credencial

    agora = datetime.now(timezone.utc)
    demanda = Demanda(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"T96{uuid.uuid4().hex[:6]}",
        ano_referencia=96, sequencial_referencia=1, numero_operacional=999904, nome="Demanda",
        status="rascunho", prioridade="media", created_at=agora, updated_at=agora,
    )
    db_session.add(demanda)
    db_session.flush()
    autor = _criar_usuario_com_credencial(
        db_session, empresa=empresa, perfil_base="operador", email_prefixo="autor-rollback"
    )
    # Commit real do setup (só estabelece um novo savepoint, sob join_transaction_mode) —
    # sem isto, o db.rollback() de dentro de criar_comentario (abaixo) desfaria também a
    # Demanda/autor criados aqui, porque nada teria fixado um checkpoint antes deles.
    db_session.commit()

    def _publish_event_quebrado(*args, **kwargs):
        raise RuntimeError("falha forçada — simula erro tardio após fixar primeira resposta")

    monkeypatch.setattr(DemandaComentarioService, "_publish_event", _publish_event_quebrado)

    with pytest.raises(RuntimeError):
        DemandaComentarioService().criar_comentario(
            db_session, demanda, DemandaComentarioCreate(texto="não deveria persistir"), autor=autor
        )

    contagem_comentarios = db_session.execute(
        select(DemandaComentario).where(DemandaComentario.demanda_id == demanda.id)
    ).scalars().all()
    assert contagem_comentarios == []

    # `db.rollback()` dentro de criar_comentario expira os objetos desta Session — recarregar
    # em vez de `refresh` num objeto que não está mais persistente nela.
    demanda_recarregada = db_session.get(Demanda, demanda.id)
    assert demanda_recarregada.sla_primeira_resposta_em is None


# --------------------------------------------------------------------------------------
# Q: concorrência — UPDATE condicional entre duas conexões reais independentes
# --------------------------------------------------------------------------------------


def test_q_concorrencia_apenas_uma_transacao_fixa_o_campo(test_engine: Engine) -> None:
    """Duas conexões reais e independentes ao mesmo banco de teste — não usa `db_session`
    (cujo rollback automático isolaria as duas "transações" uma da outra, tornando a
    concorrência impossível de observar). Cria e limpa seus próprios dados via commit real.

    Não reproduz o instante exato de bloqueio simultâneo de linha (isso exigiria threads
    reais); prova a garantia que importa: uma vez que a primeira conexão COMMITOU o valor, o
    `UPDATE ... WHERE sla_primeira_resposta_em IS NULL` de uma segunda conexão reavalia a
    condição contra o dado já commitado e não casa nenhuma linha — nunca sobrescreve. O
    bloqueio de linha sob concorrência real é garantia do próprio Postgres (MVCC/READ
    COMMITTED), não algo que esta suíte precise reproduzir via threads para confiar."""
    empresa_id = str(uuid.uuid4())
    demanda_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)

    conexao_setup = test_engine.connect()
    conexao_setup.execute(
        Empresa.__table__.insert().values(
            id=empresa_id, nome="Empresa Concorrencia", documento=None,
            codigo_interno=f"CONC-{uuid.uuid4().hex[:8]}".upper(), status="ativa",
            created_at=agora, updated_at=agora,
        )
    )
    conexao_setup.execute(
        Demanda.__table__.insert().values(
            id=demanda_id, empresa_id=empresa_id, codigo_referencia=f"T95{uuid.uuid4().hex[:6]}",
            ano_referencia=95, sequencial_referencia=1, numero_operacional=999905, nome="Demanda",
            status="rascunho", prioridade="media", created_at=agora, updated_at=agora,
        )
    )
    conexao_setup.commit()
    conexao_setup.close()

    try:
        timestamp_vencedor = agora.replace(microsecond=111111)
        conexao_a = test_engine.connect()
        resultado_a = conexao_a.execute(
            sa_update(Demanda)
            .where(
                Demanda.id == demanda_id,
                Demanda.empresa_id == empresa_id,
                Demanda.sla_primeira_resposta_em.is_(None),
            )
            .values(sla_primeira_resposta_em=timestamp_vencedor)
        )
        assert resultado_a.rowcount == 1
        conexao_a.commit()
        conexao_a.close()

        timestamp_perdedor = agora.replace(microsecond=222222)
        conexao_b = test_engine.connect()
        resultado_b = conexao_b.execute(
            sa_update(Demanda)
            .where(
                Demanda.id == demanda_id,
                Demanda.empresa_id == empresa_id,
                Demanda.sla_primeira_resposta_em.is_(None),
            )
            .values(sla_primeira_resposta_em=timestamp_perdedor)
        )
        assert resultado_b.rowcount == 0  # determinístico: já não há mais linha NULL pra casar
        conexao_b.commit()
        conexao_b.close()

        conexao_verificacao = test_engine.connect()
        valor_final = conexao_verificacao.execute(
            select(Demanda.sla_primeira_resposta_em).where(Demanda.id == demanda_id)
        ).scalar()
        conexao_verificacao.close()
        assert valor_final == timestamp_vencedor
        assert valor_final != timestamp_perdedor
    finally:
        conexao_limpeza = test_engine.connect()
        conexao_limpeza.execute(sa_delete(Demanda).where(Demanda.id == demanda_id))
        conexao_limpeza.execute(sa_delete(Empresa).where(Empresa.id == empresa_id))
        conexao_limpeza.commit()
        conexao_limpeza.close()


# --------------------------------------------------------------------------------------
# R: sem backfill de comentários anteriores
# --------------------------------------------------------------------------------------


def test_r_comentario_inserido_direto_no_banco_nao_fixa_primeira_resposta(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Simula um comentário que já existia ANTES desta fase — inserido direto via ORM, sem
    passar por `DemandaComentarioService.criar_comentario` (que é o único lugar que chama o
    UPDATE condicional). Confirma que não há varredura retroativa: o campo continua NULL até
    o PRÓXIMO comentário criado através do fluxo real."""
    demanda_dict = _criar_demanda(client_admin)
    agora = datetime.now(timezone.utc) - timedelta(days=30)
    comentario_antigo = DemandaComentario(
        id=str(uuid.uuid4()), demanda_id=demanda_dict["id"], autor_usuario_id=None,
        texto="Comentário anterior ao deploy desta fase", created_at=agora, updated_at=agora,
    )
    db_session.add(comentario_antigo)
    db_session.flush()

    lida_antes = _ler_demanda(client_admin, demanda_dict["id"])
    assert lida_antes["slaPrimeiraRespostaEm"] is None  # nenhum backfill do comentário antigo

    _criar_comentario(client_admin, demanda_dict["id"], "Primeiro comentário pós-deploy")
    lida_depois = _ler_demanda(client_admin, demanda_dict["id"])
    assert lida_depois["slaPrimeiraRespostaEm"] is not None
