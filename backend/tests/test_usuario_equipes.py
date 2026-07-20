from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.models.equipe import Equipe
from app.models.usuario_equipe import UsuarioEquipe
from conftest import auth_headers, create_auth_context, eventos, make_empresa, make_usuario, persist


def now() -> datetime:
    return datetime.now(timezone.utc)


def equipe(empresa_id: str, **overrides) -> Equipe:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"EQ-{uuid4().hex[:8]}",
        "nome": f"Equipe {uuid4().hex[:8]}",
        "descricao": "Equipe de teste",
        "status": "ativa",
        "created_at": current_time,
        "updated_at": current_time,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Equipe(**data)


def departamento(empresa_id: str) -> Departamento:
    current_time = now()
    return Departamento(
        id=str(uuid4()),
        empresa_id=empresa_id,
        codigo_interno=f"DEP-{uuid4().hex[:8]}",
        nome=f"Departamento {uuid4().hex[:8]}",
        descricao="Departamento de teste",
        status="ativa",
        created_at=current_time,
        updated_at=current_time,
        inativado_at=None,
        motivo_inativacao=None,
        inativado_por_usuario_id=None,
    )


def persist_equipe(session_factory, empresa_id: str, **overrides) -> Equipe:
    dep = persist(session_factory, departamento(empresa_id))
    return persist(
        session_factory,
        equipe(empresa_id, departamento_id=dep.id, **overrides),
    )


def usuario_equipe(empresa_id: str, usuario_id: str, equipe_id: str, **overrides) -> UsuarioEquipe:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "usuario_id": usuario_id,
        "equipe_id": equipe_id,
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
    return UsuarioEquipe(**data)


def persist_vinculo(session_factory, empresa_id: str, usuario_id: str, equipe_id: str, **overrides) -> UsuarioEquipe:
    return persist(session_factory, usuario_equipe(empresa_id, usuario_id, equipe_id, **overrides))


def payload(empresa_id: str, usuario_id: str, equipe_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "usuarioId": usuario_id,
        "equipeId": equipe_id,
        "papel": "membro",
        "principal": False,
    }
    data.update(overrides)
    return data


def create_vinculo(client, headers, empresa_id: str, usuario_id: str, equipe_id: str, **overrides):
    response = client.post(
        "/vinculos/equipes",
        json=payload(empresa_id, usuario_id, equipe_id, **overrides),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def vinculos(session_factory) -> list[UsuarioEquipe]:
    with session_factory() as db:
        return list(db.scalars(select(UsuarioEquipe).order_by(UsuarioEquipe.created_at, UsuarioEquipe.id)).all())


def test_authentication_and_authorization(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    operador_empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    team = persist_equipe(client.session_factory, empresa.id)
    gestor_target = persist(client.session_factory, make_usuario(gestor_empresa.id, perfil_base="operador"))
    gestor_team = persist_equipe(client.session_factory, gestor_empresa.id)
    gestor_vinculo = persist_vinculo(client.session_factory, gestor_empresa.id, gestor_target.id, gestor_team.id)
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)
    operador_headers = auth_headers(client, operador, operador_empresa)

    assert client.get("/vinculos/equipes", params={"empresaId": empresa.id}).status_code == 401
    assert client.get(
        "/vinculos/equipes",
        params={"empresaId": empresa.id},
        headers={"Authorization": "Bearer invalido"},
    ).status_code == 401
    assert client.post("/vinculos/equipes", json=payload(empresa.id, target.id, team.id), headers=admin_headers).status_code == 201
    assert client.post(
        "/vinculos/equipes",
        json=payload(gestor_empresa.id, gestor_target.id, gestor_team.id),
        headers=gestor_headers,
    ).status_code == 403
    assert client.get("/vinculos/equipes", params={"empresaId": operador_empresa.id}, headers=operador_headers).status_code == 403
    assert client.get("/vinculos/equipes", params={"empresaId": gestor_empresa.id}, headers=gestor_headers).status_code == 200
    assert client.get(f"/vinculos/equipes/{gestor_vinculo.id}", headers=gestor_headers).status_code == 200
    assert client.patch(f"/vinculos/equipes/{gestor_vinculo.id}", json={"papel": "coordenador"}, headers=gestor_headers).status_code == 403
    assert client.post(f"/vinculos/equipes/{gestor_vinculo.id}/encerrar", json={}, headers=gestor_headers).status_code == 403


def test_tenant_rules(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    other_user = persist(client.session_factory, make_usuario(other.id, perfil_base="operador"))
    team = persist_equipe(client.session_factory, empresa.id)
    other_team = persist_equipe(client.session_factory, other.id)
    own = persist_vinculo(client.session_factory, empresa.id, target.id, team.id)
    other_link = persist_vinculo(client.session_factory, other.id, other_user.id, other_team.id)
    headers = auth_headers(client, admin, empresa)

    assert client.get("/vinculos/equipes", params={"empresaId": other.id}, headers=headers).status_code == 403
    assert client.get(f"/vinculos/equipes/{other_link.id}", headers=headers).status_code == 404
    assert client.post("/vinculos/equipes", json=payload(empresa.id, other_user.id, team.id), headers=headers).status_code == 422
    assert client.post("/vinculos/equipes", json=payload(empresa.id, target.id, other_team.id), headers=headers).status_code == 422
    assert client.get("/vinculos/equipes", params={"empresaId": empresa.id, "usuarioId": other_user.id}, headers=headers).status_code == 422
    assert client.get("/vinculos/equipes", params={"empresaId": empresa.id, "equipeId": other_team.id}, headers=headers).status_code == 422
    response = client.get("/vinculos/equipes", params={"empresaId": empresa.id}, headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own.id]



def test_creation_roles_conflicts_principal_and_return_after_close(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    first = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    second = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    teams = [persist_equipe(client.session_factory, empresa.id) for _ in range(6)]
    inactive_user = persist(client.session_factory, make_usuario(empresa.id, status="inativo"))
    inactive_team = persist_equipe(client.session_factory, empresa.id, status="inativa")
    headers = auth_headers(client, admin, empresa)

    membro = create_vinculo(client, headers, empresa.id, first.id, teams[0].id, papel="membro")
    lider = create_vinculo(client, headers, empresa.id, first.id, teams[1].id, papel="lider")
    coordenador = create_vinculo(client, headers, empresa.id, first.id, teams[2].id, papel="coordenador")
    principal = create_vinculo(client, headers, empresa.id, first.id, teams[3].id, principal=True)
    secondary = create_vinculo(client, headers, empresa.id, first.id, teams[4].id)

    assert membro["papel"] == "membro"
    assert lider["papel"] == "lider"
    assert coordenador["papel"] == "coordenador"
    assert principal["principal"] is True
    assert secondary["principal"] is False
    assert client.post("/vinculos/equipes", json=payload(empresa.id, first.id, teams[0].id), headers=headers).status_code == 409
    assert client.post("/vinculos/equipes", json=payload(empresa.id, second.id, teams[1].id, papel="lider"), headers=headers).status_code == 409
    assert client.post("/vinculos/equipes", json=payload(empresa.id, str(uuid4()), teams[5].id), headers=headers).status_code == 422
    assert client.post("/vinculos/equipes", json=payload(empresa.id, inactive_user.id, teams[5].id), headers=headers).status_code == 422
    assert client.post("/vinculos/equipes", json=payload(empresa.id, first.id, str(uuid4())), headers=headers).status_code == 422
    assert client.post("/vinculos/equipes", json=payload(empresa.id, first.id, inactive_team.id), headers=headers).status_code == 422

    close = client.post(f"/vinculos/equipes/{membro['id']}/encerrar", json={"motivoEncerramento": "saida"}, headers=headers)
    returned = create_vinculo(client, headers, empresa.id, first.id, teams[0].id)
    assert close.status_code == 200
    assert returned["id"] != membro["id"]


def test_list_filters_limit_offset_and_no_leak(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    user = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    other_user = persist(client.session_factory, make_usuario(other.id, perfil_base="operador"))
    first_team = persist_equipe(client.session_factory, empresa.id)
    second_team = persist_equipe(client.session_factory, empresa.id)
    third_team = persist_equipe(client.session_factory, empresa.id)
    other_team = persist_equipe(client.session_factory, other.id)
    first = persist_vinculo(client.session_factory, empresa.id, user.id, first_team.id, papel="lider", principal=True)
    second = persist_vinculo(client.session_factory, empresa.id, user.id, second_team.id, papel="coordenador")
    closed = persist_vinculo(
        client.session_factory,
        empresa.id,
        user.id,
        third_team.id,
        status="encerrado",
        fim_em=now() + timedelta(minutes=1),
    )
    persist_vinculo(client.session_factory, other.id, other_user.id, other_team.id)
    headers = auth_headers(client, admin, empresa)

    base = {"empresaId": empresa.id}
    assert {item["id"] for item in client.get("/vinculos/equipes", params=base, headers=headers).json()} == {first.id, second.id, closed.id}
    assert {item["id"] for item in client.get("/vinculos/equipes", params={**base, "usuarioId": user.id}, headers=headers).json()} == {first.id, second.id, closed.id}
    assert [item["id"] for item in client.get("/vinculos/equipes", params={**base, "equipeId": first_team.id}, headers=headers).json()] == [first.id]
    assert [item["id"] for item in client.get("/vinculos/equipes", params={**base, "papel": "lider"}, headers=headers).json()] == [first.id]
    assert [item["id"] for item in client.get("/vinculos/equipes", params={**base, "status": "encerrado"}, headers=headers).json()] == [closed.id]
    assert [item["id"] for item in client.get("/vinculos/equipes", params={**base, "principal": True}, headers=headers).json()] == [first.id]
    limited = client.get("/vinculos/equipes", params={**base, "limit": 1, "offset": 1}, headers=headers)
    assert limited.status_code == 200
    assert len(limited.json()) == 1
    assert client.get("/vinculos/equipes", headers=headers).status_code == 422


def test_get_update_and_forbidden_fields(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    first_user = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    second_user = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    other_user = persist(client.session_factory, make_usuario(other.id, perfil_base="operador"))
    first_team = persist_equipe(client.session_factory, empresa.id)
    second_team = persist_equipe(client.session_factory, empresa.id)
    third_team = persist_equipe(client.session_factory, empresa.id)
    other_team = persist_equipe(client.session_factory, other.id)
    first = persist_vinculo(client.session_factory, empresa.id, first_user.id, first_team.id, papel="membro")
    leader = persist_vinculo(client.session_factory, empresa.id, second_user.id, second_team.id, papel="lider")
    blocked = persist_vinculo(client.session_factory, empresa.id, first_user.id, second_team.id, papel="membro")
    principal = persist_vinculo(client.session_factory, empresa.id, first_user.id, third_team.id, principal=True)
    other_link = persist_vinculo(client.session_factory, other.id, other_user.id, other_team.id)
    headers = auth_headers(client, admin, empresa)

    get_response = client.get(f"/vinculos/equipes/{first.id}", headers=headers)
    missing = client.get(f"/vinculos/equipes/{uuid4()}", headers=headers)
    other_response = client.get(f"/vinculos/equipes/{other_link.id}", headers=headers)
    update = client.patch(f"/vinculos/equipes/{first.id}", json={"papel": "coordenador"}, headers=headers)
    promote = client.patch(f"/vinculos/equipes/{first.id}", json={"papel": "lider"}, headers=headers)
    second_leader = client.patch(f"/vinculos/equipes/{blocked.id}", json={"papel": "lider"}, headers=headers)
    principal_change = client.patch(f"/vinculos/equipes/{first.id}", json={"principal": True}, headers=headers)
    forbidden = client.patch(f"/vinculos/equipes/{first.id}", json={"equipeId": str(uuid4())}, headers=headers)

    assert get_response.status_code == 200
    assert get_response.json()["id"] == first.id
    assert missing.status_code == 404
    assert other_response.status_code == 404
    assert update.status_code == 200
    assert update.json()["papel"] == "coordenador"
    assert promote.status_code == 200
    assert promote.json()["papel"] == "lider"
    assert second_leader.status_code == 409
    assert leader.id
    assert principal_change.status_code == 200
    assert principal_change.json()["principal"] is True
    assert forbidden.status_code == 422
    with client.session_factory() as db:
        assert db.get(UsuarioEquipe, principal.id).principal is False
        assert db.get(UsuarioEquipe, first.id).principal is True
        assert db.get(type(first_user), first_user.id).perfil_base == "operador"


def test_closed_link_update_close_again_delete_and_reactivation(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    user = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador"))
    team = persist_equipe(client.session_factory, empresa.id)
    link = persist_vinculo(client.session_factory, empresa.id, user.id, team.id, principal=True)
    headers = auth_headers(client, admin, empresa)

    fim_rejected = client.post(f"/vinculos/equipes/{link.id}/encerrar", json={"fimEm": now().isoformat()}, headers=headers)
    status_rejected = client.post(f"/vinculos/equipes/{link.id}/encerrar", json={"status": "encerrado"}, headers=headers)
    actor_rejected = client.post(f"/vinculos/equipes/{link.id}/encerrar", json={"encerradoPorUsuarioId": str(uuid4())}, headers=headers)
    close = client.post(f"/vinculos/equipes/{link.id}/encerrar", json={"motivoEncerramento": "  saida   equipe  "}, headers=headers)
    close_again = client.post(f"/vinculos/equipes/{link.id}/encerrar", json={}, headers=headers)
    update_closed = client.patch(f"/vinculos/equipes/{link.id}", json={"papel": "lider"}, headers=headers)

    assert fim_rejected.status_code == 422
    assert status_rejected.status_code == 422
    assert actor_rejected.status_code == 422
    assert close.status_code == 200
    assert close.json()["status"] == "encerrado"
    assert close.json()["fimEm"]
    assert close.json()["principal"] is False
    assert close.json()["encerradoPorUsuarioId"] == admin.id
    assert close.json()["motivoEncerramento"] == "saida equipe"
    assert close_again.status_code == 409
    assert update_closed.status_code == 409
    assert client.delete(f"/vinculos/equipes/{link.id}", headers=headers).status_code == 405
    assert client.post(f"/vinculos/equipes/{link.id}/reativar", headers=headers).status_code == 404


def test_events_payload_is_restricted_and_fields_are_correct(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    target = persist(client.session_factory, make_usuario(empresa.id, perfil_base="operador", email="sensivel@empresa.com"))
    first_team = persist_equipe(client.session_factory, empresa.id, descricao="Descricao sensivel")
    second_team = persist_equipe(client.session_factory, empresa.id)
    principal = persist_vinculo(client.session_factory, empresa.id, target.id, second_team.id, principal=True)
    headers = auth_headers(client, admin, empresa)
    created = create_vinculo(client, headers, empresa.id, target.id, first_team.id)
    client.patch(f"/vinculos/equipes/{created['id']}", json={"principal": True}, headers=headers)
    client.post(
        f"/vinculos/equipes/{created['id']}/encerrar",
        json={"motivoEncerramento": "motivo completo"},
        headers=headers,
    )

    link_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "usuario_equipe"]
    assert [evento.tipo for evento in link_events] == [
        DomainEventType.USUARIO_EQUIPE_VINCULADO.value,
        DomainEventType.USUARIO_EQUIPE_ALTERADO.value,
        DomainEventType.USUARIO_EQUIPE_ALTERADO.value,
        DomainEventType.USUARIO_EQUIPE_ENCERRADO.value,
    ]
    assert [evento.payload["campos_alterados"] for evento in link_events] == [
        [],
        ["principal"],
        ["principal"],
        ["status", "fim_em", "principal", "encerrado_por_usuario_id"],
    ]
    assert principal.id
    for evento in link_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["empresa_id"] == empresa.id
        assert evento.payload["usuario_id"] == target.id
        assert evento.payload["actor_usuario_id"] == admin.id
        assert "timestamp" in evento.payload
        assert "nome" not in evento.payload
        assert "email" not in evento.payload
        assert "descricao" not in evento.payload
        assert "motivo" not in str(evento.payload)
        assert all(isinstance(field, str) for field in evento.payload["campos_alterados"])


def test_openapi_paths_and_methods(client):
    paths = client.app.openapi()["paths"]
    equipe_paths = {path: sorted(paths[path].keys()) for path in paths if path.startswith("/vinculos/equipes")}

    assert sorted(equipe_paths) == [
        "/vinculos/equipes",
        "/vinculos/equipes/{vinculo_id}",
        "/vinculos/equipes/{vinculo_id}/encerrar",
    ]
    assert equipe_paths["/vinculos/equipes"] == ["get", "post"]
    assert equipe_paths["/vinculos/equipes/{vinculo_id}"] == ["get", "patch"]
    assert equipe_paths["/vinculos/equipes/{vinculo_id}/encerrar"] == ["post"]
    assert "delete" not in equipe_paths["/vinculos/equipes/{vinculo_id}"]
    assert "/vinculos/equipes/{vinculo_id}/reativar" not in paths
    assert paths["/vinculos/equipes"]["post"]["tags"] == ["vinculos-equipes"]
