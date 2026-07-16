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
from app.models.usuario import Usuario
from app.models.usuario_departamento import UsuarioDepartamento
from app.schemas.usuario_departamento import UsuarioDepartamentoCreate, UsuarioDepartamentoUpdate


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
    data = {
        "id": str(uuid4()),
        "nome": "Empresa Modelo",
        "documento": uuid4().hex,
        "codigo_interno": f"EMP-{uuid4().hex[:8]}",
        "status": "ativa",
        "created_at": now(),
        "updated_at": now(),
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Empresa(**data)


def usuario(empresa_id: str, **overrides) -> Usuario:
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"USR-{uuid4().hex[:8]}",
        "nome": "Usuario Modelo",
        "email": f"usuario-{uuid4().hex[:8]}@empresa.com",
        "perfil_base": "operador",
        "acesso_sistema": True,
        "status": "ativo",
        "created_at": now(),
        "updated_at": now(),
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Usuario(**data)


def departamento(empresa_id: str, **overrides) -> Departamento:
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"DEP-{uuid4().hex[:8]}",
        "nome": f"Departamento {uuid4().hex[:8]}",
        "descricao": "Departamento de teste",
        "status": "ativa",
        "created_at": now(),
        "updated_at": now(),
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Departamento(**data)


def usuario_departamento(
    empresa_id: str,
    usuario_id: str,
    departamento_id: str,
    **overrides,
) -> UsuarioDepartamento:
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
    dept = persist(session_factory, departamento(emp.id))
    return emp, user, dept


def test_usuario_departamento_persists_required_fields(session_factory):
    emp, user, dept = base_context(session_factory)
    created = persist(
        session_factory,
        usuario_departamento(emp.id, user.id, dept.id, papel="gestor", principal=True),
    )

    assert created.id
    assert created.empresa_id == emp.id
    assert created.usuario_id == user.id
    assert created.departamento_id == dept.id
    assert created.papel == "gestor"
    assert created.principal is True
    assert created.status == "ativo"
    assert created.fim_em is None
    assert UsuarioDepartamento.__table__.c.inicio_em.type.timezone is True
    assert UsuarioDepartamento.__table__.c.created_at.type.timezone is True
    assert UsuarioDepartamento.__table__.c.updated_at.type.timezone is True


def test_model_is_registered_in_base_metadata():
    assert "usuario_departamentos" in Base.metadata.tables


def test_required_foreign_keys(session_factory):
    emp, user, dept = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(None, user.id, dept.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, None, dept.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, None))


def test_foreign_keys_must_reference_existing_records(session_factory):
    emp, user, dept = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(str(uuid4()), user.id, dept.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, str(uuid4()), dept.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, str(uuid4())))


@pytest.mark.parametrize("papel", ["membro", "gestor", "head"])
def test_allowed_papel_values(session_factory, papel):
    emp, user, dept = base_context(session_factory)
    created = persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, papel=papel))

    assert created.papel == papel


def test_invalid_papel_is_rejected(session_factory):
    emp, user, dept = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, papel="temporario"))


@pytest.mark.parametrize("status", ["ativo", "inativo"])
def test_allowed_status_values(session_factory, status):
    emp, user, dept = base_context(session_factory)
    inicio_em = now()
    fim_em = inicio_em + timedelta(minutes=1) if status == "inativo" else None
    created = persist(
        session_factory,
        usuario_departamento(emp.id, user.id, dept.id, status=status, inicio_em=inicio_em, fim_em=fim_em),
    )

    assert created.status == status


def test_invalid_status_is_rejected(session_factory):
    emp, user, dept = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, status="arquivado"))


def test_principal_defaults_false(session_factory):
    emp, user, dept = base_context(session_factory)
    current_time = now()
    created = persist(
        session_factory,
        UsuarioDepartamento(
            id=str(uuid4()),
            empresa_id=emp.id,
            usuario_id=user.id,
            departamento_id=dept.id,
            papel="membro",
            status="ativo",
            inicio_em=current_time,
            created_at=current_time,
            updated_at=current_time,
        ),
    )

    assert created.principal is False


def test_inicio_em_is_required(session_factory):
    emp, user, dept = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, inicio_em=None))


def test_fim_em_nullable_for_active_link(session_factory):
    emp, user, dept = base_context(session_factory)
    created = persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, status="ativo", fim_em=None))

    assert created.fim_em is None


def test_inactive_link_requires_fim_em(session_factory):
    emp, user, dept = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, status="inativo", fim_em=None))


def test_active_link_rejects_fim_em(session_factory):
    emp, user, dept = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, status="ativo", fim_em=now()))


def test_fim_em_before_inicio_em_is_rejected(session_factory):
    emp, user, dept = base_context(session_factory)
    inicio_em = now()

    with pytest.raises(IntegrityError):
        persist(
            session_factory,
            usuario_departamento(
                emp.id,
                user.id,
                dept.id,
                status="inativo",
                inicio_em=inicio_em,
                fim_em=inicio_em - timedelta(days=1),
            ),
        )


def test_inactive_principal_link_is_rejected(session_factory):
    emp, user, dept = base_context(session_factory)

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, status="inativo", principal=True, fim_em=now()))


def test_duplicate_active_user_department_link_is_rejected(session_factory):
    emp, user, dept = base_context(session_factory)
    persist(session_factory, usuario_departamento(emp.id, user.id, dept.id))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, dept.id))


def test_new_link_allowed_when_previous_link_is_inactive(session_factory):
    emp, user, dept = base_context(session_factory)
    inicio_em = now()
    persist(
        session_factory,
        usuario_departamento(
            emp.id,
            user.id,
            dept.id,
            status="inativo",
            inicio_em=inicio_em,
            fim_em=inicio_em + timedelta(minutes=1),
        ),
    )
    active = persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, status="ativo", fim_em=None))

    assert active.status == "ativo"


def test_only_one_active_head_per_departamento(session_factory):
    emp = persist(session_factory, empresa())
    first_user = persist(session_factory, usuario(emp.id))
    second_user = persist(session_factory, usuario(emp.id))
    dept = persist(session_factory, departamento(emp.id))
    persist(session_factory, usuario_departamento(emp.id, first_user.id, dept.id, papel="head"))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, second_user.id, dept.id, papel="head"))


def test_multiple_active_gestores_in_same_departamento(session_factory):
    emp = persist(session_factory, empresa())
    first_user = persist(session_factory, usuario(emp.id))
    second_user = persist(session_factory, usuario(emp.id))
    dept = persist(session_factory, departamento(emp.id))
    first = persist(session_factory, usuario_departamento(emp.id, first_user.id, dept.id, papel="gestor"))
    second = persist(session_factory, usuario_departamento(emp.id, second_user.id, dept.id, papel="gestor"))

    assert first.papel == "gestor"
    assert second.papel == "gestor"


def test_only_one_active_principal_departamento_per_usuario(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    first_dept = persist(session_factory, departamento(emp.id))
    second_dept = persist(session_factory, departamento(emp.id))
    persist(session_factory, usuario_departamento(emp.id, user.id, first_dept.id, principal=True))

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, second_dept.id, principal=True))


def test_multiple_active_secondary_departamentos_per_usuario(session_factory):
    emp = persist(session_factory, empresa())
    user = persist(session_factory, usuario(emp.id))
    first_dept = persist(session_factory, departamento(emp.id))
    second_dept = persist(session_factory, departamento(emp.id))
    first = persist(session_factory, usuario_departamento(emp.id, user.id, first_dept.id, principal=False))
    second = persist(session_factory, usuario_departamento(emp.id, user.id, second_dept.id, principal=False))

    assert first.principal is False
    assert second.principal is False


def test_audit_fields_can_be_null(session_factory):
    emp, user, dept = base_context(session_factory)
    created = persist(
        session_factory,
        usuario_departamento(
            emp.id,
            user.id,
            dept.id,
            criado_por_usuario_id=None,
            encerrado_por_usuario_id=None,
            motivo_encerramento=None,
        ),
    )

    assert created.criado_por_usuario_id is None
    assert created.encerrado_por_usuario_id is None
    assert created.motivo_encerramento is None


def test_audit_user_foreign_keys(session_factory):
    emp, user, dept = base_context(session_factory)
    actor = persist(session_factory, usuario(emp.id))
    created = persist(
        session_factory,
        usuario_departamento(emp.id, user.id, dept.id, criado_por_usuario_id=actor.id),
    )

    assert created.criado_por_usuario_id == actor.id

    with pytest.raises(IntegrityError):
        persist(session_factory, usuario_departamento(emp.id, user.id, dept.id, encerrado_por_usuario_id=str(uuid4())))


def test_usuario_departamento_create_rejects_forbidden_fields():
    payload = {
        "empresaId": str(uuid4()),
        "usuarioId": str(uuid4()),
        "departamentoId": str(uuid4()),
        "papel": "membro",
        "principal": False,
        "inicioEm": now(),
    }

    for field, value in [
        ("status", "ativo"),
        ("fimEm", now()),
        ("motivoEncerramento", "teste"),
        ("criadoPorUsuarioId", str(uuid4())),
        ("encerradoPorUsuarioId", str(uuid4())),
        ("createdAt", now()),
        ("updatedAt", now()),
    ]:
        with pytest.raises(ValidationError):
            UsuarioDepartamentoCreate(**payload, **{field: value})


def test_usuario_departamento_update_rejects_forbidden_fields():
    for field, value in [
        ("empresaId", str(uuid4())),
        ("usuarioId", str(uuid4())),
        ("departamentoId", str(uuid4())),
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
            UsuarioDepartamentoUpdate(**{field: value})
