from uuid import uuid4

import pytest

from conftest import auth_headers, create_auth_context, eventos, make_empresa, persist
from app.domain.event_types import DomainEventType
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate
from app.services.empresa_service import EmpresaService


def empresa_payload(**overrides):
    data = {
        "nome": "Empresa Nova",
        "documento": uuid4().hex,
        "codigoInterno": f"EMP-{uuid4().hex[:8]}",
    }
    data.update(overrides)
    return data


def test_empresas_endpoints_require_authentication(client):
    response = client.get("/empresas")

    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get("/empresas", headers={"Authorization": "Bearer token-invalido"})

    assert response.status_code == 401


def test_get_empresas_returns_only_authenticated_empresa_for_admin(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.get("/empresas", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [empresa.id]
    assert other.id not in [item["id"] for item in body]


def test_get_empresas_filter_does_not_load_other_tenants(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    persist(client.session_factory, make_empresa(codigo_interno="INATIVA", status="inativa"))
    headers = auth_headers(client, admin, empresa)

    response = client.get("/empresas", params={"status": "inativa"}, headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_gestor_can_get_own_empresa_but_not_list(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    headers = auth_headers(client, gestor, empresa)

    list_response = client.get("/empresas", headers=headers)
    get_response = client.get(f"/empresas/{empresa.id}", headers=headers)

    assert list_response.status_code == 403
    assert get_response.status_code == 200
    assert get_response.json()["id"] == empresa.id


def test_get_empresa_from_other_tenant_returns_404(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.get(f"/empresas/{other.id}", headers=headers)

    assert response.status_code == 404


def test_operador_cannot_access_empresa_without_resource_leak(client):
    empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, operador, empresa)

    own_response = client.get(f"/empresas/{empresa.id}", headers=headers)
    other_response = client.get(f"/empresas/{other.id}", headers=headers)

    assert own_response.status_code == 403
    assert other_response.status_code == 403
    assert own_response.json() == other_response.json()


def test_admin_can_patch_own_empresa_and_actor_is_authenticated_user(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    response = client.patch(f"/empresas/{empresa.id}", json={"nome": "Empresa Atualizada"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["nome"] == "Empresa Atualizada"
    empresa_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.EMPRESA_ALTERADA.value]
    assert len(empresa_events) == 1
    assert empresa_events[0].usuario_id == admin.id


def test_gestor_cannot_patch_empresa(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    headers = auth_headers(client, gestor, empresa)

    response = client.patch(f"/empresas/{empresa.id}", json={"nome": "Bloqueada"}, headers=headers)

    assert response.status_code == 403


def test_admin_cannot_patch_other_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.patch(f"/empresas/{other.id}", json={"nome": "Outra"}, headers=headers)

    assert response.status_code == 403


def test_empresa_lifecycle_and_creation_are_blocked_for_admin(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    create_response = client.post("/empresas", json=empresa_payload(), headers=headers)
    inactivate_response = client.post(f"/empresas/{empresa.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    reactivate_response = client.post(f"/empresas/{empresa.id}/reativar", headers=headers)

    assert create_response.status_code == 403
    assert inactivate_response.status_code == 403
    assert reactivate_response.status_code == 403


def test_auth_me_and_apis_deny_after_usuario_becomes_inactive(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    with client.session_factory() as db:
        user = db.get(type(admin), admin.id)
        user.status = "inativo"
        db.commit()

    me_response = client.get("/auth/me", headers=headers)
    api_response = client.get("/empresas", headers=headers)

    assert me_response.status_code == 401
    assert api_response.status_code == 401


def test_auth_me_and_apis_deny_after_empresa_becomes_inactive(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    with client.session_factory() as db:
        persisted = db.get(type(empresa), empresa.id)
        persisted.status = "inativa"
        db.commit()

    me_response = client.get("/auth/me", headers=headers)
    api_response = client.get("/empresas", headers=headers)

    assert me_response.status_code == 401
    assert api_response.status_code == 401


def test_delete_route_does_not_exist(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    response = client.delete(f"/empresas/{empresa.id}", headers=headers)

    assert response.status_code == 405


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def empresas(session_factory) -> list[Empresa]:
    with session_factory() as db:
        return list(db.query(Empresa).all())


def test_service_create_empresa_preserves_duplicate_and_null_document_rules(session_factory):
    service = EmpresaService()

    with session_factory() as db:
        first = service.create_empresa(db, EmpresaCreate(nome="Empresa 1", documento=None, codigoInterno="EMP-1"))
        second = service.create_empresa(db, EmpresaCreate(nome="Empresa 2", documento=None, codigoInterno="EMP-2"))
        first_documento = first.documento
        second_documento = second.documento

    assert first_documento is None
    assert second_documento is None

    with pytest.raises(Exception, match="codigoInterno já cadastrado"):
        with session_factory() as db:
            service.create_empresa(db, EmpresaCreate(nome="Duplicada", documento="00000000000300", codigoInterno="EMP-1"))

    with pytest.raises(Exception, match="documento já cadastrado"):
        with session_factory() as db:
            service.create_empresa(db, EmpresaCreate(nome="Doc Duplicado", documento="00000000000400", codigoInterno="EMP-4"))
            service.create_empresa(db, EmpresaCreate(nome="Doc Duplicado 2", documento="00000000000400", codigoInterno="EMP-5"))


def test_service_create_empresa_persists_razao_social(session_factory):
    service = EmpresaService()

    with session_factory() as db:
        created = service.create_empresa(
            db,
            EmpresaCreate(
                nome="BOX COMUNICAÇÃO",
                razaoSocial="Box Comunicação LTDA",
                documento="15519472000122",
                codigoInterno="BOX",
            ),
        )
        razao_social = created.razao_social

    assert razao_social == "Box Comunicação LTDA"


def test_service_create_empresa_allows_missing_razao_social(session_factory):
    service = EmpresaService()

    with session_factory() as db:
        created = service.create_empresa(
            db, EmpresaCreate(nome="Empresa Sem Razão", documento=None, codigoInterno="SEM-RAZAO")
        )
        razao_social = created.razao_social

    assert razao_social is None


def test_service_create_empresa_normalizes_documento_to_digits_only(session_factory):
    service = EmpresaService()

    with session_factory() as db:
        created = service.create_empresa(
            db,
            EmpresaCreate(nome="BOX COMUNICAÇÃO", documento="15.519.472/0001-22", codigoInterno="BOX"),
        )
        documento = created.documento

    assert documento == "15519472000122"


def test_admin_can_patch_razao_social(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    response = client.patch(
        f"/empresas/{empresa.id}", json={"razaoSocial": "Nova Razão Social LTDA"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["razaoSocial"] == "Nova Razão Social LTDA"


def test_empresa_documento_is_not_in_event_payload_on_authenticated_update(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    response = client.patch(f"/empresas/{empresa.id}", json={"documento": "00000000000999"}, headers=headers)

    assert response.status_code == 200
    for evento in eventos(client.session_factory):
        assert "documento" not in evento.payload


def test_service_create_empresa_rolls_back_when_event_publish_fails(session_factory):
    service = EmpresaService(event_publisher=FailingPublisher())
    data = EmpresaCreate(nome="Empresa Rollback", documento="00000000000100", codigoInterno="EMP-ROLLBACK")

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_empresa(db, data)

    assert empresas(session_factory) == []
    assert eventos(session_factory) == []


def test_service_inativar_empresa_preserves_status_audit_and_event(session_factory):
    service = EmpresaService()
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")

    with session_factory() as db:
        updated = service.inativar_empresa(
            db,
            empresa.id,
            motivo_inativacao="encerramento operacional",
            actor_usuario_id=actor.id,
        )
        status_atual = updated.status
        inativado_por = updated.inativado_por_usuario_id
        motivo = updated.motivo_inativacao
        inativado_at = updated.inativado_at

    assert status_atual == "inativa"
    assert inativado_por == actor.id
    assert motivo == "encerramento operacional"
    assert inativado_at is not None
    empresa_events = [evento for evento in eventos(session_factory) if evento.tipo == DomainEventType.EMPRESA_INATIVADA.value]
    assert len(empresa_events) == 1
    assert empresa_events[0].usuario_id == actor.id


def test_service_reativar_empresa_preserves_status_audit_and_event(session_factory):
    service = EmpresaService()
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")

    with session_factory() as db:
        service.inativar_empresa(db, empresa.id, motivo_inativacao="teste", actor_usuario_id=actor.id)
    with session_factory() as db:
        updated = service.reativar_empresa(db, empresa.id, actor_usuario_id=actor.id)
        status_atual = updated.status
        inativado_por = updated.inativado_por_usuario_id
        motivo = updated.motivo_inativacao
        inativado_at = updated.inativado_at

    assert status_atual == "ativa"
    assert inativado_por is None
    assert motivo is None
    assert inativado_at is None
    empresa_events = [evento for evento in eventos(session_factory) if evento.tipo == DomainEventType.EMPRESA_REATIVADA.value]
    assert len(empresa_events) == 1
    assert empresa_events[0].usuario_id == actor.id


def test_service_empresa_invalid_transitions_are_preserved(session_factory):
    service = EmpresaService()
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")

    with pytest.raises(Exception, match="Empresa já está ativa"):
        with session_factory() as db:
            service.reativar_empresa(db, empresa.id, actor_usuario_id=actor.id)

    with session_factory() as db:
        service.inativar_empresa(db, empresa.id, motivo_inativacao="teste", actor_usuario_id=actor.id)

    with pytest.raises(Exception, match="Empresa já está inativa"):
        with session_factory() as db:
            service.inativar_empresa(db, empresa.id, motivo_inativacao="teste", actor_usuario_id=actor.id)
