"""Preferência PESSOAL de tema (claro | escuro | sistema | null = padrão da empresa): persistência no servidor,
exposição em /auth/me, autoria (só o próprio usuário), sem RBAC, isolamento entre empresas e independência da
configuração de tema da empresa (que continua global)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.configuracao_personalizacao import ConfiguracaoPersonalizacao
from app.models.empresa import Empresa
from app.models.usuario import Usuario

PREFERENCIAS = "/usuarios/me/preferencias"
ME = "/auth/me"
EMPRESA_TEMA = "/configuracoes/personalizacao"


def _me(client: TestClient) -> dict:
    resposta = client.get(ME)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _cliente_de(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)}"
    return cliente


def _usuario_de(db: Session, empresa: Empresa, perfil: str = "operador") -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"t-{sufixo}", nome=f"Tema {sufixo}",
        email=f"tema-{sufixo}@teste.local", perfil_base=perfil, acesso_sistema=True, status="ativo",
        is_system_account=False, created_at=agora, updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


# ------------------------------------------------------------------ default / leitura


def test_usuario_novo_herda_a_empresa_e_auth_me_expoe_null(client_admin: TestClient, usuario_admin: Usuario) -> None:
    assert usuario_admin.tema_preferencia is None
    corpo = _me(client_admin)
    assert "temaPreferencia" in corpo and corpo["temaPreferencia"] is None


def test_auth_me_mantem_o_shape_existente(client_admin: TestClient) -> None:
    corpo = _me(client_admin)
    for campo in ("usuarioId", "empresaId", "nome", "perfilBase", "acessoSistema", "status", "mustChangePassword", "permissoes"):
        assert campo in corpo
    # só campos aditivos: a preferência de tema e (Fase 2) o slug PÚBLICO da empresa da sessão — nada sensível
    assert set(corpo) - {"usuarioId", "empresaId", "nome", "perfilBase", "acessoSistema", "status", "mustChangePassword", "permissoes"} == {"temaPreferencia", "empresaSlug"}


# ------------------------------------------------------------------ gravação


@pytest.mark.parametrize("tema", ["claro", "escuro", "sistema"])
def test_define_cada_preferencia_e_persiste(client_admin: TestClient, db_session: Session, usuario_admin: Usuario, tema: str) -> None:
    resposta = client_admin.patch(PREFERENCIAS, json={"tema": tema})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {"temaPreferencia": tema}
    assert _me(client_admin)["temaPreferencia"] == tema
    db_session.refresh(usuario_admin)
    assert usuario_admin.tema_preferencia == tema


def test_null_restaura_a_heranca_da_empresa(client_admin: TestClient) -> None:
    client_admin.patch(PREFERENCIAS, json={"tema": "escuro"})
    resposta = client_admin.patch(PREFERENCIAS, json={"tema": None})
    assert resposta.status_code == 200
    assert resposta.json() == {"temaPreferencia": None}
    assert _me(client_admin)["temaPreferencia"] is None


@pytest.mark.parametrize("corpo", [{"tema": "azul"}, {"tema": ""}, {"tema": "CLARO"}, {"tema": 1}, {"tema": ["claro"]}, {}, {"tema": "claro", "extra": 1}])
def test_valor_invalido_ou_campo_extra_422_e_nao_altera(client_admin: TestClient, corpo: dict) -> None:
    client_admin.patch(PREFERENCIAS, json={"tema": "escuro"})
    resposta = client_admin.patch(PREFERENCIAS, json=corpo)
    assert resposta.status_code == 422, resposta.text
    assert _me(client_admin)["temaPreferencia"] == "escuro"


def test_exige_autenticacao(app) -> None:
    anonimo = TestClient(app)
    assert anonimo.patch(PREFERENCIAS, json={"tema": "claro"}).status_code in (401, 403)
    assert anonimo.get(ME).status_code in (401, 403)


# ------------------------------------------------------------------ sem RBAC; só o próprio usuário


def test_operador_gestor_e_admin_alteram_o_proprio_tema(client_operador: TestClient, client_gestor: TestClient, client_admin: TestClient) -> None:
    for cliente, tema in ((client_operador, "escuro"), (client_gestor, "sistema"), (client_admin, "claro")):
        assert cliente.patch(PREFERENCIAS, json={"tema": tema}).status_code == 200
        assert _me(cliente)["temaPreferencia"] == tema


def test_nao_altera_outro_usuario_pela_rota(client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario, db_session: Session) -> None:
    # nenhum identificador de usuário é aceito no corpo
    resposta = client_admin.patch(PREFERENCIAS, json={"tema": "escuro", "usuarioId": usuario_operador.id})
    assert resposta.status_code == 422
    # e não existe rota para alterar a preferência de outro
    assert client_admin.patch(f"/usuarios/{usuario_operador.id}/preferencias", json={"tema": "escuro"}).status_code in (404, 405)
    # o admin alterando o próprio não toca o operador
    client_admin.patch(PREFERENCIAS, json={"tema": "escuro"})
    db_session.refresh(usuario_operador)
    assert usuario_operador.tema_preferencia is None
    assert _me(client_operador)["temaPreferencia"] is None


def test_cadastro_nao_permite_definir_o_tema_de_terceiros(client_admin: TestClient, usuario_operador: Usuario, db_session: Session) -> None:
    # a edição administrativa de usuário (PATCH /usuarios/{id}) ignora/recusa o campo
    client_admin.patch(f"/usuarios/{usuario_operador.id}", json={"temaPreferencia": "escuro"})
    client_admin.patch(f"/usuarios/{usuario_operador.id}", json={"tema_preferencia": "escuro"})
    db_session.refresh(usuario_operador)
    assert usuario_operador.tema_preferencia is None


def test_usuarios_diferentes_do_mesmo_tenant_tem_preferencias_independentes(app, db_session: Session, empresa: Empresa) -> None:
    a = _cliente_de(app, _usuario_de(db_session, empresa))
    b = _cliente_de(app, _usuario_de(db_session, empresa))
    a.patch(PREFERENCIAS, json={"tema": "escuro"})
    b.patch(PREFERENCIAS, json={"tema": "claro"})
    assert _me(a)["temaPreferencia"] == "escuro"
    assert _me(b)["temaPreferencia"] == "claro"
    a.patch(PREFERENCIAS, json={"tema": None})
    assert _me(a)["temaPreferencia"] is None
    assert _me(b)["temaPreferencia"] == "claro"


def test_tenant_nao_interfere(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    daqui = _cliente_de(app, _usuario_de(db_session, empresa))
    de_la = _cliente_de(app, _usuario_de(db_session, outra_empresa))
    daqui.patch(PREFERENCIAS, json={"tema": "escuro"})
    assert _me(de_la)["temaPreferencia"] is None


# ------------------------------------------------------------------ empresa x usuário


def test_preferencia_pessoal_nao_mexe_na_personalizacao_da_empresa(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    client_admin.patch(EMPRESA_TEMA, json={"tema": "escuro", "corPrimaria": "#112233"})
    antes = client_admin.get(EMPRESA_TEMA).json()
    client_admin.patch(PREFERENCIAS, json={"tema": "claro"})
    assert client_admin.get(EMPRESA_TEMA).json() == antes
    linha = db_session.scalars(select(ConfiguracaoPersonalizacao).where(ConfiguracaoPersonalizacao.empresa_id == empresa.id)).one()
    assert (linha.tema, linha.cor_primaria) == ("escuro", "#112233")


def test_quem_herda_acompanha_a_empresa_e_quem_tem_override_nao(app, client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    herda = _cliente_de(app, _usuario_de(db_session, empresa))
    com_override = _cliente_de(app, _usuario_de(db_session, empresa))
    com_override.patch(PREFERENCIAS, json={"tema": "claro"})
    client_admin.patch(EMPRESA_TEMA, json={"tema": "escuro"})
    # a empresa agora é escuro: quem herda vê NULL (a empresa decide); quem tem override continua claro
    assert _me(herda)["temaPreferencia"] is None
    assert _me(com_override)["temaPreferencia"] == "claro"
    publica = herda.get("/personalizacao/publica", params={"empresaCodigo": empresa.codigo_interno}).json()
    assert publica["tema"] == "escuro"
    # o payload público da empresa não ganha nada pessoal
    assert set(publica) == {"corPrimaria", "corSecundaria", "tema", "logoDisponivel", "logoVersao", "padrao"}


# ------------------------------------------------------------------ banco / migration


def test_check_do_banco_recusa_valor_fora_da_lista(db_session: Session, empresa: Empresa) -> None:
    usuario = _usuario_de(db_session, empresa)
    usuario.tema_preferencia = "roxo"
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_usuarios_existentes_continuam_null_e_coluna_e_nullable(db_session: Session, empresa: Empresa) -> None:
    usuario = _usuario_de(db_session, empresa)
    assert usuario.tema_preferencia is None
    coluna = Usuario.__table__.c.tema_preferencia
    assert coluna.nullable is True and coluna.server_default is None


def test_migration_0039_aditiva_e_reversivel() -> None:
    from pathlib import Path

    texto = (Path(__file__).resolve().parent.parent / "migrations/versions/0039_tema_preferencia_usuario.py").read_text(encoding="utf-8")
    assert "down_revision: Union[str, None] = '48bd07aba026'" in texto
    assert "nullable=True" in texto and "server_default" not in texto
    assert "op.drop_column('usuarios', 'tema_preferencia')" in texto
    assert "UPDATE" not in texto.upper().replace("UPDATE_", "")  # não reescreve usuários
