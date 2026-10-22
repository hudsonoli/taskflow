"""Foco único por PESSOA — troca direta de sessão (A → B) sem 409 e sem tocar o status da Demanda nem as sessões de outros responsáveis.

Regra de produto: uma pessoa nunca trabalha ativamente em duas tarefas ao mesmo tempo. É regra POR USUÁRIO: não limita a empresa a uma Demanda em execução e não pausa uma Demanda
com vários responsáveis só porque um deles trocou de foco (o status da Demanda continua separado do foco pessoal).
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session as SessionRaw
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository
from app.services.sessao_trabalho_service import SessaoTrabalhoService
from tests.test_demanda import dentro_do_expediente  # noqa: F401  (fixture)
from tests.test_sessao_trabalho_integridade import (  # noqa: F401  (fixture `operadores`)
    _abrir,
    _abrir_ok,
    _demanda,
    _eventos_fim,
    _patch,
    _sessao,
    _sessoes,
    operadores,
)


@pytest.fixture(autouse=True)
def _expediente_aberto(dentro_do_expediente) -> None:  # noqa: F811
    """Abrir sessão exige a demanda EM EXECUÇÃO; entrar em execução respeita o expediente."""


def _ativas_da_pessoa(db: Session, usuario_id: str) -> list[SessaoTrabalho]:
    db.expire_all()
    return list(db.scalars(select(SessaoTrabalho).where(SessaoTrabalho.usuario_id == usuario_id, SessaoTrabalho.status == "ativa")).all())


def _status_demanda(db: Session, demanda_id: str) -> str:
    db.expire_all()
    return db.get(Demanda, demanda_id).status


def test_sem_sessao_ativa_abre_normalmente(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    b = _demanda(client_admin)
    resposta = _abrir(client_admin, b["id"], usuario_operador.id)
    assert resposta.status_code == 201
    assert [s.status for s in _sessoes(db_session, b["id"])] == ["ativa"]
    assert _eventos_fim(db_session, b["id"]) == []


def test_troca_encerra_a_anterior_abre_a_nova_e_registra_o_evento_automatico(
    db_session: Session, client_admin: TestClient, usuario_operador: Usuario
) -> None:
    a, b = _demanda(client_admin), _demanda(client_admin)
    sessao_a = _abrir_ok(client_admin, a["id"], usuario_operador.id)
    nova = _abrir_ok(client_admin, b["id"], usuario_operador.id)

    antiga = _sessao(db_session, sessao_a["id"])
    assert antiga.status == "encerrada" and antiga.motivo_encerramento == "substituicao_sessao_ativa"
    assert _sessao(db_session, nova["id"]).status == "ativa"
    (evento,) = _eventos_fim(db_session, a["id"])
    assert evento.id == antiga.evento_fim_id and evento.usuario_id == usuario_operador.id
    assert evento.payload["motivoEncerramento"] == "substituicao_sessao_ativa"
    assert evento.payload["automatico"] is True and evento.payload["substituidaPorDemandaId"] == b["id"]
    # a Demanda anterior NÃO é pausada: o status dela é separado do foco pessoal
    assert _status_demanda(db_session, a["id"]) == "em_execucao"


def test_nunca_existem_duas_sessoes_abertas_numa_sequencia_de_trocas(
    db_session: Session, client_admin: TestClient, usuario_operador: Usuario
) -> None:
    demandas = [_demanda(client_admin) for _ in range(3)]
    for alvo in (0, 1, 2, 0, 2, 1):
        _abrir_ok(client_admin, demandas[alvo]["id"], usuario_operador.id)
        ativas = _ativas_da_pessoa(db_session, usuario_operador.id)
        assert len(ativas) == 1 and ativas[0].demanda_id == demandas[alvo]["id"]


def test_reabrir_na_mesma_demanda_continua_sendo_conflito(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    a = _demanda(client_admin)
    primeira = _abrir_ok(client_admin, a["id"], usuario_operador.id)
    resposta = _abrir(client_admin, a["id"], usuario_operador.id)
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "SESSAO_ATIVA_EXISTENTE"
    assert _sessao(db_session, primeira["id"]).status == "ativa"


def test_multi_responsaveis_a_troca_de_um_nao_interrompe_o_outro_nem_pausa_a_demanda(
    db_session: Session, client_admin: TestClient, operadores: list[Usuario]
) -> None:
    hudson, joao = operadores[0], operadores[1]
    a, b = _demanda(client_admin), _demanda(client_admin)
    sessao_hudson = _abrir_ok(client_admin, a["id"], hudson.id)
    sessao_joao = _abrir_ok(client_admin, a["id"], joao.id)

    _abrir_ok(client_admin, b["id"], hudson.id)

    assert _sessao(db_session, sessao_hudson["id"]).status == "encerrada"
    assert _sessao(db_session, sessao_joao["id"]).status == "ativa"  # João continua trabalhando em A
    assert _status_demanda(db_session, a["id"]) == "em_execucao"
    assert len(_ativas_da_pessoa(db_session, hudson.id)) == 1 and len(_ativas_da_pessoa(db_session, joao.id)) == 1


def test_demanda_destino_invalida_nao_encerra_a_sessao_atual(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    a = _demanda(client_admin)
    pausada = _demanda(client_admin)
    _patch(client_admin, pausada["id"], status="pausada")
    sessao_a = _abrir_ok(client_admin, a["id"], usuario_operador.id)

    resposta = _abrir(client_admin, pausada["id"], usuario_operador.id)
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "DEMANDA_NAO_EXECUTAVEL"
    assert _sessao(db_session, sessao_a["id"]).status == "ativa"  # a validação roda ANTES de qualquer encerramento
    assert _eventos_fim(db_session, a["id"]) == []


def test_falha_ao_gravar_a_nova_desfaz_o_encerramento_da_anterior(
    db_session: Session, client_admin: TestClient, usuario_operador: Usuario, empresa, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Atomicidade: fechar A + abrir B é uma operação só. Se gravar B falha depois de A já estar fechada na transação, o SAVEPOINT desfaz o fechamento — nunca zero sessões."""
    a = _demanda(client_admin)
    sessao_a = _abrir_ok(client_admin, a["id"], usuario_operador.id)
    repositorio = SessaoTrabalhoRepository()

    def quebra(*_args, **_kwargs):
        raise RuntimeError("falha simulada ao gravar a nova sessão")

    monkeypatch.setattr(repositorio, "create", quebra)
    servico = SessaoTrabalhoService(repository=repositorio)
    with pytest.raises(RuntimeError):
        servico.open_session(
            db_session, empresa_id=empresa.id, demanda_id=str(uuid.uuid4()), evento_inicio_id=str(uuid.uuid4()),
            inicio_em=datetime.now(timezone.utc), usuario_id=usuario_operador.id,
        )
    antiga = _sessao(db_session, sessao_a["id"])
    assert antiga.status == "ativa" and antiga.fim_em is None and antiga.motivo_encerramento is None


def test_intervalos_operacionais_nao_mudam_com_a_troca_de_foco(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    """Tempo OPERACIONAL (status da Demanda) ≠ tempo PESSOAL (sessões): trocar o foco não abre nem fecha intervalo de status."""
    a, b = _demanda(client_admin), _demanda(client_admin)
    _abrir_ok(client_admin, a["id"], usuario_operador.id)

    def intervalos() -> list[tuple]:
        return sorted(
            tuple(linha)
            for linha in db_session.execute(
                text("SELECT demanda_id, status, fim_em IS NULL FROM demanda_status_intervalos WHERE demanda_id IN (:a, :b)"), {"a": a["id"], "b": b["id"]}
            ).all()
        )

    antes = intervalos()
    _abrir_ok(client_admin, b["id"], usuario_operador.id)
    assert intervalos() == antes


def test_sessao_cancelada_nao_e_tocada_pela_troca(db_session: Session, client_admin: TestClient, usuario_operador: Usuario) -> None:
    a, b, c = _demanda(client_admin), _demanda(client_admin), _demanda(client_admin)
    cancelada = _abrir_ok(client_admin, a["id"], usuario_operador.id)
    registro = _sessao(db_session, cancelada["id"])
    registro.status, registro.fim_em, registro.duracao_segundos = "cancelada", registro.inicio_em, None
    db_session.flush()
    _abrir_ok(client_admin, b["id"], usuario_operador.id)
    _abrir_ok(client_admin, c["id"], usuario_operador.id)
    final = _sessao(db_session, cancelada["id"])
    assert final.status == "cancelada" and final.motivo_encerramento is None and final.duracao_segundos is None


def test_corrida_de_duas_trocas_deixa_exatamente_uma_sessao_ativa(test_engine) -> None:
    from tests.test_sessao_trabalho_concorrencia import _criar_empresa, _criar_evento_sessao, _criar_usuario, _limpar

    with SessionRaw(bind=test_engine) as setup:
        empresa = _criar_empresa(setup)
        usuario = _criar_usuario(setup, empresa.id)
        empresa_id, usuario_id = empresa.id, usuario.id
        setup.commit()
    demanda_a, demanda_b, demanda_c = (str(uuid.uuid4()) for _ in range(3))
    try:
        with SessionRaw(bind=test_engine) as inicial:
            evento = _criar_evento_sessao(inicial, empresa_id=empresa_id, demanda_id=demanda_a, usuario_id=usuario_id)
            SessaoTrabalhoService().open_session(
                inicial, empresa_id=empresa_id, demanda_id=demanda_a, evento_inicio_id=evento, inicio_em=datetime.now(timezone.utc), usuario_id=usuario_id
            )
            inicial.commit()

        barreira = threading.Barrier(2)
        erros: list[BaseException] = []

        def trocar(destino: str) -> None:
            try:
                with SessionRaw(bind=test_engine) as sessao:
                    evento_id = _criar_evento_sessao(sessao, empresa_id=empresa_id, demanda_id=destino, usuario_id=usuario_id)
                    barreira.wait()
                    SessaoTrabalhoService().open_session(
                        sessao, empresa_id=empresa_id, demanda_id=destino, evento_inicio_id=evento_id,
                        inicio_em=datetime.now(timezone.utc), usuario_id=usuario_id,
                    )
                    sessao.commit()
            except BaseException as exc:  # noqa: BLE001 — thread não propaga sozinha
                erros.append(exc)

        threads = [threading.Thread(target=trocar, args=(demanda_b,)), threading.Thread(target=trocar, args=(demanda_c,))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        from app.services.sessao_trabalho_service import SessaoTrabalhoConflitoError

        assert all(isinstance(e, SessaoTrabalhoConflitoError) for e in erros), erros  # nenhum 500: a perdedora, se houver, leva o conflito de domínio
        with SessionRaw(bind=test_engine) as verificacao:
            ativas = verificacao.execute(
                text("SELECT count(*) FROM sessoes_trabalho WHERE empresa_id=:e AND usuario_id=:u AND status='ativa'"), {"e": empresa_id, "u": usuario_id}
            ).scalar_one()
        assert ativas == 1  # o índice único parcial é a barreira final
    finally:
        _limpar(test_engine, empresa_ids=[empresa_id])
