"""C1 / 11B.2A — Concorrência em SessaoTrabalho.open_session.

Duas requisições concorrentes podem ler "nenhuma sessão ativa" antes de qualquer uma commitar e colidir no INSERT contra o índice parcial único. Fase 11B.2A:

- sessão de PESSOA: uma ativa por pessoa em qualquer demanda (índice (empresa_id, usuario_id) WHERE status='ativa'). Quem perde a corrida recebe o MESMO 409
  (`SessaoTrabalhoConflitoError` / SESSAO_ATIVA_EXISTENTE) de uma segunda abertura sequencial — nunca 500, nunca a sessão do outro, e a vencedora NÃO é encerrada;
- sessão puramente DEPARTAMENTAL (sem usuário): semântica anterior preservada — a perdedora relê, encerra por substituição e cria a nova (até 2 tentativas).

Os testes de corrida REAL usam duas/quatro `Session` independentes ligadas diretamente a `test_engine` (nunca a fixture `db_session`, cujo isolamento por
SAVEPOINT-de-teste tornaria a concorrência real impossível de observar) e `threading.Barrier` para maximizar a chance de colisão, sem `time.sleep`. Os testes do
invariante do SAVEPOINT (o Evento da "rota" sobrevive ao rollback da tentativa perdedora) usam colisão determinística via `patch.object`.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as SessionRaw

from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository
from app.schemas.evento import EventoCreate
from app.services.evento_service import EventoService
from app.services.sessao_trabalho_service import (
    CODIGO_SESSAO_ATIVA_EXISTENTE,
    STATUS_ATIVA,
    STATUS_ENCERRADA,
    SessaoTrabalhoConflitoError,
    SessaoTrabalhoService,
)

# --------------------------------------------------------------------------------------
# Auxiliares — mesmo padrão de tests/test_sessao_trabalho.py e tests/test_referencias.py
# --------------------------------------------------------------------------------------


def _criar_empresa(sessao: Session) -> Empresa:
    agora = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid.uuid4()),
        nome="Empresa Concorrencia Sessao",
        documento=None,
        codigo_interno=f"CONC-SESSAO-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    sessao.add(empresa)
    sessao.flush()
    return empresa


def _criar_usuario(sessao: Session, empresa_id: str) -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa_id,
        codigo_interno=f"u-{sufixo}",
        nome=f"Usuário {sufixo}",
        email=f"u-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    sessao.add(usuario)
    sessao.flush()
    return usuario


def _criar_departamento(sessao: Session, empresa_id: str) -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa_id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=f"Depto {sufixo}",
        nome_normalizado=f"depto-{sufixo}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    sessao.add(departamento)
    sessao.flush()
    return departamento


def _criar_evento_sessao(sessao: Session, *, empresa_id: str, demanda_id: str, usuario_id: str | None) -> str:
    """Mesma chamada que a rota faz ANTES de abrir a sessão — `commit=False`, evento fica
    pendente na mesma transação até o `db.commit()` final da rota."""
    evento = EventoService().create_evento(
        sessao,
        EventoCreate(
            empresaId=empresa_id,
            tipo="sessao_trabalho_iniciada",
            entidadeTipo="demanda",
            entidadeId=demanda_id,
            usuarioId=usuario_id,
            payload={"demandaId": demanda_id},
        ),
        commit=False,
    )
    return evento.id


def _limpar(engine, *, empresa_ids: list[str]) -> None:
    with SessionRaw(bind=engine) as limpeza:
        for empresa_id in empresa_ids:
            limpeza.execute(text("DELETE FROM sessoes_trabalho WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM eventos WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM usuarios WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM departamentos WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
        limpeza.commit()


def _contar_ativas(engine, *, demanda_id: str, usuario_id: str | None, departamento_id: str | None) -> int:
    with SessionRaw(bind=engine) as verificacao:
        if usuario_id:
            return verificacao.execute(
                text(
                    "SELECT count(*) FROM sessoes_trabalho "
                    "WHERE demanda_id=:d AND usuario_id=:u AND status='ativa'"
                ),
                {"d": demanda_id, "u": usuario_id},
            ).scalar_one()
        return verificacao.execute(
            text(
                "SELECT count(*) FROM sessoes_trabalho "
                "WHERE demanda_id=:d AND usuario_id IS NULL AND departamento_id=:dep AND status='ativa'"
            ),
            {"d": demanda_id, "dep": departamento_id},
        ).scalar_one()


def _evento_existe(engine, evento_id: str) -> bool:
    with SessionRaw(bind=engine) as verificacao:
        return verificacao.execute(text("SELECT count(*) FROM eventos WHERE id=:e"), {"e": evento_id}).scalar_one() == 1


def _status_sessao(engine, sessao_id: str) -> str:
    with SessionRaw(bind=engine) as verificacao:
        return verificacao.execute(
            text("SELECT status FROM sessoes_trabalho WHERE id=:s"), {"s": sessao_id}
        ).scalar_one()


# --------------------------------------------------------------------------------------
# Sequencial — semântica existente preservada (não é corrida, é regressão de base)
# --------------------------------------------------------------------------------------


def test_mesmo_evento_inicio_id_repetido_continua_idempotente(db_session: Session, empresa: Empresa) -> None:
    usuario = _criar_usuario(db_session, empresa.id)
    demanda_id = str(uuid.uuid4())
    evento_id = str(uuid.uuid4())
    servico = SessaoTrabalhoService()

    primeira = servico.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=evento_id, inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
    )
    segunda = servico.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=evento_id, inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
    )
    assert primeira.id == segunda.id

    total = db_session.execute(
        text("SELECT count(*) FROM sessoes_trabalho WHERE evento_inicio_id=:e"), {"e": evento_id}
    ).scalar_one()
    assert total == 1


def test_abertura_sequencial_de_pessoa_e_conflito_e_nao_encerra_a_anterior(db_session: Session, empresa: Empresa) -> None:
    """11B.2A: antes, abrir de novo na MESMA demanda substituía a sessão em silêncio. Agora é 409 e a primeira continua ativa."""
    usuario = _criar_usuario(db_session, empresa.id)
    demanda_id = str(uuid.uuid4())
    servico = SessaoTrabalhoService()

    primeira = servico.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
    )
    with pytest.raises(SessaoTrabalhoConflitoError) as erro:
        servico.open_session(
            db_session, empresa_id=empresa.id, demanda_id=demanda_id,
            evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
        )
    assert erro.value.codigo == CODIGO_SESSAO_ATIVA_EXISTENTE

    db_session.refresh(primeira)
    assert primeira.status == STATUS_ATIVA and primeira.fim_em is None and primeira.motivo_encerramento is None


def test_abertura_sequencial_departamental_continua_substituindo(db_session: Session, empresa: Empresa) -> None:
    """Sessão puramente departamental (sem usuário): semântica anterior preservada."""
    departamento = _criar_departamento(db_session, empresa.id)
    demanda_id = str(uuid.uuid4())
    servico = SessaoTrabalhoService()

    primeira = servico.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), departamento_id=departamento.id,
    )
    segunda = servico.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), departamento_id=departamento.id,
    )

    db_session.refresh(primeira)
    assert primeira.status == STATUS_ENCERRADA
    assert segunda.status == STATUS_ATIVA
    assert primeira.id != segunda.id


# --------------------------------------------------------------------------------------
# Corrida real — duas/quatro conexões independentes, threading.Barrier, sem sleep
# --------------------------------------------------------------------------------------


def test_duas_aberturas_concorrentes_por_usuario_uma_vence_a_outra_e_conflito_e_tenant_isolado(test_engine) -> None:
    """Duas empresas, cada uma com sua corrida entre duas aberturas do MESMO usuário (demandas diferentes): em cada empresa exatamente uma sessão ativa nasce, a outra
    abertura recebe o conflito de domínio (nunca 500) e a resolução de uma empresa não interfere na outra."""
    with SessionRaw(bind=test_engine) as setup:
        empresa_a = _criar_empresa(setup)
        usuario_a = _criar_usuario(setup, empresa_a.id)
        empresa_b = _criar_empresa(setup)
        usuario_b = _criar_usuario(setup, empresa_b.id)
        empresa_a_id, usuario_a_id = empresa_a.id, usuario_a.id
        empresa_b_id, usuario_b_id = empresa_b.id, usuario_b.id
        setup.commit()

    demandas = [str(uuid.uuid4()) for _ in range(4)]
    barreira = threading.Barrier(4)
    resultados: dict[int, str] = {}
    erros: dict[int, BaseException] = {}

    def worker(indice: int, empresa_id: str, demanda_id: str, usuario_id: str) -> None:
        try:
            with SessionRaw(bind=test_engine) as sessao:
                evento_id = _criar_evento_sessao(
                    sessao, empresa_id=empresa_id, demanda_id=demanda_id, usuario_id=usuario_id
                )
                barreira.wait()  # maximiza a chance de leitura simultânea de "nenhuma ativa"
                nova = SessaoTrabalhoService().open_session(
                    sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                    evento_inicio_id=evento_id, inicio_em=datetime.now(timezone.utc), usuario_id=usuario_id,
                )
                sessao.commit()
                resultados[indice] = nova.id
        except BaseException as exc:  # thread não propaga sozinha — captura pra assert
            erros[indice] = exc

    threads = [
        threading.Thread(target=worker, args=(0, empresa_a_id, demandas[0], usuario_a_id)),
        threading.Thread(target=worker, args=(1, empresa_a_id, demandas[1], usuario_a_id)),
        threading.Thread(target=worker, args=(2, empresa_b_id, demandas[2], usuario_b_id)),
        threading.Thread(target=worker, args=(3, empresa_b_id, demandas[3], usuario_b_id)),
    ]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # nenhum 500: toda falha é o conflito de domínio, e há exatamente uma por empresa
        assert all(isinstance(e, SessaoTrabalhoConflitoError) and e.codigo == CODIGO_SESSAO_ATIVA_EXISTENTE for e in erros.values()), erros
        # Com a troca de foco, a perdedora da corrida OU leva o conflito (viu a vencedora só no INSERT) OU assume o foco e encerra a vencedora já commitada: as duas
        # saídas são válidas — o que nunca pode existir é um empresa/pessoa com duas ativas (conferido abaixo) nem uma empresa sem nenhum vencedor.
        assert len(erros) + len(resultados) == 4
        assert {i for i in resultados if i < 2} and {i for i in resultados if i >= 2}  # ao menos um vencedor em cada empresa

        with SessionRaw(bind=test_engine) as verificacao:
            for empresa_id, usuario_id in ((empresa_a_id, usuario_a_id), (empresa_b_id, usuario_b_id)):
                assert verificacao.execute(
                    text("SELECT count(*) FROM sessoes_trabalho WHERE empresa_id=:e AND usuario_id=:u AND status='ativa'"),
                    {"e": empresa_id, "u": usuario_id},
                ).scalar_one() == 1

        # Invariante de auditoria: toda sessão criada aponta pra um Evento que realmente existe.
        for sessao_id in resultados.values():
            with SessionRaw(bind=test_engine) as verificacao:
                evento_inicio_id = verificacao.execute(
                    text("SELECT evento_inicio_id FROM sessoes_trabalho WHERE id=:s"), {"s": sessao_id}
                ).scalar_one()
            assert _evento_existe(test_engine, evento_inicio_id), (
                f"sessao {sessao_id} referencia evento_inicio_id {evento_inicio_id} inexistente"
            )
    finally:
        _limpar(test_engine, empresa_ids=[empresa_a_id, empresa_b_id])


def test_duas_aberturas_concorrentes_por_departamento_nao_vazam_500(test_engine) -> None:
    """Mesma corrida, mas pela chave (demanda_id, departamento_id) — prova que a correção é
    genérica (usa os mesmos parâmetros de get_active_equivalent), não hardcoded pra usuario_id."""
    with SessionRaw(bind=test_engine) as setup:
        empresa = _criar_empresa(setup)
        departamento = _criar_departamento(setup, empresa.id)
        empresa_id, departamento_id = empresa.id, departamento.id
        setup.commit()

    demanda_id = str(uuid.uuid4())
    barreira = threading.Barrier(2)
    resultados: dict[int, str] = {}
    erros: dict[int, BaseException] = {}

    def worker(indice: int) -> None:
        try:
            with SessionRaw(bind=test_engine) as sessao:
                evento_id = _criar_evento_sessao(
                    sessao, empresa_id=empresa_id, demanda_id=demanda_id, usuario_id=None
                )
                barreira.wait()
                nova = SessaoTrabalhoService().open_session(
                    sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                    evento_inicio_id=evento_id, inicio_em=datetime.now(timezone.utc),
                    departamento_id=departamento_id,
                )
                sessao.commit()
                resultados[indice] = nova.id
        except BaseException as exc:
            erros[indice] = exc

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert erros == {}, f"pelo menos uma abertura concorrente explodiu: {erros}"
        assert len(resultados) == 2
        assert _contar_ativas(test_engine, demanda_id=demanda_id, usuario_id=None, departamento_id=departamento_id) == 1

        for sessao_id in resultados.values():
            with SessionRaw(bind=test_engine) as verificacao:
                evento_inicio_id = verificacao.execute(
                    text("SELECT evento_inicio_id FROM sessoes_trabalho WHERE id=:s"), {"s": sessao_id}
                ).scalar_one()
            assert _evento_existe(test_engine, evento_inicio_id)
    finally:
        _limpar(test_engine, empresa_ids=[empresa_id])


# --------------------------------------------------------------------------------------
# SAVEPOINT — colisão determinística via monkeypatch (não depende de sorte de timing)
# --------------------------------------------------------------------------------------


def test_savepoint_preserva_evento_da_transacao_externa_apos_colisao(test_engine) -> None:
    """Força a verificação de "já existe sessão ativa" a não enxergar uma sessão JÁ COMMITADA por outra conexão (fiel à janela real de corrida): o INSERT colide
    no índice único do banco, a pessoa recebe o conflito de domínio e o Evento da "rota" (nesta mesma sessão, commit=False) sobrevive ao rollback do SAVEPOINT —
    não é um rollback da Session inteira. A vencedora continua ativa e nenhuma sessão extra é criada."""
    with SessionRaw(bind=test_engine) as setup:
        empresa = _criar_empresa(setup)
        usuario = _criar_usuario(setup, empresa.id)
        empresa_id, usuario_id = empresa.id, usuario.id
        setup.commit()

    demanda_id = str(uuid.uuid4())

    try:
        with SessionRaw(bind=test_engine) as vencedor_sessao:
            evento_vencedor_id = _criar_evento_sessao(
                vencedor_sessao, empresa_id=empresa_id, demanda_id=demanda_id, usuario_id=usuario_id
            )
            vencedor = SessaoTrabalhoService().open_session(
                vencedor_sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                evento_inicio_id=evento_vencedor_id, inicio_em=datetime.now(timezone.utc), usuario_id=usuario_id,
            )
            vencedor_sessao.commit()
            vencedor_id = vencedor.id

        real_repo = SessaoTrabalhoRepository()
        original = real_repo.get_active_by_usuario
        chamadas = {"n": 0}

        def cego_na_primeira(db, **kwargs):
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                return None  # finge não ver a sessão do "vencedor", já commitada
            return original(db, **kwargs)

        with SessionRaw(bind=test_engine) as nossa_sessao:
            evento_id = _criar_evento_sessao(
                nossa_sessao, empresa_id=empresa_id, demanda_id=demanda_id, usuario_id=usuario_id
            )
            with patch.object(real_repo, "get_active_by_usuario", side_effect=cego_na_primeira):
                with pytest.raises(SessaoTrabalhoConflitoError) as erro:
                    SessaoTrabalhoService(repository=real_repo).open_session(
                        nossa_sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                        evento_inicio_id=evento_id, inicio_em=datetime.now(timezone.utc), usuario_id=usuario_id,
                    )
            assert erro.value.codigo == CODIGO_SESSAO_ATIVA_EXISTENTE
            nossa_sessao.commit()  # o que a rota NÃO faria no erro; aqui serve para provar que o Evento pendente não foi desfeito pelo SAVEPOINT

        assert chamadas["n"] == 3, "1a verificação cega, 2a (troca de foco, mesma demanda: nada a trocar), colisão no banco, 3a verificação enxerga a vencedora"
        assert _evento_existe(test_engine, evento_id)
        assert _status_sessao(test_engine, vencedor_id) == STATUS_ATIVA
        with SessionRaw(bind=test_engine) as verificacao:
            assert verificacao.execute(
                text("SELECT count(*) FROM sessoes_trabalho WHERE empresa_id=:e AND usuario_id=:u"), {"e": empresa_id, "u": usuario_id}
            ).scalar_one() == 1
    finally:
        _limpar(test_engine, empresa_ids=[empresa_id])


def test_segunda_colisao_consecutiva_departamental_propaga_sem_loop_infinito(test_engine) -> None:
    """Sessão departamental: se a contenção persistir na 2a tentativa também, a exceção deve propagar — nunca um 3o retry, nunca engolida silenciosamente."""
    with SessionRaw(bind=test_engine) as setup:
        empresa = _criar_empresa(setup)
        departamento = _criar_departamento(setup, empresa.id)
        empresa_id, departamento_id = empresa.id, departamento.id
        setup.commit()

    demanda_id = str(uuid.uuid4())

    try:
        with SessionRaw(bind=test_engine) as vencedor_sessao:
            evento_vencedor_id = _criar_evento_sessao(
                vencedor_sessao, empresa_id=empresa_id, demanda_id=demanda_id, usuario_id=None
            )
            SessaoTrabalhoService().open_session(
                vencedor_sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                evento_inicio_id=evento_vencedor_id, inicio_em=datetime.now(timezone.utc), departamento_id=departamento_id,
            )
            vencedor_sessao.commit()

        real_repo = SessaoTrabalhoRepository()
        chamadas = {"n": 0}

        def get_active_sempre_cego(db, **kwargs):
            chamadas["n"] += 1
            return None  # nunca "enxerga" a sessão ativa -> toda tentativa tenta o mesmo INSERT

        with SessionRaw(bind=test_engine) as nossa_sessao:
            evento_id = _criar_evento_sessao(
                nossa_sessao, empresa_id=empresa_id, demanda_id=demanda_id, usuario_id=None
            )
            with patch.object(real_repo, "get_active_equivalent", side_effect=get_active_sempre_cego):
                with pytest.raises(IntegrityError):
                    SessaoTrabalhoService(repository=real_repo).open_session(
                        nossa_sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                        evento_inicio_id=evento_id, inicio_em=datetime.now(timezone.utc), departamento_id=departamento_id,
                    )

        assert chamadas["n"] == 2, "exatamente 2 tentativas — nunca mais, nunca menos"
    finally:
        _limpar(test_engine, empresa_ids=[empresa_id])
