from datetime import datetime, timezone
from uuid import uuid4

import pytest

from conftest import auth_headers, create_auth_context, eventos, make_empresa, persist
from app.domain.event_types import DomainEventType
from app.models.cargo import Cargo
from app.schemas.cargo import CargoCreate, CargoUpdate
from app.services.cargo_service import CargoService


def cargo_payload(empresa_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "codigoInterno": f" cg-{uuid4().hex[:8]} ",
        "nome": f"  Cargo   {uuid4().hex[:8]}  ",
        "descricao": "  Cargo   operacional  ",
    }
    data.update(overrides)
    return data


def make_cargo(empresa_id: str, **overrides) -> Cargo:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"CG-{uuid4().hex[:8]}",
        "nome": f"Cargo {uuid4().hex[:8]}",
        "descricao": "Cargo operacional",
        "status": "ativa",
        "created_at": now,
        "updated_at": now,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Cargo(**data)


def persist_cargo(session_factory, empresa_id: str, **overrides) -> Cargo:
    return persist(session_factory, make_cargo(empresa_id, **overrides))


def create_cargo(client, headers, empresa_id: str, **overrides):
    response = client.post("/cargos", json=cargo_payload(empresa_id, **overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def cargos(session_factory) -> list[Cargo]:
    with session_factory() as db:
        return list(db.query(Cargo).all())


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_cargos_endpoints_require_authentication(client):
    response = client.get("/cargos", params={"empresaId": str(uuid4())})

    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get("/cargos", params={"empresaId": str(uuid4())}, headers={"Authorization": "Bearer invalido"})

    assert response.status_code == 401


def test_admin_creates_cargo_with_normalization_and_authenticated_actor(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    cargo = create_cargo(
        client,
        headers,
        empresa.id,
        codigoInterno=" cg-001 ",
        nome="  Diretor   de   Arte  ",
        descricao="   ",
    )

    assert cargo["empresaId"] == empresa.id
    assert cargo["codigoInterno"] == "CG-001"
    assert cargo["nome"] == "Diretor de Arte"
    assert cargo["descricao"] is None
    cargo_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.CARGO_CRIADO.value]
    assert len(cargo_events) == 1
    assert cargo_events[0].usuario_id == admin.id
    assert cargo_events[0].payload["actor_usuario_id"] == admin.id


def test_gestor_cannot_create_cargo(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    headers = auth_headers(client, gestor, empresa)

    response = client.post("/cargos", json=cargo_payload(empresa.id), headers=headers)

    assert response.status_code == 403


def test_operador_cannot_access_cargos(client):
    empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    headers = auth_headers(client, operador, empresa)

    response = client.get("/cargos", params={"empresaId": empresa.id}, headers=headers)

    assert response.status_code == 403


def test_admin_cannot_create_cargo_in_other_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.post("/cargos", json=cargo_payload(other.id), headers=headers)

    assert response.status_code == 403


def test_create_cargo_missing_or_inactive_empresa_still_validates_in_service(session_factory):
    service = CargoService()

    with pytest.raises(Exception, match="Empresa não encontrada"):
        with session_factory() as db:
            service.create_cargo(db, CargoCreate(**cargo_payload(str(uuid4()))))

    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    with session_factory() as db:
        persisted = db.get(type(empresa), empresa.id)
        persisted.status = "inativa"
        db.commit()

    with pytest.raises(Exception, match="Empresa inativa não permite criação de Cargo"):
        with session_factory() as db:
            service.create_cargo(db, CargoCreate(**cargo_payload(empresa.id)))


def test_create_cargo_rejects_empty_codigo_and_nome_after_normalization(session_factory):
    service = CargoService()
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")

    with pytest.raises(Exception, match="codigoInterno é obrigatório"):
        with session_factory() as db:
            service.create_cargo(db, CargoCreate(**cargo_payload(empresa.id, codigoInterno="   ")))

    with pytest.raises(Exception, match="nome é obrigatório"):
        with session_factory() as db:
            service.create_cargo(db, CargoCreate(**cargo_payload(empresa.id, nome="   ")))


def test_cargo_duplicates_and_cross_empresa_rules_with_authenticated_api(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other_empresa, other_admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    other_headers = auth_headers(client, other_admin, other_empresa)

    create_cargo(client, headers, empresa.id, codigoInterno="CG-DUP", nome="Atendimento")

    duplicate_codigo = client.post("/cargos", json=cargo_payload(empresa.id, codigoInterno=" cg-dup ", nome="Redator"), headers=headers)
    duplicate_nome = client.post("/cargos", json=cargo_payload(empresa.id, codigoInterno="CG-2", nome="  Atendimento  "), headers=headers)
    same_values_other = client.post("/cargos", json=cargo_payload(other_empresa.id, codigoInterno=" cg-dup ", nome="Atendimento"), headers=other_headers)

    assert duplicate_codigo.status_code == 409
    assert duplicate_nome.status_code == 409
    assert same_values_other.status_code == 201


def test_admin_and_gestor_list_cargos_from_own_empresa_and_filter_status(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    active = persist_cargo(client.session_factory, empresa.id, codigo_interno="CG-A", nome="Cargo Ativo")
    inactive = persist_cargo(client.session_factory, empresa.id, codigo_interno="CG-I", nome="Cargo Inativo", status="inativa")
    gestor_cargo = persist_cargo(client.session_factory, gestor_empresa.id, codigo_interno="CG-G", nome="Cargo Gestor")
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)

    admin_response = client.get("/cargos", params={"empresaId": empresa.id, "status": "ativa"}, headers=admin_headers)
    gestor_response = client.get("/cargos", params={"empresaId": gestor_empresa.id}, headers=gestor_headers)

    assert admin_response.status_code == 200
    assert [item["id"] for item in admin_response.json()] == [active.id]
    assert inactive.id not in [item["id"] for item in admin_response.json()]
    assert gestor_response.status_code == 200
    assert [item["id"] for item in gestor_response.json()] == [gestor_cargo.id]


def test_list_cargos_requires_empresa_id_for_authenticated_user(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    response = client.get("/cargos", headers=headers)

    assert response.status_code == 422


def test_list_cargos_rejects_divergent_empresa_id(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.get("/cargos", params={"empresaId": other.id}, headers=headers)

    assert response.status_code == 403


def test_get_cargo_by_id_and_other_tenant_returns_404(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    own_cargo = persist_cargo(client.session_factory, empresa.id, codigo_interno="CG-OWN", nome="Cargo Proprio")
    other_cargo = persist_cargo(client.session_factory, other.id, codigo_interno="CG-OUT", nome="Cargo Outro")
    headers = auth_headers(client, admin, empresa)

    own_response = client.get(f"/cargos/{own_cargo.id}", headers=headers)
    other_response = client.get(f"/cargos/{other_cargo.id}", headers=headers)

    assert own_response.status_code == 200
    assert own_response.json()["id"] == own_cargo.id
    assert other_response.status_code == 404


def test_admin_updates_cargo_and_gestor_operador_cannot_update(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    operador_empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    cargo = persist_cargo(client.session_factory, empresa.id)
    gestor_cargo = persist_cargo(client.session_factory, gestor_empresa.id)
    operador_cargo = persist_cargo(client.session_factory, operador_empresa.id)
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)
    operador_headers = auth_headers(client, operador, operador_empresa)

    response = client.patch(
        f"/cargos/{cargo.id}",
        json={"codigoInterno": " cg-009 ", "nome": " Analista   de   Midia ", "descricao": "  performance  "},
        headers=admin_headers,
    )
    gestor_response = client.patch(f"/cargos/{gestor_cargo.id}", json={"nome": "Bloqueado"}, headers=gestor_headers)
    operador_response = client.patch(f"/cargos/{operador_cargo.id}", json={"nome": "Bloqueado"}, headers=operador_headers)

    assert response.status_code == 200
    assert response.json()["codigoInterno"] == "CG-009"
    assert response.json()["nome"] == "Analista de Midia"
    assert response.json()["descricao"] == "performance"
    assert gestor_response.status_code == 403
    assert operador_response.status_code == 403


def test_cargo_patch_rejects_forbidden_fields_with_authenticated_admin(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    cargo = persist_cargo(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    for field, value in [
        ("empresaId", str(uuid4())),
        ("status", "inativa"),
        ("createdAt", "2026-07-15T00:00:00Z"),
        ("updatedAt", "2026-07-15T00:00:00Z"),
        ("inativadoAt", "2026-07-15T00:00:00Z"),
        ("motivoInativacao", "teste"),
        ("inativadoPorUsuarioId", str(uuid4())),
    ]:
        response = client.patch(f"/cargos/{cargo.id}", json={field: value}, headers=headers)
        assert response.status_code == 422
        assert field in response.json()["detail"]


def test_update_cargo_rejects_duplicates_after_normalization(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    first = persist_cargo(client.session_factory, empresa.id, codigo_interno="CG-1", nome="Atendimento")
    second = persist_cargo(client.session_factory, empresa.id, codigo_interno="CG-2", nome="Redator")
    headers = auth_headers(client, admin, empresa)

    duplicate_codigo = client.patch(f"/cargos/{second.id}", json={"codigoInterno": " cg-1 "}, headers=headers)
    duplicate_nome = client.patch(f"/cargos/{second.id}", json={"nome": "  Atendimento  "}, headers=headers)

    assert first.id
    assert duplicate_codigo.status_code == 409
    assert duplicate_nome.status_code == 409


def test_admin_status_actions_use_authenticated_actor_and_gestor_cannot_mutate(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    cargo = persist_cargo(client.session_factory, empresa.id)
    gestor_cargo = persist_cargo(client.session_factory, gestor_empresa.id)
    fake_actor = str(uuid4())
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)

    inactivate = client.post(
        f"/cargos/{cargo.id}/inativar",
        json={"motivoInativacao": "encerramento", "actorUsuarioId": fake_actor},
        headers=admin_headers,
    )
    gestor_inactivate = client.post(f"/cargos/{gestor_cargo.id}/inativar", json={"motivoInativacao": "teste"}, headers=gestor_headers)

    assert inactivate.status_code == 422
    inactivate = client.post(f"/cargos/{cargo.id}/inativar", json={"motivoInativacao": "encerramento"}, headers=admin_headers)
    reactivate = client.post(f"/cargos/{cargo.id}/reativar", headers=admin_headers)
    assert inactivate.status_code == 200
    assert inactivate.json()["inativadoPorUsuarioId"] == admin.id
    assert reactivate.status_code == 200
    assert reactivate.json()["status"] == "ativa"
    assert gestor_inactivate.status_code == 403
    cargo_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "cargo" and evento.entidade_id == cargo.id]
    assert [evento.tipo for evento in cargo_events] == [DomainEventType.CARGO_INATIVADO.value, DomainEventType.CARGO_REATIVADO.value]
    for evento in cargo_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["actor_usuario_id"] == admin.id


def test_invalid_status_transitions_are_rejected(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    cargo = persist_cargo(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    reactivate_active = client.post(f"/cargos/{cargo.id}/reativar", headers=headers)
    client.post(f"/cargos/{cargo.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    inactivate_inactive = client.post(f"/cargos/{cargo.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers)

    assert reactivate_active.status_code == 409
    assert reactivate_active.json() == {"detail": "Cargo já está ativo"}
    assert inactivate_inactive.status_code == 409
    assert inactivate_inactive.json() == {"detail": "Cargo já está inativo"}


def test_archived_cargo_cannot_be_reactivated(session_factory):
    service = CargoService()
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    cargo = persist_cargo(session_factory, empresa.id, status="arquivada")

    with pytest.raises(Exception, match="Cargo arquivado não pode ser reativado"):
        with session_factory() as db:
            service.reativar_cargo(db, cargo.id, actor_usuario_id=actor.id)


def test_cargo_events_full_sequence_with_restricted_payload(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    created = create_cargo(client, headers, empresa.id, codigoInterno="CG-EVENTOS", nome="Cargo Eventos")

    client.patch(f"/cargos/{created['id']}", json={"nome": "Cargo Alterado", "descricao": "nova descricao"}, headers=headers)
    client.post(f"/cargos/{created['id']}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    client.post(f"/cargos/{created['id']}/reativar", headers=headers)

    persisted_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "cargo" and evento.entidade_id == created["id"]]
    assert [evento.tipo for evento in persisted_events] == [
        DomainEventType.CARGO_CRIADO.value,
        DomainEventType.CARGO_ALTERADO.value,
        DomainEventType.CARGO_INATIVADO.value,
        DomainEventType.CARGO_REATIVADO.value,
    ]
    for evento in persisted_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["empresa_id"] == empresa.id
        assert evento.payload["cargo_id"] == created["id"]
        assert evento.payload["actor_usuario_id"] == admin.id
        assert "timestamp" in evento.payload
        assert "nome" not in evento.payload
        assert "codigo_interno" not in evento.payload
        assert "codigoInterno" not in evento.payload
        assert "descricao" not in evento.payload
    alterado = [evento for evento in persisted_events if evento.tipo == DomainEventType.CARGO_ALTERADO.value][0]
    assert alterado.payload["campos_alterados"] == ["nome", "descricao"]


def test_service_create_cargo_rolls_back_when_event_publish_fails(session_factory):
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    service = CargoService(event_publisher=FailingPublisher())
    data = CargoCreate(empresaId=empresa.id, codigoInterno="CG-ROLLBACK", nome="Cargo Rollback")

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_cargo(db, data)

    assert [cargo for cargo in cargos(session_factory) if cargo.codigo_interno == "CG-ROLLBACK"] == []


def test_service_update_cargo_rolls_back_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    cargo = persist_cargo(session_factory, empresa.id, nome="Cargo Original")
    service = CargoService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.update_cargo(db, cargo.id, CargoUpdate(nome="Cargo Alterado"), actor_usuario_id=actor.id)

    with session_factory() as db:
        persisted = db.get(Cargo, cargo.id)
        assert persisted.nome == "Cargo Original"


def test_service_status_actions_roll_back_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    active = persist_cargo(session_factory, empresa.id, codigo_interno="CG-A", nome="Cargo Ativo")
    inactive = persist_cargo(session_factory, empresa.id, codigo_interno="CG-I", nome="Cargo Inativo", status="inativa")
    service = CargoService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.inativar_cargo(db, active.id, motivo_inativacao="teste", actor_usuario_id=actor.id)

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.reativar_cargo(db, inactive.id, actor_usuario_id=actor.id)

    with session_factory() as db:
        assert db.get(Cargo, active.id).status == "ativa"
        assert db.get(Cargo, inactive.id).status == "inativa"


def test_delete_route_does_not_exist(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    cargo = persist_cargo(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    response = client.delete(f"/cargos/{cargo.id}", headers=headers)

    assert response.status_code == 405


def test_auth_login_and_me_still_work(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")

    login_response = client.post("/auth/login", json={"empresaCodigo": empresa.codigo_interno, "email": admin.email, "senha": "SenhaAtual123"})
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {login_response.json()['accessToken']}"})

    assert login_response.status_code == 200
    assert me_response.status_code == 200
