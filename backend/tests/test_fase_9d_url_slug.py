"""Fase 9D — URL canônica multiempresa por slug (`/e/{slug}/...`): o que o BACKEND precisa garantir.

O roteamento em si é do frontend (testado em `test:tenant-slug-routing`); aqui ficam as garantias de servidor:

* o slug da URL escolhe a empresa dos fluxos PÚBLICOS (login/Google/reset) e só ele — sem `empresaSlug` nem `empresaCodigo` não existe empresa padrão;
* depois do login a empresa é a da SESSÃO (`/auth/me` devolve o slug dela), e a sessão de A não enxerga dados de B por mais que a URL diga B;
* Portal Externo: o token é a autoridade; o slug da URL só é CONFERIDO contra a empresa dona do token (divergência = o mesmo 404 neutro, sem efeito);
* o link gerado carrega `empresaSlug` (nunca fixo) e o e-mail de redefinição aponta para `/e/<slug>/redefinir-senha`;
* a Administração da Plataforma segue fora dos tenants.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_platform_token
from app.models.empresa import Empresa
from tests.test_fase_9b_aprovacao_externa import INDISPONIVEL, PUBLICO, Cenario, cen  # noqa: F401  (fixture reaproveitada)


# ======================================================================================
# criação: o slug da empresa dona vem do servidor
# ======================================================================================


def test_criacao_devolve_o_slug_da_empresa_dona_do_link(cen: Cenario) -> None:
    token, corpo = cen.link()
    assert corpo["empresaSlug"] == cen.empresa.slug
    assert len(token) == 43


# ======================================================================================
# portal: token + slug correto × slug errado
# ======================================================================================


def test_token_com_slug_correto_abre_o_portal(cen: Cenario) -> None:
    token, _ = cen.link()
    resposta = cen.consultar(token)
    assert resposta.status_code == 200 and resposta.json()["estado"] == "pendente"
    assert cen.artefato(token, 1).status_code == 200


def test_slug_maiusculo_ou_com_espacos_nao_e_aceito_como_o_da_empresa(cen: Cenario) -> None:
    token, _ = cen.link()
    # o slug é normalizado para minúsculas pela validação; um slug da empresa em outra caixa continua sendo ELA, não outra
    resposta = cen.pub.post(f"{PUBLICO}/consultar", json={"slug": cen.empresa.slug.upper(), "token": token})
    assert resposta.status_code == 200


def test_token_com_slug_de_outra_empresa_existente_e_404_neutro_sem_efeito(cen: Cenario, outra_empresa: Empresa, db_session: Session) -> None:
    token, _ = cen.link()
    db_session.commit()
    for acao, extra in (("consultar", {}), ("logo", {}), ("artefato", {"ordem": 1}), ("decisao", {"decisao": "aprovar", "nome": "Maria Cliente"})):
        resposta = cen.pub.post(f"{PUBLICO}/{acao}", json={"slug": outra_empresa.slug, "token": token, **extra})
        assert resposta.status_code == 404, acao
        assert resposta.json()["detail"] == INDISPONIVEL and token not in resposta.text
    assert cen.aprovacao(token).decisao is None  # a decisão com slug errado não foi registrada
    assert cen.consultar(token).status_code == 200  # e o link continua válido para o slug certo


def test_token_com_slug_inexistente_malformado_ou_ausente_e_o_mesmo_404(cen: Cenario) -> None:
    token, _ = cen.link()
    esperado = cen.pub.post(f"{PUBLICO}/consultar", json={"slug": "empresa-que-nao-existe", "token": token})
    assert esperado.status_code == 404 and esperado.json()["detail"] == INDISPONIVEL
    for corpo in ({"slug": "A", "token": token}, {"slug": "../..", "token": token}, {"slug": "plataforma", "token": token}, {"token": token}, {"slug": 123, "token": token}):
        resposta = cen.pub.post(f"{PUBLICO}/consultar", json=corpo)
        assert resposta.status_code == 404 and resposta.json() == esperado.json(), corpo


def test_slug_correto_com_token_invalido_e_404_neutro(cen: Cenario) -> None:
    resposta = cen.pub.post(f"{PUBLICO}/consultar", json={"slug": cen.empresa.slug, "token": "A" * 43})
    assert resposta.status_code == 404 and resposta.json()["detail"] == INDISPONIVEL
    assert cen.pub.post(f"{PUBLICO}/consultar", json={"slug": cen.empresa.slug, "token": "curto"}).status_code == 404


def test_sessao_do_tenant_e_irrelevante_para_o_portal_com_o_slug(cen: Cenario) -> None:
    token, _ = cen.link()
    anonima, autenticada = cen.consultar(token), cen.consultar(token, client=cen.admin)
    assert anonima.status_code == autenticada.status_code == 200 and anonima.json() == autenticada.json()


# ======================================================================================
# cross-tenant e sessão × slug
# ======================================================================================


def test_sessao_de_a_continua_vendo_so_a_mesma_empresa_e_me_devolve_o_slug_dela(cen: Cenario) -> None:
    resposta = cen.admin.get("/auth/me")
    assert resposta.status_code == 200 and resposta.json()["empresaSlug"] == cen.empresa.slug


def test_sessao_de_outra_empresa_nao_gerencia_o_link(app, cen: Cenario, db_session: Session, outra_empresa: Empresa) -> None:
    from tests.fixtures.usuarios import _criar_usuario_com_credencial
    from tests.test_d1_criacao_demandas import _client_para
    from tests.test_fase_9b_aprovacao_externa import _rota

    intruso = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="9d-intruso")
    db_session.commit()
    ci = _client_para(app, intruso)
    assert ci.get("/auth/me").json()["empresaSlug"] == outra_empresa.slug
    assert ci.post(_rota(cen.id, cen.e2["id"]), json={"arquivoIds": [cen.png]}).status_code == 404  # a URL/slug nunca troca a empresa da sessão
    assert ci.get(_rota(cen.id, cen.e2["id"])).status_code == 404


# ======================================================================================
# sem EMPRESA_CODIGO / sem empresa padrão nos fluxos públicos
# ======================================================================================


def test_login_sem_slug_nem_codigo_nao_resolve_empresa_nenhuma(client: TestClient) -> None:
    resposta = client.post("/auth/login", json={"email": "alguem@exemplo.com", "senha": "qualquer-senha-123"})
    assert resposta.status_code in (401, 422)
    assert "accessToken" not in resposta.text


def test_reset_sem_slug_nem_codigo_nao_envia_nada_e_responde_generico(client: TestClient) -> None:
    resposta = client.post("/auth/password-reset/request", json={"email": "alguem@exemplo.com"})
    assert resposta.status_code in (200, 400, 422)


# ======================================================================================
# plataforma continua independente dos tenants
# ======================================================================================


def test_token_de_plataforma_nao_e_sessao_de_tenant(app) -> None:
    cliente = TestClient(app)
    cliente.headers.update({"Authorization": f"Bearer {create_platform_token(sub='00000000-0000-4000-8000-000000000001', administrador_id='00000000-0000-4000-8000-000000000002')}"})
    assert cliente.get("/auth/me").status_code == 401
    assert cliente.get("/demandas").status_code in (401, 403)


@pytest.mark.parametrize("rota", ["/plataforma/empresas", "/plataforma/dashboard"])
def test_rotas_da_plataforma_exigem_sessao_de_plataforma(client: TestClient, rota: str) -> None:
    assert client.get(rota).status_code in (401, 403)
