from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from conftest import auth_headers, create_auth_context, eventos, make_empresa, persist
from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.models.equipe import Equipe
from app.schemas.equipe import EquipeCreate, EquipeResponse, EquipeUpdate
from app.services.equipe_service import EquipeService


def equipe_payload(empresa_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "departamentoId": str(uuid4()),
        "codigoInterno": f" eq-{uuid4().hex[:8]} ",
        "nome": f"  Equipe   {uuid4().hex[:8]}  ",
        "descricao": "  Equipe   operacional  ",
    }
    data.update(overrides)
    return data


def make_equipe(empresa_id: str, **overrides) -> Equipe:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"EQ-{uuid4().hex[:8]}",
        "nome": f"Equipe {uuid4().hex[:8]}",
        "descricao": "Equipe operacional",
        "status": "ativa",
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return Equipe(**data)


def make_departamento(empresa_id: str, **overrides) -> Departamento:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"DEP-{uuid4().hex[:8]}",
        "nome": f"Departamento {uuid4().hex[:8]}",
        "descricao": "Departamento de teste",
        "status": "ativa",
        "created_at": now,
        "updated_at": now,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Departamento(**data)


def persist_equipe(session_factory, empresa_id: str, **overrides) -> Equipe:
    if overrides.get("departamento_id") is None:
        departamento = persist(session_factory, make_departamento(empresa_id))
        overrides["departamento_id"] = departamento.id
    return persist(session_factory, make_equipe(empresa_id, **overrides))


def create_equipe(client, headers, empresa_id: str, **overrides):
    if "departamentoId" not in overrides:
        departamento = persist(client.session_factory, make_departamento(empresa_id))
        overrides["departamentoId"] = departamento.id
    response = client.post("/equipes", json=equipe_payload(empresa_id, **overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def equipes(session_factory) -> list[Equipe]:
    with session_factory() as db:
        return list(db.query(Equipe).all())


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_equipe_create_accepts_valid_departamento_id():
    departamento_id = uuid4()

    data = EquipeCreate.model_validate(
        equipe_payload(str(uuid4()), departamentoId=str(departamento_id))
    )

    assert data.departamento_id == departamento_id
    assert isinstance(data.departamento_id, UUID)


def test_equipe_create_requires_departamento_id():
    payload = equipe_payload(str(uuid4()))
    payload.pop("departamentoId")

    with pytest.raises(ValidationError):
        EquipeCreate.model_validate(payload)


def test_equipe_create_rejects_invalid_departamento_id():
    with pytest.raises(ValidationError):
        EquipeCreate.model_validate(
            equipe_payload(str(uuid4()), departamentoId="invalido")
        )


def test_equipe_response_exposes_required_departamento_id_with_camel_case_alias():
    now = datetime.now(timezone.utc)
    departamento_id = uuid4()
    response = EquipeResponse(
        id=uuid4(),
        empresaId=uuid4(),
        departamentoId=departamento_id,
        codigoInterno="EQ-001",
        nome="Equipe",
        status="ativa",
        createdAt=now,
        updatedAt=now,
    )

    assert response.model_dump(by_alias=True)["departamentoId"] == departamento_id

    with pytest.raises(ValidationError):
        EquipeResponse(
            id=uuid4(),
            empresaId=uuid4(),
            codigoInterno="EQ-002",
            nome="Equipe sem Departamento",
            status="ativa",
            createdAt=now,
            updatedAt=now,
        )


def test_equipe_update_rejects_departamento_id_in_direct_schema_validation():
    with pytest.raises(ValidationError):
        EquipeUpdate.model_validate({"departamentoId": str(uuid4())})


def test_equipes_endpoints_require_authentication(client):
    response = client.get("/equipes", params={"empresaId": str(uuid4())})

    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get("/equipes", params={"empresaId": str(uuid4())}, headers={"Authorization": "Bearer invalido"})

    assert response.status_code == 401


def test_admin_creates_equipe_with_normalization_and_authenticated_actor(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    equipe = create_equipe(
        client,
        headers,
        empresa.id,
        codigoInterno=" eq-001 ",
        nome="  Criacao   Digital  ",
        descricao="   ",
    )

    assert equipe["empresaId"] == empresa.id
    assert UUID(equipe["departamentoId"])
    assert equipe["codigoInterno"] == "EQ-001"
    assert equipe["nome"] == "Criacao Digital"
    assert equipe["descricao"] is None
    equipe_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.EQUIPE_CRIADA.value]
    assert len(equipe_events) == 1
    assert equipe_events[0].usuario_id == admin.id
    assert equipe_events[0].payload["actor_usuario_id"] == admin.id


def test_gestor_cannot_create_equipe(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    headers = auth_headers(client, gestor, empresa)

    response = client.post("/equipes", json=equipe_payload(empresa.id), headers=headers)

    assert response.status_code == 403


def test_operador_cannot_access_equipes(client):
    empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    headers = auth_headers(client, operador, empresa)

    response = client.get("/equipes", params={"empresaId": empresa.id}, headers=headers)

    assert response.status_code == 403


def test_admin_cannot_create_equipe_in_other_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.post("/equipes", json=equipe_payload(other.id), headers=headers)

    assert response.status_code == 403


def test_create_equipe_missing_or_inactive_empresa_still_validates_in_service(session_factory):
    service = EquipeService()

    with pytest.raises(Exception, match="Empresa não encontrada"):
        with session_factory() as db:
            service.create_equipe(db, EquipeCreate(**equipe_payload(str(uuid4()))))

    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    with session_factory() as db:
        persisted = db.get(type(empresa), empresa.id)
        persisted.status = "inativa"
        db.commit()

    with pytest.raises(Exception, match="Empresa inativa não permite criação de Equipe"):
        with session_factory() as db:
            service.create_equipe(db, EquipeCreate(**equipe_payload(empresa.id)))


def test_create_equipe_validates_departamento_exists_active_and_same_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other_empresa, _, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist(client.session_factory, make_departamento(empresa.id))
    other_departamento = persist(client.session_factory, make_departamento(other_empresa.id))
    inactive_departamento = persist(
        client.session_factory,
        make_departamento(empresa.id, status="inativa"),
    )
    archived_departamento = persist(
        client.session_factory,
        make_departamento(empresa.id, status="arquivada"),
    )
    headers = auth_headers(client, admin, empresa)

    created = client.post(
        "/equipes",
        json=equipe_payload(empresa.id, departamentoId=departamento.id),
        headers=headers,
    )
    missing = client.post(
        "/equipes",
        json=equipe_payload(empresa.id, departamentoId=str(uuid4())),
        headers=headers,
    )
    other_tenant = client.post(
        "/equipes",
        json=equipe_payload(empresa.id, departamentoId=other_departamento.id),
        headers=headers,
    )
    inactive = client.post(
        "/equipes",
        json=equipe_payload(empresa.id, departamentoId=inactive_departamento.id),
        headers=headers,
    )
    archived = client.post(
        "/equipes",
        json=equipe_payload(empresa.id, departamentoId=archived_departamento.id),
        headers=headers,
    )

    assert created.status_code == 201
    assert created.json()["departamentoId"] == departamento.id
    for response in (missing, other_tenant, inactive, archived):
        assert response.status_code == 422
        assert response.json() == {"detail": "Departamento não encontrado ou inativo"}


def test_create_equipe_rejects_empty_codigo_and_nome_after_normalization(session_factory):
    service = EquipeService()
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")

    with pytest.raises(Exception, match="codigoInterno é obrigatório"):
        with session_factory() as db:
            service.create_equipe(db, EquipeCreate(**equipe_payload(empresa.id, codigoInterno="   ")))

    with pytest.raises(Exception, match="nome é obrigatório"):
        with session_factory() as db:
            service.create_equipe(db, EquipeCreate(**equipe_payload(empresa.id, nome="   ")))


def test_equipe_duplicates_and_cross_empresa_rules_with_authenticated_api(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other_empresa, other_admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    other_headers = auth_headers(client, other_admin, other_empresa)
    departamento = persist(client.session_factory, make_departamento(empresa.id))
    other_departamento = persist(client.session_factory, make_departamento(other_empresa.id))

    create_equipe(
        client,
        headers,
        empresa.id,
        departamentoId=departamento.id,
        codigoInterno="EQ-DUP",
        nome="Criacao",
    )

    duplicate_codigo = client.post(
        "/equipes",
        json=equipe_payload(
            empresa.id,
            departamentoId=departamento.id,
            codigoInterno=" eq-dup ",
            nome="Atendimento",
        ),
        headers=headers,
    )
    duplicate_nome = client.post(
        "/equipes",
        json=equipe_payload(
            empresa.id,
            departamentoId=departamento.id,
            codigoInterno="EQ-2",
            nome="  Criacao  ",
        ),
        headers=headers,
    )
    same_values_other = client.post(
        "/equipes",
        json=equipe_payload(
            other_empresa.id,
            departamentoId=other_departamento.id,
            codigoInterno=" eq-dup ",
            nome="Criacao",
        ),
        headers=other_headers,
    )

    assert duplicate_codigo.status_code == 409
    assert duplicate_nome.status_code == 409
    assert same_values_other.status_code == 201


def test_admin_and_gestor_list_equipes_from_own_empresa_and_filter_status(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    active = persist_equipe(client.session_factory, empresa.id, codigo_interno="EQ-A", nome="Equipe Ativa")
    inactive = persist_equipe(client.session_factory, empresa.id, codigo_interno="EQ-I", nome="Equipe Inativa", status="inativa")
    gestor_equipe = persist_equipe(client.session_factory, gestor_empresa.id, codigo_interno="EQ-G", nome="Equipe Gestor")
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)

    admin_response = client.get("/equipes", params={"empresaId": empresa.id, "status": "ativa"}, headers=admin_headers)
    gestor_response = client.get("/equipes", params={"empresaId": gestor_empresa.id}, headers=gestor_headers)

    assert admin_response.status_code == 200
    assert [item["id"] for item in admin_response.json()] == [active.id]
    assert inactive.id not in [item["id"] for item in admin_response.json()]
    assert gestor_response.status_code == 200
    assert [item["id"] for item in gestor_response.json()] == [gestor_equipe.id]


def test_list_equipes_filters_by_busca(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    matched = persist_equipe(client.session_factory, empresa.id, codigo_interno="EQ-MIDIA", nome="Performance")
    persist_equipe(client.session_factory, empresa.id, codigo_interno="EQ-CRIACAO", nome="Criacao")
    headers = auth_headers(client, admin, empresa)

    response = client.get("/equipes", params={"empresaId": empresa.id, "busca": "midia"}, headers=headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [matched.id]


def test_service_list_equipes_without_departamento_id_preserves_existing_behavior(session_factory):
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    departamento_a = persist(session_factory, make_departamento(empresa.id))
    departamento_b = persist(session_factory, make_departamento(empresa.id))
    equipe_a = persist_equipe(session_factory, empresa.id, departamento_id=departamento_a.id)
    equipe_b = persist_equipe(session_factory, empresa.id, departamento_id=departamento_b.id)
    service = EquipeService()

    with session_factory() as db:
        result = service.list_equipes(db, empresa_id=empresa.id)

    assert {equipe.id for equipe in result} == {
        equipe_a.id,
        equipe_b.id,
    }


def test_service_list_equipes_filters_by_departamento_id(session_factory):
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    departamento_a = persist(session_factory, make_departamento(empresa.id))
    departamento_b = persist(session_factory, make_departamento(empresa.id))
    equipe_a_1 = persist_equipe(session_factory, empresa.id, departamento_id=departamento_a.id)
    equipe_a_2 = persist_equipe(session_factory, empresa.id, departamento_id=departamento_a.id)
    persist_equipe(session_factory, empresa.id, departamento_id=departamento_b.id)
    service = EquipeService()

    with session_factory() as db:
        result = service.list_equipes(
            db,
            empresa_id=empresa.id,
            departamento_id=departamento_a.id,
        )

    assert {equipe.id for equipe in result} == {equipe_a_1.id, equipe_a_2.id}


def test_list_equipes_filters_by_departamento_id(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento_a = persist(client.session_factory, make_departamento(empresa.id))
    departamento_b = persist(client.session_factory, make_departamento(empresa.id))
    equipe_a = persist_equipe(
        client.session_factory,
        empresa.id,
        departamento_id=departamento_a.id,
    )
    persist_equipe(
        client.session_factory,
        empresa.id,
        departamento_id=departamento_b.id,
    )
    headers = auth_headers(client, admin, empresa)

    response = client.get(
        "/equipes",
        params={
            "empresaId": empresa.id,
            "departamentoId": departamento_a.id,
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [equipe_a.id]
    assert response.json()[0]["departamentoId"] == departamento_a.id


def test_list_equipes_requires_empresa_id_for_authenticated_user(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    response = client.get("/equipes", headers=headers)

    assert response.status_code == 422


def test_list_equipes_rejects_divergent_empresa_id(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.get("/equipes", params={"empresaId": other.id}, headers=headers)

    assert response.status_code == 403


def test_get_equipe_by_id_and_other_tenant_returns_404(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    own_equipe = persist_equipe(client.session_factory, empresa.id, codigo_interno="EQ-OWN", nome="Equipe Propria")
    other_equipe = persist_equipe(client.session_factory, other.id, codigo_interno="EQ-OUT", nome="Equipe Outra")
    headers = auth_headers(client, admin, empresa)

    own_response = client.get(f"/equipes/{own_equipe.id}", headers=headers)
    other_response = client.get(f"/equipes/{other_equipe.id}", headers=headers)

    assert own_response.status_code == 200
    assert own_response.json()["id"] == own_equipe.id
    assert other_response.status_code == 404


def test_admin_updates_equipe_and_gestor_operador_cannot_update(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    operador_empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    equipe = persist_equipe(client.session_factory, empresa.id)
    gestor_equipe = persist_equipe(client.session_factory, gestor_empresa.id)
    operador_equipe = persist_equipe(client.session_factory, operador_empresa.id)
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)
    operador_headers = auth_headers(client, operador, operador_empresa)

    response = client.patch(
        f"/equipes/{equipe.id}",
        json={"codigoInterno": " eq-009 ", "nome": " Criacao   Digital ", "descricao": "  conteudo  "},
        headers=admin_headers,
    )
    gestor_response = client.patch(f"/equipes/{gestor_equipe.id}", json={"nome": "Bloqueada"}, headers=gestor_headers)
    operador_response = client.patch(f"/equipes/{operador_equipe.id}", json={"nome": "Bloqueada"}, headers=operador_headers)

    assert response.status_code == 200
    assert response.json()["codigoInterno"] == "EQ-009"
    assert response.json()["nome"] == "Criacao Digital"
    assert response.json()["descricao"] == "conteudo"
    assert gestor_response.status_code == 403
    assert operador_response.status_code == 403


def test_equipe_patch_rejects_forbidden_fields_with_authenticated_admin(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    equipe = persist_equipe(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    for field, value in [
        ("empresaId", str(uuid4())),
        ("departamentoId", str(uuid4())),
        ("status", "inativa"),
        ("createdAt", "2026-07-15T00:00:00Z"),
        ("updatedAt", "2026-07-15T00:00:00Z"),
        ("deletedAt", "2026-07-15T00:00:00Z"),
        ("inativadoAt", "2026-07-15T00:00:00Z"),
        ("motivoInativacao", "teste"),
        ("inativadoPorUsuarioId", str(uuid4())),
    ]:
        response = client.patch(f"/equipes/{equipe.id}", json={field: value}, headers=headers)
        assert response.status_code == 422
        assert field in response.json()["detail"]


def test_update_equipe_rejects_duplicates_after_normalization(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    first = persist_equipe(client.session_factory, empresa.id, codigo_interno="EQ-1", nome="Criacao")
    second = persist_equipe(client.session_factory, empresa.id, codigo_interno="EQ-2", nome="Atendimento")
    headers = auth_headers(client, admin, empresa)

    duplicate_codigo = client.patch(f"/equipes/{second.id}", json={"codigoInterno": " eq-1 "}, headers=headers)
    duplicate_nome = client.patch(f"/equipes/{second.id}", json={"nome": "  Criacao  "}, headers=headers)

    assert first.id
    assert duplicate_codigo.status_code == 409
    assert duplicate_nome.status_code == 409


def test_admin_status_actions_use_authenticated_actor_and_gestor_cannot_mutate(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    departamento = persist(client.session_factory, make_departamento(empresa.id))
    gestor_departamento = persist(client.session_factory, make_departamento(gestor_empresa.id))
    equipe = persist_equipe(client.session_factory, empresa.id, departamento_id=departamento.id)
    gestor_equipe = persist_equipe(
        client.session_factory,
        gestor_empresa.id,
        departamento_id=gestor_departamento.id,
    )
    fake_actor = str(uuid4())
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)

    inactivate = client.post(
        f"/equipes/{equipe.id}/inativar",
        json={"motivoInativacao": "encerramento", "actorUsuarioId": fake_actor},
        headers=admin_headers,
    )
    gestor_inactivate = client.post(f"/equipes/{gestor_equipe.id}/inativar", json={"motivoInativacao": "teste"}, headers=gestor_headers)

    assert inactivate.status_code == 422
    inactivate = client.post(f"/equipes/{equipe.id}/inativar", json={"motivoInativacao": "encerramento"}, headers=admin_headers)
    reactivate = client.post(f"/equipes/{equipe.id}/reativar", headers=admin_headers)
    assert inactivate.status_code == 200
    assert inactivate.json()["inativadoPorUsuarioId"] == admin.id
    assert reactivate.status_code == 200
    assert reactivate.json()["status"] == "ativa"
    assert gestor_inactivate.status_code == 403
    equipe_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "equipe" and evento.entidade_id == equipe.id]
    assert [evento.tipo for evento in equipe_events] == [DomainEventType.EQUIPE_INATIVADA.value, DomainEventType.EQUIPE_REATIVADA.value]
    for evento in equipe_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["actor_usuario_id"] == admin.id


def test_reativar_equipe_validates_departamento_exists_active_and_same_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other_empresa, _, _ = create_auth_context(client.session_factory, perfil_base="admin")
    active_departamento = persist(client.session_factory, make_departamento(empresa.id))
    other_departamento = persist(client.session_factory, make_departamento(other_empresa.id))
    inactive_departamento = persist(
        client.session_factory,
        make_departamento(empresa.id, status="inativa"),
    )
    archived_departamento = persist(
        client.session_factory,
        make_departamento(empresa.id, status="arquivada"),
    )
    valid = persist_equipe(
        client.session_factory,
        empresa.id,
        departamento_id=active_departamento.id,
        status="inativa",
    )
    invalid_equipes = [
        persist_equipe(
            client.session_factory,
            empresa.id,
            departamento_id=departamento_id,
            status="inativa",
        )
        for departamento_id in (
            other_departamento.id,
            inactive_departamento.id,
            archived_departamento.id,
        )
    ]
    headers = auth_headers(client, admin, empresa)

    success = client.post(f"/equipes/{valid.id}/reativar", headers=headers)
    failures = [
        client.post(f"/equipes/{equipe.id}/reativar", headers=headers)
        for equipe in invalid_equipes
    ]

    assert success.status_code == 200
    assert success.json()["status"] == "ativa"
    for response in failures:
        assert response.status_code == 422
        assert response.json() == {"detail": "Departamento não encontrado ou inativo"}
    with client.session_factory() as db:
        assert all(db.get(Equipe, equipe.id).status == "inativa" for equipe in invalid_equipes)
    reactivated_ids = {
        evento.entidade_id
        for evento in eventos(client.session_factory)
        if evento.tipo == DomainEventType.EQUIPE_REATIVADA.value
    }
    assert valid.id in reactivated_ids
    assert not reactivated_ids.intersection(equipe.id for equipe in invalid_equipes)


def test_reativar_equipe_rejects_missing_departamento(session_factory, monkeypatch):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    departamento = persist(session_factory, make_departamento(empresa.id))
    equipe = persist_equipe(
        session_factory,
        empresa.id,
        departamento_id=departamento.id,
        status="inativa",
    )
    service = EquipeService()
    monkeypatch.setattr(service.departamento_repository, "get_by_id", lambda db, departamento_id: None)

    with pytest.raises(Exception, match="Departamento não encontrado ou inativo"):
        with session_factory() as db:
            service.reativar_equipe(db, equipe.id, actor_usuario_id=actor.id)

    with session_factory() as db:
        assert db.get(Equipe, equipe.id).status == "inativa"
    assert not any(
        evento.tipo == DomainEventType.EQUIPE_REATIVADA.value
        and evento.entidade_id == equipe.id
        for evento in eventos(session_factory)
    )


def test_invalid_status_transitions_are_rejected(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    equipe = persist_equipe(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    reactivate_active = client.post(f"/equipes/{equipe.id}/reativar", headers=headers)
    client.post(f"/equipes/{equipe.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    inactivate_inactive = client.post(f"/equipes/{equipe.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers)

    assert reactivate_active.status_code == 409
    assert reactivate_active.json() == {"detail": "Equipe já está ativa"}
    assert inactivate_inactive.status_code == 409
    assert inactivate_inactive.json() == {"detail": "Equipe já está inativa"}


def test_archived_equipe_cannot_be_reactivated(session_factory):
    service = EquipeService()
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    equipe = persist_equipe(session_factory, empresa.id, status="arquivada")

    with pytest.raises(Exception, match="Equipe arquivada não pode ser reativada"):
        with session_factory() as db:
            service.reativar_equipe(db, equipe.id, actor_usuario_id=actor.id)


def test_equipe_events_full_sequence_with_restricted_payload(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    created = create_equipe(client, headers, empresa.id, codigoInterno="EQ-EVENTOS", nome="Equipe Eventos")

    client.patch(f"/equipes/{created['id']}", json={"nome": "Equipe Alterada", "descricao": "nova descricao"}, headers=headers)
    client.post(f"/equipes/{created['id']}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    client.post(f"/equipes/{created['id']}/reativar", headers=headers)

    persisted_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "equipe" and evento.entidade_id == created["id"]]
    assert [evento.tipo for evento in persisted_events] == [
        DomainEventType.EQUIPE_CRIADA.value,
        DomainEventType.EQUIPE_ALTERADA.value,
        DomainEventType.EQUIPE_INATIVADA.value,
        DomainEventType.EQUIPE_REATIVADA.value,
    ]
    for evento in persisted_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["empresa_id"] == empresa.id
        assert evento.payload["equipe_id"] == created["id"]
        assert evento.payload["actor_usuario_id"] == admin.id
        assert "timestamp" in evento.payload
        assert "nome" not in evento.payload
        assert "codigo_interno" not in evento.payload
        assert "codigoInterno" not in evento.payload
        assert "descricao" not in evento.payload
    alterado = [evento for evento in persisted_events if evento.tipo == DomainEventType.EQUIPE_ALTERADA.value][0]
    assert alterado.payload["campos_alterados"] == ["nome", "descricao"]


def test_service_create_equipe_rolls_back_when_event_publish_fails(session_factory):
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    departamento = persist(session_factory, make_departamento(empresa.id))
    service = EquipeService(event_publisher=FailingPublisher())
    data = EquipeCreate(
        empresaId=empresa.id,
        departamentoId=departamento.id,
        codigoInterno="EQ-ROLLBACK",
        nome="Equipe Rollback",
    )

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_equipe(db, data)

    assert [equipe for equipe in equipes(session_factory) if equipe.codigo_interno == "EQ-ROLLBACK"] == []


def test_service_update_equipe_rolls_back_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    equipe = persist_equipe(session_factory, empresa.id, nome="Equipe Original")
    service = EquipeService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.update_equipe(db, equipe.id, EquipeUpdate(nome="Equipe Alterada"), actor_usuario_id=actor.id)

    with session_factory() as db:
        persisted = db.get(Equipe, equipe.id)
        assert persisted.nome == "Equipe Original"


def test_service_status_actions_roll_back_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    departamento = persist(session_factory, make_departamento(empresa.id))
    active = persist_equipe(session_factory, empresa.id, codigo_interno="EQ-A", nome="Equipe Ativa")
    inactive = persist_equipe(
        session_factory,
        empresa.id,
        departamento_id=departamento.id,
        codigo_interno="EQ-I",
        nome="Equipe Inativa",
        status="inativa",
    )
    service = EquipeService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.inativar_equipe(db, active.id, motivo_inativacao="teste", actor_usuario_id=actor.id)

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.reativar_equipe(db, inactive.id, actor_usuario_id=actor.id)

    with session_factory() as db:
        assert db.get(Equipe, active.id).status == "ativa"
        assert db.get(Equipe, inactive.id).status == "inativa"


def test_delete_route_does_not_exist(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    equipe = persist_equipe(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    response = client.delete(f"/equipes/{equipe.id}", headers=headers)

    assert response.status_code == 405


def test_auth_login_and_me_still_work(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")

    login_response = client.post("/auth/login", json={"empresaCodigo": empresa.codigo_interno, "email": admin.email, "senha": "SenhaAtual123"})
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {login_response.json()['accessToken']}"})

    assert login_response.status_code == 200
    assert me_response.status_code == 200
