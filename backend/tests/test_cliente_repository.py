from datetime import datetime, timezone
from uuid import uuid4

from app.models.cliente import Cliente
from app.repositories.cliente_repository import ClienteRepository
from tests.conftest import make_empresa, persist, persist_agencia


def now():
    return datetime.now(timezone.utc)


def make_cliente(empresa_id: str, **overrides) -> Cliente:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "agencia_id": None,
        "codigo_interno": f"CLI-{uuid4().hex[:8]}",
        "tipo_pessoa": "juridica",
        "documento": f"{uuid4().int % 10**14:014d}",
        "razao_social": f"Razao {uuid4().hex[:8]} Ltda",
        "nome_fantasia": f"Fantasia {uuid4().hex[:8]}",
        "nome": None,
        "sigla": "CLI",
        "email": "contato@cliente.com",
        "telefone": None,
        "celular": None,
        "site": None,
        "codigo_externo": None,
        "observacoes": None,
        "status": "ativo",
        "status_alterado_at": None,
        "status_alterado_por_usuario_id": None,
        "motivo_status": None,
        "created_at": current_time,
        "updated_at": current_time,
    }
    data.update(overrides)
    return Cliente(**data)


def test_create_and_get_by_id_isolated_by_empresa(session_factory):
    repo = ClienteRepository()
    emp_a = persist(session_factory, make_empresa())
    emp_b = persist(session_factory, make_empresa())

    with session_factory() as db:
        cliente = repo.create(db, make_cliente(emp_a.id, codigo_interno="CLI-001", documento="12345678000190"))
        db.commit()
        cliente_id = cliente.id

    with session_factory() as db:
        assert repo.get_by_id(db, empresa_id=emp_a.id, cliente_id=cliente_id).id == cliente_id
        assert repo.get_by_id(db, empresa_id=emp_b.id, cliente_id=cliente_id) is None


def test_get_by_codigo_interno_and_documento_use_empresa(session_factory):
    repo = ClienteRepository()
    emp_a, emp_b = persist(session_factory, make_empresa(), make_empresa())
    persist(
        session_factory,
        make_cliente(emp_a.id, codigo_interno="CLI-001", documento="12345678000190"),
        make_cliente(emp_b.id, codigo_interno="CLI-001", documento="12345678000190"),
    )

    with session_factory() as db:
        cliente_a = repo.get_by_codigo_interno(db, empresa_id=emp_a.id, codigo_interno="CLI-001")
        cliente_b = repo.get_by_documento(db, empresa_id=emp_b.id, documento="12345678000190")

    assert cliente_a.empresa_id == emp_a.id
    assert cliente_b.empresa_id == emp_b.id


def test_list_filters_do_not_leak_other_empresa(session_factory):
    repo = ClienteRepository()
    emp_a, emp_b = persist(session_factory, make_empresa(), make_empresa())
    agencia_a = persist_agencia(session_factory, emp_a.id)
    persist(
        session_factory,
        make_cliente(emp_a.id, agencia_id=agencia_a.id, codigo_interno="CLI-001", tipo_pessoa="juridica", status="ativo"),
        make_cliente(emp_a.id, codigo_interno="CLI-002", tipo_pessoa="fisica", documento="12345678901", nome="Maria", razao_social=None, nome_fantasia=None, status="suspenso"),
        make_cliente(emp_b.id, codigo_interno="CLI-003", tipo_pessoa="juridica", status="ativo"),
    )

    with session_factory() as db:
        assert [c.codigo_interno for c in repo.list(db, empresa_id=emp_a.id)] == ["CLI-001", "CLI-002"]
        assert [c.codigo_interno for c in repo.list(db, empresa_id=emp_a.id, status="suspenso")] == ["CLI-002"]
        assert [c.codigo_interno for c in repo.list(db, empresa_id=emp_a.id, tipo_pessoa="fisica")] == ["CLI-002"]
        assert [c.codigo_interno for c in repo.list(db, empresa_id=emp_a.id, agencia_id=agencia_a.id)] == ["CLI-001"]


def test_list_busca_textual_uses_allowed_fields_only(session_factory):
    repo = ClienteRepository()
    emp = persist(session_factory, make_empresa())
    persist(
        session_factory,
        make_cliente(emp.id, codigo_interno="CLI-ALFA", documento="12345678000190", nome_fantasia="Alfa Digital", email="secreto@alfa.com"),
        make_cliente(emp.id, codigo_interno="CLI-BETA", documento="22345678000190", nome_fantasia="Beta"),
    )

    with session_factory() as db:
        by_nome = repo.list(db, empresa_id=emp.id, busca="Alfa")
        by_documento = repo.list(db, empresa_id=emp.id, busca="12345678000190")
        by_email = repo.list(db, empresa_id=emp.id, busca="secreto")

    assert [c.codigo_interno for c in by_nome] == ["CLI-ALFA"]
    assert by_documento == []
    assert by_email == []


def test_list_pagination_and_stable_order(session_factory):
    repo = ClienteRepository()
    emp = persist(session_factory, make_empresa())
    persist(
        session_factory,
        make_cliente(emp.id, codigo_interno="CLI-003", nome_fantasia="Charlie", documento="12345678000193"),
        make_cliente(emp.id, codigo_interno="CLI-001", nome_fantasia="Alpha", documento="12345678000191"),
        make_cliente(emp.id, codigo_interno="CLI-002", nome_fantasia="Bravo", documento="12345678000192"),
    )

    with session_factory() as db:
        first_page = repo.list(db, empresa_id=emp.id, limit=2, offset=0)
        second_page = repo.list(db, empresa_id=emp.id, limit=2, offset=2)

    assert [c.codigo_interno for c in first_page] == ["CLI-001", "CLI-002"]
    assert [c.codigo_interno for c in second_page] == ["CLI-003"]


def test_update_flushes_changes(session_factory):
    repo = ClienteRepository()
    emp = persist(session_factory, make_empresa())
    created = persist(session_factory, make_cliente(emp.id, codigo_interno="CLI-001", nome_fantasia="Antes"))

    with session_factory() as db:
        cliente = repo.get_by_id(db, empresa_id=emp.id, cliente_id=created.id)
        cliente.nome_fantasia = "Depois"
        repo.update(db, cliente)
        db.commit()

    with session_factory() as db:
        assert repo.get_by_id(db, empresa_id=emp.id, cliente_id=created.id).nome_fantasia == "Depois"


def test_repository_has_no_delete_method():
    assert not hasattr(ClienteRepository, "delete")
    assert not hasattr(ClienteRepository, "remove")
