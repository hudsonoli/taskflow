from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.models.equipe import Equipe
from app.models.usuario_equipe import UsuarioEquipe
from app.repositories.usuario_equipe_repository import UsuarioEquipeRepository
from app.schemas.usuario_equipe import UsuarioEquipeCreate, UsuarioEquipeEncerrar, UsuarioEquipeUpdate
from app.services.usuario_equipe_service import (
    UsuarioEquipeConflictError,
    UsuarioEquipeInvalidDataError,
    UsuarioEquipeInvalidTransitionError,
    UsuarioEquipeService,
)
from conftest import create_auth_context, eventos, make_empresa, make_usuario, persist


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


def payload(empresa_id: str, usuario_id: str, equipe_id: str, **overrides) -> dict:
    data = {
        "empresaId": empresa_id,
        "usuarioId": usuario_id,
        "equipeId": equipe_id,
        "papel": "membro",
        "principal": False,
    }
    data.update(overrides)
    return data


def vinculos(session_factory) -> list[UsuarioEquipe]:
    with session_factory() as db:
        return list(db.scalars(select(UsuarioEquipe).order_by(UsuarioEquipe.created_at, UsuarioEquipe.id)).all())


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_repository_create_get_list_filters_and_active_queries(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    other = persist(session_factory, make_empresa(codigo_interno="OUTRA"))
    user = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    other_user = persist(session_factory, make_usuario(other.id, perfil_base="operador"))
    first_team = persist_equipe(session_factory, empresa.id)
    second_team = persist_equipe(session_factory, empresa.id)
    other_team = persist_equipe(session_factory, other.id)
    repository = UsuarioEquipeRepository()
    inicio_em = now()

    with session_factory() as db:
        created = repository.create(
            db,
            usuario_equipe(empresa.id, user.id, first_team.id, papel="lider", principal=True, criado_por_usuario_id=actor.id),
        )
        db.commit()
        created_id = created.id

    closed = persist_vinculo(
        session_factory,
        empresa.id,
        user.id,
        second_team.id,
        status="encerrado",
        inicio_em=inicio_em,
        fim_em=inicio_em + timedelta(minutes=1),
    )
    other_link = persist_vinculo(session_factory, other.id, other_user.id, other_team.id)

    with session_factory() as db:
        assert repository.get_by_id(db, created_id).id == created_id
        assert [item.id for item in repository.list_by_empresa(db, empresa_id=empresa.id)] == [closed.id, created_id]
        assert [item.id for item in repository.list_by_empresa(db, empresa_id=empresa.id, usuario_id=user.id)] == [closed.id, created_id]
        assert [item.id for item in repository.list_by_empresa(db, empresa_id=empresa.id, equipe_id=first_team.id)] == [created_id]
        assert [item.id for item in repository.list_by_empresa(db, empresa_id=empresa.id, papel="lider")] == [created_id]
        assert [item.id for item in repository.list_by_empresa(db, empresa_id=empresa.id, status="encerrado")] == [closed.id]
        assert [item.id for item in repository.list_by_empresa(db, empresa_id=empresa.id, principal=True)] == [created_id]
        assert [item.id for item in repository.list_by_usuario(db, empresa_id=empresa.id, usuario_id=user.id)] == [closed.id, created_id]
        assert [item.id for item in repository.list_by_equipe(db, empresa_id=empresa.id, equipe_id=first_team.id)] == [created_id]
        assert repository.get_active_by_usuario_equipe(db, empresa_id=empresa.id, usuario_id=user.id, equipe_id=first_team.id).id == created_id
        assert repository.get_active_lider_by_equipe(db, empresa_id=empresa.id, equipe_id=first_team.id).id == created_id
        assert repository.get_active_principal_by_usuario(db, empresa_id=empresa.id, usuario_id=user.id).id == created_id
        assert repository.get_by_id(db, other_link.id).empresa_id == other.id
        assert repository.list_by_empresa(db, empresa_id=empresa.id, equipe_id=other_team.id) == []

        link = repository.get_by_id(db, created_id)
        link.status = "encerrado"
        link.principal = False
        link.fim_em = now()
        returned = repository.encerrar(db, link)
        assert returned is link
        assert returned.status == "encerrado"


@pytest.mark.parametrize("papel", ["membro", "lider", "coordenador"])
def test_service_creates_link_for_allowed_roles(session_factory, papel):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    team = persist_equipe(session_factory, empresa.id)

    with session_factory() as db:
        created = UsuarioEquipeService().vincular_usuario_equipe(
            db,
            UsuarioEquipeCreate(**payload(empresa.id, target.id, team.id, papel=papel)),
            actor_usuario_id=actor.id,
        )

    assert created.papel == papel
    assert created.status == "ativo"
    assert created.inicio_em is not None
    assert created.fim_em is None
    assert created.criado_por_usuario_id == actor.id


def test_service_allows_multiple_active_teams_and_secondary_links(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_team = persist_equipe(session_factory, empresa.id)
    second_team = persist_equipe(session_factory, empresa.id)
    third_team = persist_equipe(session_factory, empresa.id)
    service = UsuarioEquipeService()

    with session_factory() as db:
        first = service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**payload(empresa.id, target.id, first_team.id)), actor_usuario_id=actor.id)
    with session_factory() as db:
        second = service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**payload(empresa.id, target.id, second_team.id)), actor_usuario_id=actor.id)
    with session_factory() as db:
        third = service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**payload(empresa.id, target.id, third_team.id)), actor_usuario_id=actor.id)

    assert [first.principal, second.principal, third.principal] == [False, False, False]
    assert [item.status for item in vinculos(session_factory)] == ["ativo", "ativo", "ativo"]


def test_creation_validates_entities_and_tenant(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    inactive_empresa = persist(session_factory, make_empresa(status="inativa", codigo_interno="INATIVA"))
    other = persist(session_factory, make_empresa(codigo_interno="OUTRA"))
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    inactive_user = persist(session_factory, make_usuario(empresa.id, status="inativo"))
    other_user = persist(session_factory, make_usuario(other.id, perfil_base="operador"))
    team = persist_equipe(session_factory, empresa.id)
    inactive_team = persist_equipe(session_factory, empresa.id, status="inativa")
    other_team = persist_equipe(session_factory, other.id)
    service = UsuarioEquipeService()

    invalid_payloads = [
        payload(str(uuid4()), target.id, team.id),
        payload(inactive_empresa.id, target.id, team.id),
        payload(empresa.id, str(uuid4()), team.id),
        payload(empresa.id, inactive_user.id, team.id),
        payload(empresa.id, other_user.id, team.id),
        payload(empresa.id, target.id, str(uuid4())),
        payload(empresa.id, target.id, inactive_team.id),
        payload(empresa.id, target.id, other_team.id),
    ]

    for invalid in invalid_payloads:
        with pytest.raises(UsuarioEquipeInvalidDataError):
            with session_factory() as db:
                service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**invalid), actor_usuario_id=actor.id)


def test_duplicate_active_link_is_rejected_and_closed_link_allows_return(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    team = persist_equipe(session_factory, empresa.id)
    service = UsuarioEquipeService()

    with session_factory() as db:
        first = service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**payload(empresa.id, target.id, team.id)), actor_usuario_id=actor.id)
    with pytest.raises(UsuarioEquipeConflictError):
        with session_factory() as db:
            service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**payload(empresa.id, target.id, team.id)), actor_usuario_id=actor.id)

    with session_factory() as db:
        service.encerrar_vinculo(db, first.id, UsuarioEquipeEncerrar(motivoEncerramento="saida"), actor_usuario_id=actor.id)
    with session_factory() as db:
        second = service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**payload(empresa.id, target.id, team.id)), actor_usuario_id=actor.id)

    assert second.id != first.id
    assert second.status == "ativo"


def test_single_leader_per_team_and_same_user_can_lead_different_teams(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    first_user = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    second_user = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_team = persist_equipe(session_factory, empresa.id)
    second_team = persist_equipe(session_factory, empresa.id)
    service = UsuarioEquipeService()

    with session_factory() as db:
        service.vincular_usuario_equipe(
            db,
            UsuarioEquipeCreate(**payload(empresa.id, first_user.id, first_team.id, papel="lider")),
            actor_usuario_id=actor.id,
        )
    with pytest.raises(UsuarioEquipeConflictError):
        with session_factory() as db:
            service.vincular_usuario_equipe(
                db,
                UsuarioEquipeCreate(**payload(empresa.id, second_user.id, first_team.id, papel="lider")),
                actor_usuario_id=actor.id,
            )
    with session_factory() as db:
        second_lead = service.vincular_usuario_equipe(
            db,
            UsuarioEquipeCreate(**payload(empresa.id, first_user.id, second_team.id, papel="lider")),
            actor_usuario_id=actor.id,
        )

    assert second_lead.papel == "lider"


def test_single_principal_and_principal_change_is_transactional(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_team = persist_equipe(session_factory, empresa.id)
    second_team = persist_equipe(session_factory, empresa.id)
    service = UsuarioEquipeService()

    with session_factory() as db:
        first = service.vincular_usuario_equipe(
            db,
            UsuarioEquipeCreate(**payload(empresa.id, target.id, first_team.id, principal=True)),
            actor_usuario_id=actor.id,
        )
    with session_factory() as db:
        second = service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**payload(empresa.id, target.id, second_team.id)), actor_usuario_id=actor.id)
    with session_factory() as db:
        changed = service.alterar_vinculo(db, second.id, UsuarioEquipeUpdate(principal=True), actor_usuario_id=actor.id)

    assert changed.principal is True
    with session_factory() as db:
        assert db.get(UsuarioEquipe, first.id).principal is False
        assert db.get(UsuarioEquipe, second.id).principal is True

    changed_events = [evento for evento in eventos(session_factory) if evento.tipo == DomainEventType.USUARIO_EQUIPE_ALTERADO.value]
    assert [evento.payload["campos_alterados"] for evento in changed_events] == [["principal"], ["principal"]]


def test_update_changes_role_promotes_to_leader_and_preserves_user_profile(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    other_user = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_team = persist_equipe(session_factory, empresa.id)
    second_team = persist_equipe(session_factory, empresa.id)
    service = UsuarioEquipeService()
    active = persist_vinculo(session_factory, empresa.id, target.id, first_team.id, papel="membro")
    existing_leader = persist_vinculo(session_factory, empresa.id, other_user.id, second_team.id, papel="lider")
    blocked = persist_vinculo(session_factory, empresa.id, target.id, second_team.id, papel="membro")

    with session_factory() as db:
        updated = service.alterar_vinculo(db, active.id, UsuarioEquipeUpdate(papel="coordenador"), actor_usuario_id=actor.id)
    with session_factory() as db:
        promoted = service.alterar_vinculo(db, active.id, UsuarioEquipeUpdate(papel="lider"), actor_usuario_id=actor.id)
    with pytest.raises(UsuarioEquipeConflictError):
        with session_factory() as db:
            service.alterar_vinculo(db, blocked.id, UsuarioEquipeUpdate(papel="lider"), actor_usuario_id=actor.id)

    assert updated.papel == "coordenador"
    assert promoted.papel == "lider"
    with session_factory() as db:
        assert db.get(UsuarioEquipe, existing_leader.id).papel == "lider"
        assert db.get(UsuarioEquipe, blocked.id).papel == "membro"
        assert db.get(type(target), target.id).perfil_base == "operador"


def test_closed_link_cannot_be_updated_or_closed_again(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    team = persist_equipe(session_factory, empresa.id)
    closed = persist_vinculo(
        session_factory,
        empresa.id,
        target.id,
        team.id,
        status="encerrado",
        fim_em=now() + timedelta(minutes=1),
    )
    service = UsuarioEquipeService()

    with pytest.raises(UsuarioEquipeInvalidTransitionError):
        with session_factory() as db:
            service.alterar_vinculo(db, closed.id, UsuarioEquipeUpdate(papel="lider"), actor_usuario_id=actor.id)
    with pytest.raises(UsuarioEquipeInvalidTransitionError):
        with session_factory() as db:
            service.encerrar_vinculo(db, closed.id, UsuarioEquipeEncerrar(), actor_usuario_id=actor.id)


def test_close_active_link_sets_status_dates_actor_and_principal_false(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    team = persist_equipe(session_factory, empresa.id)
    link = persist_vinculo(session_factory, empresa.id, target.id, team.id, principal=True)
    service = UsuarioEquipeService()

    with session_factory() as db:
        closed = service.encerrar_vinculo(
            db,
            link.id,
            UsuarioEquipeEncerrar(motivoEncerramento="  saida   equipe  "),
            actor_usuario_id=actor.id,
        )

    assert closed.status == "encerrado"
    assert closed.fim_em is not None
    assert closed.fim_em >= closed.inicio_em
    assert closed.principal is False
    assert closed.encerrado_por_usuario_id == actor.id
    assert closed.motivo_encerramento == "saida equipe"


def test_listar_vinculos_validates_filters_and_does_not_leak_other_tenant(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    other = persist(session_factory, make_empresa(codigo_interno="OUTRA"))
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    other_user = persist(session_factory, make_usuario(other.id, perfil_base="operador"))
    team = persist_equipe(session_factory, empresa.id)
    second_team = persist_equipe(session_factory, empresa.id)
    other_team = persist_equipe(session_factory, other.id)
    own = persist_vinculo(session_factory, empresa.id, target.id, team.id, papel="lider", principal=True)
    persist_vinculo(session_factory, empresa.id, target.id, second_team.id, papel="membro")
    persist_vinculo(session_factory, other.id, other_user.id, other_team.id)
    service = UsuarioEquipeService()

    with session_factory() as db:
        by_empresa = service.listar_vinculos(db, empresa_id=empresa.id)
        by_user = service.listar_vinculos(db, empresa_id=empresa.id, usuario_id=target.id)
        by_team = service.listar_vinculos(db, empresa_id=empresa.id, equipe_id=team.id)
        leaders = service.listar_vinculos(db, empresa_id=empresa.id, papel="lider")
        principals = service.listar_vinculos(db, empresa_id=empresa.id, principal=True)

    assert {item.empresa_id for item in by_empresa} == {empresa.id}
    assert {item.id for item in by_user} == {item.id for item in by_empresa}
    assert [item.id for item in by_team] == [own.id]
    assert [item.id for item in leaders] == [own.id]
    assert [item.id for item in principals] == [own.id]

    for invalid_kwargs in [
        {"empresa_id": str(uuid4())},
        {"empresa_id": empresa.id, "usuario_id": other_user.id},
        {"empresa_id": empresa.id, "equipe_id": other_team.id},
    ]:
        with pytest.raises(UsuarioEquipeInvalidDataError):
            with session_factory() as db:
                service.listar_vinculos(db, **invalid_kwargs)


def test_events_payload_is_restricted(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador", email="sensivel@empresa.com"))
    team = persist_equipe(session_factory, empresa.id, descricao="Descricao sensivel")
    service = UsuarioEquipeService()

    with session_factory() as db:
        created = service.vincular_usuario_equipe(db, UsuarioEquipeCreate(**payload(empresa.id, target.id, team.id)), actor_usuario_id=actor.id)
    with session_factory() as db:
        service.alterar_vinculo(db, created.id, UsuarioEquipeUpdate(papel="coordenador"), actor_usuario_id=actor.id)
    with session_factory() as db:
        service.encerrar_vinculo(db, created.id, UsuarioEquipeEncerrar(motivoEncerramento="motivo completo"), actor_usuario_id=actor.id)

    link_events = [evento for evento in eventos(session_factory) if evento.entidade_tipo == "usuario_equipe"]
    assert [evento.tipo for evento in link_events] == [
        DomainEventType.USUARIO_EQUIPE_VINCULADO.value,
        DomainEventType.USUARIO_EQUIPE_ALTERADO.value,
        DomainEventType.USUARIO_EQUIPE_ENCERRADO.value,
    ]
    assert [evento.payload["campos_alterados"] for evento in link_events] == [
        [],
        ["papel"],
        ["status", "fim_em", "principal", "encerrado_por_usuario_id"],
    ]
    for evento in link_events:
        assert evento.usuario_id == actor.id
        assert evento.payload["empresa_id"] == empresa.id
        assert evento.payload["usuario_id"] == target.id
        assert evento.payload["equipe_id"] == team.id
        assert evento.payload["actor_usuario_id"] == actor.id
        assert "timestamp" in evento.payload
        assert "nome" not in evento.payload
        assert "email" not in evento.payload
        assert "descricao" not in evento.payload
        assert "motivo" not in str(evento.payload)
        assert all(isinstance(field, str) for field in evento.payload["campos_alterados"])


def test_rollbacks_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    first_team = persist_equipe(session_factory, empresa.id)
    second_team = persist_equipe(session_factory, empresa.id)
    service = UsuarioEquipeService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.vincular_usuario_equipe(
                db,
                UsuarioEquipeCreate(**payload(empresa.id, target.id, first_team.id)),
                actor_usuario_id=actor.id,
            )
    assert vinculos(session_factory) == []

    active = persist_vinculo(session_factory, empresa.id, target.id, first_team.id, papel="membro")
    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.alterar_vinculo(db, active.id, UsuarioEquipeUpdate(papel="coordenador"), actor_usuario_id=actor.id)
    with session_factory() as db:
        assert db.get(UsuarioEquipe, active.id).papel == "membro"

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.encerrar_vinculo(db, active.id, UsuarioEquipeEncerrar(motivoEncerramento="saida"), actor_usuario_id=actor.id)
    with session_factory() as db:
        assert db.get(UsuarioEquipe, active.id).status == "ativo"

    principal = persist_vinculo(session_factory, empresa.id, target.id, second_team.id, principal=True)
    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.alterar_vinculo(db, active.id, UsuarioEquipeUpdate(principal=True), actor_usuario_id=actor.id)
    with session_factory() as db:
        assert db.get(UsuarioEquipe, principal.id).principal is True
        assert db.get(UsuarioEquipe, active.id).principal is False


def test_to_response_maps_fields(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    target = persist(session_factory, make_usuario(empresa.id, perfil_base="operador"))
    team = persist_equipe(session_factory, empresa.id)
    link = persist_vinculo(session_factory, empresa.id, target.id, team.id, criado_por_usuario_id=actor.id)

    response = UsuarioEquipeService().to_response(link)

    assert str(response.id) == link.id
    assert str(response.empresa_id) == empresa.id
    assert str(response.usuario_id) == target.id
    assert str(response.equipe_id) == team.id
    assert response.papel == "membro"
