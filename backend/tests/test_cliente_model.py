from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.agencia import Agencia
from app.models.cliente import Cliente, ClienteStatus, ClienteTipoPessoa
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate


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


def agencia(empresa_id: str, **overrides) -> Agencia:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"AG-{uuid4().hex[:8]}",
        "nome": f"Agencia {uuid4().hex[:8]}",
        "sigla": f"A{uuid4().hex[:4]}",
        "descricao": None,
        "status": "ativa",
        "created_at": current_time,
        "updated_at": current_time,
        "inativado_at": None,
        "inativado_por_usuario_id": None,
        "motivo_inativacao": None,
    }
    data.update(overrides)
    return Agencia(**data)


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


def cliente(empresa_id: str | None, **overrides) -> Cliente:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "agencia_id": None,
        "codigo_interno": f"CLI-{uuid4().hex[:8]}",
        "tipo_pessoa": ClienteTipoPessoa.JURIDICA.value,
        "documento": f"{uuid4().int % 10**14:014d}",
        "razao_social": "Cliente Modelo Ltda",
        "nome_fantasia": "Cliente Modelo",
        "nome": None,
        "sigla": "CLM",
        "email": "contato@cliente.com",
        "telefone": "1133334444",
        "celular": "11999998888",
        "site": "https://cliente.com",
        "codigo_externo": "EXT-001",
        "observacoes": "Observacao de teste",
        "status": ClienteStatus.ATIVO.value,
        "status_alterado_at": None,
        "status_alterado_por_usuario_id": None,
        "motivo_status": None,
        "created_at": current_time,
        "updated_at": current_time,
    }
    data.update(overrides)
    return Cliente(**data)


def persist(session_factory, *objects):
    with session_factory() as db:
        db.add_all(objects)
        db.commit()
        for obj in objects:
            db.refresh(obj)
        return objects[0] if len(objects) == 1 else objects


def test_model_is_registered_in_base_metadata():
    assert "clientes" in Base.metadata.tables


def test_expected_columns_exist():
    assert set(Cliente.__table__.columns.keys()) == {
        "id",
        "empresa_id",
        "agencia_id",
        "codigo_interno",
        "tipo_pessoa",
        "documento",
        "razao_social",
        "nome_fantasia",
        "nome",
        "sigla",
        "email",
        "telefone",
        "celular",
        "site",
        "codigo_externo",
        "observacoes",
        "status",
        "status_alterado_at",
        "status_alterado_por_usuario_id",
        "motivo_status",
        "created_at",
        "updated_at",
    }


def test_expected_indexes_and_constraints_exist():
    index_names = {index.name for index in Cliente.__table__.indexes}
    constraint_names = {constraint.name for constraint in Cliente.__table__.constraints}

    assert {
        "ix_clientes_empresa_id",
        "ix_clientes_agencia_id",
        "ix_clientes_status",
        "ix_clientes_tipo_pessoa",
        "ix_clientes_documento",
        "ix_clientes_created_at",
        "uq_clientes_empresa_documento",
    }.issubset(index_names)
    assert {
        "ck_clientes_tipo_pessoa",
        "ck_clientes_status",
        "ck_clientes_codigo_interno_nao_vazio",
        "ck_clientes_documento_apenas_digitos",
        "ck_clientes_documento_tamanho",
        "uq_clientes_empresa_codigo_interno",
    }.issubset(constraint_names)


def test_documento_digits_constraint_is_dialect_neutral():
    constraint = next(
        constraint
        for constraint in Cliente.__table__.constraints
        if constraint.name == "ck_clientes_documento_apenas_digitos"
    )
    expression = str(constraint.sqltext)

    assert "replace(" in expression
    assert "GLOB" not in expression.upper()
    assert "~" not in expression
    assert "REGEXP" not in expression.upper()


def test_cria_pessoa_juridica_valida(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, cliente(emp.id, documento="12345678000190"))

    assert created.id
    assert created.empresa_id == emp.id
    assert created.tipo_pessoa == "juridica"
    assert created.documento == "12345678000190"
    assert created.status == "ativo"
    assert Cliente.__table__.c.created_at.type.timezone is True
    assert Cliente.__table__.c.updated_at.type.timezone is True


def test_cria_pessoa_fisica_valida(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(
        session_factory,
        cliente(
            emp.id,
            tipo_pessoa="fisica",
            documento="12345678901",
            razao_social=None,
            nome_fantasia=None,
            nome="Maria Cliente",
        ),
    )

    assert created.tipo_pessoa == "fisica"
    assert created.documento == "12345678901"
    assert created.nome == "Maria Cliente"


def test_status_default_ativo(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, cliente(emp.id, status=None))

    assert created.status == "ativo"


def test_empresa_id_is_required(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(None))


def test_empresa_id_must_reference_existing_empresa(session_factory):
    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(str(uuid4())))


def test_agencia_is_optional(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, cliente(emp.id, agencia_id=None))

    assert created.agencia_id is None


def test_agencia_id_can_reference_existing_agencia(session_factory):
    emp = persist(session_factory, empresa())
    ag = persist(session_factory, agencia(emp.id))
    created = persist(session_factory, cliente(emp.id, agencia_id=ag.id))

    assert created.agencia_id == ag.id


def test_agencia_id_must_reference_existing_agencia(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, agencia_id=str(uuid4())))


def test_status_alterado_por_usuario_id_can_reference_usuario(session_factory):
    emp = persist(session_factory, empresa())
    actor = persist(session_factory, usuario(emp.id))
    changed_at = now()
    created = persist(
        session_factory,
        cliente(
            emp.id,
            status="suspenso",
            status_alterado_at=changed_at,
            status_alterado_por_usuario_id=actor.id,
            motivo_status="Contrato pausado",
        ),
    )

    assert created.status_alterado_por_usuario_id == actor.id
    assert created.status_alterado_at == changed_at.replace(tzinfo=None)


def test_status_alterado_por_usuario_id_must_reference_existing_usuario(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, status_alterado_por_usuario_id=str(uuid4())))


def test_documento_can_be_null(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, cliente(emp.id, documento=None))

    assert created.documento is None


@pytest.mark.parametrize("documento", ["12345678901", "12345678000190"])
def test_documento_allowed_lengths(session_factory, documento):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, cliente(emp.id, documento=documento))

    assert created.documento == documento


@pytest.mark.parametrize("documento", ["123.456.789-01", "1234567890A", "123", "123456789012"])
def test_documento_invalid_values_rejected_by_schema(documento):
    with pytest.raises(ValidationError):
        ClienteCreate.model_validate(
            {
                "empresaId": str(uuid4()),
                "codigoInterno": "CLI-001",
                "tipoPessoa": "fisica",
                "documento": documento,
                "nome": "Maria Cliente",
            }
        )


def test_documento_only_digits_is_accepted_by_database(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, cliente(emp.id, documento="12345678000190"))

    assert created.documento == "12345678000190"


@pytest.mark.parametrize("documento", ["1234567890A", "123.45678901", "123456789 1"])
def test_documento_with_non_digits_is_rejected_by_database(session_factory, documento):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, documento=documento))


def test_documento_with_invalid_length_is_rejected_by_database(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, documento="1234567890"))


def test_pf_sem_nome_rejeitada_no_schema():
    with pytest.raises(ValidationError):
        ClienteCreate.model_validate(
            {
                "empresaId": str(uuid4()),
                "codigoInterno": "CLI-001",
                "tipoPessoa": "fisica",
                "documento": "12345678901",
            }
        )


def test_pj_sem_razao_social_e_sem_nome_fantasia_rejeitada_no_schema():
    with pytest.raises(ValidationError):
        ClienteCreate.model_validate(
            {
                "empresaId": str(uuid4()),
                "codigoInterno": "CLI-001",
                "tipoPessoa": "juridica",
                "documento": "12345678000190",
            }
        )


def test_pj_com_somente_razao_social_aceita_no_schema():
    payload = ClienteCreate.model_validate(
        {
            "empresaId": str(uuid4()),
            "codigoInterno": "CLI-001",
            "tipoPessoa": "juridica",
            "documento": "12345678000190",
            "razaoSocial": "Cliente Modelo Ltda",
        }
    )

    assert payload.razao_social == "Cliente Modelo Ltda"
    assert payload.nome_fantasia is None


def test_pj_com_somente_nome_fantasia_aceita_no_schema():
    payload = ClienteCreate.model_validate(
        {
            "empresaId": str(uuid4()),
            "codigoInterno": "CLI-001",
            "tipoPessoa": "juridica",
            "documento": "12345678000190",
            "nomeFantasia": "Cliente Modelo",
        }
    )

    assert payload.nome_fantasia == "Cliente Modelo"
    assert payload.razao_social is None


def test_cliente_create_rejects_non_active_initial_status():
    with pytest.raises(ValidationError):
        ClienteCreate.model_validate(
            {
                "empresaId": str(uuid4()),
                "codigoInterno": "CLI-001",
                "tipoPessoa": "fisica",
                "documento": "12345678901",
                "nome": "Maria Cliente",
                "status": "suspenso",
            }
        )


def test_codigo_interno_required_by_schema():
    with pytest.raises(ValidationError):
        ClienteCreate.model_validate(
            {
                "empresaId": str(uuid4()),
                "tipoPessoa": "fisica",
                "documento": "12345678901",
                "nome": "Maria Cliente",
            }
        )


def test_codigo_interno_empty_is_rejected_by_database(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, codigo_interno="   "))


def test_codigo_interno_unique_per_empresa(session_factory):
    emp = persist(session_factory, empresa())
    persist(session_factory, cliente(emp.id, codigo_interno="CLI-DUP", documento="12345678000190"))

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, codigo_interno="CLI-DUP", documento="12345678000191"))


def test_codigo_interno_can_repeat_in_different_empresas(session_factory):
    emp_a, emp_b = persist(session_factory, empresa(), empresa(documento=uuid4().hex))

    first = persist(session_factory, cliente(emp_a.id, codigo_interno="CLI-001", documento="12345678000190"))
    second = persist(session_factory, cliente(emp_b.id, codigo_interno="CLI-001", documento="12345678000190"))

    assert first.codigo_interno == second.codigo_interno
    assert first.empresa_id != second.empresa_id


def test_documento_unique_per_empresa(session_factory):
    emp = persist(session_factory, empresa())
    persist(session_factory, cliente(emp.id, codigo_interno="CLI-001", documento="12345678000190"))

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, codigo_interno="CLI-002", documento="12345678000190"))


def test_documento_can_repeat_in_different_empresas(session_factory):
    emp_a, emp_b = persist(session_factory, empresa(), empresa(documento=uuid4().hex))

    first = persist(session_factory, cliente(emp_a.id, codigo_interno="CLI-001", documento="12345678000190"))
    second = persist(session_factory, cliente(emp_b.id, codigo_interno="CLI-002", documento="12345678000190"))

    assert first.documento == second.documento
    assert first.empresa_id != second.empresa_id


def test_multiple_null_documentos_same_empresa(session_factory):
    emp = persist(session_factory, empresa())

    first = persist(session_factory, cliente(emp.id, codigo_interno="CLI-001", documento=None))
    second = persist(session_factory, cliente(emp.id, codigo_interno="CLI-002", documento=None))

    assert first.documento is None
    assert second.documento is None


@pytest.mark.parametrize("status", [item.value for item in ClienteStatus])
def test_valid_status_values(session_factory, status):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, cliente(emp.id, status=status))

    assert created.status == status


def test_invalid_status_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, status="arquivado"))


@pytest.mark.parametrize("tipo_pessoa", [item.value for item in ClienteTipoPessoa])
def test_valid_tipo_pessoa_values(session_factory, tipo_pessoa):
    emp = persist(session_factory, empresa())
    overrides = {"tipo_pessoa": tipo_pessoa}
    if tipo_pessoa == "fisica":
        overrides.update({"documento": "12345678901", "nome": "Maria Cliente", "razao_social": None, "nome_fantasia": None})
    created = persist(session_factory, cliente(emp.id, **overrides))

    assert created.tipo_pessoa == tipo_pessoa


def test_invalid_tipo_pessoa_is_rejected(session_factory):
    emp = persist(session_factory, empresa())

    with pytest.raises(IntegrityError):
        persist(session_factory, cliente(emp.id, tipo_pessoa="empresa"))


def test_persists_and_reads_all_foundation_fields(session_factory):
    emp = persist(session_factory, empresa())
    ag = persist(session_factory, agencia(emp.id))
    actor = persist(session_factory, usuario(emp.id))
    changed_at = now()
    created = persist(
        session_factory,
        cliente(
            emp.id,
            agencia_id=ag.id,
            codigo_interno="CLI-100",
            documento="12345678000190",
            razao_social="Razao Social Ltda",
            nome_fantasia="Fantasia",
            sigla="FAN",
            email="contato@fantasia.com",
            telefone="1133334444",
            celular="11999998888",
            site="https://fantasia.com",
            codigo_externo="EXT-100",
            observacoes="Cliente estratégico",
            status="suspenso",
            status_alterado_at=changed_at,
            status_alterado_por_usuario_id=actor.id,
            motivo_status="Pausa contratual",
        ),
    )

    assert created.agencia_id == ag.id
    assert created.codigo_interno == "CLI-100"
    assert created.razao_social == "Razao Social Ltda"
    assert created.nome_fantasia == "Fantasia"
    assert created.sigla == "FAN"
    assert created.email == "contato@fantasia.com"
    assert created.telefone == "1133334444"
    assert created.celular == "11999998888"
    assert created.site == "https://fantasia.com"
    assert created.codigo_externo == "EXT-100"
    assert created.observacoes == "Cliente estratégico"
    assert created.motivo_status == "Pausa contratual"


def test_cliente_update_rejects_forbidden_fields():
    forbidden = [
        "empresaId",
        "status",
        "statusAlteradoAt",
        "statusAlteradoPorUsuarioId",
        "motivoStatus",
        "createdAt",
        "updatedAt",
        "deletedAt",
    ]

    for field in forbidden:
        with pytest.raises(ValidationError):
            ClienteUpdate.model_validate({field: "valor"})


def test_cliente_update_accepts_allowed_fields_and_aliases():
    payload = ClienteUpdate.model_validate(
        {
            "agenciaId": str(uuid4()),
            "codigoInterno": " CLI-001 ",
            "tipoPessoa": "juridica",
            "documento": "12345678000190",
            "razaoSocial": "Cliente Modelo Ltda",
            "nomeFantasia": "Cliente Modelo",
            "codigoExterno": "EXT-001",
        }
    )

    assert payload.codigo_interno == "CLI-001"
    assert payload.razao_social == "Cliente Modelo Ltda"
    assert payload.nome_fantasia == "Cliente Modelo"


def test_cliente_response_from_attributes_and_aliases(session_factory):
    emp = persist(session_factory, empresa())
    created = persist(session_factory, cliente(emp.id, documento="12345678000190"))

    response = ClienteResponse.model_validate(created)
    dumped = response.model_dump(by_alias=True)

    assert str(dumped["empresaId"]) == emp.id
    assert dumped["codigoInterno"] == created.codigo_interno
    assert dumped["tipoPessoa"] == "juridica"
    assert dumped["statusAlteradoPorUsuarioId"] is None
    assert dumped["createdAt"].tzinfo is not None
    assert dumped["updatedAt"].tzinfo is not None


def test_cliente_response_converts_status_alterado_por_usuario_id_to_uuid(session_factory):
    emp = persist(session_factory, empresa())
    actor = persist(session_factory, usuario(emp.id))
    created = persist(
        session_factory,
        cliente(
            emp.id,
            documento="12345678000190",
            status="suspenso",
            status_alterado_at=now(),
            status_alterado_por_usuario_id=actor.id,
        ),
    )

    response = ClienteResponse.model_validate(created)
    dumped = response.model_dump(by_alias=True)

    assert response.status_alterado_por_usuario_id == UUID(actor.id)
    assert dumped["statusAlteradoPorUsuarioId"] == UUID(actor.id)
