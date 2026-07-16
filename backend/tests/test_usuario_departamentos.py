from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from conftest import auth_headers, create_auth_context, eventos, make_empresa, make_usuario, persist
from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.models.usuario_departamento import UsuarioDepartamento
from app.schemas.usuario_departamento import UsuarioDepartamentoCreate, UsuarioDepartamentoEncerrar, UsuarioDepartamentoUpdate
from app.services.usuario_departamento_service import UsuarioDepartamentoService


def now() -> datetime:
    return datetime.now(timezone.utc)


def departamento(empresa_id: str, **overrides) -> Departamento:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"DEP-{uuid4().hex[:8]}",
        "nome": f"Departamento {uuid4().hex[:8]}",
        "descricao": "Departamento operacional",
        "status": "ativa",
        "created_at": current_time,
        "updated_at": current_time,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Departamento(**data)


def persist_departamento(session_factory, empresa_id: str, **overrides) -> Departamento:
    return persist(session_factory, departamento(empresa_id, **overrides))


def usuario_departamento(empresa_id: str, usuario_id: str, departamento_id: str, **overrides) -> UsuarioDepartamento:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "usuario_id": usuario_id,
        "departamento_id": departamento_id,
        "papel": "membro",
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
    return UsuarioDepartamento(**data)


def persist_vinculo(session_factory, empresa_id: str, usuario_id: str, departamento_id: str, **overrides) -> UsuarioDepartamento:
    return persist(session_factory, usuario_departamento(empresa_id, usuario_id, departamento_id, **overrides))


def payload(empresa_id: str, usuario_id: str, departamento_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "usuarioId": usuario_id,
        "departamentoId": departamento_id,
        "papel": "membro",
        "principal": False,
        "inicioEm": now().isoformat(),
    }
    data.update(overrides)
    return data


def create_vinculo(client, headers, empresa_id: str, usuario_id: str, departamento_id: str, **overrides):
    response = client.post(
        "/vinculos/departamentos",
        json=payload(empresa_id, usuario_id, departamento_id, **overrides),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def vinculos(session_factory) -> list[UsuarioDepartamento]:
    with session_factory() as db:
        return list(db.scalars(select(UsuarioDepartamento)).all())


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_authentication_and_authorization(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    operador_empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    dept = persist_departamento(client.session_factory, empresa.id)
    gestor_target = persist(client.session_factory, make_usuario(gestor_empresa.id, perfil_base="operador"))
    gestor_dept = persist_departamento(client.session_factory, gestor_empresa.id)
    gestor_vinculo = persist_vinculo(client.session_factory, gestor_empresa.id, gestor_target.id, gestor_dept.id)
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)
    operador_headers = auth_headers(client, operador, operador_empresa)

    assert client.get("/vinculos/departamentos", params={"empresaId": empresa.id}).status_code == 401
    assert client.get(
        "/vinculos/departamentos",
        params={"empresaId": empresa.id},
        headers={"Authorization": "Bearer invalido"},
    ).status_code == 401
    assert client.post(
        "/vinculos/departamentos",
        json=payload(empresa.id, target.id, dept.id),
        headers=admin_headers,
    ).status_code == 201
    assert client.post(
        "/vinculos/departamentos",
        json=payload(gestor_empresa.id, gestor_target.id, gestor_dept.id),
        headers=gestor_headers,
    ).status_code == 403
    assert client.get("/vinculos/departamentos", params={"empresaId": operador_empresa.id}, headers=operador_headers).status_code == 403
    assert client.get("/vinculos/departamentos", params={"empresaId": gestor_empresa.id}, headers=gestor_headers).status_code == 200
    assert client.get(f"/vinculos/departamentos/{gestor_vinculo.id}", headers=gestor_headers).status_code == 200
    assert client.patch(f"/vinculos/departamentos/{gestor_vinculo.id}", json={"papel": "gestor"}, headers=gestor_headers).status_code == 403
    assert client.post(
        f"/vinculos/departamentos/{gestor_vinculo.id}/encerrar",
        json={"fimEm": (now() + timedelta(days=1)).isoformat()},
        headers=gestor_headers,
    ).status_code == 403


def test_tenant_rules(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    other_user = persist(client.session_factory, make_usuario(other.id, perfil_base="operador"))
    dept = persist_departamento(client.session_factory, empresa.id)
    other_dept = persist_departamento(client.session_factory, other.id)
    own = persist_vinculo(client.session_factory, empresa.id, target.id, dept.id)
    other_link = persist_vinculo(client.session_factory, other.id, other_user.id, other_dept.id)
    headers = auth_headers(client, admin, empresa)

    assert client.get("/vinculos/departamentos", params={"empresaId": other.id}, headers=headers).status_code == 403
    assert client.get(f"/vinculos/departamentos/{other_link.id}", headers=headers).status_code == 404
    assert client.post(
        "/vinculos/departamentos",
        json=payload(empresa.id, other_user.id, dept.id),
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/vinculos/departamentos",
        json=payload(empresa.id, target.id, other_dept.id),
        headers=headers,
    ).status_code == 422
    assert client.get(
        "/vinculos/departamentos",
        params={"empresaId": empresa.id, "usuarioId": other_user.id},
        headers=headers,
    ).status_code == 422
    response = client.get("/vinculos/departamentos", params={"empresaId": empresa.id}, headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own.id]


@pytest.mark.parametrize("papel", ["membro", "gestor", "head"])
def test_admin_creates_allowed_papeis(client, papel):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    dept = persist_departamento(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    created = create_vinculo(client, headers, empresa.id, target.id, dept.id, papel=papel)

    assert created["papel"] == papel
    assert created["criadoPorUsuarioId"] == admin.id


def test_creation_validates_entities_and_conflicts(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    inactive_user = persist(client.session_factory, make_usuario(empresa.id, status="inativo"))
    dept = persist_departamento(client.session_factory, empresa.id)
    inactive_dept = persist_departamento(client.session_factory, empresa.id, status="inativa")
    inactive_empresa = persist(client.session_factory, make_empresa(status="inativa", codigo_interno="INATIVA"))
    headers = auth_headers(client, admin, empresa)

    create_vinculo(client, headers, empresa.id, target.id, dept.id)
    assert client.post("/vinculos/departamentos", json=payload(empresa.id, target.id, dept.id), headers=headers).status_code == 409
    assert client.post("/vinculos/departamentos", json=payload(empresa.id, str(uuid4()), dept.id), headers=headers).status_code == 422
    assert client.post("/vinculos/departamentos", json=payload(empresa.id, inactive_user.id, dept.id), headers=headers).status_code == 422
    assert client.post("/vinculos/departamentos", json=payload(empresa.id, target.id, str(uuid4())), headers=headers).status_code == 422
    assert client.post("/vinculos/departamentos", json=payload(empresa.id, target.id, inactive_dept.id), headers=headers).status_code == 422
    assert client.post("/vinculos/departamentos", json=payload(str(uuid4()), target.id, dept.id), headers=headers).status_code == 403

    inactive_target = persist(client.session_factory, make_usuario(inactive_empresa.id, perfil_base="operador"))
    inactive_empresa_dept = persist_departamento(client.session_factory, inactive_empresa.id)
    with pytest.raises(Exception, match="Empresa não encontrada ou inativa"):
        with client.session_factory() as db:
            UsuarioDepartamentoService().vincular_usuario_departamento(
                db,
                UsuarioDepartamentoCreate(**payload(inactive_empresa.id, inactive_target.id, inactive_empresa_dept.id)),
                actor_usuario_id=admin.id,
            )


def test_head_gestor_and_principal_rules(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    first = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    second = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    dept = persist_departamento(client.session_factory, empresa.id)
    another_dept = persist_departamento(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    create_vinculo(client, headers, empresa.id, first.id, dept.id, papel="head")
    assert client.post(
        "/vinculos/departamentos",
        json=payload(empresa.id, second.id, dept.id, papel="head"),
        headers=headers,
    ).status_code == 409
    gestor_1 = create_vinculo(client, headers, empresa.id, second.id, dept.id, papel="gestor")
    gestor_2 = create_vinculo(client, headers, empresa.id, second.id, another_dept.id, papel="gestor")
    assert gestor_1["papel"] == "gestor"
    assert gestor_2["papel"] == "gestor"

    principal_dept = persist_departamento(client.session_factory, empresa.id)
    secondary_dept = persist_departamento(client.session_factory, empresa.id)
    principal = create_vinculo(client, headers, empresa.id, first.id, principal_dept.id, principal=True)
    secondary = create_vinculo(client, headers, empresa.id, first.id, secondary_dept.id)
    assert principal["principal"] is True
    assert secondary["principal"] is False


def test_return_to_department_after_closure_creates_new_record(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    dept = persist_departamento(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)
    first = create_vinculo(client, headers, empresa.id, target.id, dept.id)

    close = client.post(
        f"/vinculos/departamentos/{first['id']}/encerrar",
        json={"fimEm": (now() + timedelta(days=1)).isoformat()},
        headers=headers,
    )
    second = create_vinculo(client, headers, empresa.id, target.id, dept.id)

    assert close.status_code == 200
    assert second["id"] != first["id"]


def test_update_rules_and_forbidden_fields(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    first = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    second = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    dept = persist_departamento(client.session_factory, empresa.id)
    second_dept = persist_departamento(client.session_factory, empresa.id)
    first_link = persist_vinculo(client.session_factory, empresa.id, first.id, dept.id)
    second_link = persist_vinculo(client.session_factory, empresa.id, second.id, dept.id, papel="head")
    inactive = persist_vinculo(
        client.session_factory,
        empresa.id,
        first.id,
        second_dept.id,
        status="inativo",
        fim_em=now() + timedelta(days=1),
    )
    headers = auth_headers(client, admin, empresa)

    update = client.patch(f"/vinculos/departamentos/{first_link.id}", json={"papel": "gestor"}, headers=headers)
    promote = client.patch(f"/vinculos/departamentos/{first_link.id}", json={"papel": "head"}, headers=headers)
    inactive_update = client.patch(f"/vinculos/departamentos/{inactive.id}", json={"papel": "gestor"}, headers=headers)
    forbidden = client.patch(f"/vinculos/departamentos/{first_link.id}", json={"usuarioId": str(uuid4())}, headers=headers)

    assert update.status_code == 200
    assert update.json()["papel"] == "gestor"
    assert promote.status_code == 409
    assert second_link.id
    assert inactive_update.status_code == 409
    assert forbidden.status_code == 422


def test_principal_change_is_transactional_and_emits_two_events(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_dept = persist_departamento(client.session_factory, empresa.id)
    second_dept = persist_departamento(client.session_factory, empresa.id)
    first = persist_vinculo(client.session_factory, empresa.id, target.id, first_dept.id, principal=True)
    second = persist_vinculo(client.session_factory, empresa.id, target.id, second_dept.id)
    headers = auth_headers(client, admin, empresa)

    response = client.patch(f"/vinculos/departamentos/{second.id}", json={"principal": True}, headers=headers)

    assert response.status_code == 200
    with client.session_factory() as db:
        assert db.get(UsuarioDepartamento, first.id).principal is False
        assert db.get(UsuarioDepartamento, second.id).principal is True
    changed_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.USUARIO_DEPARTAMENTO_ALTERADO.value]
    assert [evento.payload["campos_alterados"] for evento in changed_events] == [["principal"], ["principal"]]


def test_encerrar_rules_and_no_delete_or_reactivation(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    dept = persist_departamento(client.session_factory, empresa.id)
    link = persist_vinculo(client.session_factory, empresa.id, target.id, dept.id, principal=True)
    headers = auth_headers(client, admin, empresa)

    missing_fim = client.post(f"/vinculos/departamentos/{link.id}/encerrar", json={}, headers=headers)
    naive_fim = client.post(f"/vinculos/departamentos/{link.id}/encerrar", json={"fimEm": "2026-07-16T10:00:00"}, headers=headers)
    extra_actor = client.post(
        f"/vinculos/departamentos/{link.id}/encerrar",
        json={"fimEm": (now() + timedelta(days=1)).isoformat(), "actorUsuarioId": str(uuid4())},
        headers=headers,
    )
    close = client.post(
        f"/vinculos/departamentos/{link.id}/encerrar",
        json={"fimEm": (now() + timedelta(days=1)).isoformat(), "motivoEncerramento": "  saida   operacao  "},
        headers=headers,
    )
    close_again = client.post(
        f"/vinculos/departamentos/{link.id}/encerrar",
        json={"fimEm": (now() + timedelta(days=2)).isoformat()},
        headers=headers,
    )

    assert missing_fim.status_code == 422
    assert naive_fim.status_code == 422
    assert extra_actor.status_code == 422
    assert close.status_code == 200
    assert close.json()["status"] == "inativo"
    assert close.json()["principal"] is False
    assert close.json()["encerradoPorUsuarioId"] == admin.id
    assert close_again.status_code == 409
    assert client.post(f"/vinculos/departamentos/{link.id}/reativar", headers=headers).status_code == 404
    assert client.delete(f"/vinculos/departamentos/{link.id}", headers=headers).status_code == 405


def test_events_payload_is_restricted(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador", email="sensivel@empresa.com"))
    dept = persist_departamento(client.session_factory, empresa.id, descricao="Descricao sensivel")
    headers = auth_headers(client, admin, empresa)
    created = create_vinculo(client, headers, empresa.id, target.id, dept.id)
    client.patch(f"/vinculos/departamentos/{created['id']}", json={"papel": "gestor"}, headers=headers)
    client.post(
        f"/vinculos/departamentos/{created['id']}/encerrar",
        json={"fimEm": (now() + timedelta(days=1)).isoformat(), "motivoEncerramento": "motivo completo"},
        headers=headers,
    )

    link_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "usuario_departamento"]
    assert [evento.tipo for evento in link_events] == [
        DomainEventType.USUARIO_DEPARTAMENTO_VINCULADO.value,
        DomainEventType.USUARIO_DEPARTAMENTO_ALTERADO.value,
        DomainEventType.USUARIO_DEPARTAMENTO_ENCERRADO.value,
    ]
    for evento in link_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["empresa_id"] == empresa.id
        assert evento.payload["usuario_id"] == target.id
        assert evento.payload["departamento_id"] == dept.id
        assert evento.payload["actor_usuario_id"] == admin.id
        assert "timestamp" in evento.payload
        assert "nome" not in evento.payload
        assert "email" not in evento.payload
        assert "descricao" not in evento.payload
        assert "motivo" not in str(evento.payload)
        if "campos_alterados" in evento.payload:
            assert all(isinstance(field, str) for field in evento.payload["campos_alterados"])


def test_rollbacks_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_dept = persist_departamento(session_factory, empresa.id)
    second_dept = persist_departamento(session_factory, empresa.id)
    service = UsuarioDepartamentoService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.vincular_usuario_departamento(
                db,
                UsuarioDepartamentoCreate(**payload(empresa.id, target.id, first_dept.id)),
                actor_usuario_id=actor.id,
            )
    assert vinculos(session_factory) == []

    active = persist_vinculo(session_factory, empresa.id, target.id, first_dept.id, papel="membro")
    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.alterar_vinculo(db, active.id, UsuarioDepartamentoUpdate(papel="gestor"), actor_usuario_id=actor.id)
    with session_factory() as db:
        assert db.get(UsuarioDepartamento, active.id).papel == "membro"

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.encerrar_vinculo(
                db,
                active.id,
                UsuarioDepartamentoEncerrar(fimEm=(now() + timedelta(days=1)).isoformat()),
                actor_usuario_id=actor.id,
            )
    with session_factory() as db:
        assert db.get(UsuarioDepartamento, active.id).status == "ativo"

    principal = persist_vinculo(session_factory, empresa.id, target.id, second_dept.id, principal=True)
    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.alterar_vinculo(db, active.id, UsuarioDepartamentoUpdate(principal=True), actor_usuario_id=actor.id)
    with session_factory() as db:
        assert db.get(UsuarioDepartamento, principal.id).principal is True
        assert db.get(UsuarioDepartamento, active.id).principal is False


def test_auth_regression(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    login = client.post("/auth/login", json={"empresaCodigo": empresa.codigo_interno, "email": admin.email, "senha": "SenhaAtual123"})
    assert login.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {login.json()['accessToken']}"})
    assert me.status_code == 200
    assert me.json()["usuarioId"] == admin.id
