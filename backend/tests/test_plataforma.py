"""Fase 1B — Administração da Plataforma (`/plataforma/*`): autoridade separada do RBAC tenant.

Cobre: sessão de plataforma (troca do token tenant), isolamento dos dois tipos de token, revogação imediata, CRUD de
empresas (slug/código/documento, inativar/reativar, empresa que hospeda administrador ativo), branding de qualquer
empresa (mesma validação do tenant, isolado por empresa), criação de Gestor (perfil forçado, senha temporária one-shot,
troca obrigatória, sem vazamento em evento/log), privacidade do ator (conta de sistema) e o CLI de bootstrap.

SEGUNDO_TENANT_GO_LIVE_BLOQUEADO: o login do produto ainda usa EMPRESA_CODIGO; estes testes exercitam a API, não o login web.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli import seed_platform_admin
from app.core.security import (
    AuthTokenError,
    create_access_token,
    create_platform_token,
    decode_access_token,
    decode_platform_token,
)
from app.dependencies.plataforma import require_platform_admin
from app.models.administrador_plataforma import AdministradorPlataforma
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.services.plataforma_service import gerar_senha_temporaria

from tests.fixtures.usuarios import SENHA_CONHECIDA, _criar_usuario_com_credencial
from tests.test_personalizacao_visual import png

PLAT = "/plataforma"


# --------------------------------------------------------------------------------------
# Fixtures locais
# --------------------------------------------------------------------------------------


def _client(app, token: str | None) -> TestClient:
    cliente = TestClient(app)
    if token:
        cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _tenant_client(app, usuario: Usuario) -> TestClient:
    return _client(app, create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base))


def _conceder(db: Session, usuario: Usuario, *, ativo: bool = True) -> AdministradorPlataforma:
    agora = datetime.now(timezone.utc)
    linha = AdministradorPlataforma(
        id=str(uuid.uuid4()), usuario_id=usuario.id, ativo=ativo, criado_em=agora,
        revogado_em=None if ativo else agora,
    )
    db.add(linha)
    db.flush()
    return linha


@pytest.fixture()
def usuario_plataforma(db_session: Session, empresa: Empresa) -> Usuario:
    """Como o proprietário real: conta de sistema, perfil admin legado, dentro de uma empresa."""
    conta = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="admin", email_prefixo="plataforma")
    conta.is_system_account = True
    conta.nome = "Proprietário Plataforma"
    db_session.flush()
    return conta


@pytest.fixture()
def administrador(db_session: Session, usuario_plataforma: Usuario) -> AdministradorPlataforma:
    return _conceder(db_session, usuario_plataforma)


@pytest.fixture()
def client_plataforma(app, administrador: AdministradorPlataforma, usuario_plataforma: Usuario) -> TestClient:
    return _client(app, create_platform_token(sub=usuario_plataforma.id, administrador_id=administrador.id))


def _payload_empresa(**extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    corpo = {"nome": f"Empresa {sufixo}", "codigoInterno": f"emp-{sufixo}"}
    corpo.update(extra)
    return corpo


def _criar_empresa(client: TestClient, **extra) -> dict:
    resposta = client.post(f"{PLAT}/empresas", json=_payload_empresa(**extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# --------------------------------------------------------------------------------------
# Tokens: tipo próprio e isolamento mútuo
# --------------------------------------------------------------------------------------


def test_decoders_sao_mutuamente_exclusivos(usuario_plataforma: Usuario, administrador: AdministradorPlataforma) -> None:
    plataforma = create_platform_token(sub=usuario_plataforma.id, administrador_id=administrador.id)
    tenant = create_access_token(sub=usuario_plataforma.id, empresa_id=usuario_plataforma.empresa_id, perfil_base="admin")
    assert decode_platform_token(plataforma)["tipo"] == "plataforma"
    assert decode_access_token(tenant)["tipo"] == "access"
    with pytest.raises(AuthTokenError):
        decode_access_token(plataforma)  # o decoder tenant NÃO foi enfraquecido
    with pytest.raises(AuthTokenError):
        decode_platform_token(tenant)


def test_token_de_plataforma_expirado_e_recusado(usuario_plataforma: Usuario, administrador: AdministradorPlataforma) -> None:
    velho = create_platform_token(
        sub=usuario_plataforma.id, administrador_id=administrador.id,
        now=datetime.now(timezone.utc) - timedelta(hours=2), expires_delta=timedelta(minutes=1),
    )
    with pytest.raises(AuthTokenError):
        decode_platform_token(velho)


# --------------------------------------------------------------------------------------
# Sessão de plataforma e capacidade
# --------------------------------------------------------------------------------------


def test_sessao_troca_o_token_tenant_pelo_de_plataforma(app, usuario_plataforma: Usuario, administrador) -> None:
    resposta = _tenant_client(app, usuario_plataforma).post(f"{PLAT}/sessao")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["tokenType"] == "bearer" and corpo["expiresIn"] > 0
    assert decode_platform_token(corpo["accessToken"])["adm"] == administrador.id
    assert _client(app, corpo["accessToken"]).get(f"{PLAT}/me").status_code == 200


def test_sessao_exige_ser_administrador_ativo(app, usuario_gestor: Usuario, db_session: Session, usuario_plataforma: Usuario) -> None:
    assert _tenant_client(app, usuario_gestor).post(f"{PLAT}/sessao").status_code == 403
    revogado = _conceder(db_session, usuario_plataforma, ativo=False)
    assert revogado.ativo is False
    assert _tenant_client(app, usuario_plataforma).post(f"{PLAT}/sessao").status_code == 403
    assert _client(app, None).post(f"{PLAT}/sessao").status_code == 401


def test_acesso_diz_se_o_usuario_e_administrador(app, usuario_plataforma: Usuario, administrador, usuario_gestor: Usuario) -> None:
    assert _tenant_client(app, usuario_plataforma).get(f"{PLAT}/acesso").json() == {"administradorPlataforma": True}
    assert _tenant_client(app, usuario_gestor).get(f"{PLAT}/acesso").json() == {"administradorPlataforma": False}


def test_me_devolve_so_o_necessario(client_plataforma: TestClient, usuario_plataforma: Usuario, administrador) -> None:
    corpo = client_plataforma.get(f"{PLAT}/me").json()
    assert set(corpo) == {"administradorId", "usuarioId", "nome", "ativo", "criadoEm"}
    assert corpo["administradorId"] == administrador.id and corpo["usuarioId"] == usuario_plataforma.id and corpo["ativo"] is True


# --------------------------------------------------------------------------------------
# Isolamento: tenant × plataforma
# --------------------------------------------------------------------------------------

ROTAS_PLATAFORMA_LEITURA = ["/me", "/empresas"]


@pytest.mark.parametrize("caminho", ROTAS_PLATAFORMA_LEITURA)
def test_token_tenant_nao_entra_em_plataforma(app, usuario_plataforma: Usuario, administrador, caminho: str) -> None:
    for usuario in (usuario_plataforma,):  # até o MESMO usuário administrador: o token tenant não serve
        assert _tenant_client(app, usuario).get(f"{PLAT}{caminho}").status_code in (401, 403)


def test_tenant_admin_gestor_e_usuario_recebem_negado_em_toda_a_plataforma(
    app, client_admin: TestClient, client_gestor: TestClient, client_operador: TestClient, empresa: Empresa
) -> None:
    for cliente in (client_admin, client_gestor, client_operador):
        assert cliente.get(f"{PLAT}/me").status_code in (401, 403)
        assert cliente.get(f"{PLAT}/empresas").status_code in (401, 403)
        assert cliente.post(f"{PLAT}/empresas", json=_payload_empresa()).status_code in (401, 403)
        assert cliente.get(f"{PLAT}/empresas/{empresa.id}/usuarios").status_code in (401, 403)
        assert cliente.post(f"{PLAT}/empresas/{empresa.id}/gestores", json={"nome": "X", "email": "x@x.co"}).status_code in (401, 403)


def test_token_de_plataforma_nao_entra_em_rotas_tenant(client_plataforma: TestClient, empresa: Empresa) -> None:
    for caminho in ("/usuarios/me", "/auth/me", "/empresas", "/notificacoes", "/personalizacao/publica"):
        if caminho == "/personalizacao/publica":
            continue  # pública: não autentica ninguém
        assert client_plataforma.get(caminho).status_code in (401, 403), caminho
    assert client_plataforma.get("/usuarios", params={"empresaId": empresa.id}).status_code in (401, 403)
    assert client_plataforma.get("/demandas").status_code in (401, 403)


def test_sem_token_e_401_em_toda_a_plataforma(app) -> None:
    anonimo = _client(app, None)
    assert anonimo.get(f"{PLAT}/me").status_code == 401
    assert anonimo.get(f"{PLAT}/empresas").status_code == 401


def test_toda_rota_de_plataforma_tem_guarda(app) -> None:
    """Nenhuma rota `/plataforma/*` fica sem guarda: ou `require_platform_admin`, ou as duas que partem da sessão
    TENANT (`/sessao` e `/acesso`)."""
    from app.dependencies.auth import get_current_user_password_ready

    permitidas_tenant = {"/plataforma/sessao", "/plataforma/acesso"}
    from app.api.routes import plataforma as modulo_plataforma

    # FastAPI recente aninha os routers incluídos; o router original traz as rotas e seus dependants.
    rotas = [r for r in modulo_plataforma.router.routes if isinstance(r, APIRoute)]
    assert rotas, "rotas de plataforma não registradas"
    publicadas = app.openapi()["paths"]  # e o app realmente as expõe
    assert all(r.path in publicadas for r in rotas)

    def chamaveis(dependant) -> set:
        encontrados = set()
        for sub in dependant.dependencies:
            encontrados.add(sub.call)
            encontrados |= chamaveis(sub)
        return encontrados

    for rota in rotas:
        deps = chamaveis(rota.dependant)
        if rota.path in permitidas_tenant:
            assert get_current_user_password_ready in deps, rota.path
        else:
            assert require_platform_admin in deps, f"{rota.methods} {rota.path} sem require_platform_admin"
        assert "DELETE" not in rota.methods or rota.path.endswith(("/personalizacao", "/logo")), (
            f"DELETE inesperado: {rota.path} (empresa nunca é apagada)"
        )


def test_revogacao_vale_na_requisicao_seguinte(app, client_plataforma: TestClient, administrador, db_session: Session) -> None:
    assert client_plataforma.get(f"{PLAT}/me").status_code == 200
    administrador.ativo = False
    administrador.revogado_em = datetime.now(timezone.utc)
    db_session.flush()
    assert client_plataforma.get(f"{PLAT}/me").status_code == 403  # o token ainda estava dentro do prazo
    assert client_plataforma.get(f"{PLAT}/empresas").status_code == 403


def test_usuario_inativado_perde_a_plataforma_na_hora(client_plataforma: TestClient, usuario_plataforma: Usuario, db_session: Session) -> None:
    usuario_plataforma.status = "inativo"
    db_session.flush()
    assert client_plataforma.get(f"{PLAT}/me").status_code == 403


def test_token_com_adm_de_outra_pessoa_e_negado(app, administrador, usuario_gestor: Usuario) -> None:
    forjado = create_platform_token(sub=usuario_gestor.id, administrador_id=administrador.id)
    assert _client(app, forjado).get(f"{PLAT}/me").status_code == 403


# --------------------------------------------------------------------------------------
# Empresas
# --------------------------------------------------------------------------------------


def test_criar_empresa_normaliza_codigo_e_deriva_slug(client_plataforma: TestClient) -> None:
    sufixo = uuid.uuid4().hex[:6]
    empresa = _criar_empresa(client_plataforma, codigoInterno=f" acme-{sufixo} ", nome="ACME Ltda", nomeFantasia="Acme")
    assert empresa["codigoInterno"] == f"ACME-{sufixo.upper()}"  # maiúsculas: é o código de login
    assert empresa["slug"] == f"acme-{sufixo}"
    assert empresa["nomeFantasia"] == "Acme" and empresa["status"] == "ativa"
    assert empresa["gestoresAtivos"] == 0 and empresa["hospedaAdministradorPlataforma"] is False


def test_slug_explicito_unico_e_validado(client_plataforma: TestClient) -> None:
    slug = f"loja-{uuid.uuid4().hex[:6]}"
    _criar_empresa(client_plataforma, slug=slug)
    repetido = client_plataforma.post(f"{PLAT}/empresas", json=_payload_empresa(slug=slug))
    assert repetido.status_code == 409 and "slug" in repetido.text
    for invalido in ("ab", "x" * 41, "Tem Espaço", "-comeca", "termina-", "acentuação", "Maiúscula"):
        resposta = client_plataforma.post(f"{PLAT}/empresas", json=_payload_empresa(slug=invalido))
        # maiúsculas são normalizadas (válido); os demais devem ser recusados
        if invalido == "Maiúscula":
            assert resposta.status_code == 422
        else:
            assert resposta.status_code == 422, (invalido, resposta.text)


@pytest.mark.parametrize("reservado", ["plataforma", "api", "login", "logout", "admin", "suporte"])
def test_slug_reservado_e_recusado(client_plataforma: TestClient, reservado: str) -> None:
    resposta = client_plataforma.post(f"{PLAT}/empresas", json=_payload_empresa(slug=reservado))
    assert resposta.status_code == 422 and "reservado" in resposta.text


def test_codigo_e_documento_duplicados(client_plataforma: TestClient) -> None:
    base = _criar_empresa(client_plataforma, documento="12345678000199")
    assert client_plataforma.post(f"{PLAT}/empresas", json=_payload_empresa(codigoInterno=base["codigoInterno"])).status_code == 409
    assert client_plataforma.post(f"{PLAT}/empresas", json=_payload_empresa(documento=" 12345678000199 ")).status_code == 409


def test_slug_derivado_nao_colide(client_plataforma: TestClient) -> None:
    uma = _criar_empresa(client_plataforma, codigoInterno="colide-um", slug="colide")
    outra = _criar_empresa(client_plataforma, codigoInterno="COLIDE")  # derivaria "colide", que já existe
    assert uma["slug"] == "colide" and outra["slug"] != "colide" and outra["slug"].startswith("colide")


def test_listar_obter_buscar_e_filtrar(client_plataforma: TestClient) -> None:
    empresa = _criar_empresa(client_plataforma, nome="Zeta Distinta Comunicação")
    assert any(e["id"] == empresa["id"] for e in client_plataforma.get(f"{PLAT}/empresas", params={"search": "zeta distinta"}).json())
    assert client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}").json()["slug"] == empresa["slug"]
    assert not any(e["id"] == empresa["id"] for e in client_plataforma.get(f"{PLAT}/empresas", params={"status": "inativa"}).json())
    assert client_plataforma.get(f"{PLAT}/empresas/{uuid.uuid4()}").status_code == 404


def test_editar_empresa_inclui_codigo_e_slug(client_plataforma: TestClient) -> None:
    empresa = _criar_empresa(client_plataforma)
    novo = f"novo-{uuid.uuid4().hex[:6]}"
    resposta = client_plataforma.patch(
        f"{PLAT}/empresas/{empresa['id']}",
        json={"nome": "Nome Novo", "nomeFantasia": "Fantasia Nova", "slug": novo, "codigoInterno": f"{novo}-x"},
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Nome Novo" and corpo["nomeFantasia"] == "Fantasia Nova"
    assert corpo["slug"] == novo and corpo["codigoInterno"] == f"{novo}-x".upper()
    assert client_plataforma.patch(f"{PLAT}/empresas/{empresa['id']}", json={"status": "inativa"}).status_code == 422  # campo fora


def test_inativar_reativar_e_sem_hard_delete(client_plataforma: TestClient, db_session: Session) -> None:
    empresa = _criar_empresa(client_plataforma)
    inativa = client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/inativar", json={"motivoInativacao": "teste"})
    assert inativa.status_code == 200 and inativa.json()["status"] == "inativa"
    assert client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/inativar", json={}).status_code == 409
    # a plataforma continua vendo o cadastro de uma empresa inativa
    assert client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}").json()["status"] == "inativa"
    assert client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/reativar").json()["status"] == "ativa"
    assert client_plataforma.delete(f"{PLAT}/empresas/{empresa['id']}").status_code in (404, 405)
    assert db_session.get(Empresa, empresa["id"]) is not None  # nunca apagada


def test_empresa_inativa_derruba_a_sessao_e_o_login_tenant(app, client_plataforma: TestClient, db_session: Session) -> None:
    empresa = _criar_empresa(client_plataforma)
    gestor = client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/gestores", json={"nome": "G", "email": "g@acme.test"}).json()
    login = _client(app, None).post(
        "/auth/login", json={"empresaCodigo": empresa["codigoInterno"], "email": "g@acme.test", "senha": gestor["senhaTemporaria"]}
    )
    assert login.status_code == 200
    tenant = _client(app, login.json()["accessToken"])
    assert tenant.get("/auth/me").status_code == 200

    client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/inativar", json={})
    assert tenant.get("/auth/me").status_code == 401  # a sessão tenant cai na requisição seguinte
    novo = _client(app, None).post(
        "/auth/login", json={"empresaCodigo": empresa["codigoInterno"], "email": "g@acme.test", "senha": gestor["senhaTemporaria"]}
    )
    assert novo.status_code == 401  # login normal rejeitado

    client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/reativar")
    assert tenant.get("/auth/me").status_code == 200  # dados preservados; volta a funcionar


def test_nao_inativa_a_empresa_que_hospeda_um_administrador_ativo(
    client_plataforma: TestClient, empresa: Empresa, administrador
) -> None:
    # (a leitura vem antes: a recusa do serviço faz rollback e, no teste, leva junto as linhas só "flushed" das fixtures)
    assert client_plataforma.get(f"{PLAT}/empresas/{empresa.id}").json()["hospedaAdministradorPlataforma"] is True
    protegida = client_plataforma.post(f"{PLAT}/empresas/{empresa.id}/inativar", json={})
    assert protegida.status_code == 409 and "Administrador da Plataforma" in protegida.text


def test_servico_recusa_inativar_empresa_que_hospeda_administrador(
    db_session: Session, empresa: Empresa, administrador: AdministradorPlataforma, usuario_plataforma: Usuario
) -> None:
    from app.services.empresa_service import EmpresaHospedaPlataformaError, EmpresaService

    servico = EmpresaService()
    with pytest.raises(EmpresaHospedaPlataformaError):
        servico.inativar_empresa(db_session, empresa.id, actor_usuario_id=usuario_plataforma.id)


def test_inativa_depois_de_revogada_a_autoridade(db_session: Session, usuario_plataforma: Usuario, empresa: Empresa) -> None:
    from app.services.empresa_service import EmpresaService

    _conceder(db_session, usuario_plataforma, ativo=False)  # revogada: não "hospeda" mais
    inativa = EmpresaService().inativar_empresa(db_session, empresa.id, actor_usuario_id=usuario_plataforma.id)
    assert inativa.status == "inativa"


# --------------------------------------------------------------------------------------
# Tenant /empresas: no máximo LER a própria empresa
# --------------------------------------------------------------------------------------


def test_tenant_so_le_a_propria_empresa(client_gestor: TestClient, client_operador: TestClient, empresa: Empresa) -> None:
    lista = client_gestor.get("/empresas")
    assert lista.status_code == 200 and [e["id"] for e in lista.json()] == [empresa.id]
    assert client_gestor.get(f"/empresas/{empresa.id}").json()["slug"] == empresa.slug
    assert client_operador.get("/empresas").status_code == 403
    assert client_gestor.patch(f"/empresas/{empresa.id}", json={"codigoInterno": "OUTRO"}).status_code == 403
    assert client_gestor.patch(f"/empresas/{empresa.id}", json={"slug": "outro-slug"}).status_code == 403
    assert client_gestor.post("/empresas", json=_payload_empresa()).status_code == 403
    assert client_gestor.post(f"/empresas/{empresa.id}/inativar", json={}).status_code == 403
    assert client_gestor.post(f"/empresas/{empresa.id}/reativar").status_code == 403


def test_tenant_admin_legado_tambem_nao_altera_a_empresa(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    codigo = empresa.codigo_interno
    assert client_admin.patch(f"/empresas/{empresa.id}", json={"codigoInterno": "TROCADO"}).status_code == 403
    db_session.refresh(empresa)
    assert empresa.codigo_interno == codigo


# --------------------------------------------------------------------------------------
# Branding por empresa
# --------------------------------------------------------------------------------------


def test_branding_por_empresa_e_isolado(app, client_plataforma: TestClient, empresa: Empresa, db_session: Session) -> None:
    acme = _criar_empresa(client_plataforma, codigoInterno=f"acme-{uuid.uuid4().hex[:5]}")
    atualizado = client_plataforma.patch(
        f"{PLAT}/empresas/{acme['id']}/personalizacao", json={"corPrimaria": "#ff9500", "corSecundaria": "#0ea5e9", "tema": "escuro"}
    )
    assert atualizado.status_code == 200, atualizado.text
    assert (atualizado.json()["corPrimaria"], atualizado.json()["tema"]) == ("#ff9500", "escuro")

    # a outra empresa segue com os padrões (nenhuma consulta cruza empresas)
    outra = client_plataforma.get(f"{PLAT}/empresas/{empresa.id}/personalizacao").json()
    assert outra["padrao"] is True and outra["corPrimaria"] != "#ff9500"
    # e a leitura pública (por código) devolve a de cada uma
    publica = _client(app, None).get("/personalizacao/publica", params={"empresaCodigo": acme["codigoInterno"]}).json()
    assert publica["corPrimaria"] == "#ff9500" and publica["tema"] == "escuro"


def test_branding_valida_cores_e_tema_como_no_tenant(client_plataforma: TestClient) -> None:
    empresa = _criar_empresa(client_plataforma)
    for corpo in ({"corPrimaria": "vermelho"}, {"corPrimaria": "#12345"}, {"tema": "roxo"}):
        assert client_plataforma.patch(f"{PLAT}/empresas/{empresa['id']}/personalizacao", json=corpo).status_code == 422, corpo
    assert client_plataforma.get(f"{PLAT}/empresas/{uuid.uuid4()}/personalizacao").status_code == 404


def test_logo_por_empresa_valida_bytes_e_fica_na_pasta_da_empresa(app, client_plataforma: TestClient, db_session: Session) -> None:
    from app.models.configuracao_personalizacao import ConfiguracaoPersonalizacao

    empresa = _criar_empresa(client_plataforma)
    ok = client_plataforma.post(
        f"{PLAT}/empresas/{empresa['id']}/personalizacao/logo", files={"arquivo": ("logo.png", png(), "image/png")}
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["logoDisponivel"] is True
    registro = db_session.scalar(select(ConfiguracaoPersonalizacao).where(ConfiguracaoPersonalizacao.empresa_id == empresa["id"]))
    assert registro.logo_storage_key.startswith(f"personalizacao/{empresa['id']}/")  # isolado por empresa
    # arquivo falso (extensão/MIME de PNG, bytes de outra coisa) é recusado — validação por bytes continua valendo
    falso = client_plataforma.post(
        f"{PLAT}/empresas/{empresa['id']}/personalizacao/logo", files={"arquivo": ("logo.png", b"<html>nao sou png</html>", "image/png")}
    )
    assert falso.status_code in (400, 415, 422), falso.text
    bytes_logo = client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}/personalizacao/logo")
    assert bytes_logo.status_code == 200 and bytes_logo.headers["content-type"] == "image/png"
    assert bytes_logo.headers["x-content-type-options"] == "nosniff" and bytes_logo.content == png()
    removido = client_plataforma.delete(f"{PLAT}/empresas/{empresa['id']}/personalizacao/logo")
    assert removido.status_code == 200 and removido.json()["logoDisponivel"] is False
    assert client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}/personalizacao/logo").status_code == 404
    assert client_plataforma.delete(f"{PLAT}/empresas/{empresa['id']}/personalizacao").status_code == 200  # restaurar padrão


def test_branding_da_plataforma_e_auditado_sem_expor_o_administrador_ao_tenant(
    app, client_plataforma: TestClient, db_session: Session, usuario_plataforma: Usuario
) -> None:
    empresa = _criar_empresa(client_plataforma)
    client_plataforma.patch(f"{PLAT}/empresas/{empresa['id']}/personalizacao", json={"corPrimaria": "#ff9500"})
    tipos = {e.tipo for e in db_session.scalars(select(Evento).where(Evento.empresa_id == empresa["id"]))}
    assert {"empresa.criada", "empresa.personalizacao_alterada"} <= tipos


# --------------------------------------------------------------------------------------
# Usuários da empresa e primeiro Gestor
# --------------------------------------------------------------------------------------


def test_listagem_de_usuarios_e_so_metadados_e_oculta_conta_de_sistema(
    client_plataforma: TestClient, empresa: Empresa, usuario_gestor: Usuario, usuario_operador: Usuario, usuario_plataforma: Usuario
) -> None:
    resposta = client_plataforma.get(f"{PLAT}/empresas/{empresa.id}/usuarios", params={"limit": 200})
    assert resposta.status_code == 200
    ids = {u["id"] for u in resposta.json()}
    assert usuario_gestor.id in ids and usuario_operador.id in ids
    assert usuario_plataforma.id not in ids  # conta de sistema não é "usuário da empresa"
    assert set(resposta.json()[0]) == {"id", "nome", "email", "perfilBase", "status", "acessoSistema", "createdAt"}
    assert "senha" not in resposta.text.lower() and "hash" not in resposta.text.lower()


def test_criar_gestor_forca_perfil_senha_temporaria_e_troca_obrigatoria(app, client_plataforma: TestClient, db_session: Session) -> None:
    empresa = _criar_empresa(client_plataforma)
    resposta = client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/gestores", json={"nome": "Ana Gestora", "email": "ana@acme.test"})
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["usuario"]["perfilBase"] == "gestor" and corpo["deveAlterarSenha"] is True
    senha = corpo["senhaTemporaria"]
    assert len(senha) >= 12 and senha != SENHA_CONHECIDA

    usuario = db_session.scalar(select(Usuario).where(Usuario.id == corpo["usuario"]["id"]))
    assert usuario.empresa_id == empresa["id"] and usuario.perfil_base == "gestor" and usuario.acesso_sistema is True
    assert usuario.is_system_account is False

    # troca obrigatória no primeiro login
    login = _client(app, None).post("/auth/login", json={"empresaCodigo": empresa["codigoInterno"], "email": "ana@acme.test", "senha": senha})
    assert login.status_code == 200 and login.json()["mustChangePassword"] is True
    # e a empresa agora conta um Gestor ativo
    assert client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}").json()["gestoresAtivos"] == 1


def test_criar_gestor_nunca_aceita_perfil_admin_nem_campos_extras(client_plataforma: TestClient) -> None:
    empresa = _criar_empresa(client_plataforma)
    for extra in ({"perfilBase": "admin"}, {"perfilBase": "gestor"}, {"senha": "SenhaQualquer1!"}, {"empresaId": str(uuid.uuid4())}):
        resposta = client_plataforma.post(
            f"{PLAT}/empresas/{empresa['id']}/gestores", json={"nome": "X", "email": "x@acme.test", **extra}
        )
        assert resposta.status_code == 422, (extra, resposta.text)


def test_gestor_pertence_somente_a_empresa_alvo_e_email_repetido_conflita(client_plataforma: TestClient, db_session: Session) -> None:
    a = _criar_empresa(client_plataforma)
    b = _criar_empresa(client_plataforma)
    criado = client_plataforma.post(f"{PLAT}/empresas/{a['id']}/gestores", json={"nome": "A", "email": "mesmo@x.test"}).json()
    assert db_session.get(Usuario, criado["usuario"]["id"]).empresa_id == a["id"]
    assert client_plataforma.post(f"{PLAT}/empresas/{a['id']}/gestores", json={"nome": "A2", "email": "mesmo@x.test"}).status_code == 409
    # a MESMA pessoa em outra empresa é outro usuário (e-mail é único por empresa)
    assert client_plataforma.post(f"{PLAT}/empresas/{b['id']}/gestores", json={"nome": "A", "email": "mesmo@x.test"}).status_code == 201
    assert not [u for u in client_plataforma.get(f"{PLAT}/empresas/{b['id']}/usuarios").json() if u["id"] == criado["usuario"]["id"]]


def test_gestor_em_empresa_inativa_e_recusado(client_plataforma: TestClient) -> None:
    empresa = _criar_empresa(client_plataforma)
    client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/inativar", json={})
    assert client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/gestores", json={"nome": "G", "email": "g@z.test"}).status_code == 409
    assert client_plataforma.post(f"{PLAT}/empresas/{uuid.uuid4()}/gestores", json={"nome": "G", "email": "g@z.test"}).status_code == 404


def test_senha_temporaria_nunca_vaza_para_evento_ou_log(
    client_plataforma: TestClient, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    empresa = _criar_empresa(client_plataforma)
    corpo = client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/gestores", json={"nome": "Sigilo", "email": "sigilo@acme.test"}).json()
    senha = corpo["senhaTemporaria"]

    eventos = db_session.scalars(select(Evento).where(Evento.empresa_id == empresa["id"])).all()
    assert eventos, "a criação deve ser auditada"
    assert senha not in json.dumps([e.payload for e in eventos], default=str)
    assert senha not in json.dumps([e.metadata_ for e in eventos], default=str)
    assert senha not in caplog.text
    # nem a empresa nem a listagem a devolvem de novo
    assert senha not in client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}/usuarios").text
    assert senha not in client_plataforma.get(f"{PLAT}/empresas/{empresa['id']}").text


def test_gerar_senha_temporaria_e_aleatoria_e_legivel() -> None:
    senhas = {gerar_senha_temporaria() for _ in range(50)}
    assert len(senhas) == 50
    assert all(len(s) == 14 and not set(s) & set("0O1lI") for s in senhas)


# --------------------------------------------------------------------------------------
# Privacidade do ator (conta de sistema) e auditoria
# --------------------------------------------------------------------------------------


def test_gestor_da_nova_empresa_nao_ve_o_administrador_da_plataforma_nos_eventos(
    app, client_plataforma: TestClient, db_session: Session, usuario_plataforma: Usuario
) -> None:
    empresa = _criar_empresa(client_plataforma)
    corpo = client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/gestores", json={"nome": "Visão", "email": "visao@acme.test"}).json()
    client_plataforma.patch(f"{PLAT}/empresas/{empresa['id']}", json={"nomeFantasia": "Fantasia"})
    # os eventos existem (auditoria) …
    do_admin = db_session.scalars(
        select(Evento).where(Evento.empresa_id == empresa["id"], Evento.usuario_id == usuario_plataforma.id)
    ).all()
    assert len(do_admin) >= 3
    # … mas o Gestor da empresa não os recebe (ator is_system_account), nem o nome/id do administrador
    gestor = db_session.get(Usuario, corpo["usuario"]["id"])
    credencial = db_session.scalar(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == gestor.id))
    credencial.senha_deve_ser_alterada = False  # (o Gestor já trocou a senha temporária)
    db_session.flush()
    bruto = _tenant_client(app, gestor).get("/eventos", params={"limit": 200})
    assert bruto.status_code == 200
    assert usuario_plataforma.id not in bruto.text and "Proprietário Plataforma" not in bruto.text
    assert not [e for e in bruto.json() if e["usuarioId"] == usuario_plataforma.id]


def test_toda_acao_de_plataforma_gera_evento_com_o_ator(client_plataforma: TestClient, db_session: Session, usuario_plataforma: Usuario) -> None:
    empresa = _criar_empresa(client_plataforma)
    client_plataforma.patch(f"{PLAT}/empresas/{empresa['id']}", json={"nome": "Outro Nome"})
    client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/inativar", json={})
    client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/reativar")
    client_plataforma.post(f"{PLAT}/empresas/{empresa['id']}/gestores", json={"nome": "G", "email": "ev@acme.test"})
    client_plataforma.patch(f"{PLAT}/empresas/{empresa['id']}/personalizacao", json={"tema": "escuro"})
    eventos = db_session.scalars(select(Evento).where(Evento.empresa_id == empresa["id"])).all()
    tipos = {e.tipo for e in eventos}
    assert {"empresa.criada", "empresa.alterada", "empresa.inativada", "empresa.reativada", "usuario.criado",
            "empresa.gestor_criado", "empresa.personalizacao_alterada"} <= tipos
    assert all(e.usuario_id == usuario_plataforma.id for e in eventos if e.tipo.startswith("empresa."))


# --------------------------------------------------------------------------------------
# CLI de bootstrap (único lugar onde um e-mail localiza a autoridade)
# --------------------------------------------------------------------------------------


def _cli(db: Session, *argv: str) -> tuple[int, list[str]]:
    saidas: list[str] = []
    codigo = seed_platform_admin.main(list(argv), session_factory=lambda: nullcontext(db), output=saidas.append)
    return codigo, saidas


def test_cli_concede_e_e_idempotente(db_session: Session, usuario_plataforma: Usuario, empresa: Empresa) -> None:
    antes = (usuario_plataforma.perfil_base, usuario_plataforma.is_system_account, usuario_plataforma.empresa_id, usuario_plataforma.status)
    codigo, saida = _cli(db_session, "--email", usuario_plataforma.email, "--empresa-codigo", empresa.codigo_interno)
    assert codigo == 0 and "concedida" in saida[0]
    codigo, saida = _cli(db_session, "--email", usuario_plataforma.email.upper(), "--empresa-codigo", empresa.codigo_interno)
    assert codigo == 0 and "já estava ativa" in saida[0]
    assert db_session.scalars(select(AdministradorPlataforma).where(AdministradorPlataforma.usuario_id == usuario_plataforma.id)).all().__len__() == 1
    # a linha tenant do usuário NÃO é alterada
    db_session.refresh(usuario_plataforma)
    assert antes == (usuario_plataforma.perfil_base, usuario_plataforma.is_system_account, usuario_plataforma.empresa_id, usuario_plataforma.status)


def test_cli_le_o_email_do_ambiente_e_reativa(db_session: Session, usuario_plataforma: Usuario, empresa: Empresa, monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_ADMIN_EMAIL", usuario_plataforma.email)
    assert _cli(db_session, "--empresa-codigo", empresa.codigo_interno)[0] == 0
    codigo, saida = _cli(db_session, "--revogar", "--empresa-codigo", empresa.codigo_interno)
    assert codigo == 0 and "revogada" in saida[0]
    linha = db_session.scalar(select(AdministradorPlataforma).where(AdministradorPlataforma.usuario_id == usuario_plataforma.id))
    assert linha.ativo is False and linha.revogado_em is not None
    codigo, saida = _cli(db_session, "--empresa-codigo", empresa.codigo_interno)
    assert codigo == 0 and "reativada" in saida[0]
    db_session.refresh(linha)
    assert linha.ativo is True and linha.revogado_em is None


def test_cli_exige_usuario_ativo_e_existente(db_session: Session, usuario_plataforma: Usuario, empresa: Empresa) -> None:
    assert _cli(db_session, "--email", "naoexiste@x.test", "--empresa-codigo", empresa.codigo_interno)[0] == 1
    assert _cli(db_session, "--empresa-codigo", empresa.codigo_interno)[0] == 1  # sem e-mail
    assert _cli(db_session, "--email", usuario_plataforma.email, "--empresa-codigo", "NAOEXISTE")[0] == 1
    usuario_plataforma.status = "inativo"
    db_session.flush()
    assert _cli(db_session, "--email", usuario_plataforma.email, "--empresa-codigo", empresa.codigo_interno)[0] == 1


def test_cli_nao_imprime_segredo(db_session: Session, usuario_plataforma: Usuario, empresa: Empresa) -> None:
    _, saida = _cli(db_session, "--email", usuario_plataforma.email, "--empresa-codigo", empresa.codigo_interno)
    texto = " ".join(saida)
    assert usuario_plataforma.email not in texto and SENHA_CONHECIDA not in texto
