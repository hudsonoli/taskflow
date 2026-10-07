"""Fase 1A — Gestor como autoridade tenant sobre Usuários.

Hierarquia (app/core/autoridade_usuarios.py), imposta no BACKEND:
- admin LEGADO: cria/edita Gestor e Usuário; NUNCA atribui `admin` (422 no schema);
- Gestor: administra SOMENTE Usuário (`operador`): cria, edita, suspende, reativa, bloqueia, desbloqueia,
  exclui/restaura e gerencia permissões individuais — nunca outro Gestor, o admin legado ou a si mesmo;
- Usuário: sem administração (mesmo com `usuarios.*` por concessão, só atua sobre Usuário);
- a empresa nunca perde o ÚLTIMO Gestor ativo por uma operação administrativa normal — mas uma empresa que
  ainda não tem nenhum (estado legado) não é afetada.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.autoridade_usuarios import (
    AutoridadeUsuarioError,
    ensure_nao_e_auto_administracao,
    ensure_pode_administrar_alvo,
    ensure_pode_atribuir_perfil,
    perfis_atribuiveis_por,
)
from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from app.repositories.usuario_repository import UsuarioRepository

from tests.fixtures.usuarios import _criar_usuario_com_credencial


def _client_para(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _payload(empresa_id: str, perfil: str = "operador", **extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    corpo = {
        "empresaId": empresa_id,
        "nome": f"Pessoa {sufixo}",
        "email": f"pessoa-{sufixo}@teste.taskfloww.local",
        "perfilBase": perfil,
    }
    corpo.update(extra)
    return corpo


def _usuario(db: Session, empresa: Empresa, perfil: str, prefixo: str | None = None) -> Usuario:
    return _criar_usuario_com_credencial(db, empresa=empresa, perfil_base=perfil, email_prefixo=prefixo or perfil)


def _conceder(db: Session, usuario: Usuario, permissao: str) -> None:
    agora = datetime.now(timezone.utc)
    db.add(
        UsuarioPermissao(
            id=str(uuid.uuid4()),
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            permissao=permissao,
            efeito="conceder",
            created_at=agora,
            updated_at=agora,
        )
    )
    db.flush()


# --------------------------------------------------------------------------------------
# Regras puras
# --------------------------------------------------------------------------------------


def test_perfis_atribuiveis_nunca_inclui_admin() -> None:
    assert perfis_atribuiveis_por("admin") == frozenset({"gestor", "operador"})
    assert perfis_atribuiveis_por("gestor") == frozenset({"operador"})
    assert perfis_atribuiveis_por("operador") == frozenset({"operador"})


def test_regras_puras_de_alvo_e_perfil() -> None:
    ensure_pode_administrar_alvo("admin", "gestor")
    ensure_pode_administrar_alvo("gestor", "operador")
    with pytest.raises(AutoridadeUsuarioError):
        ensure_pode_administrar_alvo("gestor", "gestor")
    with pytest.raises(AutoridadeUsuarioError):
        ensure_pode_administrar_alvo("gestor", "admin")
    ensure_pode_atribuir_perfil("admin", "gestor")
    with pytest.raises(AutoridadeUsuarioError):
        ensure_pode_atribuir_perfil("admin", "admin")
    with pytest.raises(AutoridadeUsuarioError):
        ensure_pode_atribuir_perfil("gestor", "gestor")
    with pytest.raises(AutoridadeUsuarioError):
        ensure_nao_e_auto_administracao("a", "a")
    ensure_nao_e_auto_administracao("a", "b")


# --------------------------------------------------------------------------------------
# Defaults e piso
# --------------------------------------------------------------------------------------


def test_gestor_recebe_defaults_de_usuarios_e_permissoes() -> None:
    from app.core.permissoes import DEFAULTS_POR_PERFIL

    gestor = DEFAULTS_POR_PERFIL["gestor"]
    for chave in ("usuarios.visualizar", "usuarios.criar", "usuarios.editar", "usuarios.suspender", "permissoes.gerenciar"):
        assert chave in gestor
    # Nada de plataforma/empresa entra no catálogo do gestor.
    assert not any(chave.startswith(("empresas.", "plataforma.")) for chave in gestor)
    assert "usuarios.criar" not in DEFAULTS_POR_PERFIL["operador"]
    assert "permissoes.gerenciar" not in DEFAULTS_POR_PERFIL["operador"]


# --------------------------------------------------------------------------------------
# ADMIN LEGADO
# --------------------------------------------------------------------------------------


def test_admin_legado_cria_gestor_e_usuario(client_admin: TestClient, empresa: Empresa) -> None:
    gestor = client_admin.post("/usuarios", json=_payload(empresa.id, "gestor"))
    assert gestor.status_code == 201, gestor.text
    assert gestor.json()["perfilBase"] == "gestor"
    usuario = client_admin.post("/usuarios", json=_payload(empresa.id, "operador"))
    assert usuario.status_code == 201, usuario.text
    assert usuario.json()["perfilBase"] == "operador"


def test_admin_legado_nao_cria_admin(client_admin: TestClient, empresa: Empresa) -> None:
    resposta = client_admin.post("/usuarios", json=_payload(empresa.id, "admin"))
    assert resposta.status_code == 422, resposta.text


def test_admin_legado_nao_promove_para_admin(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    alvo = _usuario(db_session, empresa, "operador", "alvo-promo")
    resposta = client_admin.patch(f"/usuarios/{alvo.id}", json={"perfilBase": "admin"})
    assert resposta.status_code == 422, resposta.text
    db_session.refresh(alvo)
    assert alvo.perfil_base == "operador"


def test_admin_legado_edita_gestor_e_promove_usuario_a_gestor(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    gestor = _usuario(db_session, empresa, "gestor", "gestor-edit")
    assert client_admin.patch(f"/usuarios/{gestor.id}", json={"nome": "Gestor Renomeado"}).status_code == 200
    comum = _usuario(db_session, empresa, "operador", "promovido")
    resposta = client_admin.patch(f"/usuarios/{comum.id}", json={"perfilBase": "gestor"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["perfilBase"] == "gestor"


# --------------------------------------------------------------------------------------
# GESTOR — o que PODE (somente Usuário)
# --------------------------------------------------------------------------------------


def test_gestor_cria_edita_e_administra_usuario(
    client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    criado = client_gestor.post("/usuarios", json=_payload(empresa.id, "operador"))
    assert criado.status_code == 201, criado.text
    usuario_id = criado.json()["id"]

    assert client_gestor.patch(f"/usuarios/{usuario_id}", json={"nome": "Nome Novo"}).status_code == 200
    assert client_gestor.post(f"/usuarios/{usuario_id}/inativar", json={}).status_code == 200
    assert client_gestor.post(f"/usuarios/{usuario_id}/reativar", json={}).status_code == 200
    assert client_gestor.post(f"/usuarios/{usuario_id}/bloquear", json={}).status_code == 200
    assert client_gestor.post(f"/usuarios/{usuario_id}/desbloquear", json={}).status_code == 200
    excluido = client_gestor.post(f"/usuarios/{usuario_id}/excluir", json={"motivoArquivamento": "teste"})
    assert excluido.status_code == 200, excluido.text
    assert client_gestor.post(f"/usuarios/{usuario_id}/restaurar").status_code == 200


def test_gestor_gerencia_permissoes_de_usuario(
    client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    alvo = _usuario(db_session, empresa, "operador", "alvo-perm")
    assert client_gestor.get(f"/usuarios/{alvo.id}/permissoes").status_code == 200
    definido = client_gestor.put(f"/usuarios/{alvo.id}/permissoes/demandas.criar", json={"efeito": "conceder"})
    assert definido.status_code == 200, definido.text
    assert client_gestor.delete(f"/usuarios/{alvo.id}/permissoes/demandas.criar").status_code == 204


# --------------------------------------------------------------------------------------
# GESTOR — o que NÃO pode
# --------------------------------------------------------------------------------------


def test_gestor_nao_cria_gestor_nem_admin(client_gestor: TestClient, empresa: Empresa) -> None:
    gestor = client_gestor.post("/usuarios", json=_payload(empresa.id, "gestor"))
    assert gestor.status_code == 403, gestor.text
    admin = client_gestor.post("/usuarios", json=_payload(empresa.id, "admin"))
    assert admin.status_code == 422, admin.text


def test_gestor_nao_promove_usuario_a_gestor_nem_a_admin(
    client_gestor: TestClient, db_session: Session, empresa: Empresa
) -> None:
    alvo = _usuario(db_session, empresa, "operador", "alvo-promo-g")
    assert client_gestor.patch(f"/usuarios/{alvo.id}", json={"perfilBase": "gestor"}).status_code == 403
    assert client_gestor.patch(f"/usuarios/{alvo.id}", json={"perfilBase": "admin"}).status_code == 422
    db_session.refresh(alvo)
    assert alvo.perfil_base == "operador"


@pytest.mark.parametrize("perfil_alvo", ["gestor", "admin"])
def test_gestor_nao_opera_sobre_gestor_nem_admin(
    client_gestor: TestClient, db_session: Session, empresa: Empresa, perfil_alvo: str
) -> None:
    alvo = _usuario(db_session, empresa, perfil_alvo, f"alvo-{perfil_alvo}")
    assert client_gestor.patch(f"/usuarios/{alvo.id}", json={"nome": "X"}).status_code == 403
    assert client_gestor.post(f"/usuarios/{alvo.id}/inativar", json={}).status_code == 403
    assert client_gestor.post(f"/usuarios/{alvo.id}/bloquear", json={}).status_code == 403
    assert client_gestor.post(f"/usuarios/{alvo.id}/reativar", json={}).status_code == 403
    assert client_gestor.post(f"/usuarios/{alvo.id}/desbloquear", json={}).status_code == 403
    assert client_gestor.post(f"/usuarios/{alvo.id}/excluir", json={"motivoArquivamento": "x"}).status_code == 403
    assert client_gestor.post(f"/usuarios/{alvo.id}/restaurar").status_code == 403
    # Permissões individuais: nem ver, nem alterar.
    assert client_gestor.get(f"/usuarios/{alvo.id}/permissoes").status_code == 403
    assert client_gestor.put(f"/usuarios/{alvo.id}/permissoes/demandas.criar", json={"efeito": "conceder"}).status_code == 403
    assert client_gestor.delete(f"/usuarios/{alvo.id}/permissoes/demandas.criar").status_code == 403
    db_session.refresh(alvo)
    assert alvo.status == "ativo" and alvo.nome != "X"


def test_gestor_nao_se_auto_administra(
    client_gestor: TestClient, usuario_gestor: Usuario
) -> None:
    for acao in ("inativar", "bloquear"):
        assert client_gestor.post(f"/usuarios/{usuario_gestor.id}/{acao}", json={}).status_code == 403
    assert client_gestor.post(f"/usuarios/{usuario_gestor.id}/excluir", json={"motivoArquivamento": "x"}).status_code == 403
    # Nem editar o próprio cadastro administrativo nem as próprias permissões (o autoatendimento é /usuarios/me).
    assert client_gestor.patch(f"/usuarios/{usuario_gestor.id}", json={"perfilBase": "operador"}).status_code == 403
    assert client_gestor.get(f"/usuarios/{usuario_gestor.id}/permissoes").status_code == 403
    assert client_gestor.put(f"/usuarios/{usuario_gestor.id}/permissoes/demandas.criar", json={"efeito": "conceder"}).status_code == 403


# --------------------------------------------------------------------------------------
# USUÁRIO continua sem administração
# --------------------------------------------------------------------------------------


def test_usuario_continua_sem_administracao(
    client_operador: TestClient, db_session: Session, empresa: Empresa
) -> None:
    alvo = _usuario(db_session, empresa, "operador", "alvo-op")
    assert client_operador.post("/usuarios", json=_payload(empresa.id)).status_code == 403
    assert client_operador.get("/usuarios", params={"empresaId": empresa.id}).status_code == 403
    assert client_operador.patch(f"/usuarios/{alvo.id}", json={"nome": "X"}).status_code == 403
    assert client_operador.post(f"/usuarios/{alvo.id}/inativar", json={}).status_code == 403
    assert client_operador.get(f"/usuarios/{alvo.id}/permissoes").status_code == 403


def test_usuario_com_concessao_so_age_sobre_usuario(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Uma concessão de `usuarios.criar` não é hierarquia: quem a recebe só cria Usuário."""
    comum = _usuario(db_session, empresa, "operador", "com-grant")
    _conceder(db_session, comum, "usuarios.criar")
    _conceder(db_session, comum, "usuarios.editar")
    gestor_alvo = _usuario(db_session, empresa, "gestor", "gestor-alvo")
    cliente = _client_para(app, comum)
    assert cliente.post("/usuarios", json=_payload(empresa.id, "operador")).status_code == 201
    assert cliente.post("/usuarios", json=_payload(empresa.id, "gestor")).status_code == 403
    assert cliente.patch(f"/usuarios/{gestor_alvo.id}", json={"nome": "X"}).status_code == 403


# --------------------------------------------------------------------------------------
# ÚLTIMO GESTOR
# --------------------------------------------------------------------------------------


def test_empresa_nao_perde_o_ultimo_gestor(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    ultimo = _usuario(db_session, empresa, "gestor", "ultimo")
    mensagem = "ao menos um Gestor ativo"

    for acao, corpo in (("inativar", {}), ("bloquear", {}), ("excluir", {"motivoArquivamento": "x"})):
        resposta = client_admin.post(f"/usuarios/{ultimo.id}/{acao}", json=corpo)
        assert resposta.status_code == 409, (acao, resposta.text)
        assert mensagem in resposta.text
    assert client_admin.patch(f"/usuarios/{ultimo.id}", json={"perfilBase": "operador"}).status_code == 409
    assert client_admin.patch(f"/usuarios/{ultimo.id}", json={"acessoSistema": False}).status_code == 409

    db_session.refresh(ultimo)
    assert ultimo.status == "ativo" and ultimo.perfil_base == "gestor" and ultimo.acesso_sistema is True


def test_empresa_com_varios_gestores_pode_perder_um_mas_nao_o_ultimo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    a = _usuario(db_session, empresa, "gestor", "gestor-a")
    b = _usuario(db_session, empresa, "gestor", "gestor-b")
    assert client_admin.post(f"/usuarios/{a.id}/inativar", json={}).status_code == 200
    # b virou o último ativo
    assert client_admin.post(f"/usuarios/{b.id}/inativar", json={}).status_code == 409
    # criar outro gestor primeiro libera a operação
    assert client_admin.post("/usuarios", json=_payload(empresa.id, "gestor")).status_code == 201
    assert client_admin.post(f"/usuarios/{b.id}/inativar", json={}).status_code == 200


def test_empresa_sem_gestor_legado_nao_e_afetada(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Estado de produção hoje: nenhum Gestor. Nada impede operar sobre Usuários, nem criar o primeiro Gestor."""
    comum = _usuario(db_session, empresa, "operador", "legado-op")
    assert client_admin.post(f"/usuarios/{comum.id}/inativar", json={}).status_code == 200
    assert client_admin.post(f"/usuarios/{comum.id}/reativar", json={}).status_code == 200
    assert client_admin.post("/usuarios", json=_payload(empresa.id, "gestor")).status_code == 201


def test_gestor_inativo_ou_sem_acesso_nao_conta_como_ativo(db_session: Session, empresa: Empresa) -> None:
    repo = UsuarioRepository()
    ativo = _usuario(db_session, empresa, "gestor", "g-ativo")
    inativo = _usuario(db_session, empresa, "gestor", "g-inativo")
    inativo.status = "inativo"
    sem_acesso = _usuario(db_session, empresa, "gestor", "g-sem-acesso")
    sem_acesso.acesso_sistema = False
    sistema = _usuario(db_session, empresa, "gestor", "g-sistema")
    sistema.is_system_account = True
    db_session.flush()
    assert repo.contar_gestores_ativos(db_session, empresa_id=empresa.id) == 1
    assert repo.contar_gestores_ativos(db_session, empresa_id=empresa.id, exceto_id=ativo.id) == 0


def test_ultimo_gestor_e_por_empresa(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    """Gestor ativo de OUTRA empresa não conta: aqui o gestor continua sendo o último."""
    ultimo = _usuario(db_session, empresa, "gestor", "unico-empresa")
    _usuario(db_session, outra_empresa, "gestor", "gestor-alheio")
    assert client_admin.post(f"/usuarios/{ultimo.id}/inativar", json={}).status_code == 409
