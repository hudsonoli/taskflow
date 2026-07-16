from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.equipe import Equipe
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.schemas.equipe import EquipeCreate, EquipeInativar, EquipeResponse, EquipeUpdate


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
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
        "created_at": current_time,
        "updated_at": current_time,
    }
    data.update(overrides)
    return Equipe(**data)


def persist(session_factory, *objects):
    with session_factory() as db:
        db.add_all(objects)
        db.commit()
        for obj in objects:
            db.refresh(obj)
        return objects[0] if len(objects) == 1 else objects


def test_equipe_persists_required_fields(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, equipe(emp.id, codigo_interno="EQ-001", nome="Equipe Criacao"))

    assert created.id
    assert created.empresa_id == emp.id
    assert created.codigo_interno == "EQ-001"
    assert created.nome == "Equipe Criacao"
    assert created.status == "ativa"
    assert Equipe.__table__.c.created_at.type.timezone is True
    assert Equipe.__table__.c.updated_at.type.timezone is True


def test_model_is_registered_in_base_metadata():
    assert "equipes" in Base.metadata.tables


def test_expected_columns_exist_and_no_out_of_scope_relationship_fields():
    columns = set(Equipe.__table__.columns.keys())

    assert columns == {
        "id",
        "empresa_id",
        "codigo_interno",
        "nome",
        "descricao",
        "status",
        "inativado_at",
        "motivo_inativacao",
        "inativado_por_usuario_id",
        "created_at",
        "updated_at",
    }
    assert "usuario_id" not in columns
    assert "cargo_id" not in columns
    assert "departamento_id" not in columns
    assert "squad_id" not in columns


def test_expected_indexes_exist():
    index_names = {index.name for index in Equipe.__table__.indexes}

    assert index_names == {
        "ix_equipes_empresa_id",
        "ix_equipes_status",
        "ix_equipes_created_at",
    }


def test_expected_constraints_exist():
    constraint_names = {constraint.name for constraint in Equipe.__table__.constraints}

    assert "ck_equipes_status" in constraint_names
    assert "ck_equipes_nome_nao_vazio" in constraint_names
    assert "ck_equipes_codigo_interno_nao_vazio" in constraint_names
    assert "uq_equipes_empresa_codigo_interno" in constraint_names
    assert "uq_equipes_empresa_nome" in constraint_names


def test_empresa_id_is_required(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, equipe(None))


def test_empresa_id_must_reference_existing_empresa(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, equipe(str(uuid4())))


def test_inativado_por_usuario_id_must_reference_existing_usuario(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, equipe(emp.id, inativado_por_usuario_id=str(uuid4())))


def test_inativado_por_usuario_id_can_reference_usuario(session_factory):
    emp = persist(session_factory, empresa())
    actor = persist(session_factory, usuario(emp.id))
    created = persist(
        session_factory,
        equipe(
            emp.id,
            status="inativa",
            inativado_at=now(),
            motivo_inativacao="encerramento",
            inativado_por_usuario_id=actor.id,
        ),
    )

    assert created.inativado_por_usuario_id == actor.id


def test_codigo_interno_unique_per_empresa(session_factory):
    emp = persist(session_factory, empresa())
    persist(session_factory, equipe(emp.id, codigo_interno="EQ-DUP"))

    with pytest.raises(IntegrityError):
        persist(session_factory, equipe(emp.id, codigo_interno="EQ-DUP"))


def test_codigo_interno_can_repeat_in_different_empresas(session_factory):
    emp_a, emp_b = persist(session_factory, empresa(), empresa(documento=uuid4().hex))

    first = persist(session_factory, equipe(emp_a.id, codigo_interno="EQ-001"))
    second = persist(session_factory, equipe(emp_b.id, codigo_interno="EQ-001"))

    assert first.codigo_interno == second.codigo_interno
    assert first.empresa_id != second.empresa_id


def test_nome_unique_per_empresa(session_factory):
    emp = persist(session_factory, empresa())
    persist(session_factory, equipe(emp.id, nome="Criacao"))

    with pytest.raises(IntegrityError):
        persist(session_factory, equipe(emp.id, nome="Criacao"))


def test_nome_can_repeat_in_different_empresas(session_factory):
    emp_a, emp_b = persist(session_factory, empresa(), empresa(documento=uuid4().hex))

    first = persist(session_factory, equipe(emp_a.id, nome="Atendimento"))
    second = persist(session_factory, equipe(emp_b.id, nome="Atendimento"))

    assert first.nome == second.nome
    assert first.empresa_id != second.empresa_id


def test_nome_empty_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, equipe(emp.id, nome="   "))


def test_codigo_interno_empty_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, equipe(emp.id, codigo_interno="   "))


@pytest.mark.parametrize("status", ["ativa", "inativa", "arquivada"])
def test_allowed_status_values(session_factory, status):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, equipe(emp.id, status=status))

    assert created.status == status


def test_invalid_status_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, equipe(emp.id, status="bloqueada"))


def test_descricao_can_be_null(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, equipe(emp.id, descricao=None))

    assert created.descricao is None


def test_inativacao_fields_can_be_null(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(
        session_factory,
        equipe(
            emp.id,
            inativado_at=None,
            motivo_inativacao=None,
            inativado_por_usuario_id=None,
        ),
    )

    assert created.inativado_at is None
    assert created.motivo_inativacao is None
    assert created.inativado_por_usuario_id is None


def test_equipe_create_uses_aliases_and_rejects_forbidden_fields():
    payload = {
        "empresaId": str(uuid4()),
        "codigoInterno": "EQ-001",
        "nome": "Equipe Criacao",
        "descricao": "Equipe interna",
    }
    created = EquipeCreate.model_validate(payload)

    assert str(created.empresa_id) == payload["empresaId"]
    assert created.codigo_interno == "EQ-001"

    for field in [
        "status",
        "createdAt",
        "updatedAt",
        "deletedAt",
        "inativadoAt",
        "motivoInativacao",
        "inativadoPorUsuarioId",
    ]:
        with pytest.raises(ValidationError):
            EquipeCreate.model_validate({**payload, field: "valor"})


def test_equipe_update_rejects_forbidden_fields():
    forbidden = [
        "empresaId",
        "empresa_id",
        "status",
        "createdAt",
        "created_at",
        "updatedAt",
        "updated_at",
        "deletedAt",
        "deleted_at",
        "inativadoAt",
        "inativado_at",
        "motivoInativacao",
        "motivo_inativacao",
        "inativadoPorUsuarioId",
        "inativado_por_usuario_id",
    ]

    for field in forbidden:
        with pytest.raises(ValidationError):
            EquipeUpdate.model_validate({field: "valor"})


def test_equipe_inativar_accepts_only_motivo():
    payload = {"motivoInativacao": "encerramento"}
    inativar = EquipeInativar.model_validate(payload)

    assert inativar.motivo_inativacao == "encerramento"

    for field in ["actorUsuarioId", "status", "inativadoAt"]:
        with pytest.raises(ValidationError):
            EquipeInativar.model_validate({**payload, field: "valor"})


def test_equipe_response_serializes_with_aliases_and_timezone():
    current_time = now()
    response = EquipeResponse(
        id=str(uuid4()),
        empresaId=str(uuid4()),
        codigoInterno="EQ-001",
        nome="Equipe Criacao",
        descricao="Equipe interna",
        status="ativa",
        inativadoAt=None,
        motivoInativacao=None,
        inativadoPorUsuarioId=None,
        createdAt=current_time,
        updatedAt=current_time,
    )

    dumped = response.model_dump(by_alias=True)

    assert dumped["empresaId"] == response.empresa_id
    assert dumped["codigoInterno"] == "EQ-001"
    assert dumped["createdAt"].tzinfo is not None
    assert dumped["updatedAt"].tzinfo is not None
