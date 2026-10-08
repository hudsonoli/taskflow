"""Fase 4 — Dashboard da Administração da Plataforma (`GET /plataforma/dashboard`).

Métricas AGREGADAS de adoção por empresa a partir de dados existentes (usuarios + eventos `auth.login_sucesso`). Os eventos
de login dos testes são publicados pelo MESMO publisher e com o MESMO formato de `AuthService._publish_login_sucesso`
(só o `occurred_at` varia para exercitar as janelas de 7/30 dias) — nada de formato inventado.

Provas: só o Administrador da Plataforma acessa; conta de sistema fora de TODAS as métricas; empresas isoladas; já/nunca
acessaram, ativos 7d/30d e último acesso exatos; múltiplos Gestores; regras de atenção objetivas; empresa inativa e vazia;
nenhum dado individual/operacional na resposta; número de queries constante (sem N+1).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.services.domain_event_publisher import DomainEventPublisher
from tests.test_plataforma import PLAT, _criar_empresa, administrador, client_plataforma, usuario_plataforma  # noqa: F401
from tests.test_plataforma_gestor_existente import _usuario

URL = f"{PLAT}/dashboard"
AGORA = lambda: datetime.now(timezone.utc)  # noqa: E731


def _login(db: Session, usuario: Usuario, *, ha: timedelta) -> None:
    """Evento `auth.login_sucesso` no formato real de AuthService._publish_login_sucesso."""
    quando = AGORA() - ha
    DomainEventPublisher().publish(
        db,
        tipo=DomainEventType.AUTH_LOGIN_SUCESSO,
        empresa_id=usuario.empresa_id,
        entidade_tipo="auth",
        entidade_id=usuario.id,
        usuario_id=usuario.id,
        payload={
            "empresa_id": usuario.empresa_id, "usuario_id": usuario.id, "nome": usuario.nome,
            "timestamp": quando.isoformat(), "resultado": "sucesso", "ip_address": "127.0.0.1", "user_agent": "pytest",
        },
        occurred_at=quando,
    )
    db.flush()


def _empresa_na_lista(corpo: dict, empresa_id: str) -> dict:
    return next(e for e in corpo["empresas"] if e["id"] == empresa_id)


def _atencoes(corpo: dict, empresa_id: str) -> set[str]:
    return {a["tipo"] for a in corpo["atencoes"] if a["empresaId"] == empresa_id}


def _cenario(client: TestClient, db: Session) -> tuple[dict, dict]:
    """A: 2 Gestores + 3 Usuários (1 nunca acessou) + inativo + arquivado + conta de sistema. B: 1 Gestor, 2 Usuários sem login."""
    a, b = _criar_empresa(client), _criar_empresa(client)
    g1 = _usuario(db, a["id"], "Gestor Um", perfil="gestor")
    g2 = _usuario(db, a["id"], "Gestor Dois", perfil="gestor")
    u1 = _usuario(db, a["id"], "Usuario Recente")
    u2 = _usuario(db, a["id"], "Usuario Mensal")
    u3 = _usuario(db, a["id"], "Usuario Antigo")
    _usuario(db, a["id"], "Usuario Nunca")
    inativo = _usuario(db, a["id"], "Usuario Inativo", status="inativo")
    _usuario(db, a["id"], "Usuario Arquivado", status="arquivado")
    sistema = _usuario(db, a["id"], "Conta Sistema", perfil="admin", sistema=True)
    _login(db, g1, ha=timedelta(hours=3))      # ativo 7d e 30d
    _login(db, g2, ha=timedelta(days=40))      # já acessou, mas fora das janelas
    _login(db, u1, ha=timedelta(days=2))       # ativo 7d e 30d
    _login(db, u1, ha=timedelta(days=50))      # login antigo do mesmo usuário não conta duas vezes
    _login(db, u2, ha=timedelta(days=20))      # ativo só em 30d
    _login(db, u3, ha=timedelta(days=60))      # já acessou, inativo nas janelas
    _login(db, inativo, ha=timedelta(hours=1))  # usuário inativo: fora das métricas de adoção
    _login(db, sistema, ha=timedelta(minutes=1))  # conta de sistema: fora de TUDO
    _usuario(db, b["id"], "Gestora B", perfil="gestor")
    _usuario(db, b["id"], "Usuario B1")
    _usuario(db, b["id"], "Usuario B2")
    return a, b


# --------------------------------------------------------------------------------------
# Autoridade
# --------------------------------------------------------------------------------------


def test_so_o_administrador_da_plataforma_acessa(
    client_plataforma: TestClient, client_admin: TestClient, client_gestor: TestClient, client_operador: TestClient
) -> None:
    assert client_plataforma.get(URL).status_code == 200
    for tenant in (client_admin, client_gestor, client_operador):
        assert tenant.get(URL).status_code in (401, 403)
    assert TestClient(client_plataforma.app).get(URL).status_code == 401


def test_autoridade_revogada_perde_o_dashboard_na_hora(client_plataforma: TestClient, administrador, db_session: Session) -> None:
    administrador.ativo = False
    administrador.revogado_em = AGORA()
    db_session.flush()
    assert client_plataforma.get(URL).status_code == 403


# --------------------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------------------


def test_metricas_exatas_da_empresa_a(client_plataforma: TestClient, db_session: Session) -> None:
    a, _b = _cenario(client_plataforma, db_session)
    linha = _empresa_na_lista(client_plataforma.get(URL).json(), a["id"])
    # utilizáveis = 2 Gestores + 4 Usuários (Recente, Mensal, Antigo, Nunca); inativo/arquivado/sistema ficam de fora
    assert linha["usuarios"] == 6
    assert linha["cadastrados"] == 7  # + o inativo (o arquivado e a conta de sistema nunca entram)
    assert linha["gestores"] == 2
    assert linha["jaAcessaram"] == 5  # g1, g2, u1, u2, u3
    assert linha["nuncaAcessaram"] == 1  # só "Usuario Nunca"
    assert linha["ativos7d"] == 2  # g1 (3h) e u1 (2d)
    assert linha["ativos30d"] == 3  # + u2 (20d)
    assert linha["jaAcessaram"] + linha["nuncaAcessaram"] == linha["usuarios"]
    assert linha["status"] == "ativa" and linha["projetos"] == 0 and linha["demandas"] == 0


def test_ultimo_acesso_e_o_ultimo_login_humano_e_ignora_a_conta_de_sistema(client_plataforma: TestClient, db_session: Session) -> None:
    a, _b = _cenario(client_plataforma, db_session)
    ultimo = _empresa_na_lista(client_plataforma.get(URL).json(), a["id"])["ultimoAcesso"]
    ultimo_dt = datetime.fromisoformat(ultimo)
    # o mais recente humano é o do usuário inativo (1h); a conta de sistema (1 min) NÃO conta
    assert abs((AGORA() - ultimo_dt) - timedelta(hours=1)) < timedelta(minutes=2)


def test_empresas_sao_isoladas_e_empresa_sem_login_tem_ultimo_acesso_nulo(client_plataforma: TestClient, db_session: Session) -> None:
    _a, b = _cenario(client_plataforma, db_session)
    linha = _empresa_na_lista(client_plataforma.get(URL).json(), b["id"])
    assert (linha["usuarios"], linha["gestores"], linha["jaAcessaram"], linha["nuncaAcessaram"], linha["ativos7d"], linha["ativos30d"]) == (3, 1, 0, 3, 0, 0)
    assert linha["ultimoAcesso"] is None


def test_resumo_global_soma_as_empresas_ativas_sem_a_conta_de_sistema(client_plataforma: TestClient, db_session: Session) -> None:
    corpo_antes = client_plataforma.get(URL).json()["resumo"]
    a, b = _cenario(client_plataforma, db_session)
    resumo = client_plataforma.get(URL).json()["resumo"]
    # deltas em relação ao que já existia: A (6 utilizáveis) + B (3)
    assert resumo["usuarios"] - corpo_antes["usuarios"] == 9
    assert resumo["gestores"] - corpo_antes["gestores"] == 3
    assert resumo["jaAcessaram"] - corpo_antes["jaAcessaram"] == 5
    assert resumo["nuncaAcessaram"] - corpo_antes["nuncaAcessaram"] == 4
    assert resumo["ativos7d"] - corpo_antes["ativos7d"] == 2
    assert resumo["ativos30d"] - corpo_antes["ativos30d"] == 3
    assert resumo["empresasAtivas"] - corpo_antes["empresasAtivas"] == 2
    assert resumo["jaAcessaram"] + resumo["nuncaAcessaram"] == resumo["usuarios"]


def test_conta_de_sistema_nao_conta_nem_como_gestor_nem_como_acesso(client_plataforma: TestClient, db_session: Session) -> None:
    empresa = _criar_empresa(client_plataforma)
    sistema = _usuario(db_session, empresa["id"], "Sistema Gestor", perfil="gestor", sistema=True)
    _login(db_session, sistema, ha=timedelta(minutes=5))
    linha = _empresa_na_lista(client_plataforma.get(URL).json(), empresa["id"])
    assert (linha["usuarios"], linha["cadastrados"], linha["gestores"], linha["jaAcessaram"], linha["ativos7d"], linha["ativos30d"]) == (0, 0, 0, 0, 0, 0)
    assert linha["ultimoAcesso"] is None


def test_admin_legado_e_usuario_nao_contam_como_gestor(client_plataforma: TestClient, db_session: Session) -> None:
    empresa = _criar_empresa(client_plataforma)
    _usuario(db_session, empresa["id"], "Admin Legado", perfil="admin")
    _usuario(db_session, empresa["id"], "Usuario Comum")
    linha = _empresa_na_lista(client_plataforma.get(URL).json(), empresa["id"])
    assert linha["gestores"] == 0 and linha["usuarios"] == 2


# --------------------------------------------------------------------------------------
# Atenção
# --------------------------------------------------------------------------------------


def test_regras_de_atencao_sao_objetivas(client_plataforma: TestClient, db_session: Session) -> None:
    a, b = _cenario(client_plataforma, db_session)
    corpo = client_plataforma.get(URL).json()
    # A: tem Gestores e gente acessando; só "1 usuário nunca acessou" (informativo)
    assert _atencoes(corpo, a["id"]) == {"nunca_acessaram"}
    nunca = next(x for x in corpo["atencoes"] if x["empresaId"] == a["id"])
    assert nunca["severidade"] == "info" and nunca["quantidade"] == 1 and "1 usuário nunca acessou" in nunca["mensagem"]
    # B: criada agora → carência (não é "sem acesso 30d"), tem Gestor, mas 3 nunca acessaram
    assert _atencoes(corpo, b["id"]) == {"nunca_acessaram"}


def test_empresa_sem_gestor_e_sem_acesso_30d_depois_da_carencia(client_plataforma: TestClient, db_session: Session) -> None:
    empresa = _criar_empresa(client_plataforma)
    pessoa = _usuario(db_session, empresa["id"], "Pessoa Antiga")
    _login(db_session, pessoa, ha=timedelta(days=45))
    db_session.execute(
        Empresa.__table__.update().where(Empresa.id == empresa["id"]).values(created_at=AGORA() - timedelta(days=90))
    )
    db_session.flush()
    corpo = client_plataforma.get(URL).json()
    assert _atencoes(corpo, empresa["id"]) == {"sem_gestor", "sem_acesso_30d"}
    avisos = [a for a in corpo["atencoes"] if a["empresaId"] == empresa["id"]]
    assert {a["severidade"] for a in avisos} == {"aviso"}


def test_empresa_nova_ou_sem_usuarios_nao_vira_alerta_de_acesso(client_plataforma: TestClient) -> None:
    empresa = _criar_empresa(client_plataforma)  # zero usuários, criada agora
    corpo = client_plataforma.get(URL).json()
    linha = _empresa_na_lista(corpo, empresa["id"])
    assert (linha["usuarios"], linha["jaAcessaram"], linha["nuncaAcessaram"], linha["gestores"]) == (0, 0, 0, 0)
    assert _atencoes(corpo, empresa["id"]) == {"sem_gestor"}  # única regra aplicável; sem divisão por zero


def test_empresa_inativa_aparece_na_tabela_mas_nao_gera_atencao_nem_entra_no_resumo(client_plataforma: TestClient, db_session: Session) -> None:
    empresa = _criar_empresa(client_plataforma)
    _usuario(db_session, empresa["id"], "Gestor Inativa", perfil="gestor")
    _usuario(db_session, empresa["id"], "Usuario Inativa")
    antes = client_plataforma.get(URL).json()["resumo"]
    assert client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/inativar", json={}).status_code == 200
    corpo = client_plataforma.get(URL).json()
    linha = _empresa_na_lista(corpo, empresa["id"])
    assert linha["status"] == "inativa" and linha["usuarios"] == 2  # dados continuam visíveis na tabela
    assert _atencoes(corpo, empresa["id"]) == set()
    assert antes["usuarios"] - corpo["resumo"]["usuarios"] == 2  # sai das métricas de adoção (não autentica)
    assert antes["empresasAtivas"] - corpo["resumo"]["empresasAtivas"] == 1
    assert corpo["resumo"]["empresasTotal"] == antes["empresasTotal"]


# --------------------------------------------------------------------------------------
# Privacidade e performance
# --------------------------------------------------------------------------------------


def test_nenhum_dado_individual_ou_operacional_na_resposta(client_plataforma: TestClient, db_session: Session) -> None:
    a, _b = _cenario(client_plataforma, db_session)
    resposta = client_plataforma.get(URL)
    texto = resposta.text
    for nome in ("Gestor Um", "Usuario Recente", "Conta Sistema", "Usuario Arquivado", "@alvo.test", "pytest", "127.0.0.1"):
        assert nome not in texto, nome
    campos = {k for e in resposta.json()["empresas"] for k in e}
    assert campos == {
        "id", "nome", "nomeFantasia", "slug", "status", "createdAt", "usuarios", "cadastrados", "jaAcessaram", "nuncaAcessaram",
        "ativos7d", "ativos30d", "gestores", "ultimoAcesso", "projetos", "demandas",
    }
    assert set(resposta.json()) == {"geradoEm", "resumo", "empresas", "atencoes"}


def test_numero_de_queries_nao_cresce_com_o_numero_de_empresas(client_plataforma: TestClient, db_session: Session) -> None:
    contagem: list[str] = []
    engine = db_session.get_bind()

    def contar(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        contagem.append(statement)

    def medir() -> int:
        contagem.clear()
        event.listen(engine, "before_cursor_execute", contar)
        try:
            assert client_plataforma.get(URL).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", contar)
        return len(contagem)

    for _ in range(2):
        e = _criar_empresa(client_plataforma)
        _usuario(db_session, e["id"], "Pessoa", perfil="gestor")
    com_poucas = medir()
    for _ in range(12):
        e = _criar_empresa(client_plataforma)
        _usuario(db_session, e["id"], "Pessoa", perfil="gestor")
        _usuario(db_session, e["id"], "Outra Pessoa")
    com_muitas = medir()
    assert com_poucas == com_muitas, (com_poucas, com_muitas)  # constante: nenhuma query por empresa
    assert com_muitas <= 12  # autenticação da plataforma + as 4 consultas agregadas do dashboard
