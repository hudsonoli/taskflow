from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.cargo import Cargo
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_cargo import UsuarioCargo
from app.schemas.usuario_cargo import UsuarioCargoCreate, UsuarioCargoEncerrar, UsuarioCargoUpdate


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


def persist(session_factory, *objects):
    with session_factory() as db:
        db.add_all(objects)
        db.commit()
        for obj in objects:
            db.refresh(obj)
        return objects[0] if len(objects) == 1 else objects


def base_context(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    role = persist(session_factory, cargo(emp.id))
    return emp, user, role


def test_usuario_cargo_persists_required_fields(session_factory):
    emp, user, role = base_context(session_factory)
    created = persist(session_factory, usuario_cargo(emp.id, user.id, role.id, principal=True))

    assert created.id
    assert created.empresa_id == emp.id
    assert created.usuario_id == user.id
    assert created.cargo_id == role.id
    assert created.principal is True
    assert created.status == "ativo"
    assert created.fim_em is None
    assert UsuarioCargo.__table__.c.inicio_em.type.timezone is True
    assert UsuarioCargo.__table__.c.created_at.type.timezone is True
    assert UsuarioCargo.__table__.c.updated_at.type.timezone is True


def test_model_is_registered_in_base_metadata():
    assert "usuario_cargos" in Base.metadata.tables


def test_expected_columns_exist():
    assert set(UsuarioCargo.__table__.columns.keys()) == {
        "id",
        "empresa_id",
        "usuario_id",
        "cargo_id",
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


def test_required_foreign_keys(session_factory):
    emp, user, role = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(None, user.id, role.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, None, role.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, None))


def test_foreign_keys_must_reference_existing_records(session_factory):
    emp, user, role = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(str(uuid4()), user.id, role.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, str(uuid4()), role.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, str(uuid4())))


@pytest.mark.parametrize("status", ["ativo", "inativo"])
def test_allowed_status_values(session_factory, status):
    emp, user, role = base_context(session_factory)
    inicio_em = now()
    fim_em = inicio_em + timedelta(minutes=1) if status == "inativo" else None
    created = persist(session_factory, usuario_cargo(emp.id, user.id, role.id, status=status, inicio_em=inicio_em, fim_em=fim_em))

    assert created.status == status


def test_invalid_status_is_rejected(session_factory):
    emp, user, role = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, role.id, status="arquivado"))


def test_principal_defaults_false(session_factory):
    emp, user, role = base_context(session_factory)
    current_time = now()
    created = persist(
        session_factory,
        UsuarioCargo(
            id=str(uuid4()),
            empresa_id=emp.id,
            usuario_id=user.id,
            cargo_id=role.id,
            status="ativo",
            inicio_em=current_time,
            created_at=current_time,
            updated_at=current_time,
        ),
    )

    assert created.principal is False


def test_inicio_em_is_required(session_factory):
    emp, user, role = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, role.id, inicio_em=None))


def test_inactive_link_requires_fim_em(session_factory):
    emp, user, role = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, role.id, status="inativo", fim_em=None))


def test_active_link_rejects_fim_em(session_factory):
    emp, user, role = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, role.id, status="ativo", fim_em=now()))


def test_fim_em_before_inicio_em_is_rejected(session_factory):
    emp, user, role = base_context(session_factory)
    inicio_em = now()

    with pytest.raises(IntegrityError):
        persist(
            session_factory,
            usuario_cargo(
                emp.id,
                user.id,
                role.id,
                status="inativo",
                inicio_em=inicio_em,
                fim_em=inicio_em - timedelta(days=1),
            ),
        )


def test_inactive_principal_link_is_rejected(session_factory):
    emp, user, role = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, role.id, status="inativo", principal=True, fim_em=now()))


def test_duplicate_active_user_cargo_link_is_rejected(session_factory):
    emp, user, role = base_context(session_factory)
    persist(session_factory, usuario_cargo(emp.id, user.id, role.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, role.id))


def test_new_link_allowed_when_previous_link_is_inactive(session_factory):
    emp, user, role = base_context(session_factory)
    inicio_em = now()
    persist(
        session_factory,
        usuario_cargo(
            emp.id,
            user.id,
            role.id,
            status="inativo",
            inicio_em=inicio_em,
            fim_em=inicio_em + timedelta(minutes=1),
        ),
    )
    active = persist(session_factory, usuario_cargo(emp.id, user.id, role.id, status="ativo", fim_em=None))

    assert active.status == "ativo"


def test_only_one_active_principal_cargo_per_usuario(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    first_role = persist(session_factory, cargo(emp.id))
    second_role = persist(session_factory, cargo(emp.id))
    persist(session_factory, usuario_cargo(emp.id, user.id, first_role.id, principal=True))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, second_role.id, principal=True))


def test_multiple_active_secondary_cargos_per_usuario(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    first_role = persist(session_factory, cargo(emp.id))
    second_role = persist(session_factory, cargo(emp.id))
    first = persist(session_factory, usuario_cargo(emp.id, user.id, first_role.id, principal=False))
    second = persist(session_factory, usuario_cargo(emp.id, user.id, second_role.id, principal=False))

    assert first.principal is False
    assert second.principal is False


def test_multiple_users_can_have_same_active_cargo(session_factory):
    emp = persist(session_factory, empresa())
    first_user = persist(session_factory, usuario(emp.id))
    second_user = persist(session_factory, usuario(emp.id))
    role = persist(session_factory, cargo(emp.id))
    first = persist(session_factory, usuario_cargo(emp.id, first_user.id, role.id))
    second = persist(session_factory, usuario_cargo(emp.id, second_user.id, role.id))

    assert first.cargo_id == role.id
    assert second.cargo_id == role.id


def test_audit_fields_can_be_null(session_factory):
    emp, user, role = base_context(session_factory)
    created = persist(
        session_factory,
        usuario_cargo(
            emp.id,
            user.id,
            role.id,
            criado_por_usuario_id=None,
            encerrado_por_usuario_id=None,
            motivo_encerramento=None,
        ),
    )

    assert created.criado_por_usuario_id is None
    assert created.encerrado_por_usuario_id is None
    assert created.motivo_encerramento is None


def test_audit_user_foreign_keys(session_factory):
    emp, user, role = base_context(session_factory)
    actor = persist(session_factory, usuario(emp.id))
    created = persist(session_factory, usuario_cargo(emp.id, user.id, role.id, criado_por_usuario_id=actor.id))

    assert created.criado_por_usuario_id == actor.id

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_cargo(emp.id, user.id, role.id, encerrado_por_usuario_id=str(uuid4())))


def test_usuario_cargo_create_rejects_service_managed_fields():
    payload = {
        "empresaId": str(uuid4()),
        "usuarioId": str(uuid4()),
        "cargoId": str(uuid4()),
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
            UsuarioCargoCreate(**payload, **{field: value})


def test_usuario_cargo_update_rejects_forbidden_fields():
    for field, value in [
        ("empresaId", str(uuid4())),
        ("usuarioId", str(uuid4())),
        ("cargoId", str(uuid4())),
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
            UsuarioCargoUpdate(**{field: value})


def test_usuario_cargo_encerrar_accepts_only_motivo():
    payload = {"motivoEncerramento": "saida"}
    encerramento = UsuarioCargoEncerrar(**payload)

    assert encerramento.motivo_encerramento == "saida"

    for field, value in [
        ("fimEm", now()),
        ("actorUsuarioId", str(uuid4())),
        ("status", "inativo"),
    ]:
        with pytest.raises(ValidationError):
            UsuarioCargoEncerrar(**payload, **{field: value})
