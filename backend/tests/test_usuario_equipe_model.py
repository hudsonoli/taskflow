from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.equipe import Equipe
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from app.schemas.usuario_equipe import (
    UsuarioEquipeCreate,
    UsuarioEquipeEncerrar,
    UsuarioEquipeResponse,
    UsuarioEquipeUpdate,
)


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)


def now() -> datetime:
    return datetime.now(timezone.utc)


def empresa(**overrides) -> Empresa:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "nome": "Empresa Modelo",
        "documento": uuid4().hex,
        "codigo_interno": f"EMP-{uuid4().hex[:8]}",
        "status": "ativa",
        "created_at": current_time,
        "updated_at": current_time,
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Empresa(**data)


def usuario(empresa_id: str, **overrides) -> Usuario:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"USR-{uuid4().hex[:8]}",
        "nome": "Usuario Modelo",
        "email": f"usuario-{uuid4().hex[:8]}@empresa.com",
        "perfil_base": "operador",
        "acesso_sistema": True,
        "status": "ativo",
        "created_at": current_time,
        "updated_at": current_time,
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Usuario(**data)


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


def persist(session_factory, *objects):
    with session_factory() as db:
        db.add_all(objects)
        db.commit()
        for obj in objects:
            db.refresh(obj)
        return objects[0] if len(objects) == 1 else objects


def persist_equipe(session_factory, empresa_id: str, **overrides) -> Equipe:
    dep = departamento(empresa_id)
    team = equipe(empresa_id, departamento_id=dep.id, **overrides)
    return persist(session_factory, dep, team)[1]


def base_context(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    team = persist_equipe(session_factory, emp.id)
    return emp, user, team


def index_by_name(name: str):
    return next(index for index in UsuarioEquipe.__table__.indexes if index.name == name)


def test_usuario_equipe_persists_required_fields(session_factory):
    emp, user, team = base_context(session_factory)
    created = persist(session_factory, usuario_equipe(emp.id, user.id, team.id, papel="lider", principal=True))

    assert created.id
    assert created.empresa_id == emp.id
    assert created.usuario_id == user.id
    assert created.equipe_id == team.id
    assert created.papel == "lider"
    assert created.principal is True
    assert created.status == "ativo"
    assert created.fim_em is None
    assert UsuarioEquipe.__table__.c.inicio_em.type.timezone is True
    assert UsuarioEquipe.__table__.c.created_at.type.timezone is True
    assert UsuarioEquipe.__table__.c.updated_at.type.timezone is True


def test_model_is_registered_in_base_metadata():
    assert "usuario_equipes" in Base.metadata.tables


def test_expected_columns_exist():
    assert set(UsuarioEquipe.__table__.columns.keys()) == {
        "id",
        "empresa_id",
        "usuario_id",
        "equipe_id",
        "papel",
        "principal",
        "status",
        "inicio_em",
        "fim_em",
        "motivo_encerramento",
        "criado_por_usuario_id",
        "encerrado_por_usuario_id",
        "created_at",
        "updated_at",
    }


def test_expected_indexes_exist_with_sqlite_and_postgresql_partial_constraints():
    index_names = {index.name for index in UsuarioEquipe.__table__.indexes}

    assert {
        "ix_usuario_equipes_empresa_id",
        "ix_usuario_equipes_usuario_id",
        "ix_usuario_equipes_equipe_id",
        "ix_usuario_equipes_papel",
        "ix_usuario_equipes_status",
        "ix_usuario_equipes_created_at",
        "uq_usuario_equipes_ativo_usuario_equipe",
        "uq_usuario_equipes_lider_ativo_equipe",
        "uq_usuario_equipes_principal_ativo_usuario",
    }.issubset(index_names)

    duplicate = index_by_name("uq_usuario_equipes_ativo_usuario_equipe")
    leader = index_by_name("uq_usuario_equipes_lider_ativo_equipe")
    principal = index_by_name("uq_usuario_equipes_principal_ativo_usuario")

    assert duplicate.unique is True
    assert [column.name for column in duplicate.columns] == ["usuario_id", "equipe_id"]
    assert str(duplicate.dialect_options["sqlite"]["where"]) == "status = 'ativo'"
    assert str(duplicate.dialect_options["postgresql"]["where"]) == "status = 'ativo'"

    assert leader.unique is True
    assert [column.name for column in leader.columns] == ["equipe_id"]
    assert str(leader.dialect_options["sqlite"]["where"]) == "status = 'ativo' AND papel = 'lider'"
    assert str(leader.dialect_options["postgresql"]["where"]) == "status = 'ativo' AND papel = 'lider'"

    assert principal.unique is True
    assert [column.name for column in principal.columns] == ["usuario_id"]
    assert str(principal.dialect_options["sqlite"]["where"]) == "status = 'ativo' AND principal = true"
    assert str(principal.dialect_options["postgresql"]["where"]) == "status = 'ativo' AND principal = true"


def test_required_foreign_keys(session_factory):
    emp, user, team = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(None, user.id, team.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, None, team.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, None))


def test_foreign_keys_must_reference_existing_records(session_factory):
    emp, user, team = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(str(uuid4()), user.id, team.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, str(uuid4()), team.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, str(uuid4())))


@pytest.mark.parametrize("papel", ["membro", "lider", "coordenador"])
def test_allowed_papel_values(session_factory, papel):
    emp, user, team = base_context(session_factory)
    created = persist(session_factory, usuario_equipe(emp.id, user.id, team.id, papel=papel))

    assert created.papel == papel


def test_invalid_papel_is_rejected(session_factory):
    emp, user, team = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, team.id, papel="gestor"))


@pytest.mark.parametrize("status", ["ativo", "encerrado"])
def test_allowed_status_values(session_factory, status):
    emp, user, team = base_context(session_factory)
    inicio_em = now()
    fim_em = inicio_em + timedelta(minutes=1) if status == "encerrado" else None
    created = persist(session_factory, usuario_equipe(emp.id, user.id, team.id, status=status, inicio_em=inicio_em, fim_em=fim_em))

    assert created.status == status


def test_inativo_status_is_not_allowed(session_factory):
    emp, user, team = base_context(session_factory)
    inicio_em = now()

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, team.id, status="inativo", inicio_em=inicio_em, fim_em=inicio_em))


def test_invalid_status_is_rejected(session_factory):
    emp, user, team = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, team.id, status="arquivado"))


def test_principal_defaults_false(session_factory):
    emp, user, team = base_context(session_factory)
    current_time = now()
    created = persist(
        session_factory,
        UsuarioEquipe(
            id=str(uuid4()),
            empresa_id=emp.id,
            usuario_id=user.id,
            equipe_id=team.id,
            papel="membro",
            status="ativo",
            inicio_em=current_time,
            created_at=current_time,
            updated_at=current_time,
        ),
    )

    assert created.principal is False


def test_inicio_em_is_required(session_factory):
    emp, user, team = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, team.id, inicio_em=None))


def test_closed_link_requires_fim_em(session_factory):
    emp, user, team = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, team.id, status="encerrado", fim_em=None))


def test_active_link_rejects_fim_em(session_factory):
    emp, user, team = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, team.id, status="ativo", fim_em=now()))


def test_fim_em_before_inicio_em_is_rejected(session_factory):
    emp, user, team = base_context(session_factory)
    inicio_em = now()

    with pytest.raises(IntegrityError):
        persist(
            session_factory,
            usuario_equipe(
                emp.id,
                user.id,
                team.id,
                status="encerrado",
                inicio_em=inicio_em,
                fim_em=inicio_em - timedelta(days=1),
            ),
        )


def test_closed_principal_link_is_rejected(session_factory):
    emp, user, team = base_context(session_factory)
    inicio_em = now()

    with pytest.raises(IntegrityError):
        persist(
            session_factory,
            usuario_equipe(
                emp.id,
                user.id,
                team.id,
                status="encerrado",
                principal=True,
                inicio_em=inicio_em,
                fim_em=inicio_em + timedelta(minutes=1),
            ),
        )


def test_duplicate_active_user_team_link_is_rejected(session_factory):
    emp, user, team = base_context(session_factory)
    persist(session_factory, usuario_equipe(emp.id, user.id, team.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, team.id))


def test_return_to_same_team_allowed_when_previous_link_is_closed(session_factory):
    emp, user, team = base_context(session_factory)
    inicio_em = now()
    closed = persist(
        session_factory,
        usuario_equipe(
            emp.id,
            user.id,
            team.id,
            status="encerrado",
            inicio_em=inicio_em,
            fim_em=inicio_em + timedelta(minutes=1),
        ),
    )
    active = persist(session_factory, usuario_equipe(emp.id, user.id, team.id, status="ativo", fim_em=None))

    assert closed.id != active.id
    assert active.status == "ativo"


def test_only_one_active_principal_team_per_usuario(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    first_team = persist_equipe(session_factory, emp.id)
    second_team = persist_equipe(session_factory, emp.id)
    persist(session_factory, usuario_equipe(emp.id, user.id, first_team.id, principal=True))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, second_team.id, principal=True))


def test_multiple_active_secondary_teams_per_usuario(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    first_team = persist_equipe(session_factory, emp.id)
    second_team = persist_equipe(session_factory, emp.id)
    first = persist(session_factory, usuario_equipe(emp.id, user.id, first_team.id, principal=False))
    second = persist(session_factory, usuario_equipe(emp.id, user.id, second_team.id, principal=False))

    assert first.status == "ativo"
    assert second.status == "ativo"
    assert first.principal is False
    assert second.principal is False


def test_multiple_active_teams_per_usuario_are_allowed(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    first_team = persist_equipe(session_factory, emp.id)
    second_team = persist_equipe(session_factory, emp.id)

    first = persist(session_factory, usuario_equipe(emp.id, user.id, first_team.id))
    second = persist(session_factory, usuario_equipe(emp.id, user.id, second_team.id))

    assert first.usuario_id == user.id
    assert second.usuario_id == user.id


def test_only_one_active_leader_per_team(session_factory):
    emp = persist(session_factory, empresa())
    first_user = persist(session_factory, usuario(emp.id))
    second_user = persist(session_factory, usuario(emp.id))
    team = persist_equipe(session_factory, emp.id)
    persist(session_factory, usuario_equipe(emp.id, first_user.id, team.id, papel="lider"))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, second_user.id, team.id, papel="lider"))


def test_multiple_active_non_leaders_per_team_are_allowed(session_factory):
    emp = persist(session_factory, empresa())
    first_user = persist(session_factory, usuario(emp.id))
    second_user = persist(session_factory, usuario(emp.id))
    third_user = persist(session_factory, usuario(emp.id))
    team = persist_equipe(session_factory, emp.id)

    member = persist(session_factory, usuario_equipe(emp.id, first_user.id, team.id, papel="membro"))
    coordinator = persist(session_factory, usuario_equipe(emp.id, second_user.id, team.id, papel="coordenador"))
    second_member = persist(session_factory, usuario_equipe(emp.id, third_user.id, team.id, papel="membro"))

    assert {member.papel, coordinator.papel, second_member.papel} == {"membro", "coordenador"}


def test_closed_leader_does_not_block_new_active_leader(session_factory):
    emp = persist(session_factory, empresa())
    first_user = persist(session_factory, usuario(emp.id))
    second_user = persist(session_factory, usuario(emp.id))
    team = persist_equipe(session_factory, emp.id)
    inicio_em = now()
    persist(
        session_factory,
        usuario_equipe(
            emp.id,
            first_user.id,
            team.id,
            papel="lider",
            status="encerrado",
            inicio_em=inicio_em,
            fim_em=inicio_em + timedelta(minutes=1),
        ),
    )
    active = persist(session_factory, usuario_equipe(emp.id, second_user.id, team.id, papel="lider"))

    assert active.papel == "lider"
    assert active.status == "ativo"


def test_audit_fields_can_be_null(session_factory):
    emp, user, team = base_context(session_factory)
    created = persist(
        session_factory,
        usuario_equipe(
            emp.id,
            user.id,
            team.id,
            criado_por_usuario_id=None,
            encerrado_por_usuario_id=None,
            motivo_encerramento=None,
        ),
    )

    assert created.criado_por_usuario_id is None
    assert created.encerrado_por_usuario_id is None
    assert created.motivo_encerramento is None


def test_audit_user_foreign_keys(session_factory):
    emp, user, team = base_context(session_factory)
    actor = persist(session_factory, usuario(emp.id))
    created = persist(session_factory, usuario_equipe(emp.id, user.id, team.id, criado_por_usuario_id=actor.id))

    assert created.criado_por_usuario_id == actor.id

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_equipe(emp.id, user.id, team.id, encerrado_por_usuario_id=str(uuid4())))


def test_usuario_equipe_create_schema_aliases_and_serialization():
    payload = {
        "empresaId": str(uuid4()),
        "usuarioId": str(uuid4()),
        "equipeId": str(uuid4()),
        "papel": "membro",
        "principal": True,
    }
    data = UsuarioEquipeCreate(**payload)

    assert str(data.empresa_id) == payload["empresaId"]
    assert str(data.usuario_id) == payload["usuarioId"]
    assert str(data.equipe_id) == payload["equipeId"]
    assert str(data.model_dump(by_alias=True)["equipeId"]) == payload["equipeId"]


def test_usuario_equipe_create_rejects_service_managed_fields():
    payload = {
        "empresaId": str(uuid4()),
        "usuarioId": str(uuid4()),
        "equipeId": str(uuid4()),
        "papel": "membro",
        "principal": False,
    }

    for field, value in [
        ("status", "ativo"),
        ("inicioEm", now()),
        ("fimEm", now()),
        ("motivoEncerramento", "teste"),
        ("criadoPorUsuarioId", str(uuid4())),
        ("encerradoPorUsuarioId", str(uuid4())),
        ("createdAt", now()),
        ("updatedAt", now()),
    ]:
        with pytest.raises(ValidationError):
            UsuarioEquipeCreate(**payload, **{field: value})


def test_usuario_equipe_update_rejects_forbidden_fields():
    for field, value in [
        ("empresaId", str(uuid4())),
        ("usuarioId", str(uuid4())),
        ("equipeId", str(uuid4())),
        ("status", "ativo"),
        ("inicioEm", now()),
        ("fimEm", now()),
        ("motivoEncerramento", "teste"),
        ("criadoPorUsuarioId", str(uuid4())),
        ("encerradoPorUsuarioId", str(uuid4())),
        ("createdAt", now()),
        ("updatedAt", now()),
    ]:
        with pytest.raises(ValidationError):
            UsuarioEquipeUpdate(**{field: value})


def test_usuario_equipe_encerrar_accepts_only_motivo():
    payload = {"motivoEncerramento": "saida"}
    encerramento = UsuarioEquipeEncerrar(**payload)

    assert encerramento.motivo_encerramento == "saida"

    for field, value in [
        ("fimEm", now()),
        ("actorUsuarioId", str(uuid4())),
        ("status", "encerrado"),
    ]:
        with pytest.raises(ValidationError):
            UsuarioEquipeEncerrar(**payload, **{field: value})


def test_usuario_equipe_response_serializes_aliases_and_timezone():
    current_time = now()
    response = UsuarioEquipeResponse(
        id=str(uuid4()),
        empresaId=str(uuid4()),
        usuarioId=str(uuid4()),
        equipeId=str(uuid4()),
        papel="coordenador",
        principal=False,
        status="ativo",
        inicioEm=current_time.replace(tzinfo=None),
        fimEm=None,
        motivoEncerramento=None,
        criadoPorUsuarioId=None,
        encerradoPorUsuarioId=None,
        createdAt=current_time,
        updatedAt=current_time,
    )
    serialized = response.model_dump(by_alias=True)

    assert serialized["equipeId"] == response.equipe_id
    assert response.inicio_em.tzinfo is not None
    assert response.created_at.tzinfo is not None
