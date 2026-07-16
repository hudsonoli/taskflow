from uuid import uuid4

import pytest

from conftest import auth_headers, create_auth_context, eventos, make_empresa, persist, persist_agencia
from app.domain.event_types import DomainEventType
from app.models.agencia import Agencia
from app.schemas.agencia import AgenciaCreate
from app.services.agencia_service import AgenciaService


def agencia_payload(empresa_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "codigoInterno": f"ag-{uuid4().hex[:8]}",
        "nome": f"  Agencia {uuid4().hex[:8]}  ",
        "sigla": " ag ",
        "descricao": "  Unidade operacional  ",
    }
    data.update(overrides)
    return data


def create_agencia(client, headers, empresa_id: str, **overrides):
    response = client.post("/agencias", json=agencia_payload(empresa_id, **overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def test_agencias_endpoints_require_authentication(client):
    response = client.get("/agencias", params={"empresaId": str(uuid4())})

    assert response.status_code == 401


def test_admin_creates_agencia_in_own_empresa_with_authenticated_actor(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    agencia = create_agencia(
        client,
        headers,
        empresa.id,
        codigoInterno=" ag-001 ",
        nome="  Agencia   Centro  ",
        sigla=" ctr ",
        descricao="  Unidade   central  ",
    )

    assert agencia["empresaId"] == empresa.id
    assert agencia["codigoInterno"] == "AG-001"
    assert agencia["nome"] == "Agencia Centro"
    assert agencia["sigla"] == "CTR"
    agencia_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.AGENCIA_CRIADA.value]
    assert len(agencia_events) == 1
    assert agencia_events[0].usuario_id == admin.id


def test_admin_cannot_create_agencia_in_other_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.post("/agencias", json=agencia_payload(other.id), headers=headers)

    assert response.status_code == 403


def test_gestor_lists_and_gets_agencias_from_own_empresa(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    agencia = persist_agencia(client.session_factory, empresa.id, codigo_interno="AG-001", nome="Agencia A")
    headers = auth_headers(client, gestor, empresa)

    list_response = client.get("/agencias", params={"empresaId": empresa.id}, headers=headers)
    get_response = client.get(f"/agencias/{agencia.id}", headers=headers)

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [agencia.id]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == agencia.id


def test_gestor_cannot_mutate_agencia(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    agencia = persist_agencia(client.session_factory, empresa.id)
    headers = auth_headers(client, gestor, empresa)

    response = client.patch(f"/agencias/{agencia.id}", json={"nome": "Bloqueada"}, headers=headers)

    assert response.status_code == 403


def test_operador_cannot_access_agencias(client):
    empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    headers = auth_headers(client, operador, empresa)

    response = client.get("/agencias", params={"empresaId": empresa.id}, headers=headers)

    assert response.status_code == 403


def test_list_agencias_rejects_divergent_empresa_id(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.get("/agencias", params={"empresaId": other.id}, headers=headers)

    assert response.status_code == 403


def test_get_agencia_from_other_tenant_returns_404(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    agencia = persist_agencia(client.session_factory, other.id, codigo_interno="AG-OUTRA")
    headers = auth_headers(client, admin, empresa)

    response = client.get(f"/agencias/{agencia.id}", headers=headers)

    assert response.status_code == 404


def test_admin_updates_agencia_in_own_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    agencia = persist_agencia(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    response = client.patch(
        f"/agencias/{agencia.id}",
        json={"codigoInterno": " ag-009 ", "nome": " Agencia Sul ", "sigla": " sul ", "descricao": " nova unidade "},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["codigoInterno"] == "AG-009"
    assert response.json()["nome"] == "Agencia Sul"
    assert response.json()["sigla"] == "SUL"


def test_admin_cannot_update_agencia_from_other_tenant(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    agencia = persist_agencia(client.session_factory, other.id)
    headers = auth_headers(client, admin, empresa)

    response = client.patch(f"/agencias/{agencia.id}", json={"nome": "Outra"}, headers=headers)

    assert response.status_code == 404


def test_admin_status_actions_use_authenticated_actor_not_payload(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    agencia = persist_agencia(client.session_factory, empresa.id)
    fake_actor = str(uuid4())
    headers = auth_headers(client, admin, empresa)

    response = client.post(
        f"/agencias/{agencia.id}/inativar",
        json={"motivoInativacao": "encerramento", "actorUsuarioId": fake_actor},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["inativadoPorUsuarioId"] == admin.id
    agencia_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.AGENCIA_INATIVADA.value]
    assert len(agencia_events) == 1
    assert agencia_events[0].usuario_id == admin.id
    assert agencia_events[0].payload["actor_usuario_id"] == admin.id


def test_admin_reactivates_agencia(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    agencia = persist_agencia(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    assert client.post(f"/agencias/{agencia.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers).status_code == 200
    response = client.post(f"/agencias/{agencia.id}/reativar", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "ativa"


def test_invalid_transition_is_rejected(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    agencia = persist_agencia(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    response = client.post(f"/agencias/{agencia.id}/reativar", headers=headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "Agência já está ativa"}


def test_delete_route_does_not_exist(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    agencia = persist_agencia(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    response = client.delete(f"/agencias/{agencia.id}", headers=headers)

    assert response.status_code == 405


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def agencias(session_factory) -> list[Agencia]:
    with session_factory() as db:
        return list(db.query(Agencia).all())


def test_list_agencias_still_requires_empresa_id_for_authenticated_user(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    response = client.get("/agencias", headers=headers)

    assert response.status_code == 422


def test_create_agencia_missing_or_inactive_empresa_still_validates_in_service(session_factory):
    service = AgenciaService()

    with pytest.raises(Exception, match="Empresa não encontrada"):
        with session_factory() as db:
            service.create_agencia(db, AgenciaCreate(**agencia_payload(str(uuid4()))))

    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    with session_factory() as db:
        persisted = db.get(type(empresa), empresa.id)
        persisted.status = "inativa"
        db.commit()

    with pytest.raises(Exception, match="Empresa inativa não permite criação de Agência"):
        with session_factory() as db:
            service.create_agencia(db, AgenciaCreate(**agencia_payload(empresa.id)))


def test_list_agencias_filters_by_status_with_authenticated_user(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    active = persist_agencia(client.session_factory, empresa.id, codigo_interno="AG-A", nome="Agencia Ativa")
    inactive = persist_agencia(client.session_factory, empresa.id, codigo_interno="AG-I", nome="Agencia Inativa", status="inativa")
    headers = auth_headers(client, admin, empresa)

    response = client.get("/agencias", params={"empresaId": empresa.id, "status": "ativa"}, headers=headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [active.id]
    assert inactive.id not in [item["id"] for item in response.json()]


def test_agencia_patch_rejects_forbidden_fields_with_authenticated_admin(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    agencia = persist_agencia(client.session_factory, empresa.id)
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
        response = client.patch(f"/agencias/{agencia.id}", json={field: value}, headers=headers)
        assert response.status_code == 422
        assert field in response.json()["detail"]


def test_agencia_duplicates_and_cross_empresa_rules_with_authenticated_api(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other_empresa, other_admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    other_headers = auth_headers(client, other_admin, other_empresa)

    create_agencia(client, headers, empresa.id, codigoInterno="AG-DUP", nome="Agencia Norte")

    duplicate_codigo = client.post("/agencias", json=agencia_payload(empresa.id, codigoInterno=" ag-dup ", nome="Agencia Sul"), headers=headers)
    duplicate_nome = client.post("/agencias", json=agencia_payload(empresa.id, codigoInterno="AG-2", nome="  Agencia   Norte  "), headers=headers)
    same_values_other = client.post("/agencias", json=agencia_payload(other_empresa.id, codigoInterno=" ag-dup ", nome="Agencia Norte"), headers=other_headers)

    assert duplicate_codigo.status_code == 409
    assert duplicate_nome.status_code == 409
    assert same_values_other.status_code == 201


def test_agencia_events_full_sequence_with_restricted_payload(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    created = create_agencia(client, headers, empresa.id, codigoInterno="AG-EVENTOS", nome="Agencia Eventos")

    client.patch(f"/agencias/{created['id']}", json={"nome": "Agencia Alterada"}, headers=headers)
    client.post(f"/agencias/{created['id']}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    client.post(f"/agencias/{created['id']}/reativar", headers=headers)

    persisted_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "agencia" and evento.entidade_id == created["id"]]
    assert [evento.tipo for evento in persisted_events] == [
        DomainEventType.AGENCIA_CRIADA.value,
        DomainEventType.AGENCIA_ALTERADA.value,
        DomainEventType.AGENCIA_INATIVADA.value,
        DomainEventType.AGENCIA_REATIVADA.value,
    ]
    for evento in persisted_events:
        assert evento.usuario_id == admin.id
        assert set(evento.payload) == {"empresa_id", "agencia_id", "timestamp", "actor_usuario_id"}
        assert evento.payload["actor_usuario_id"] == admin.id
        assert "nome" not in evento.payload
        assert "sigla" not in evento.payload
        assert "descricao" not in evento.payload


def test_service_create_agencia_rolls_back_when_event_publish_fails(session_factory):
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    service = AgenciaService(event_publisher=FailingPublisher())
    data = AgenciaCreate(
        empresaId=empresa.id,
        codigoInterno="AG-ROLLBACK",
        nome="Agencia Rollback",
        sigla="RB",
        descricao="teste rollback",
    )

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_agencia(db, data)

    assert [agencia for agencia in agencias(session_factory) if agencia.codigo_interno == "AG-ROLLBACK"] == []
