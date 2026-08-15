"""SessaoTrabalho — invariantes pós-contract (migrations 0015–0018 concluídas).

## Por que este arquivo mudou

Até o contract (`0018`) esta suíte cobria o estado TRANSITÓRIO do expand/contract:
`usuario_id`/`departamento_id` (texto legado, `"user-1"`) coexistindo com
`usuario_uuid`/`departamento_uuid` (FK real) — backfill comprovável por `codigo_interno`,
escrita dupla nas duas colunas, e as guardas G1–G4 que `0018` executa antes de qualquer DROP
(G3, em particular, aceitando os dois formatos legítimos que uma linha podia ter: texto igual
ao `codigo_interno` do backfill, ou texto igual ao próprio UUID da escrita dupla).

`0018` removeu a coluna textual e renomeou `usuario_uuid`/`departamento_uuid` para os nomes
finais. As asserções antigas passariam a rodar contra colunas que não existem mais — não é
possível "manter" aquele teste: ele testava um estado transitório que acabou. As migrations
`0015`–`0018` continuam no repositório como história e rodam em qualquer banco novo pelo
`upgrade head` (a suíte já roda `alembic upgrade head` contra base vazia antes do primeiro
teste — é onde a sequência inteira é exercitada de verdade, mesmo padrão de
`test_migracao_departamento.py` para `usuarios.departamento_id`, `0007`–`0009`).

O que substitui aquela cobertura são as invariantes que **sobrevivem** ao contract: a FK, o
`ON DELETE SET NULL`, o escopo por empresa (guarda de cross-tenant, que a FK sozinha não
garante — ela garante existência, não que o registro é da mesma empresa) e o comportamento de
domínio (validação, escrita, leitura por UUID) que nunca dependeu da forma transitória do
schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository
from app.services.sessao_trabalho_service import (
    SessaoTrabalhoDepartamentoInvalidoError,
    SessaoTrabalhoService,
    SessaoTrabalhoUsuarioInvalidoError,
)
from tests.helpers.api import get

# Guarda de cross-tenant idêntica à que a migration 0018 executa antes do DROP — a FK garante
# existência, não que usuário/departamento pertence à mesma empresa da sessão.
SQL_GUARDA_CROSS_TENANT_USUARIO = text(
    """
    SELECT count(*) FROM sessoes_trabalho s
    JOIN usuarios u ON u.id = s.usuario_id
    WHERE u.empresa_id <> s.empresa_id
    """
)

SQL_GUARDA_CROSS_TENANT_DEPARTAMENTO = text(
    """
    SELECT count(*) FROM sessoes_trabalho s
    JOIN departamentos d ON d.id = s.departamento_id
    WHERE d.empresa_id <> s.empresa_id
    """
)

SQL_GUARDA_EMPRESA_ORFA = text(
    """
    SELECT count(*) FROM sessoes_trabalho s
    WHERE NOT EXISTS (SELECT 1 FROM empresas e WHERE e.id = s.empresa_id)
    """
)


# --------------------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------------------

def _usuario(db: Session, empresa: Empresa) -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"u-{sufixo}",
        nome=f"Usuário {sufixo}",
        email=f"u-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _departamento(db: Session, empresa: Empresa) -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
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
    db.add(departamento)
    db.flush()
    return departamento


def _sessao(
    db: Session,
    empresa: Empresa,
    *,
    usuario_id: str | None = None,
    departamento_id: str | None = None,
    status: str = "ativa",
    duracao_segundos: int | None = None,
) -> SessaoTrabalho:
    """Construída direto pelo ORM (sem passar pelo service) — usada nos testes de invariante
    de schema, onde o que importa é a constraint, não o fluxo de abertura de sessão.

    `status="encerrada"` preenche `fim_em`/`evento_fim_id`/`duracao_segundos` sozinha —
    `ck_sessoes_trabalho_encerrada_com_fim` exige os três não-nulos juntos; `duracao_segundos`
    é ajustável para os testes de agregado, default 0 quando só a presença da sessão importa.
    """
    agora = datetime.now(timezone.utc)
    encerrada = status == "encerrada"
    sessao = SessaoTrabalho(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        demanda_id=str(uuid.uuid4()),
        usuario_id=usuario_id,
        departamento_id=departamento_id,
        evento_inicio_id=str(uuid.uuid4()),
        evento_fim_id=str(uuid.uuid4()) if encerrada else None,
        status=status,
        created_at=agora,
        updated_at=agora,
        inicio_em=agora,
        fim_em=agora if encerrada else None,
        duracao_segundos=(duracao_segundos if duracao_segundos is not None else 0) if encerrada else None,
    )
    db.add(sessao)
    db.flush()
    return sessao


@pytest.fixture()
def service() -> SessaoTrabalhoService:
    return SessaoTrabalhoService()


def _client_para(app, usuario: Usuario) -> TestClient:
    """Cliente autenticado pra um usuário construído ad-hoc (Head, Atendimento não-Head) que
    não tem fixture própria em tests/fixtures/auth.py — mesmo padrão de token direto."""
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


# --------------------------------------------------------------------------------------
# Base vazia — as guardas são estruturais (roda em qualquer banco, inclusive o de teste)
# --------------------------------------------------------------------------------------

def test_base_vazia_nao_viola_guardas(db_session: Session) -> None:
    assert db_session.execute(SQL_GUARDA_CROSS_TENANT_USUARIO).scalar_one() == 0
    assert db_session.execute(SQL_GUARDA_CROSS_TENANT_DEPARTAMENTO).scalar_one() == 0
    assert db_session.execute(SQL_GUARDA_EMPRESA_ORFA).scalar_one() == 0


# --------------------------------------------------------------------------------------
# FK — órfão é impossível por construção (G1 da migration 0018, agora permanente)
# --------------------------------------------------------------------------------------

def test_fk_impede_usuario_orfao(db_session: Session, empresa: Empresa) -> None:
    sessao = _sessao(db_session, empresa)
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE sessoes_trabalho SET usuario_id = :u WHERE id = :i"),
            {"u": str(uuid.uuid4()), "i": sessao.id},
        )
        db_session.flush()


def test_fk_impede_departamento_orfao(db_session: Session, empresa: Empresa) -> None:
    sessao = _sessao(db_session, empresa)
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE sessoes_trabalho SET departamento_id = :d WHERE id = :i"),
            {"d": str(uuid.uuid4()), "i": sessao.id},
        )
        db_session.flush()


def test_fk_impede_empresa_orfa(db_session: Session, empresa: Empresa) -> None:
    sessao = _sessao(db_session, empresa)
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE sessoes_trabalho SET empresa_id = :e WHERE id = :i"),
            {"e": str(uuid.uuid4()), "i": sessao.id},
        )
        db_session.flush()


def test_on_delete_set_null_preserva_sessao(db_session: Session, empresa: Empresa) -> None:
    """Apagar um Usuário nunca pode apagar a sessão — só desfaz o vínculo. (Na prática
    Usuário é arquivado, nunca apagado — a garantia é do schema.)"""
    usuario = _usuario(db_session, empresa)
    sessao = _sessao(db_session, empresa, usuario_id=usuario.id)

    db_session.execute(text("DELETE FROM usuarios WHERE id = :u"), {"u": usuario.id})
    db_session.flush()
    db_session.expire_all()

    sobreviveu, vinculo = db_session.execute(
        text("SELECT count(*), max(usuario_id) FROM sessoes_trabalho WHERE id = :i"), {"i": sessao.id}
    ).one()
    assert sobreviveu == 1
    assert vinculo is None


# --------------------------------------------------------------------------------------
# Cross-tenant — a FK garante existência, não tenant (G2 da migration 0018, permanente)
# --------------------------------------------------------------------------------------

def test_guarda_cross_tenant_usuario(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    """Forjado por SQL cru de propósito — pelo service isso já é recusado (422, ver
    test_open_session_recusa_usuario_de_outra_empresa); só assim dá pra provar que a guarda
    enxergaria uma inconsistência vinda de fora."""
    alheio = _usuario(db_session, outra_empresa)
    sessao = _sessao(db_session, empresa)

    assert db_session.execute(SQL_GUARDA_CROSS_TENANT_USUARIO).scalar_one() == 0

    db_session.execute(
        text("UPDATE sessoes_trabalho SET usuario_id = :u WHERE id = :i"), {"u": alheio.id, "i": sessao.id}
    )
    db_session.flush()

    assert db_session.execute(SQL_GUARDA_CROSS_TENANT_USUARIO).scalar_one() == 1


def test_guarda_cross_tenant_departamento(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    alheio = _departamento(db_session, outra_empresa)
    sessao = _sessao(db_session, empresa)

    db_session.execute(
        text("UPDATE sessoes_trabalho SET departamento_id = :d WHERE id = :i"),
        {"d": alheio.id, "i": sessao.id},
    )
    db_session.flush()

    assert db_session.execute(SQL_GUARDA_CROSS_TENANT_DEPARTAMENTO).scalar_one() == 1


# --------------------------------------------------------------------------------------
# Índices únicos parciais — sobreviveram ao rename (achado do próprio alembic check: o DROP
# da coluna textual original derrubava os dois em cascata; 0018 os recria explicitamente)
# --------------------------------------------------------------------------------------

def test_nao_permite_duas_sessoes_ativas_para_mesma_demanda_e_usuario(
    db_session: Session, empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    usuario = _usuario(db_session, empresa)
    demanda_id = str(uuid.uuid4())
    service.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
    )
    db_session.flush()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO sessoes_trabalho
                    (id, empresa_id, demanda_id, usuario_id, evento_inicio_id, status, inicio_em, created_at, updated_at)
                VALUES (:id, :empresa_id, :demanda_id, :usuario_id, :evento_id, 'ativa', now(), now(), now())
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "empresa_id": empresa.id,
                "demanda_id": demanda_id,
                "usuario_id": usuario.id,
                "evento_id": str(uuid.uuid4()),
            },
        )
        db_session.flush()


# --------------------------------------------------------------------------------------
# Escrita — validação de vínculo (não depende da forma do schema, sempre foi assim)
# --------------------------------------------------------------------------------------

def test_open_session_grava_usuario_id_real(
    db_session: Session, empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    usuario = _usuario(db_session, empresa)
    sessao = service.open_session(
        db_session,
        empresa_id=empresa.id,
        demanda_id=str(uuid.uuid4()),
        evento_inicio_id=str(uuid.uuid4()),
        inicio_em=datetime.now(timezone.utc),
        usuario_id=usuario.id,
    )
    assert sessao.usuario_id == usuario.id
    assert sessao.departamento_id is None


def test_open_session_grava_departamento_id_real(
    db_session: Session, empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    departamento = _departamento(db_session, empresa)
    sessao = service.open_session(
        db_session,
        empresa_id=empresa.id,
        demanda_id=str(uuid.uuid4()),
        evento_inicio_id=str(uuid.uuid4()),
        inicio_em=datetime.now(timezone.utc),
        departamento_id=departamento.id,
    )
    assert sessao.departamento_id == departamento.id
    assert sessao.usuario_id is None


def test_open_session_recusa_usuario_inexistente(
    db_session: Session, empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    with pytest.raises(SessaoTrabalhoUsuarioInvalidoError):
        service.open_session(
            db_session,
            empresa_id=empresa.id,
            demanda_id=str(uuid.uuid4()),
            evento_inicio_id=str(uuid.uuid4()),
            inicio_em=datetime.now(timezone.utc),
            usuario_id=str(uuid.uuid4()),
        )


def test_open_session_recusa_usuario_de_outra_empresa(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    alheio = _usuario(db_session, outra_empresa)
    with pytest.raises(SessaoTrabalhoUsuarioInvalidoError):
        service.open_session(
            db_session,
            empresa_id=empresa.id,
            demanda_id=str(uuid.uuid4()),
            evento_inicio_id=str(uuid.uuid4()),
            inicio_em=datetime.now(timezone.utc),
            usuario_id=alheio.id,
        )


def test_open_session_recusa_departamento_arquivado(
    db_session: Session, empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    departamento = _departamento(db_session, empresa)
    departamento.status = "arquivado"
    db_session.flush()

    with pytest.raises(SessaoTrabalhoDepartamentoInvalidoError):
        service.open_session(
            db_session,
            empresa_id=empresa.id,
            demanda_id=str(uuid.uuid4()),
            evento_inicio_id=str(uuid.uuid4()),
            inicio_em=datetime.now(timezone.utc),
            departamento_id=departamento.id,
        )


def test_close_session_encerra_e_calcula_duracao(
    db_session: Session, empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    usuario = _usuario(db_session, empresa)
    inicio = datetime.now(timezone.utc)
    sessao = service.open_session(
        db_session, empresa_id=empresa.id, demanda_id=str(uuid.uuid4()),
        evento_inicio_id=str(uuid.uuid4()), inicio_em=inicio, usuario_id=usuario.id,
    )

    from datetime import timedelta
    fim = inicio + timedelta(seconds=42)
    encerrada = service.close_session(
        db_session, sessao, evento_fim_id=str(uuid.uuid4()), fim_em=fim, motivo_encerramento="conclusao"
    )

    assert encerrada.status == "encerrada"
    assert encerrada.duracao_segundos == 42


# --------------------------------------------------------------------------------------
# Leitura (repository) — filtra pela FK real
# --------------------------------------------------------------------------------------

def test_list_filtra_por_usuario(db_session: Session, empresa: Empresa, service: SessaoTrabalhoService) -> None:
    usuario_a = _usuario(db_session, empresa)
    usuario_b = _usuario(db_session, empresa)

    service.open_session(
        db_session, empresa_id=empresa.id, demanda_id=str(uuid.uuid4()),
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario_a.id,
    )
    service.open_session(
        db_session, empresa_id=empresa.id, demanda_id=str(uuid.uuid4()),
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario_b.id,
    )

    repository = SessaoTrabalhoRepository()
    achadas = repository.list(db_session, empresa_id=empresa.id, usuario_id=usuario_a.id)

    assert len(achadas) == 1
    assert achadas[0].usuario_id == usuario_a.id


def test_list_filtra_por_empresa(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    usuario = _usuario(db_session, empresa)
    usuario_alheio = _usuario(db_session, outra_empresa)
    service.open_session(
        db_session, empresa_id=empresa.id, demanda_id=str(uuid.uuid4()),
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
    )
    service.open_session(
        db_session, empresa_id=outra_empresa.id, demanda_id=str(uuid.uuid4()),
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario_alheio.id,
    )

    repository = SessaoTrabalhoRepository()
    achadas = repository.list(db_session, empresa_id=empresa.id)
    assert len(achadas) == 1
    assert achadas[0].empresa_id == empresa.id


def test_get_active_equivalent_usa_fk(
    db_session: Session, empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    usuario = _usuario(db_session, empresa)
    demanda_id = str(uuid.uuid4())
    aberta = service.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), usuario_id=usuario.id,
    )

    repository = SessaoTrabalhoRepository()
    equivalente = repository.get_active_equivalent(
        db_session, demanda_id=demanda_id, usuario_id=usuario.id, departamento_id=None
    )
    assert equivalente is not None
    assert equivalente.id == aberta.id


def test_get_active_equivalent_departamento_exige_usuario_nulo(
    db_session: Session, empresa: Empresa, service: SessaoTrabalhoService
) -> None:
    """Vínculo por departamento (usuario_id NULL) não pode ser confundido com vínculo por
    usuário na mesma demanda — são casos mutuamente exclusivos por desenho."""
    departamento = _departamento(db_session, empresa)
    demanda_id = str(uuid.uuid4())
    aberta = service.open_session(
        db_session, empresa_id=empresa.id, demanda_id=demanda_id,
        evento_inicio_id=str(uuid.uuid4()), inicio_em=datetime.now(timezone.utc), departamento_id=departamento.id,
    )

    repository = SessaoTrabalhoRepository()
    equivalente = repository.get_active_equivalent(
        db_session, demanda_id=demanda_id, usuario_id=None, departamento_id=departamento.id
    )
    assert equivalente is not None
    assert equivalente.id == aberta.id


# --------------------------------------------------------------------------------------
# GET /sessoes-trabalho/horas — agregado por departamento, autorização via Head central.
#
# Regra definitiva: operador comum NUNCA vê métrica ou histórico temporal de execução — nem
# agregado, nem lista própria. Duas rotas foram removidas por essa razão:
#
# - /minhas/horas (agregado autoescopado do próprio operador) — nasceu só para alimentar o
#   card "Horas executadas" do Dashboard, que deixou de existir.
# - /minhas (lista das próprias sessões, sem agregado) — sem nenhum consumidor real (nenhum
#   componente/hook do frontend a chamava) e o payload (SessaoTrabalhoRead) expõe `inicioEm`,
#   `fimEm` e `duracaoSegundos` por sessão: qualquer operador autenticado podia reconstruir o
#   próprio histórico/horas chamando a rota direto, sem precisar de UI nenhuma.
#
# /horas (departamento) é o único agregado de horas que sobra, e é exclusivo de quem tem
# visão de gestão (admin/gestor/Head) — nunca do operador comum, mesmo sobre o próprio
# departamento. Se no futuro o operador precisar controlar início/fim do próprio trabalho, o
# desenho correto é uma rota nova e mínima (ex.: `GET /sessoes-trabalho/minha-ativa` devolvendo
# só `sessaoId`/`demandaId`/estado ativo, sem duração nem histórico) — não reaproveitar esta.
# --------------------------------------------------------------------------------------

def test_horas_departamento_sem_token_401(client) -> None:
    resposta = get(client, f"/sessoes-trabalho/horas?departamentoId={uuid.uuid4()}")
    assert resposta.status_code == 401


def test_horas_departamento_admin_acessa_qualquer_departamento_da_empresa(
    app, db_session: Session, empresa: Empresa, token_admin: str
) -> None:
    departamento = _departamento(db_session, empresa)
    resposta = get(TestClient(app), f"/sessoes-trabalho/horas?departamentoId={departamento.id}", token=token_admin)
    assert resposta.status_code == 200
    assert resposta.json()["departamentoId"] == departamento.id


def test_horas_departamento_gestor_acessa_qualquer_departamento_da_empresa(
    app, db_session: Session, empresa: Empresa, token_gestor: str
) -> None:
    departamento = _departamento(db_session, empresa)
    resposta = get(TestClient(app), f"/sessoes-trabalho/horas?departamentoId={departamento.id}", token=token_gestor)
    assert resposta.status_code == 200


def test_horas_departamento_head_acessa_o_proprio(app, db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    head = _usuario(db_session, empresa)
    departamento.responsavel_usuario_id = head.id
    db_session.flush()

    cliente = _client_para(app, head)
    resposta = get(cliente, f"/sessoes-trabalho/horas?departamentoId={departamento.id}")
    assert resposta.status_code == 200
    assert resposta.json()["departamentoId"] == departamento.id


def test_horas_departamento_head_de_outro_departamento_403(app, db_session: Session, empresa: Empresa) -> None:
    departamento_do_head = _departamento(db_session, empresa)
    outro_departamento = _departamento(db_session, empresa)
    head = _usuario(db_session, empresa)
    departamento_do_head.responsavel_usuario_id = head.id
    db_session.flush()

    cliente = _client_para(app, head)
    resposta = get(cliente, f"/sessoes-trabalho/horas?departamentoId={outro_departamento.id}")
    assert resposta.status_code == 403


def test_horas_departamento_operador_comum_403(app, db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    operador = _usuario(db_session, empresa)

    cliente = _client_para(app, operador)
    resposta = get(cliente, f"/sessoes-trabalho/horas?departamentoId={departamento.id}")
    assert resposta.status_code == 403


def test_horas_departamento_atendimento_sem_ser_head_403(app, db_session: Session, empresa: Empresa) -> None:
    """Atendimento não dá direito a /horas por si só — só admin/gestor ou Head de verdade,
    a mesma regra central de app/core/escopo.py."""
    departamento_atendimento = _departamento(db_session, empresa)
    departamento_atendimento.nome = "Atendimento"
    departamento_atendimento.nome_normalizado = "atendimento"
    usuario_atendimento = _usuario(db_session, empresa)
    usuario_atendimento.departamento_id = departamento_atendimento.id
    db_session.flush()

    cliente = _client_para(app, usuario_atendimento)
    resposta = get(cliente, f"/sessoes-trabalho/horas?departamentoId={departamento_atendimento.id}")
    assert resposta.status_code == 403


def test_horas_departamento_inexistente_404(app, token_admin: str) -> None:
    resposta = get(TestClient(app), f"/sessoes-trabalho/horas?departamentoId={uuid.uuid4()}", token=token_admin)
    assert resposta.status_code == 404


def test_horas_departamento_de_outra_empresa_404(
    app, db_session: Session, outra_empresa: Empresa, token_admin: str
) -> None:
    departamento_alheio = _departamento(db_session, outra_empresa)
    resposta = get(
        TestClient(app), f"/sessoes-trabalho/horas?departamentoId={departamento_alheio.id}", token=token_admin
    )
    assert resposta.status_code == 404


def test_horas_departamento_soma_sessao_encerrada_e_ativa(
    app, db_session: Session, empresa: Empresa, token_admin: str
) -> None:
    departamento = _departamento(db_session, empresa)
    colaborador = _usuario(db_session, empresa)
    colaborador.departamento_id = departamento.id
    db_session.flush()

    _sessao(db_session, empresa, usuario_id=colaborador.id, status="encerrada", duracao_segundos=3600)
    ativa = _sessao(db_session, empresa, usuario_id=colaborador.id, status="ativa")
    ativa.inicio_em = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.flush()

    resposta = get(TestClient(app), f"/sessoes-trabalho/horas?departamentoId={departamento.id}", token=token_admin)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["sessoesConsideradas"] == 2
    assert corpo["horasConsumidas"] == pytest.approx(2.0, abs=0.02)
