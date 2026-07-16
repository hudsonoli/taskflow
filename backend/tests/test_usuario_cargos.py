from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from conftest import auth_headers, create_auth_context, eventos, make_empresa, make_usuario, persist
from app.domain.event_types import DomainEventType
from app.models.cargo import Cargo
from app.models.usuario_cargo import UsuarioCargo
from app.schemas.usuario_cargo import UsuarioCargoCreate, UsuarioCargoEncerrar, UsuarioCargoUpdate
from app.services.usuario_cargo_service import UsuarioCargoService


def now() -> datetime:
    return datetime.now(timezone.utc)


def cargo(empresa_id: str, **overrides) -> Cargo:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"CG-{uuid4().hex[:8]}",
        "nome": f"Cargo {uuid4().hex[:8]}",
        "descricao": "Cargo de teste",
        "status": "ativa",
        "created_at": current_time,
        "updated_at": current_time,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Cargo(**data)


def persist_cargo(session_factory, empresa_id: str, **overrides) -> Cargo:
    return persist(session_factory, cargo(empresa_id, **overrides))


def usuario_cargo(empresa_id: str, usuario_id: str, cargo_id: str, **overrides) -> UsuarioCargo:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "usuario_id": usuario_id,
        "cargo_id": cargo_id,
        "principal": False,
        "status": "ativo",
        "inicio_em": current_time,
        "fim_em": None,
        "motivo_encerramento": None,
        "criado_por_usuario_id": None,
        "encerrado_por_usuario_id": None,
        "created_at": current_time,
        "updated_at": current_time,
    }
    data.update(overrides)
    return UsuarioCargo(**data)


def persist_vinculo(session_factory, empresa_id: str, usuario_id: str, cargo_id: str, **overrides) -> UsuarioCargo:
    return persist(session_factory, usuario_cargo(empresa_id, usuario_id, cargo_id, **overrides))


def payload(empresa_id: str, usuario_id: str, cargo_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "usuarioId": usuario_id,
        "cargoId": cargo_id,
        "principal": False,
    }
    data.update(overrides)
    return data


def create_vinculo(client, headers, empresa_id: str, usuario_id: str, cargo_id: str, **overrides):
    response = client.post(
        "/vinculos/cargos",
        json=payload(empresa_id, usuario_id, cargo_id, **overrides),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def vinculos(session_factory) -> list[UsuarioCargo]:
    with session_factory() as db:
        return list(db.scalars(select(UsuarioCargo).order_by(UsuarioCargo.created_at)).all())


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_authentication_and_authorization(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    operador_empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    role = persist_cargo(client.session_factory, empresa.id)
    gestor_target = persist(client.session_factory, make_usuario(gestor_empresa.id, perfil_base="operador"))
    gestor_role = persist_cargo(client.session_factory, gestor_empresa.id)
    gestor_vinculo = persist_vinculo(client.session_factory, gestor_empresa.id, gestor_target.id, gestor_role.id)
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)
    operador_headers = auth_headers(client, operador, operador_empresa)

    assert client.get("/vinculos/cargos", params={"empresaId": empresa.id}).status_code == 401
    assert client.get(
        "/vinculos/cargos",
        params={"empresaId": empresa.id},
        headers={"Authorization": "Bearer invalido"},
    ).status_code == 401
    assert client.post("/vinculos/cargos", json=payload(empresa.id, target.id, role.id), headers=admin_headers).status_code == 201
    assert client.post(
        "/vinculos/cargos",
        json=payload(gestor_empresa.id, gestor_target.id, gestor_role.id),
        headers=gestor_headers,
    ).status_code == 403
    assert client.get("/vinculos/cargos", params={"empresaId": operador_empresa.id}, headers=operador_headers).status_code == 403
    assert client.get("/vinculos/cargos", params={"empresaId": gestor_empresa.id}, headers=gestor_headers).status_code == 200
    assert client.get(f"/vinculos/cargos/{gestor_vinculo.id}", headers=gestor_headers).status_code == 200
    assert client.patch(f"/vinculos/cargos/{gestor_vinculo.id}", json={"principal": True}, headers=gestor_headers).status_code == 403
    assert client.post(f"/vinculos/cargos/{gestor_vinculo.id}/encerrar", json={}, headers=gestor_headers).status_code == 403


def test_tenant_rules(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    other_user = persist(client.session_factory, make_usuario(other.id, perfil_base="operador"))
    role = persist_cargo(client.session_factory, empresa.id)
    other_role = persist_cargo(client.session_factory, other.id)
    own = persist_vinculo(client.session_factory, empresa.id, target.id, role.id)
    other_link = persist_vinculo(client.session_factory, other.id, other_user.id, other_role.id)
    headers = auth_headers(client, admin, empresa)

    assert client.get("/vinculos/cargos", params={"empresaId": other.id}, headers=headers).status_code == 403
    assert client.get(f"/vinculos/cargos/{other_link.id}", headers=headers).status_code == 404
    assert client.post("/vinculos/cargos", json=payload(empresa.id, other_user.id, role.id), headers=headers).status_code == 422
    assert client.post("/vinculos/cargos", json=payload(empresa.id, target.id, other_role.id), headers=headers).status_code == 422
    assert client.get("/vinculos/cargos", params={"empresaId": empresa.id, "usuarioId": other_user.id}, headers=headers).status_code == 422
    response = client.get("/vinculos/cargos", params={"empresaId": empresa.id}, headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own.id]


def test_creation_validates_entities_and_conflicts(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    inactive_user = persist(client.session_factory, make_usuario(empresa.id, status="inativo"))
    role = persist_cargo(client.session_factory, empresa.id)
    inactive_role = persist_cargo(client.session_factory, empresa.id, status="inativa")
    inactive_empresa = persist(client.session_factory, make_empresa(status="inativa", codigo_interno="INATIVA"))
    headers = auth_headers(client, admin, empresa)

    created = create_vinculo(client, headers, empresa.id, target.id, role.id)
    assert created["inicioEm"]
    assert created["criadoPorUsuarioId"] == admin.id
    assert client.post("/vinculos/cargos", json=payload(empresa.id, target.id, role.id), headers=headers).status_code == 409
    assert client.post("/vinculos/cargos", json=payload(empresa.id, str(uuid4()), role.id), headers=headers).status_code == 422
    assert client.post("/vinculos/cargos", json=payload(empresa.id, inactive_user.id, role.id), headers=headers).status_code == 422
    assert client.post("/vinculos/cargos", json=payload(empresa.id, target.id, str(uuid4())), headers=headers).status_code == 422
    assert client.post("/vinculos/cargos", json=payload(empresa.id, target.id, inactive_role.id), headers=headers).status_code == 422
    assert client.post("/vinculos/cargos", json=payload(str(uuid4()), target.id, role.id), headers=headers).status_code == 403

    inactive_target = persist(client.session_factory, make_usuario(inactive_empresa.id, perfil_base="operador"))
    inactive_empresa_role = persist_cargo(client.session_factory, inactive_empresa.id)
    with pytest.raises(Exception, match="Empresa não encontrada ou inativa"):
        with client.session_factory() as db:
            UsuarioCargoService().vincular_usuario_cargo(
                db,
                UsuarioCargoCreate(**payload(inactive_empresa.id, inactive_target.id, inactive_empresa_role.id)),
                actor_usuario_id=admin.id,
            )


def test_multiple_active_cargos_and_single_principal(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_role = persist_cargo(client.session_factory, empresa.id)
    second_role = persist_cargo(client.session_factory, empresa.id)
    third_role = persist_cargo(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    first = create_vinculo(client, headers, empresa.id, target.id, first_role.id, principal=True)
    second = create_vinculo(client, headers, empresa.id, target.id, second_role.id)
    third = create_vinculo(client, headers, empresa.id, target.id, third_role.id)

    assert first["principal"] is True
    assert second["principal"] is False
    assert third["principal"] is False
    with client.session_factory() as db:
        assert db.get(UsuarioCargo, first["id"]).principal is True
        assert db.get(UsuarioCargo, second["id"]).status == "ativo"
        assert db.get(UsuarioCargo, third["id"]).status == "ativo"


def test_return_to_cargo_after_closure_creates_new_record(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    role = persist_cargo(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)
    first = create_vinculo(client, headers, empresa.id, target.id, role.id)

    close = client.post(f"/vinculos/cargos/{first['id']}/encerrar", json={"motivoEncerramento": "saida"}, headers=headers)
    second = create_vinculo(client, headers, empresa.id, target.id, role.id)

    assert close.status_code == 200
    assert close.json()["fimEm"]
    assert second["id"] != first["id"]


def test_update_rules_and_forbidden_fields(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_role = persist_cargo(client.session_factory, empresa.id)
    second_role = persist_cargo(client.session_factory, empresa.id)
    active = persist_vinculo(client.session_factory, empresa.id, target.id, first_role.id)
    inactive = persist_vinculo(
        client.session_factory,
        empresa.id,
        target.id,
        second_role.id,
        status="inativo",
        fim_em=now() + timedelta(days=1),
    )
    headers = auth_headers(client, admin, empresa)

    update = client.patch(f"/vinculos/cargos/{active.id}", json={"principal": True}, headers=headers)
    inactive_update = client.patch(f"/vinculos/cargos/{inactive.id}", json={"principal": True}, headers=headers)
    forbidden = client.patch(f"/vinculos/cargos/{active.id}", json={"cargoId": str(uuid4())}, headers=headers)

    assert update.status_code == 200
    assert update.json()["principal"] is True
    assert inactive_update.status_code == 409
    assert forbidden.status_code == 422


def test_principal_change_is_transactional_and_emits_two_events(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_role = persist_cargo(client.session_factory, empresa.id)
    second_role = persist_cargo(client.session_factory, empresa.id)
    first = persist_vinculo(client.session_factory, empresa.id, target.id, first_role.id, principal=True)
    second = persist_vinculo(client.session_factory, empresa.id, target.id, second_role.id)
    headers = auth_headers(client, admin, empresa)

    response = client.patch(f"/vinculos/cargos/{second.id}", json={"principal": True}, headers=headers)

    assert response.status_code == 200
    with client.session_factory() as db:
        assert db.get(UsuarioCargo, first.id).principal is False
        assert db.get(UsuarioCargo, second.id).principal is True
    changed_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.USUARIO_CARGO_ALTERADO.value]
    assert [evento.payload["campos_alterados"] for evento in changed_events] == [["principal"], ["principal"]]


def test_encerrar_rules_and_no_delete_or_reactivation(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    role = persist_cargo(client.session_factory, empresa.id)
    link = persist_vinculo(client.session_factory, empresa.id, target.id, role.id, principal=True)
    headers = auth_headers(client, admin, empresa)

    fim_rejected = client.post(f"/vinculos/cargos/{link.id}/encerrar", json={"fimEm": now().isoformat()}, headers=headers)
    actor_rejected = client.post(f"/vinculos/cargos/{link.id}/encerrar", json={"actorUsuarioId": str(uuid4())}, headers=headers)
    close = client.post(
        f"/vinculos/cargos/{link.id}/encerrar",
        json={"motivoEncerramento": "  saida   operacao  "},
        headers=headers,
    )
    close_again = client.post(f"/vinculos/cargos/{link.id}/encerrar", json={}, headers=headers)

    assert fim_rejected.status_code == 422
    assert actor_rejected.status_code == 422
    assert close.status_code == 200
    assert close.json()["status"] == "inativo"
    assert close.json()["principal"] is False
    assert close.json()["fimEm"]
    assert close.json()["motivoEncerramento"] == "saida operacao"
    assert close.json()["encerradoPorUsuarioId"] == admin.id
    assert close_again.status_code == 409
    assert client.post(f"/vinculos/cargos/{link.id}/reativar", headers=headers).status_code == 404
    assert client.delete(f"/vinculos/cargos/{link.id}", headers=headers).status_code == 405


def test_events_payload_is_restricted(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador", email="sensivel@empresa.com"))
    role = persist_cargo(client.session_factory, empresa.id, descricao="Descricao sensivel")
    headers = auth_headers(client, admin, empresa)
    created = create_vinculo(client, headers, empresa.id, target.id, role.id)
    client.patch(f"/vinculos/cargos/{created['id']}", json={"principal": True}, headers=headers)
    client.post(
        f"/vinculos/cargos/{created['id']}/encerrar",
        json={"motivoEncerramento": "motivo completo"},
        headers=headers,
    )

    link_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "usuario_cargo"]
    assert [evento.tipo for evento in link_events] == [
        DomainEventType.USUARIO_CARGO_VINCULADO.value,
        DomainEventType.USUARIO_CARGO_ALTERADO.value,
        DomainEventType.USUARIO_CARGO_ENCERRADO.value,
    ]
    for evento in link_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["empresa_id"] == empresa.id
        assert evento.payload["usuario_id"] == target.id
        assert evento.payload["cargo_id"] == role.id
        assert evento.payload["actor_usuario_id"] == admin.id
        assert "timestamp" in evento.payload
        assert "campos_alterados" in evento.payload
        assert "nome" not in evento.payload
        assert "email" not in evento.payload
        assert "descricao" not in evento.payload
        assert "motivo" not in str(evento.payload)
        assert all(isinstance(field, str) for field in evento.payload["campos_alterados"])


def test_rollbacks_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_role = persist_cargo(session_factory, empresa.id)
    second_role = persist_cargo(session_factory, empresa.id)
    service = UsuarioCargoService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.vincular_usuario_cargo(
                db,
                UsuarioCargoCreate(**payload(empresa.id, target.id, first_role.id)),
                actor_usuario_id=actor.id,
            )
    assert vinculos(session_factory) == []

    active = persist_vinculo(session_factory, empresa.id, target.id, first_role.id)
    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.alterar_vinculo(db, active.id, UsuarioCargoUpdate(principal=True), actor_usuario_id=actor.id)
    with session_factory() as db:
        assert db.get(UsuarioCargo, active.id).principal is False

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.encerrar_vinculo(db, active.id, UsuarioCargoEncerrar(motivoEncerramento="saida"), actor_usuario_id=actor.id)
    with session_factory() as db:
        assert db.get(UsuarioCargo, active.id).status == "ativo"

    principal = persist_vinculo(session_factory, empresa.id, target.id, second_role.id, principal=True)
    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.alterar_vinculo(db, active.id, UsuarioCargoUpdate(principal=True), actor_usuario_id=actor.id)
    with session_factory() as db:
        assert db.get(UsuarioCargo, principal.id).principal is True
        assert db.get(UsuarioCargo, active.id).principal is False


def test_auth_regression(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    login = client.post("/auth/login", json={"empresaCodigo": empresa.codigo_interno, "email": admin.email, "senha": "SenhaAtual123"})
    assert login.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {login.json()['accessToken']}"})
    assert me.status_code == 200
    assert me.json()["usuarioId"] == admin.id
