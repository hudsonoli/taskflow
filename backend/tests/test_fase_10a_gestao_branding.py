"""Fase 10A — Gestão da plataforma (`/gestao`) e nome comercial TaskFlow: o que o BACKEND garante.

A interface migrou de `/plataforma` para `/gestao` (frontend); a API continua em `/plataforma/*` com a MESMA autoridade (Administrador da Plataforma, nunca um
perfil tenant). Aqui ficam: slugs reservados das rotas globais, o e-mail transacional com a empresa em destaque e o nome comercial TaskFlow.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.empresa_slug import SLUG_RESERVADOS, validar_slug
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.test_acesso_por_slug import _token_do_email, _url_publica_slug, email, empresa_a, usuario_a  # noqa: F401  (fixtures reaproveitadas)
from tests.test_plataforma import PLAT, _payload_empresa, administrador, client_plataforma, usuario_plataforma  # noqa: F401  (fixtures reaproveitadas)
from tests.test_password_reset import URL_PUBLICA

pytestmark = pytest.mark.usefixtures("_url_publica_slug")


# ======================================================================================
# slugs reservados (rotas globais do host)
# ======================================================================================


def test_rotas_globais_estao_na_lista_de_slugs_reservados() -> None:
    assert {"gestao", "api", "e", "aprovacao", "plataforma", "login"} <= SLUG_RESERVADOS
    for reservado in ("gestao", "aprovacao", "plataforma", "api"):
        with pytest.raises(ValueError, match="reservado"):
            validar_slug(reservado)
    with pytest.raises(ValueError):  # "e" nem chega a reservado: é curto demais — recusado de qualquer forma
        validar_slug("e")


@pytest.mark.parametrize("reservado", ["gestao", "aprovacao", "e"])
def test_criar_empresa_com_slug_de_rota_global_e_recusado(client_plataforma: TestClient, reservado: str) -> None:
    resposta = client_plataforma.post(f"{PLAT}/empresas", json=_payload_empresa(slug=reservado))
    assert resposta.status_code == 422, resposta.text


def test_login_por_slug_reservado_nao_resolve_empresa(client: TestClient) -> None:
    for slug in ("gestao", "aprovacao"):
        resposta = client.post("/auth/login", json={"empresaSlug": slug, "email": "alguem@exemplo.com", "senha": "qualquer-senha-123"})
        assert resposta.status_code in (401, 422)
        assert "accessToken" not in resposta.text


# ======================================================================================
# e-mail transacional: empresa em destaque, produto TaskFlow
# ======================================================================================


def test_email_de_redefinicao_destaca_a_empresa_e_usa_o_nome_taskflow(
    client: TestClient, email, empresa_a: Empresa, usuario_a: Usuario  # noqa: F811
) -> None:
    resposta = client.post("/auth/password-reset/request", json={"empresaSlug": empresa_a.slug, "email": usuario_a.email})
    assert resposta.status_code == 200 and len(email.enviados) == 1
    enviado = email.enviados[-1]
    assert enviado["assunto"] == "Redefinição de senha — TaskFlow"
    texto = enviado["texto"]
    assert (empresa_a.nome_fantasia or empresa_a.nome) in texto and "via TaskFlow" in texto
    assert "TaskFloww" not in texto and "TaskFloww" not in enviado["assunto"]
    link, _ = _token_do_email(email)
    assert link.startswith(f"{URL_PUBLICA}/e/{empresa_a.slug}/redefinir-senha#token=")  # o slug do tenant continua no link


# ======================================================================================
# nome comercial na API
# ======================================================================================


def test_raiz_da_api_usa_o_nome_comercial(client: TestClient) -> None:
    corpo = client.get("/").json()
    assert corpo["app"] == "TaskFlow API"
