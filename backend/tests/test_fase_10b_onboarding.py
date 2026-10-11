"""Fase 10B — onboarding de nova empresa pela Gestão: Empresa (ativa) + primeiro Gestor + convite, numa operação atômica.

Provas: só o Administrador da Plataforma cria; slug validado no backend (formato, reservados, único — inclusive a corrida resolvida pelo UNIQUE do banco);
Gestor sempre `gestor`, só desta empresa, sem admin tenant nem platform admin novos; NENHUMA senha existe (convite de primeiro acesso: o Gestor define a própria);
falha de convite não desfaz a empresa; falha de criação não deixa estado parcial; sem sessão tenant; auditoria com o ator real; cross-tenant.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes import plataforma as plataforma_routes
from app.models.administrador_plataforma import AdministradorPlataforma
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.services.configuracao_email_service import EmailEnvioFalhouError, EmailNaoConfiguradoError
from app.services.empresa_service import EmpresaConflictError
from tests.test_password_reset import EmailFalso
from tests.test_plataforma import PLAT, _client, _definir_senha_pelo_convite, administrador, client_plataforma, usuario_plataforma  # noqa: F401  (fixtures)

URL_PUBLICA = "https://taskflow.exemplo.test"
ONBOARDING = f"{PLAT}/empresas/onboarding"


def _payload(**empresa_extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    empresa = {"nome": f"Empresa Onboarding {sufixo}", "nomeFantasia": f"Onboarding {sufixo}", "codigoInterno": f"onb-{sufixo}", "slug": f"onb-{sufixo}"}
    empresa.update(empresa_extra)
    return {"empresa": empresa, "gestor": {"nome": "Gestora Inicial", "email": f"gestora-{sufixo}@onboarding.test"}}


def _contagens(db: Session) -> tuple[int, int, int, int]:
    db.expire_all()
    return (
        db.scalar(select(func.count()).select_from(Empresa)),
        db.scalar(select(func.count()).select_from(Usuario)),
        db.scalar(select(func.count()).select_from(UsuarioCredencial)),
        db.scalar(select(func.count()).select_from(AdministradorPlataforma)),
    )


@pytest.fixture()
def email(monkeypatch: pytest.MonkeyPatch) -> EmailFalso:
    """E-mail NUNCA enviado de verdade: o sender da empresa nova é trocado por um fake que registra o que receberia."""
    falso = EmailFalso()
    servico = plataforma_routes.plataforma_service.auth_service
    monkeypatch.setattr(servico, "configuracao_email_service", falso)
    monkeypatch.setattr(servico, "settings", replace(servico.settings, app_public_url=URL_PUBLICA))
    return falso


# ======================================================================================
# criação: caminho feliz
# ======================================================================================


def test_administrador_da_plataforma_cria_empresa_ativa_com_gestor_e_url_de_acesso(client_plataforma: TestClient, db_session: Session) -> None:
    antes = _contagens(db_session)
    corpo_enviado = _payload()
    resposta = client_plataforma.post(ONBOARDING, json=corpo_enviado)
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    empresa, gestor = corpo["empresa"], corpo["gestor"]

    assert empresa["status"] == "ativa" and empresa["slug"] == corpo_enviado["empresa"]["slug"]
    assert corpo["urlAcesso"].endswith(f"/e/{empresa['slug']}/login") and "token" not in corpo["urlAcesso"]
    assert gestor["perfilBase"] == "gestor" and gestor["status"] == "ativo" and gestor["acessoSistema"] is True and gestor["primeiroAcessoPendente"] is True

    depois = _contagens(db_session)
    assert depois[0] == antes[0] + 1 and depois[1] == antes[1] + 1 and depois[2] == antes[2] + 1  # empresa, usuário, credencial
    assert depois[3] == antes[3]  # NENHUM platform admin novo
    usuario = db_session.get(Usuario, gestor["id"])
    assert usuario.empresa_id == empresa["id"] and usuario.perfil_base == "gestor" and usuario.is_system_account is False
    # nenhum admin tenant foi criado nessa empresa; o único usuário é o Gestor
    perfis = db_session.scalars(select(Usuario.perfil_base).where(Usuario.empresa_id == empresa["id"])).all()
    assert perfis == ["gestor"]


def test_nenhuma_senha_e_exposta_e_nenhuma_sessao_tenant_e_criada(client_plataforma: TestClient) -> None:
    resposta = client_plataforma.post(ONBOARDING, json=_payload())
    assert resposta.status_code == 201
    corpo = resposta.json()
    texto = json.dumps(corpo)
    for proibido in ("senhaTemporaria", "deveAlterarSenha", "accessToken", "tf_session", "Authorization"):
        assert proibido not in texto
    assert not resposta.cookies  # a Gestão continua na Gestão: nada de cookie/sessão tenant
    assert set(corpo) == {"empresa", "gestor", "convite", "urlAcesso"}


def test_gestor_define_a_propria_senha_pelo_convite_e_entra_somente_na_empresa_criada(app, client_plataforma: TestClient, db_session: Session) -> None:
    corpo = client_plataforma.post(ONBOARDING, json=_payload()).json()
    empresa, gestor = corpo["empresa"], corpo["gestor"]
    email_gestor = db_session.get(Usuario, gestor["id"]).email
    # antes do convite concluído ninguém entra (senha aleatória descartada)
    assert _client(app, None).post(
        "/auth/login", json={"empresaSlug": empresa["slug"], "email": email_gestor, "senha": "AlgumaSenha123!"}
    ).status_code == 401
    senha = _definir_senha_pelo_convite(app, empresa, corpo)
    login = _client(app, None).post("/auth/login", json={"empresaSlug": empresa["slug"], "email": email_gestor, "senha": senha})
    assert login.status_code == 200 and login.json()["mustChangePassword"] is False
    sessao = _client(app, login.json()["accessToken"]).get("/auth/me").json()
    assert sessao["empresaSlug"] == empresa["slug"]
    # o mesmo e-mail/senha NÃO entra em outra empresa (slug de outra empresa)
    outra = client_plataforma.post(ONBOARDING, json=_payload()).json()["empresa"]
    assert _client(app, None).post("/auth/login", json={"empresaSlug": outra["slug"], "email": email_gestor, "senha": senha}).status_code == 401


def test_branding_publico_da_empresa_nova_ja_responde_pelo_slug(client_plataforma: TestClient) -> None:
    payload = _payload(nomeFantasia="Marca Imediata Ltda")
    empresa = client_plataforma.post(ONBOARDING, json=payload).json()["empresa"]
    publico = client_plataforma.get(f"/publico/empresas/{empresa['slug']}/branding").json()
    assert publico["disponivel"] is True and publico["nomeExibicao"] == "Marca Imediata Ltda"


def test_auditoria_registra_empresa_criada_e_gestor_inicial_com_o_ator_real(
    client_plataforma: TestClient, db_session: Session, usuario_plataforma: Usuario  # noqa: F811
) -> None:
    corpo = client_plataforma.post(ONBOARDING, json=_payload()).json()
    eventos = db_session.scalars(select(Evento).where(Evento.empresa_id == corpo["empresa"]["id"])).all()
    tipos = {e.tipo for e in eventos}
    assert {"empresa.criada", "empresa.gestor_criado", "usuario.criado"} <= tipos
    assert {e.usuario_id for e in eventos if e.tipo in ("empresa.criada", "empresa.gestor_criado")} == {usuario_plataforma.id}  # ator = Administrador real
    gestor_evento = next(e for e in eventos if e.tipo == "empresa.gestor_criado")
    assert gestor_evento.payload["primeiroGestor"] is True
    token = corpo["convite"]["linkAcesso"].split("#token=", 1)[1]
    assert token not in json.dumps([e.payload for e in eventos], default=str)  # token nunca em evento


# ======================================================================================
# autoridade
# ======================================================================================


def test_gestor_e_operador_tenant_nao_criam_empresa(client_gestor: TestClient, client_operador: TestClient) -> None:
    for cliente in (client_gestor, client_operador):
        resposta = cliente.post(ONBOARDING, json=_payload())
        assert resposta.status_code in (401, 403), resposta.text
    assert client_gestor.post(f"{PLAT}/empresas", json=_payload()["empresa"]).status_code in (401, 403)


def test_sem_autenticacao_nao_cria_empresa(app) -> None:
    assert _client(app, None).post(ONBOARDING, json=_payload()).status_code in (401, 403)


# ======================================================================================
# slug
# ======================================================================================


@pytest.mark.parametrize("reservado", ["gestao", "plataforma", "api", "e", "login", "aprovacao", "logout", "admin", "suporte"])
def test_slug_reservado_e_recusado_no_backend_sem_criar_nada(client_plataforma: TestClient, db_session: Session, reservado: str) -> None:
    antes = _contagens(db_session)
    resposta = client_plataforma.post(ONBOARDING, json=_payload(slug=reservado))
    assert resposta.status_code == 422, resposta.text
    assert _contagens(db_session) == antes


@pytest.mark.parametrize("invalido", ["Com Espaço", "acentuação", "-comeca", "termina-", "a_b", "ab", "x" * 41, "tem/barra", "ponto.final"])
def test_slug_invalido_e_recusado(client_plataforma: TestClient, invalido: str) -> None:
    assert client_plataforma.post(ONBOARDING, json=_payload(slug=invalido)).status_code == 422


def test_slug_e_normalizado_para_minusculas_e_pode_ser_diferente_do_nome(client_plataforma: TestClient) -> None:
    sufixo = uuid.uuid4().hex[:6]
    empresa = client_plataforma.post(ONBOARDING, json=_payload(nome="BOX Comunicação", slug=f"BoxCom-{sufixo}")).json()["empresa"]
    assert empresa["slug"] == f"boxcom-{sufixo}" and empresa["nome"] == "BOX Comunicação"


def test_slug_duplicado_da_conflito_controlado_e_nao_deixa_estado_parcial(client_plataforma: TestClient, db_session: Session) -> None:
    primeira = client_plataforma.post(ONBOARDING, json=_payload()).json()["empresa"]
    antes = _contagens(db_session)
    repetida = _payload(slug=primeira["slug"])
    resposta = client_plataforma.post(ONBOARDING, json=repetida)
    assert resposta.status_code == 409 and "slug" in resposta.json()["detail"].lower()
    assert "Traceback" not in resposta.text and "sqlalchemy" not in resposta.text.lower()
    assert _contagens(db_session) == antes  # nem a empresa nem o Gestor ficaram pela metade


def test_codigo_e_documento_duplicados_dao_conflito_controlado(client_plataforma: TestClient, db_session: Session) -> None:
    base = _payload(documento=f"{uuid.uuid4().int % 10**14:014d}")
    assert client_plataforma.post(ONBOARDING, json=base).status_code == 201
    antes = _contagens(db_session)
    mesmo_codigo = _payload(codigoInterno=base["empresa"]["codigoInterno"])
    mesmo_documento = _payload(documento=base["empresa"]["documento"])
    for dados in (mesmo_codigo, mesmo_documento):
        resposta = client_plataforma.post(ONBOARDING, json=dados)
        assert resposta.status_code == 409, resposta.text
    assert _contagens(db_session) == antes


def test_corrida_de_slug_e_decidida_pelo_banco_com_conflito_controlado(client_plataforma: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dois admins passam pela checagem "slug livre" ao mesmo tempo: sem a checagem, o UNIQUE do banco decide e o perdedor recebe 409 (nunca 500/IntegrityError)."""
    vencedora = client_plataforma.post(ONBOARDING, json=_payload()).json()["empresa"]
    servico = plataforma_routes.plataforma_service.empresa_service
    monkeypatch.setattr(servico, "_ensure_slug_available", lambda *a, **k: None)  # simula a janela da corrida
    resposta = client_plataforma.post(ONBOARDING, json=_payload(slug=vencedora["slug"]))
    assert resposta.status_code == 409, resposta.text
    assert "Traceback" not in resposta.text
    assert db_session.scalars(select(Empresa).where(Empresa.slug == vencedora["slug"])).all().__len__() == 1


def test_edicao_nao_troca_o_slug(client_plataforma: TestClient) -> None:
    empresa = client_plataforma.post(ONBOARDING, json=_payload()).json()["empresa"]
    resposta = client_plataforma.patch(f"{PLAT}/empresas/{empresa['id']}", json={"slug": f"novo-{uuid.uuid4().hex[:6]}"})
    assert resposta.status_code == 409
    assert client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}").json()["slug"] == empresa["slug"]


# ======================================================================================
# Gestor inicial: dados e atomicidade
# ======================================================================================


def test_email_do_gestor_invalido_nao_cria_a_empresa(client_plataforma: TestClient, db_session: Session) -> None:
    antes = _contagens(db_session)
    dados = _payload()
    dados["gestor"]["email"] = "nao-e-um-email"
    resposta = client_plataforma.post(ONBOARDING, json=dados)
    assert resposta.status_code == 422, resposta.text
    assert _contagens(db_session) == antes


def test_campos_extras_e_perfil_admin_sao_recusados(client_plataforma: TestClient) -> None:
    for extra in ({"perfilBase": "admin"}, {"perfilBase": "gestor"}, {"senha": "SenhaQualquer1!"}, {"empresaId": str(uuid.uuid4())}):
        dados = _payload()
        dados["gestor"].update(extra)
        assert client_plataforma.post(ONBOARDING, json=dados).status_code == 422, extra
    dados = _payload()
    dados["status"] = "inativa"  # status da empresa nova é decidido pelo servidor (ativa)
    assert client_plataforma.post(ONBOARDING, json=dados).status_code == 422


def test_falha_no_meio_da_transacao_desfaz_empresa_e_gestor(client_plataforma: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    db_session.commit()  # fixtures persistidas: o rollback do serviço só pode desfazer o que ELE iniciou
    antes = _contagens(db_session)

    def quebrar(*a, **k):
        raise RuntimeError("falha simulada ao emitir o convite")

    monkeypatch.setattr(plataforma_routes.plataforma_service.auth_service, "preparar_convite", quebrar)
    with pytest.raises(RuntimeError):
        plataforma_routes.plataforma_service.criar_empresa_com_gestor(
            db_session, plataforma_routes.PlataformaEmpresaOnboardingCreate.model_validate(_payload()), ator=db_session.scalars(select(Usuario)).first()
        )
    assert _contagens(db_session) == antes  # tudo ou nada


# ======================================================================================
# convite: e-mail, falha controlada, reenvio
# ======================================================================================


def test_sem_smtp_na_empresa_nova_o_convite_nao_e_enviado_mas_a_empresa_fica_criada(client_plataforma: TestClient) -> None:
    resposta = client_plataforma.post(ONBOARDING, json=_payload())
    assert resposta.status_code == 201
    convite = resposta.json()["convite"]
    assert convite["enviado"] is False and convite["motivo"] in ("email_nao_configurado", "url_publica_ausente")
    assert "#token=" in convite["linkAcesso"] and "/redefinir-senha" in convite["linkAcesso"]  # entrega manual, tenant-aware
    assert resposta.json()["empresa"]["status"] == "ativa"


def test_com_smtp_o_convite_vai_por_e_mail_com_link_do_tenant_e_sem_link_na_resposta(client_plataforma: TestClient, email: EmailFalso) -> None:
    dados = _payload()
    resposta = client_plataforma.post(ONBOARDING, json=dados)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["convite"]["enviado"] is True and corpo["convite"]["motivo"] is None and corpo["convite"]["linkAcesso"] is None
    assert corpo["urlAcesso"] == f"{URL_PUBLICA}/e/{dados['empresa']['slug']}/login"
    (enviado,) = email.enviados
    assert enviado["assunto"] == "Convite de acesso — TaskFlow" and enviado["empresa_id"] == corpo["empresa"]["id"]
    assert enviado["destinatario"] == dados["gestor"]["email"]
    texto = enviado["texto"]
    assert f"{URL_PUBLICA}/e/{dados['empresa']['slug']}/redefinir-senha#token=" in texto and "?token=" not in texto
    assert dados["empresa"]["nomeFantasia"] in texto and "TaskFlow" in texto and "TaskFloww" not in texto
    assert "senha:" not in texto.lower() and "senha temporária" not in texto.lower()


@pytest.mark.parametrize(
    "falha, motivo",
    [(EmailNaoConfiguradoError("configuracao_ausente", "x"), "email_nao_configurado"), (EmailEnvioFalhouError("falha_tcp", "x"), "falha_envio")],
)
def test_falha_de_envio_nao_desfaz_a_empresa_e_expoe_o_estado(client_plataforma: TestClient, email: EmailFalso, falha: Exception, motivo: str) -> None:
    email.falha = falha
    resposta = client_plataforma.post(ONBOARDING, json=_payload())
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["convite"]["enviado"] is False and corpo["convite"]["motivo"] == motivo
    assert corpo["convite"]["linkAcesso"]  # entrega manual possível
    assert client_plataforma.get(f"{PLAT}/empresas/{corpo['empresa']['id']}").json()["status"] == "ativa"


def test_reenviar_convite_invalida_o_anterior_e_so_vale_para_quem_nao_definiu_senha(app, client_plataforma: TestClient) -> None:
    corpo = client_plataforma.post(ONBOARDING, json=_payload()).json()
    empresa, gestor = corpo["empresa"], corpo["gestor"]
    token_antigo = corpo["convite"]["linkAcesso"].split("#token=", 1)[1]
    novo = client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/usuarios/{gestor['id']}/convite")
    assert novo.status_code == 200, novo.text
    token_novo = novo.json()["convite"]["linkAcesso"].split("#token=", 1)[1]
    assert token_novo != token_antigo
    corpo_reset = {"empresaSlug": empresa["slug"], "novaSenha": "SenhaDoGestor123!", "confirmacaoSenha": "SenhaDoGestor123!"}
    assert _client(app, None).post("/auth/password-reset/confirm", json={**corpo_reset, "token": token_antigo}).status_code == 400  # convite anterior morreu
    assert _client(app, None).post("/auth/password-reset/confirm", json={**corpo_reset, "token": token_novo}).status_code in (200, 204)
    # já definiu a própria senha: não há convite pendente
    assert client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/usuarios/{gestor['id']}/convite").status_code == 409


def test_reenviar_convite_de_usuario_de_outra_empresa_e_404(client_plataforma: TestClient) -> None:
    a = client_plataforma.post(ONBOARDING, json=_payload()).json()
    b = client_plataforma.post(ONBOARDING, json=_payload()).json()
    resposta = client_plataforma.post(f"{PLAT}/empresas/{b['empresa']['id']}/usuarios/{a['gestor']['id']}/convite")
    assert resposta.status_code == 404  # cross-tenant: a mesma resposta de "não existe"
    assert client_plataforma.post(f"{PLAT}/empresas/{uuid.uuid4()}/usuarios/{a['gestor']['id']}/convite").status_code == 404


def test_token_do_convite_nunca_vai_para_log(client_plataforma: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    corpo = client_plataforma.post(ONBOARDING, json=_payload()).json()
    token = corpo["convite"]["linkAcesso"].split("#token=", 1)[1]
    assert token not in caplog.text


# ======================================================================================
# empresa suspensa e detalhe
# ======================================================================================


def test_empresa_inativa_nao_aceita_convite_nem_login(app, client_plataforma: TestClient, db_session: Session) -> None:
    corpo = client_plataforma.post(ONBOARDING, json=_payload()).json()
    empresa = corpo["empresa"]
    assert client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/inativar", json={}).status_code == 200
    token = corpo["convite"]["linkAcesso"].split("#token=", 1)[1]
    resposta = _client(app, None).post(
        "/auth/password-reset/confirm", json={"empresaSlug": empresa["slug"], "token": token, "novaSenha": "SenhaDoGestor123!", "confirmacaoSenha": "SenhaDoGestor123!"}
    )
    assert resposta.status_code == 400
    assert client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/usuarios/{corpo['gestor']['id']}/convite").status_code == 409
    publico = client_plataforma.get(f"/publico/empresas/{empresa['slug']}/branding").json()
    assert publico["disponivel"] is False  # /e/<slug>/login mostra "empresa indisponível"


def test_detalhe_da_empresa_lista_gestor_e_nao_expoe_segredos(client_plataforma: TestClient) -> None:
    corpo = client_plataforma.post(ONBOARDING, json=_payload()).json()
    empresa = corpo["empresa"]
    detalhe = client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}").json()
    assert detalhe["gestoresAtivos"] == 1 and detalhe["slug"] == empresa["slug"] and detalhe["status"] == "ativa"
    usuarios = client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}/usuarios")
    texto = usuarios.text.lower()
    for proibido in ("hash", "token", "senha_hash", "smtp", "reset"):
        assert proibido not in texto
    assert [u["perfilBase"] for u in usuarios.json()] == ["gestor"]
    assert usuarios.json()[0]["primeiroAcessoPendente"] is True
