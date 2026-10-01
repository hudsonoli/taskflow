"""Testes de `POST /auth/google` — login Google Workspace para usuário PRÉ-CADASTRADO.

Nunca chama a internet: `verify_google_id_token` é monkeypatchado em
`app.services.auth_service` (onde o nome É USADO, não onde é definido — mock no ponto de
consumo). A verificação real da biblioteca `google-auth` (assinatura/issuer/audience/
expiração) tem seus próprios testes em `tests/test_security_google.py` — aqui o foco é a
regra de negócio: quem pode entrar, o que é gravado, e que nenhum caminho revela detalhe."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import AuthTokenError
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.api.routes import auth as auth_route_module
from app.repositories.usuario_repository import UsuarioRepository
from app.services import auth_service as auth_service_module
from tests.helpers.api import post_json

EMAIL_PRE_CADASTRADO = "pessoa.pre.cadastrada@empresa-teste.com"


def _usuario_pre_cadastrado(
    db_session: Session,
    *,
    empresa: Empresa,
    email: str = EMAIL_PRE_CADASTRADO,
    status: str = "ativo",
    acesso_sistema: bool = True,
    google_sub: str | None = None,
    foto_url: str | None = None,
) -> Usuario:
    """Pré-cadastro SEM senha — nenhuma UsuarioCredencial é criada aqui, provando que a
    arquitetura atual já suporta usuário aguardando primeiro acesso via Google (nunca cria
    usuário novo a partir de uma conta Google)."""
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"GOOGLE-{sufixo}",
        nome="Pessoa Pre Cadastrada",
        email=email,
        perfil_base="operador",
        acesso_sistema=acesso_sistema,
        status=status,
        created_at=agora,
        updated_at=agora,
        google_sub=google_sub,
        foto_url=foto_url,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _mock_claims(**overrides) -> dict:
    claims = {
        "sub": "google-sub-" + uuid.uuid4().hex[:12],
        "email": EMAIL_PRE_CADASTRADO,
        "email_verified": True,
        "given_name": "Pessoa",
        "family_name": "Cadastrada",
        "locale": "pt-BR",
        "picture": "https://lh3.googleusercontent.com/foto-exemplo",
    }
    claims.update(overrides)
    return claims


def _mock_verify_sucesso(monkeypatch, claims: dict) -> None:
    def fake(id_token_value, *, settings=None):
        return claims

    monkeypatch.setattr(auth_service_module, "verify_google_id_token", fake)


def _mock_verify_falha(monkeypatch) -> None:
    def fake(id_token_value, *, settings=None):
        raise AuthTokenError("Token Google inválido")

    monkeypatch.setattr(auth_service_module, "verify_google_id_token", fake)


def _post_google(client, *, empresa: Empresa, email: str, id_token: str = "id-token-fake"):
    return post_json(
        client,
        "/auth/google",
        {"empresaCodigo": empresa.codigo_interno, "email": email, "idToken": id_token},
    )


# 1 + 2 — pré-cadastrado SEM senha entra via Google (primeiro login)
def test_pre_cadastrado_sem_senha_entra_via_google(client, db_session, empresa, monkeypatch):
    usuario = _usuario_pre_cadastrado(db_session, empresa=empresa)
    assert UsuarioRepository().get_by_id(db_session, usuario.id) is not None
    tem_credencial = (
        db_session.query(UsuarioCredencial).filter(UsuarioCredencial.usuario_id == usuario.id).first()
    )
    assert tem_credencial is None  # confirma: sem senha, mesmo assim pode entrar via Google

    _mock_verify_sucesso(monkeypatch, _mock_claims())
    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["accessToken"]
    assert corpo["mustChangePassword"] is False


# 3 — inexistente → 403 genérico
def test_usuario_inexistente_nega(client, empresa, monkeypatch):
    _mock_verify_sucesso(monkeypatch, _mock_claims(email="ninguem@empresa-teste.com"))
    resposta = _post_google(client, empresa=empresa, email="ninguem@empresa-teste.com")
    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["detail"] == "Acesso não autorizado."


# 4 — inativo → 403
def test_usuario_inativo_nega(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa, status="inativo")
    _mock_verify_sucesso(monkeypatch, _mock_claims())
    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["detail"] == "Acesso não autorizado."


# 5 — acesso_sistema=false → 403
def test_acesso_sistema_false_nega(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa, acesso_sistema=False)
    _mock_verify_sucesso(monkeypatch, _mock_claims())
    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 403, resposta.text


# 6 — token inválido (verify_google_id_token rejeita) → 401
def test_token_invalido_401(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa)
    _mock_verify_falha(monkeypatch)
    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 401, resposta.text


# 7 — audience inválida: mesma camada de "token inválido" (a biblioteca google-auth rejeita
# e verify_google_id_token converte em AuthTokenError — comportamento específico da
# audience é testado isoladamente em tests/test_security_google.py). Aqui confirmamos que o
# router nunca distingue o motivo — mesma resposta 401 genérica de test_token_invalido_401.
def test_audience_invalida_mesma_resposta_generica_401(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa)
    _mock_verify_falha(monkeypatch)
    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 401, resposta.text
    assert resposta.json()["detail"] == "Token Google inválido"


# 8 — email_verified=false → 401 (camada de confiança do token, não de autorização)
def test_email_nao_verificado_401(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa)
    _mock_verify_sucesso(monkeypatch, _mock_claims(email_verified=False))
    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 401, resposta.text


# 9 — email do claim != email digitado → 401
def test_email_claim_diferente_do_digitado_401(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa)
    _mock_verify_sucesso(monkeypatch, _mock_claims(email="outro@empresa-teste.com"))
    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 401, resposta.text


# 10 — domínio hd inválido quando GOOGLE_WORKSPACE_ALLOWED_DOMAIN está configurado → 401
def test_dominio_hd_invalido_quando_allowlist_ativa_401(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa)
    # `Settings` é um dataclass frozen — a instância usada pelo AuthService do router é um
    # singleton de módulo (`auth_service.settings`); mutamos esse atributo diretamente só
    # para este teste e desfazemos no fim (Settings não suporta atribuição normal, por isso
    # `object.__setattr__`, não é um padrão a reaproveitar fora de teste).
    settings_em_uso = auth_route_module.auth_service.settings
    original = settings_em_uso.google_workspace_allowed_domain
    object.__setattr__(settings_em_uso, "google_workspace_allowed_domain", "empresa-correta.com")
    try:
        _mock_verify_sucesso(monkeypatch, _mock_claims(hd="empresa-errada.com"))
        resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
        assert resposta.status_code == 401, resposta.text
    finally:
        object.__setattr__(settings_em_uso, "google_workspace_allowed_domain", original)


# 11 + 12 — primeiro login grava google_sub e google_linked_at
def test_primeiro_login_grava_google_sub_e_linked_at(client, db_session, empresa, monkeypatch):
    usuario = _usuario_pre_cadastrado(db_session, empresa=empresa)
    claims = _mock_claims(sub="sub-primeiro-vinculo")
    _mock_verify_sucesso(monkeypatch, claims)

    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 200, resposta.text

    db_session.refresh(usuario)
    assert usuario.google_sub == "sub-primeiro-vinculo"
    assert usuario.google_linked_at is not None
    assert usuario.last_google_login_at is not None


# 13 — foto_url vazia recebe picture
def test_foto_vazia_recebe_picture(client, db_session, empresa, monkeypatch):
    usuario = _usuario_pre_cadastrado(db_session, empresa=empresa, foto_url=None)
    claims = _mock_claims(picture="https://lh3.googleusercontent.com/nova-foto")
    _mock_verify_sucesso(monkeypatch, claims)

    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 200, resposta.text

    db_session.refresh(usuario)
    assert usuario.foto_url == "https://lh3.googleusercontent.com/nova-foto"


# 14 — foto existente NÃO é sobrescrita
def test_foto_existente_nao_sobrescrita(client, db_session, empresa, monkeypatch):
    usuario = _usuario_pre_cadastrado(db_session, empresa=empresa, foto_url="https://cdn.taskfloww.local/foto-pessoal.jpg")
    claims = _mock_claims(picture="https://lh3.googleusercontent.com/foto-google")
    _mock_verify_sucesso(monkeypatch, claims)

    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 200, resposta.text

    db_session.refresh(usuario)
    assert usuario.foto_url == "https://cdn.taskfloww.local/foto-pessoal.jpg"


# 15 + 16 — segundo login usa google_sub; alteração de e-mail no TaskFloww não quebra login
def test_segundo_login_usa_google_sub_mesmo_apos_mudanca_de_email(client, db_session, empresa, monkeypatch):
    usuario = _usuario_pre_cadastrado(db_session, empresa=empresa, google_sub="sub-ja-vinculado")

    # Admin muda o e-mail do usuário no TaskFloww depois do vínculo.
    usuario.email = "novo-email-taskfloww@empresa-teste.com"
    db_session.flush()

    # O e-mail digitado no login (e o claim do Google) continua sendo o e-mail REAL da conta
    # Google (nunca precisa bater com o que está salvo no TaskFloww agora).
    claims = _mock_claims(sub="sub-ja-vinculado", email=EMAIL_PRE_CADASTRADO)
    _mock_verify_sucesso(monkeypatch, claims)

    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 200, resposta.text

    db_session.refresh(usuario)
    assert usuario.google_sub == "sub-ja-vinculado"
    assert usuario.email == "novo-email-taskfloww@empresa-teste.com"  # não foi revertido


# 17 — sub já vinculado a outro usuário: a UNIQUE constraint é a garantia final (defesa em
# profundidade) — forçamos o conflito direto no flush, simulando uma corrida vencida por
# outra requisição um instante antes.
def test_sub_ja_vinculado_a_outro_usuario_nega_via_conflito(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa)
    claims = _mock_claims()
    _mock_verify_sucesso(monkeypatch, claims)

    def flush_que_falha(*args, **kwargs):
        raise IntegrityError("duplicate key", {}, Exception("uq_usuarios_google_sub"))

    monkeypatch.setattr(db_session, "flush", flush_que_falha)

    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["detail"] == "Acesso não autorizado."


# 18 — usuário encontrado por e-mail já possui OUTRO google_sub → nega (nunca revincula)
def test_usuario_encontrado_por_email_ja_possui_outro_sub_nega(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa, google_sub="sub-antigo-ja-vinculado")
    claims = _mock_claims(sub="sub-completamente-novo")
    _mock_verify_sucesso(monkeypatch, claims)

    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 403, resposta.text
    assert resposta.json()["detail"] == "Acesso não autorizado."


# 19 — cross-tenant → nega (usuário vinculado pertence a OUTRA empresa)
def test_cross_tenant_nega(client, db_session, empresa, outra_empresa, monkeypatch):
    usuario = _usuario_pre_cadastrado(db_session, empresa=empresa, google_sub="sub-de-outra-empresa")
    claims = _mock_claims(sub="sub-de-outra-empresa", email=usuario.email)
    _mock_verify_sucesso(monkeypatch, claims)

    resposta = _post_google(client, empresa=outra_empresa, email=usuario.email)
    assert resposta.status_code == 403, resposta.text


# 20 — RBAC do JWT emitido continua vindo do Usuario, nunca do Google
def test_rbac_do_token_vem_do_usuario_nao_do_google(client, db_session, empresa, monkeypatch):
    usuario = _usuario_pre_cadastrado(db_session, empresa=empresa)
    assert usuario.perfil_base == "operador"
    claims = _mock_claims()
    _mock_verify_sucesso(monkeypatch, claims)

    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code == 200, resposta.text

    token = resposta.json()["accessToken"]
    claims_jwt = jwt.decode(token, options={"verify_signature": False})
    assert claims_jwt["perfil_base"] == "operador"
    assert claims_jwt["sub"] == usuario.id


# 21 — concorrência: conflito de unique não vira 500 (mesma mecânica do item 17, nome
# próprio pra deixar a cobertura explícita por si só)
def test_concorrencia_sub_duplicado_nao_produz_500(client, db_session, empresa, monkeypatch):
    _usuario_pre_cadastrado(db_session, empresa=empresa)
    claims = _mock_claims()
    _mock_verify_sucesso(monkeypatch, claims)

    def flush_que_falha(*args, **kwargs):
        raise IntegrityError("duplicate key", {}, Exception("uq_usuarios_google_sub"))

    monkeypatch.setattr(db_session, "flush", flush_que_falha)

    resposta = _post_google(client, empresa=empresa, email=EMAIL_PRE_CADASTRADO)
    assert resposta.status_code != 500
    assert resposta.status_code == 403


# Login local continua intacto (zero regressão) — prova rápida de que a rota /auth/login
# não foi tocada por esta mudança.
def test_login_local_continua_funcionando(client, db_session, empresa):
    from app.core.security import hash_password

    agora = datetime.now(timezone.utc)
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno="LOCAL-" + uuid.uuid4().hex[:8],
        nome="Usuario Local",
        email="local@empresa-teste.com",
        perfil_base="admin",
        acesso_sistema=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(usuario)
    db_session.flush()
    credencial = UsuarioCredencial(
        id=str(uuid.uuid4()),
        usuario_id=usuario.id,
        senha_hash=hash_password("SenhaValida123!"),
        senha_definida_em=agora,
        senha_deve_ser_alterada=False,
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(credencial)
    db_session.flush()

    resposta = post_json(
        client,
        "/auth/login",
        {"empresaCodigo": empresa.codigo_interno, "email": "local@empresa-teste.com", "senha": "SenhaValida123!"},
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["accessToken"]
