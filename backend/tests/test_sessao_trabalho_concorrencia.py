"""C1 — Concorrência em SessaoTrabalho.open_session.

Duas requisições concorrentes para a MESMA chave lógica ((demanda_id, usuario_id) ou
(demanda_id, departamento_id)) podem executar `get_active_equivalent` (nenhuma ativa) antes
de qualquer uma commitar, e então colidir no INSERT contra o índice parcial único — sem
tratamento, a perdedora recebia `IntegrityError` não tratado (500). `open_session` agora
reexecuta a unidade inteira (relê ativa, encerra por substituição, cria a nova) dentro de um
SAVEPOINT (`db.begin_nested()`), até 2 tentativas, convergindo pra mesma semântica de duas
chamadas sequenciais — nunca 409, nunca "retorna a sessão do outro".

Os testes de corrida REAL usam duas/quatro `Session` independentes ligadas diretamente a
`test_engine` (nunca a fixture `db_session`, cujo isolamento por SAVEPOINT-de-teste tornaria a
concorrência real impossível de observar — mesmo racional de test_referencias.py e
test_demanda_primeira_resposta.py) e `threading.Barrier` pra maximizar a chance de colisão
real, sem `time.sleep`. Os testes do invariante do SAVEPOINT (que o Evento da "rota" sobrevive
ao rollback da tentativa perdedora) usam colisão determinística via monkeypatch — provar isso
por sorte de timing de thread seria frágil; a técnica aqui é exatamente a mesma classe de
`patch.object` com captura do método original ANTES do patch, já usada em test_financeiro_visualizar.py.
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
from app.services.sessao_trabalho_service import STATUS_ATIVA, STATUS_ENCERRADA, SessaoTrabalhoService

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


def test_abertura_sequencial_encerra_anterior_e_cria_nova(db_session: Session, empresa: Empresa) -> None:
    usuario = _criar_usuario(db_session, empresa.id)
    demanda_id = str(uuid.uuid4())
    servico = SessaoTrabalhoService()

    primeira = servico.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
    )
    segunda = servico.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
    )

    db_session.refresh(primeira)
    assert primeira.status == STATUS_ENCERRADA
    assert segunda.status == STATUS_ATIVA
    assert primeira.id != segunda.id


# --------------------------------------------------------------------------------------
# Corrida real — duas/quatro conexões independentes, threading.Barrier, sem sleep
# --------------------------------------------------------------------------------------


def test_duas_aberturas_concorrentes_por_usuario_nao_vazam_500_e_tenant_isolado(test_engine) -> None:
    """Duas empresas, cada uma com sua própria corrida (demanda_id, usuario_id) — prova ao
    mesmo tempo que a corrida não gera 500 e que a resolução de uma empresa não interfere na
    outra (nenhum lock/estado global entre requisições)."""
    with SessionRaw(bind=test_engine) as setup:
        empresa_a = _criar_empresa(setup)
        usuario_a = _criar_usuario(setup, empresa_a.id)
        empresa_b = _criar_empresa(setup)
        usuario_b = _criar_usuario(setup, empresa_b.id)
        empresa_a_id, usuario_a_id = empresa_a.id, usuario_a.id
        empresa_b_id, usuario_b_id = empresa_b.id, usuario_b.id
        setup.commit()

    demanda_a = str(uuid.uuid4())
    demanda_b = str(uuid.uuid4())
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
        threading.Thread(target=worker, args=(0, empresa_a_id, demanda_a, usuario_a_id)),
        threading.Thread(target=worker, args=(1, empresa_a_id, demanda_a, usuario_a_id)),
        threading.Thread(target=worker, args=(2, empresa_b_id, demanda_b, usuario_b_id)),
        threading.Thread(target=worker, args=(3, empresa_b_id, demanda_b, usuario_b_id)),
    ]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert erros == {}, f"pelo menos uma abertura concorrente explodiu: {erros}"
        assert len(resultados) == 4

        assert _contar_ativas(test_engine, demanda_id=demanda_a, usuario_id=usuario_a_id, departamento_id=None) == 1
        assert _contar_ativas(test_engine, demanda_id=demanda_b, usuario_id=usuario_b_id, departamento_id=None) == 1

        # Invariante de auditoria: TODA sessão criada pelas 4 tentativas aponta pra um Evento
        # que realmente existe — nenhum evento_inicio_id órfão, mesmo sob corrida real.
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
    """Força a 1ª tentativa a "não enxergar" uma sessão ativa que JÁ FOI commitada por outra
    conexão (fiel à janela real de corrida), garantindo IntegrityError na 1ª tentativa e
    provando que o Evento da "rota" (nesta mesma sessão, commit=False) sobrevive ao rollback
    do SAVEPOINT — não é um rollback da Session inteira."""
    with SessionRaw(bind=test_engine) as setup:
        empresa = _criar_empresa(setup)
        usuario = _criar_usuario(setup, empresa.id)
        empresa_id, usuario_id = empresa.id, usuario.id
        setup.commit()

    demanda_id = str(uuid.uuid4())

    try:
        # Sessão "vencedora": já ativa e commitada por outra conexão antes da nossa chamada.
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
        original_get_active = real_repo.get_active_equivalent
        chamadas = {"n": 0}

        def get_active_forcando_colisao_na_primeira(db, **kwargs):
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                return None  # finge não ver a sessão do "vencedor", já commitada
            return original_get_active(db, **kwargs)

        with SessionRaw(bind=test_engine) as nossa_sessao:
            evento_id = _criar_evento_sessao(
                nossa_sessao, empresa_id=empresa_id, demanda_id=demanda_id, usuario_id=usuario_id
            )
            with patch.object(real_repo, "get_active_equivalent", side_effect=get_active_forcando_colisao_na_primeira):
                nossa = SessaoTrabalhoService(repository=real_repo).open_session(
                    nossa_sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                    evento_inicio_id=evento_id, inicio_em=datetime.now(timezone.utc), usuario_id=usuario_id,
                )
            nossa_sessao.commit()
            nossa_id = nossa.id

        assert chamadas["n"] == 2, "a 1a tentativa precisa colidir e a 2a precisa de fato reler o estado"

        # O Evento desta chamada (equivalente ao que a rota cria com commit=False ANTES de
        # chamar open_session) sobrevive — não foi um rollback da Session inteira que o apagou.
        assert _evento_existe(test_engine, evento_id)
        assert _status_sessao(test_engine, nossa_id) == STATUS_ATIVA
        assert _status_sessao(test_engine, vencedor_id) == STATUS_ENCERRADA
        assert _contar_ativas(test_engine, demanda_id=demanda_id, usuario_id=usuario_id, departamento_id=None) == 1
    finally:
        _limpar(test_engine, empresa_ids=[empresa_id])


def test_segunda_colisao_consecutiva_propaga_sem_loop_infinito(test_engine) -> None:
    """Se a contenção persistir na 2a tentativa também, a exceção deve propagar — nunca um
    3o retry, nunca engolida silenciosamente."""
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
            SessaoTrabalhoService().open_session(
                vencedor_sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                evento_inicio_id=evento_vencedor_id, inicio_em=datetime.now(timezone.utc), usuario_id=usuario_id,
            )
            vencedor_sessao.commit()

        real_repo = SessaoTrabalhoRepository()
        chamadas = {"n": 0}

        def get_active_sempre_cego(db, **kwargs):
            chamadas["n"] += 1
            return None  # nunca "enxerga" a sessão ativa -> toda tentativa tenta o mesmo INSERT

        with SessionRaw(bind=test_engine) as nossa_sessao:
            evento_id = _criar_evento_sessao(
                nossa_sessao, empresa_id=empresa_id, demanda_id=demanda_id, usuario_id=usuario_id
            )
            with patch.object(real_repo, "get_active_equivalent", side_effect=get_active_sempre_cego):
                with pytest.raises(IntegrityError):
                    SessaoTrabalhoService(repository=real_repo).open_session(
                        nossa_sessao, empresa_id=empresa_id, demanda_id=demanda_id,
                        evento_inicio_id=evento_id, inicio_em=datetime.now(timezone.utc), usuario_id=usuario_id,
                    )

        assert chamadas["n"] == 2, "exatamente 2 tentativas — nunca mais, nunca menos"
    finally:
        _limpar(test_engine, empresa_ids=[empresa_id])
