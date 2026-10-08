"""Fase 2 — acesso multiempresa por SLUG: login, Google, recuperação de senha e branding público de cada empresa.

Duas empresas lado a lado (A e B), cada uma com slug, usuário, cores, tema e logo próprios. O que a suíte precisa provar:

* a empresa de um fluxo PÚBLICO é resolvida pelo slug da URL e só por ele (nada de código fixo do servidor);
* credencial de A não entra em B e vice-versa, mesmo com o mesmo e-mail nas duas;
* depois do login a empresa é a da SESSÃO (`/auth/me`), nunca a do slug;
* token de reset de A nunca redefine senha em B (e o e-mail de A leva o slug de A);
* empresa inativa/inexistente/slug inválido: tudo igual e genérico (login, reset, Google, branding);
* branding público devolve só dados públicos e nunca mistura identidades.

O login legado (`empresaCodigo`) continua funcionando — testado em test_auth*/test_password_reset.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import auth as auth_routes
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.schemas.configuracao_personalizacao import PersonalizacaoUpdate
from app.services import auth_service as auth_service_module
from app.services.configuracao_personalizacao_service import ConfiguracaoPersonalizacaoService
from tests.fixtures.usuarios import SENHA_CONHECIDA, _criar_usuario_com_credencial
from tests.test_password_reset import EmailFalso, URL_PUBLICA
from tests.test_personalizacao_visual import png

pytestmark = pytest.mark.usefixtures("_url_publica_slug")

NOVA_SENHA = "OutraSenhaBoa456!"
GENERICA = "Credenciais inválidas"


@pytest.fixture()
def _url_publica_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    configuracao = replace(auth_routes.auth_service.settings, app_public_url=URL_PUBLICA)
    monkeypatch.setattr(auth_routes.auth_service, "settings", configuracao)


@pytest.fixture()
def email(monkeypatch: pytest.MonkeyPatch) -> EmailFalso:
    falso = EmailFalso()
    monkeypatch.setattr(auth_routes.auth_service, "configuracao_email_service", falso)
    return falso


def _nova_empresa(db: Session, nome: str, slug: str, *, status: str = "ativa") -> Empresa:
    agora = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid.uuid4()), nome=nome, codigo_interno=f"{slug}-{uuid.uuid4().hex[:6]}".upper(), slug=slug,
        status=status, created_at=agora, updated_at=agora,
    )
    db.add(empresa)
    db.flush()
    return empresa


@pytest.fixture()
def empresa_a(db_session: Session) -> Empresa:
    return _nova_empresa(db_session, "Alfa Comunicação", f"alfa-{uuid.uuid4().hex[:6]}")


@pytest.fixture()
def empresa_b(db_session: Session) -> Empresa:
    return _nova_empresa(db_session, "Beta Operações", f"beta-{uuid.uuid4().hex[:6]}")


@pytest.fixture()
def usuario_a(db_session: Session, empresa_a: Empresa) -> Usuario:
    return _criar_usuario_com_credencial(db_session, empresa=empresa_a, perfil_base="gestor", email_prefixo="a")


@pytest.fixture()
def usuario_b(db_session: Session, empresa_b: Empresa) -> Usuario:
    return _criar_usuario_com_credencial(db_session, empresa=empresa_b, perfil_base="gestor", email_prefixo="b")


def _login_slug(client: TestClient, slug: str, usuario: Usuario, senha: str = SENHA_CONHECIDA):
    return client.post("/auth/login", json={"empresaSlug": slug, "email": usuario.email, "senha": senha})


def _me(client: TestClient, token: str) -> dict:
    resposta = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --------------------------------------------------------------------------------------
# Formato do pedido: exatamente um identificador de empresa
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("caminho", ["/auth/login", "/auth/google", "/auth/password-reset/request", "/auth/password-reset/confirm"])
def test_pedido_publico_exige_exatamente_um_identificador_de_empresa(client: TestClient, caminho: str, empresa_a: Empresa) -> None:
    base = {"login": {"email": "x@y.z", "senha": "s"}, "google": {"email": "x@y.z", "idToken": "t"},
            "request": {"email": "x@y.z"}, "confirm": {"token": "t", "novaSenha": "a", "confirmacaoSenha": "a"}}
    corpo = base[caminho.rsplit("/", 1)[-1]]
    assert client.post(caminho, json=corpo).status_code == 422  # nenhum
    ambos = {**corpo, "empresaSlug": empresa_a.slug, "empresaCodigo": empresa_a.codigo_interno}
    assert client.post(caminho, json=ambos).status_code == 422  # os dois


# --------------------------------------------------------------------------------------
# Login por slug
# --------------------------------------------------------------------------------------


def test_login_por_slug_entra_na_empresa_do_slug(client: TestClient, empresa_a: Empresa, empresa_b: Empresa, usuario_a: Usuario, usuario_b: Usuario) -> None:
    ra = _login_slug(client, empresa_a.slug, usuario_a)
    rb = _login_slug(client, empresa_b.slug, usuario_b)
    assert ra.status_code == 200 and rb.status_code == 200
    ma, mb = _me(client, ra.json()["accessToken"]), _me(client, rb.json()["accessToken"])
    assert (ma["empresaId"], ma["empresaSlug"]) == (empresa_a.id, empresa_a.slug)
    assert (mb["empresaId"], mb["empresaSlug"]) == (empresa_b.id, empresa_b.slug)


def test_slug_e_normalizado_e_codigo_legado_continua_valendo(client: TestClient, empresa_a: Empresa, usuario_a: Usuario) -> None:
    assert _login_slug(client, f"  {empresa_a.slug.upper()}  ", usuario_a).status_code == 200
    legado = client.post("/auth/login", json={"empresaCodigo": empresa_a.codigo_interno, "email": usuario_a.email, "senha": SENHA_CONHECIDA})
    assert legado.status_code == 200  # /login legado = código da empresa padrão do servidor


def test_credencial_de_uma_empresa_nao_entra_na_outra(client: TestClient, empresa_a: Empresa, empresa_b: Empresa, usuario_a: Usuario, usuario_b: Usuario) -> None:
    for slug, usuario in ((empresa_b.slug, usuario_a), (empresa_a.slug, usuario_b)):
        r = _login_slug(client, slug, usuario)
        assert r.status_code == 401 and r.json()["detail"] == GENERICA


def test_mesmo_email_em_duas_empresas_entra_pelo_tenant_do_slug(
    client: TestClient, db_session: Session, empresa_a: Empresa, empresa_b: Empresa, usuario_a: Usuario
) -> None:
    from app.core.security import hash_password
    from app.models.usuario_credencial import UsuarioCredencial

    agora = datetime.now(timezone.utc)
    gemeo = Usuario(
        id=str(uuid.uuid4()), empresa_id=empresa_b.id, codigo_interno="GEMEO", nome="Gêmeo", email=usuario_a.email,
        perfil_base="gestor", acesso_sistema=True, status="ativo", created_at=agora, updated_at=agora,
    )
    db_session.add(gemeo)
    db_session.flush()
    db_session.add(UsuarioCredencial(
        id=str(uuid.uuid4()), usuario_id=gemeo.id, senha_hash=hash_password("SenhaDoGemeo789!"), senha_definida_em=agora,
        senha_deve_ser_alterada=False, created_at=agora, updated_at=agora,
    ))
    db_session.flush()
    ra = client.post("/auth/login", json={"empresaSlug": empresa_a.slug, "email": usuario_a.email, "senha": SENHA_CONHECIDA})
    rb = client.post("/auth/login", json={"empresaSlug": empresa_b.slug, "email": usuario_a.email, "senha": "SenhaDoGemeo789!"})
    assert _me(client, ra.json()["accessToken"])["empresaId"] == empresa_a.id
    assert _me(client, rb.json()["accessToken"])["empresaId"] == empresa_b.id
    # a senha de um tenant nunca vale no outro, mesmo e-mail
    assert client.post("/auth/login", json={"empresaSlug": empresa_b.slug, "email": usuario_a.email, "senha": SENHA_CONHECIDA}).status_code == 401


def test_depois_do_login_a_empresa_e_a_da_sessao_nao_a_do_slug(client: TestClient, empresa_a: Empresa, empresa_b: Empresa, usuario_a: Usuario) -> None:
    token = _login_slug(client, empresa_a.slug, usuario_a).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    # nenhuma rota autenticada aceita slug/empresa na URL ou query para trocar de tenant
    assert _me(client, token)["empresaId"] == empresa_a.id
    assert client.get(f"/empresas/{empresa_b.id}", headers=headers).status_code == 404  # B não existe para a sessão de A
    assert client.get("/empresas", headers=headers, params={"slug": empresa_b.slug, "empresaSlug": empresa_b.slug}).json()[0]["id"] == empresa_a.id
    assert client.get("/usuarios", headers={**headers, "X-Empresa-Slug": empresa_b.slug, "X-Tf-Tenant-Slug": empresa_b.slug},
                      params={"empresaId": empresa_b.id}).status_code == 403


@pytest.mark.parametrize("slug", ["", "x", "ab", "Tem Espaco", "com_underscore", "plataforma", "login", "admin", "../etc/passwd", "nao-existe-xyz", "a" * 80])
def test_slug_invalido_ou_inexistente_falha_com_a_mesma_resposta_generica(client: TestClient, usuario_a: Usuario, slug: str) -> None:
    r = client.post("/auth/login", json={"empresaSlug": slug or "x", "email": usuario_a.email, "senha": SENHA_CONHECIDA})
    assert r.status_code in (401, 422)
    if r.status_code == 401:
        assert r.json()["detail"] == GENERICA


def test_empresa_inativa_nao_autentica_por_slug(client: TestClient, db_session: Session, empresa_a: Empresa, usuario_a: Usuario) -> None:
    empresa_a.status = "inativa"
    db_session.flush()
    r = _login_slug(client, empresa_a.slug, usuario_a)
    assert r.status_code == 401 and r.json()["detail"] == GENERICA  # indistinguível de "não existe"


# --------------------------------------------------------------------------------------
# Google por slug (a verificação do token é mockada; o que importa é o contexto de empresa)
# --------------------------------------------------------------------------------------


def _mock_google(monkeypatch: pytest.MonkeyPatch, email_google: str) -> None:
    monkeypatch.setattr(
        auth_service_module, "verify_google_id_token",
        lambda token, settings=None: {"sub": "g-" + uuid.uuid4().hex[:10], "email": email_google, "email_verified": True},
    )


def test_google_resolve_a_empresa_pelo_slug_e_nao_cruza_tenant(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session: Session, empresa_a: Empresa, empresa_b: Empresa
) -> None:
    agora = datetime.now(timezone.utc)
    pessoa = Usuario(
        id=str(uuid.uuid4()), empresa_id=empresa_a.id, codigo_interno="GOO-A", nome="Pessoa Google A", email="pessoa@alfa.example",
        perfil_base="operador", acesso_sistema=True, status="ativo", created_at=agora, updated_at=agora,
    )
    db_session.add(pessoa)
    db_session.flush()
    _mock_google(monkeypatch, "pessoa@alfa.example")
    ok = client.post("/auth/google", json={"empresaSlug": empresa_a.slug, "email": "pessoa@alfa.example", "idToken": "tok"})
    assert ok.status_code == 200
    assert _me(client, ok.json()["accessToken"])["empresaId"] == empresa_a.id
    # mesmo Google na URL da OUTRA empresa: negado (cross-tenant), sempre a mesma mensagem genérica
    _mock_google(monkeypatch, "pessoa@alfa.example")
    negado = client.post("/auth/google", json={"empresaSlug": empresa_b.slug, "email": "pessoa@alfa.example", "idToken": "tok"})
    assert negado.status_code == 403


def test_google_com_empresa_inativa_ou_slug_inexistente_e_negado(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session: Session, empresa_a: Empresa
) -> None:
    _mock_google(monkeypatch, "qualquer@x.example")
    empresa_a.status = "inativa"
    db_session.flush()
    for slug in (empresa_a.slug, "nao-existe-xyz"):
        r = client.post("/auth/google", json={"empresaSlug": slug, "email": "qualquer@x.example", "idToken": "tok"})
        assert r.status_code == 403


# --------------------------------------------------------------------------------------
# Recuperação de senha por slug
# --------------------------------------------------------------------------------------


def _token_do_email(falso: EmailFalso) -> tuple[str, str]:
    import re

    texto = falso.enviados[-1]["texto"]
    link = re.search(r"https?://\S+", texto).group(0)
    return link, link.split("#token=", 1)[1]


def test_link_de_reset_por_slug_volta_ao_mesmo_tenant(client: TestClient, email: EmailFalso, empresa_a: Empresa, usuario_a: Usuario) -> None:
    r = client.post("/auth/password-reset/request", json={"empresaSlug": empresa_a.slug, "email": usuario_a.email})
    assert r.status_code == 200 and len(email.enviados) == 1
    link, token = _token_do_email(email)
    assert link.startswith(f"{URL_PUBLICA}/e/{empresa_a.slug}/redefinir-senha#token=")
    assert "?token=" not in link  # token no fragmento, nunca na query


def test_link_de_reset_legado_continua_sem_slug(client: TestClient, email: EmailFalso, empresa_a: Empresa, usuario_a: Usuario) -> None:
    client.post("/auth/password-reset/request", json={"empresaCodigo": empresa_a.codigo_interno, "email": usuario_a.email})
    link, _ = _token_do_email(email)
    assert link.startswith(f"{URL_PUBLICA}/redefinir-senha#token=")


def test_token_de_a_nao_redefine_senha_em_b(
    client: TestClient, email: EmailFalso, empresa_a: Empresa, empresa_b: Empresa, usuario_a: Usuario, usuario_b: Usuario
) -> None:
    client.post("/auth/password-reset/request", json={"empresaSlug": empresa_a.slug, "email": usuario_a.email})
    _, token_a = _token_do_email(email)
    cruzado = client.post(
        "/auth/password-reset/confirm",
        json={"empresaSlug": empresa_b.slug, "token": token_a, "novaSenha": NOVA_SENHA, "confirmacaoSenha": NOVA_SENHA},
    )
    assert cruzado.status_code == 400  # mensagem única de link inválido
    # e o token continua intacto: o dono ainda consegue usá-lo no tenant certo
    certo = client.post(
        "/auth/password-reset/confirm",
        json={"empresaSlug": empresa_a.slug, "token": token_a, "novaSenha": NOVA_SENHA, "confirmacaoSenha": NOVA_SENHA},
    )
    assert certo.status_code == 204
    assert _login_slug(client, empresa_a.slug, usuario_a, NOVA_SENHA).status_code == 200
    assert _login_slug(client, empresa_b.slug, usuario_b).status_code == 200  # B nunca foi tocada
    # uso único preservado
    de_novo = client.post(
        "/auth/password-reset/confirm",
        json={"empresaSlug": empresa_a.slug, "token": token_a, "novaSenha": "Terceira789!!", "confirmacaoSenha": "Terceira789!!"},
    )
    assert de_novo.status_code == 400


def test_reset_com_slug_nao_enumera_conta_nem_empresa(client: TestClient, email: EmailFalso, empresa_a: Empresa, usuario_a: Usuario) -> None:
    existente = client.post("/auth/password-reset/request", json={"empresaSlug": empresa_a.slug, "email": usuario_a.email})
    inexistente = client.post("/auth/password-reset/request", json={"empresaSlug": empresa_a.slug, "email": "ninguem@nada.example"})
    sem_empresa = client.post("/auth/password-reset/request", json={"empresaSlug": "nao-existe-xyz", "email": usuario_a.email})
    assert existente.status_code == inexistente.status_code == sem_empresa.status_code == 200
    assert existente.json() == inexistente.json() == sem_empresa.json()
    assert len(email.enviados) == 1  # só o primeiro realmente enviou


def test_reset_de_empresa_inativa_nao_envia_nem_confirma(
    client: TestClient, email: EmailFalso, db_session: Session, empresa_a: Empresa, usuario_a: Usuario
) -> None:
    client.post("/auth/password-reset/request", json={"empresaSlug": empresa_a.slug, "email": usuario_a.email})
    _, token = _token_do_email(email)
    empresa_a.status = "inativa"
    db_session.flush()
    assert client.post("/auth/password-reset/request", json={"empresaSlug": empresa_a.slug, "email": usuario_a.email}).status_code == 200
    assert len(email.enviados) == 1
    r = client.post("/auth/password-reset/confirm",
                    json={"empresaSlug": empresa_a.slug, "token": token, "novaSenha": NOVA_SENHA, "confirmacaoSenha": NOVA_SENHA})
    assert r.status_code == 400


# --------------------------------------------------------------------------------------
# Branding público por slug
# --------------------------------------------------------------------------------------


def _personalizar(db: Session, empresa: Empresa, primaria: str, secundaria: str, tema: str, *, logo: bool = True) -> None:
    servico = ConfiguracaoPersonalizacaoService()
    servico.atualizar(db, empresa_id=empresa.id, payload=PersonalizacaoUpdate(corPrimaria=primaria, corSecundaria=secundaria, tema=tema))
    if logo:
        servico.salvar_logo(db, empresa_id=empresa.id, conteudo=png(), nome_arquivo="logo.png", content_type="image/png")


@pytest.fixture()
def empresas_personalizadas(db_session: Session, empresa_a: Empresa, empresa_b: Empresa) -> None:
    _personalizar(db_session, empresa_a, "#ff7a00", "#0891b2", "escuro")
    _personalizar(db_session, empresa_b, "#16a34a", "#9333ea", "claro", logo=False)


def test_branding_publico_de_cada_empresa_nao_se_mistura(client: TestClient, empresas_personalizadas, empresa_a: Empresa, empresa_b: Empresa) -> None:
    for _ in range(2):  # A → B → A → B: nenhuma contaminação
        a = client.get(f"/publico/empresas/{empresa_a.slug}/branding").json()
        b = client.get(f"/publico/empresas/{empresa_b.slug}/branding").json()
        assert (a["corPrimaria"], a["corSecundaria"], a["tema"], a["logoDisponivel"], a["disponivel"]) == ("#ff7a00", "#0891b2", "escuro", True, True)
        assert (b["corPrimaria"], b["corSecundaria"], b["tema"], b["logoDisponivel"], b["disponivel"]) == ("#16a34a", "#9333ea", "claro", False, True)
        assert a["nomeExibicao"] == "Alfa Comunicação" and b["nomeExibicao"] == "Beta Operações"


def test_branding_publico_so_expoe_dados_publicos(client: TestClient, empresas_personalizadas, empresa_a: Empresa) -> None:
    corpo = client.get(f"/publico/empresas/{empresa_a.slug}/branding").json()
    assert set(corpo) == {"corPrimaria", "corSecundaria", "tema", "logoDisponivel", "logoVersao", "padrao", "disponivel", "nomeExibicao"}
    texto = str(corpo)
    assert empresa_a.id not in texto and empresa_a.codigo_interno not in texto


def test_logo_publico_por_slug_serve_so_o_logo_da_propria_empresa(client: TestClient, empresas_personalizadas, empresa_a: Empresa, empresa_b: Empresa) -> None:
    r = client.get(f"/publico/empresas/{empresa_a.slug}/branding/logo")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.headers["x-content-type-options"] == "nosniff" and r.content == png()
    assert "personalizacao/" not in r.headers.get("content-disposition", "")
    assert client.get(f"/publico/empresas/{empresa_b.slug}/branding/logo").status_code == 404  # B não tem logo; nunca o de A
    versao = client.get(f"/publico/empresas/{empresa_a.slug}/branding").json()["logoVersao"]
    assert "immutable" in client.get(f"/publico/empresas/{empresa_a.slug}/branding/logo", params={"v": versao}).headers["cache-control"]


@pytest.mark.parametrize("slug", ["nao-existe-xyz", "plataforma", "AB", "x" * 70, "com espaco"])
def test_slug_inexistente_reservado_ou_malformado_cai_na_identidade_neutra(client: TestClient, empresas_personalizadas, slug: str) -> None:
    r = client.get(f"/publico/empresas/{slug}/branding")
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        corpo = r.json()
        assert corpo["disponivel"] is False and corpo["nomeExibicao"] is None
        assert (corpo["corPrimaria"], corpo["corSecundaria"], corpo["tema"], corpo["logoDisponivel"], corpo["padrao"]) == ("#6366f1", "#7c3aed", "claro", False, True)
    assert client.get(f"/publico/empresas/{slug}/branding/logo").status_code in (404, 422)


def test_branding_de_empresa_inativa_e_neutro_e_sem_logo(client: TestClient, db_session: Session, empresas_personalizadas, empresa_a: Empresa) -> None:
    empresa_a.status = "inativa"
    db_session.flush()
    corpo = client.get(f"/publico/empresas/{empresa_a.slug}/branding").json()
    assert corpo["disponivel"] is False and corpo["nomeExibicao"] is None
    assert corpo["corPrimaria"] == "#6366f1" and corpo["logoDisponivel"] is False
    assert client.get(f"/publico/empresas/{empresa_a.slug}/branding/logo").status_code == 404


@pytest.mark.parametrize("tentativa", ["..%2f..%2fetc%2fpasswd", "%2e%2e", "a%00b", "..\\..\\windows"])
def test_slug_nao_permite_path_traversal(client: TestClient, tentativa: str) -> None:
    for sufixo in ("branding", "branding/logo"):
        r = client.get(f"/publico/empresas/{tentativa}/{sufixo}")
        assert r.status_code in (200, 404, 422)
        assert "root:" not in r.text and "[extensions]" not in r.text.lower()


def test_resposta_publica_nao_exige_sessao_e_nao_revela_segredo(client: TestClient, empresas_personalizadas, empresa_a: Empresa) -> None:
    r = client.get(f"/publico/empresas/{empresa_a.slug}/branding")  # sem Authorization
    assert r.status_code == 200
    assert not any(t in r.text.lower() for t in ("smtp", "senha", "token", "documento", "usuario"))


# --------------------------------------------------------------------------------------
# Plataforma e tenant seguem separados
# --------------------------------------------------------------------------------------


def test_rotas_publicas_novas_nao_autenticam_nem_aceitam_token_de_plataforma(client: TestClient) -> None:
    from app.core.security import create_platform_token

    token = create_platform_token(sub=str(uuid.uuid4()), administrador_id=str(uuid.uuid4()))
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401  # token de plataforma não serve de sessão tenant
