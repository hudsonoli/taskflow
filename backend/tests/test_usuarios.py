from uuid import uuid4

import pytest

from conftest import auth_headers, create_auth_context, eventos, make_empresa, make_usuario, persist
from app.domain.event_types import DomainEventType
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate
from app.services.usuario_service import UsuarioService


def usuario_payload(empresa_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "codigoInterno": f"USR-{uuid4().hex[:8]}",
        "nome": "Hudson Silva",
        "email": f"hudson-{uuid4().hex[:8]}@empresa.com",
        "perfilBase": "operador",
        "acessoSistema": True,
    }
    data.update(overrides)
    return data


def create_usuario(client, headers, empresa_id: str, **overrides):
    response = client.post("/usuarios", json=usuario_payload(empresa_id, **overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def test_usuarios_endpoints_require_authentication(client):
    response = client.get("/usuarios", params={"empresaId": str(uuid4())})

    assert response.status_code == 401


def test_admin_creates_usuario_in_own_empresa_with_authenticated_actor(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    usuario = create_usuario(client, headers, empresa.id, email=" Hudson@Empresa.COM ")

    assert usuario["empresaId"] == empresa.id
    assert usuario["email"] == "hudson@empresa.com"
    user_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.USUARIO_CRIADO.value]
    assert len(user_events) == 1
    assert user_events[0].usuario_id == admin.id


def test_admin_cannot_create_usuario_in_other_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.post("/usuarios", json=usuario_payload(other.id), headers=headers)

    assert response.status_code == 403


def test_gestor_lists_and_gets_usuarios_from_own_empresa(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    headers = auth_headers(client, gestor, empresa)

    list_response = client.get("/usuarios", params={"empresaId": empresa.id}, headers=headers)
    get_response = client.get(f"/usuarios/{target.id}", headers=headers)

    assert list_response.status_code == 200
    assert target.id in [item["id"] for item in list_response.json()]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == target.id


def test_gestor_cannot_mutate_usuario(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    headers = auth_headers(client, gestor, empresa)

    response = client.patch(f"/usuarios/{target.id}", json={"nome": "Bloqueado"}, headers=headers)

    assert response.status_code == 403


def test_operador_cannot_access_usuarios(client):
    empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    headers = auth_headers(client, operador, empresa)

    response = client.get("/usuarios", params={"empresaId": empresa.id}, headers=headers)

    assert response.status_code == 403


def test_list_usuarios_rejects_divergent_empresa_id(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.get("/usuarios", params={"empresaId": other.id}, headers=headers)

    assert response.status_code == 403


def test_get_usuario_from_other_tenant_returns_404(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    other_user = persist(client.session_factory, make_usuario(other.id, email="outro@empresa.com"))
    headers = auth_headers(client, admin, empresa)

    response = client.get(f"/usuarios/{other_user.id}", headers=headers)

    assert response.status_code == 404


def test_admin_updates_usuario_in_own_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    headers = auth_headers(client, admin, empresa)

    response = client.patch(
        f"/usuarios/{target.id}",
        json={"nome": "Hudson Atualizado", "email": " Novo.Email@Empresa.COM ", "perfilBase": "gestor"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Hudson Atualizado"
    assert response.json()["email"] == "novo.email@empresa.com"
    assert response.json()["perfilBase"] == "gestor"


def test_admin_cannot_update_usuario_from_other_tenant(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    other_user = persist(client.session_factory, make_usuario(other.id, email="outro@empresa.com"))
    headers = auth_headers(client, admin, empresa)

    response = client.patch(f"/usuarios/{other_user.id}", json={"nome": "Outro"}, headers=headers)

    assert response.status_code == 404


def test_admin_cannot_inactivate_or_block_self(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    inactivate = client.post(f"/usuarios/{admin.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    block = client.post(f"/usuarios/{admin.id}/bloquear", headers=headers)

    assert inactivate.status_code == 403
    assert block.status_code == 403


def test_admin_status_actions_use_authenticated_actor_not_payload(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    fake_actor = str(uuid4())
    headers = auth_headers(client, admin, empresa)

    response = client.post(
        f"/usuarios/{target.id}/inativar",
        json={"motivoInativacao": "saida", "actorUsuarioId": fake_actor},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["inativadoPorUsuarioId"] == admin.id
    user_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.USUARIO_INATIVADO.value]
    assert len(user_events) == 1
    assert user_events[0].usuario_id == admin.id


def test_admin_reactivates_blocks_and_unblocks_usuario(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    headers = auth_headers(client, admin, empresa)

    assert client.post(f"/usuarios/{target.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers).status_code == 200
    assert client.post(f"/usuarios/{target.id}/reativar", headers=headers).status_code == 200
    assert client.post(f"/usuarios/{target.id}/bloquear", headers=headers).status_code == 200
    unblock = client.post(f"/usuarios/{target.id}/desbloquear", headers=headers)

    assert unblock.status_code == 200
    assert unblock.json()["status"] == "ativo"


def test_invalid_transitions_are_rejected(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    headers = auth_headers(client, admin, empresa)

    response = client.post(f"/usuarios/{target.id}/reativar", headers=headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "Usuário já está ativo"}


def test_delete_route_does_not_exist(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    headers = auth_headers(client, admin, empresa)

    response = client.delete(f"/usuarios/{target.id}", headers=headers)

    assert response.status_code == 405


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def usuarios(session_factory) -> list[Usuario]:
    with session_factory() as db:
        return list(db.query(Usuario).all())


def test_create_usuario_with_missing_or_inactive_empresa_still_validates_in_service(session_factory):
    service = UsuarioService()

    with pytest.raises(Exception, match="Empresa não encontrada"):
        with session_factory() as db:
            service.create_usuario(db, UsuarioCreate(**usuario_payload(str(uuid4()))))

    empresa, admin, _ = create_auth_context(client_session := session_factory, perfil_base="admin")
    with client_session() as db:
        persisted = db.get(type(empresa), empresa.id)
        persisted.status = "inativa"
        db.commit()

    with pytest.raises(Exception, match="Empresa inativa não permite criação de usuário"):
        with session_factory() as db:
            service.create_usuario(db, UsuarioCreate(**usuario_payload(empresa.id)))


def test_usuario_duplicates_and_same_email_across_empresas_with_authenticated_api(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other_empresa, other_admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    other_headers = auth_headers(client, other_admin, other_empresa)

    create_usuario(client, headers, empresa.id, codigoInterno="USR-DUP", email="hudson@empresa.com")

    duplicate_codigo = client.post("/usuarios", json=usuario_payload(empresa.id, codigoInterno="USR-DUP"), headers=headers)
    duplicate_email = client.post("/usuarios", json=usuario_payload(empresa.id, email=" Hudson@Empresa.COM "), headers=headers)
    same_email_other = client.post("/usuarios", json=usuario_payload(other_empresa.id, email=" Hudson@Empresa.COM "), headers=other_headers)

    assert duplicate_codigo.status_code == 409
    assert duplicate_email.status_code == 409
    assert same_email_other.status_code == 201
    assert same_email_other.json()["email"] == "hudson@empresa.com"


def test_usuario_patch_rejects_forbidden_fields_with_authenticated_admin(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    headers = auth_headers(client, admin, empresa)

    empresa_change = client.patch(f"/usuarios/{target.id}", json={"empresaId": str(uuid4())}, headers=headers)
    status_change = client.patch(f"/usuarios/{target.id}", json={"status": "inativo"}, headers=headers)

    assert empresa_change.status_code == 422
    assert status_change.status_code == 422


def test_usuario_events_full_sequence_and_sensitive_payload(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    created = create_usuario(client, headers, empresa.id, codigoInterno="USR-EVENTOS", email="hudson@empresa.com")

    client.patch(f"/usuarios/{created['id']}", json={"email": "novo@empresa.com"}, headers=headers)
    client.post(f"/usuarios/{created['id']}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    client.post(f"/usuarios/{created['id']}/reativar", headers=headers)
    client.post(f"/usuarios/{created['id']}/bloquear", headers=headers)
    client.post(f"/usuarios/{created['id']}/desbloquear", headers=headers)

    user_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "usuario" and evento.entidade_id == created["id"]]
    assert [evento.tipo for evento in user_events] == [
        DomainEventType.USUARIO_CRIADO.value,
        DomainEventType.USUARIO_ALTERADO.value,
        DomainEventType.USUARIO_INATIVADO.value,
        DomainEventType.USUARIO_REATIVADO.value,
        DomainEventType.USUARIO_BLOQUEADO.value,
        DomainEventType.USUARIO_DESBLOQUEADO.value,
    ]
    for evento in user_events:
        assert evento.usuario_id == admin.id
        assert "email" not in evento.payload
        assert "hudson@empresa.com" not in str(evento.payload)
        assert "novo@empresa.com" not in str(evento.payload)
        assert "documento" not in evento.payload


def test_service_create_usuario_rolls_back_when_event_publish_fails(session_factory):
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    service = UsuarioService(event_publisher=FailingPublisher())
    data = UsuarioCreate(
        empresaId=empresa.id,
        codigoInterno="USR-ROLLBACK",
        nome="Usuario Rollback",
        email="rollback@empresa.com",
        perfilBase="operador",
    )

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_usuario(db, data)

    assert [usuario for usuario in usuarios(session_factory) if usuario.codigo_interno == "USR-ROLLBACK"] == []
