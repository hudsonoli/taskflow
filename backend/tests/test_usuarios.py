from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.domain.event_types import DomainEventType
from app.main import app
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate
from app.services.usuario_service import UsuarioService


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


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.session_factory = session_factory
        yield test_client
    app.dependency_overrides.clear()


def empresa_payload(**overrides):
    data = {
        "nome": "TaskFloww Agencia",
        "documento": uuid4().hex,
        "codigoInterno": f"EMP-{uuid4().hex[:8]}",
    }
    data.update(overrides)
    return data


def create_empresa(client, **overrides):
    response = client.post("/empresas", json=empresa_payload(**overrides))
    assert response.status_code == 201
    return response.json()


def usuario_payload(empresa_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "codigoInterno": f"USR-{uuid4().hex[:8]}",
        "nome": "Hudson Silva",
        "email": f"hudson-{uuid4().hex[:8]}@empresa.com",
        "perfilBase": "operador",
        "acessoSistema": True,
    }
    data.update(overrides)
    return data


def create_usuario(client, empresa_id: str, **overrides):
    response = client.post("/usuarios", json=usuario_payload(empresa_id, **overrides))
    assert response.status_code == 201
    return response.json()


def eventos(session_factory) -> list[Evento]:
    with session_factory() as db:
        return list(db.scalars(select(Evento).order_by(Evento.created_at)).all())


def usuarios(session_factory) -> list[Usuario]:
    with session_factory() as db:
        return list(db.scalars(select(Usuario)).all())


def persist_empresa(session_factory, *, status: str = "ativa") -> Empresa:
    now = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid4()),
        nome="Empresa Persistida",
        documento=uuid4().hex,
        codigo_interno=f"EMP-{uuid4().hex[:8]}",
        status=status,
        created_at=now,
        updated_at=now,
        inativado_at=None,
        inativado_por_usuario_id=None,
        motivo_inativacao=None,
    )
    with session_factory() as db:
        db.add(empresa)
        db.commit()
        db.refresh(empresa)
        return empresa


def test_create_usuario_normalizes_email(client):
    empresa = create_empresa(client)

    usuario = create_usuario(client, empresa["id"], email=" Hudson@Empresa.COM ")

    assert usuario["id"]
    assert usuario["empresaId"] == empresa["id"]
    assert usuario["nome"] == "Hudson Silva"
    assert usuario["email"] == "hudson@empresa.com"
    assert usuario["perfilBase"] == "operador"
    assert usuario["acessoSistema"] is True
    assert usuario["status"] == "ativo"
    assert usuario["createdAt"]
    assert usuario["updatedAt"]


def test_create_usuario_with_missing_empresa_returns_422(client):
    response = client.post("/usuarios", json=usuario_payload(str(uuid4())))

    assert response.status_code == 422
    assert response.json() == {"detail": "Empresa não encontrada"}


def test_create_usuario_with_inactive_empresa_returns_422(client):
    empresa = create_empresa(client)
    client.post(f"/empresas/{empresa['id']}/inativar", json={"motivoInativacao": "teste"})

    response = client.post("/usuarios", json=usuario_payload(empresa["id"]))

    assert response.status_code == 422
    assert response.json() == {"detail": "Empresa inativa não permite criação de usuário"}


def test_list_usuarios_by_empresa(client):
    empresa_a = create_empresa(client, codigoInterno="EMP-A")
    empresa_b = create_empresa(client, codigoInterno="EMP-B")
    first = create_usuario(client, empresa_a["id"], codigoInterno="USR-A")
    create_usuario(client, empresa_b["id"], codigoInterno="USR-B")

    response = client.get("/usuarios", params={"empresaId": empresa_a["id"]})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [first["id"]]


def test_list_usuarios_filters_by_status_perfil_and_search(client):
    empresa = create_empresa(client)
    active = create_usuario(client, empresa["id"], nome="Hudson Operador", codigoInterno="USR-OP", perfilBase="operador")
    blocked = create_usuario(client, empresa["id"], nome="Maria Gestora", codigoInterno="USR-GE", perfilBase="gestor")
    client.post(f"/usuarios/{blocked['id']}/bloquear")

    response = client.get(
        "/usuarios",
        params={"empresaId": empresa["id"], "status": "ativo", "perfilBase": "operador", "search": "hudson"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [active["id"]]


def test_get_usuario_by_id(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])

    response = client.get(f"/usuarios/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_usuario_by_id_returns_404(client):
    response = client.get(f"/usuarios/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário não encontrado"}


def test_update_nome_email_perfil_and_acesso_sistema(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])

    response = client.patch(
        f"/usuarios/{created['id']}",
        json={
            "nome": "Hudson Atualizado",
            "email": " Novo.Email@Empresa.COM ",
            "perfilBase": "gestor",
            "acessoSistema": False,
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["nome"] == "Hudson Atualizado"
    assert updated["email"] == "novo.email@empresa.com"
    assert updated["perfilBase"] == "gestor"
    assert updated["acessoSistema"] is False


def test_patch_rejects_empresa_change(client):
    empresa = create_empresa(client)
    another_empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])

    response = client.patch(f"/usuarios/{created['id']}", json={"empresaId": another_empresa["id"]})

    assert response.status_code == 422
    assert "empresaId" in response.json()["detail"]


def test_patch_rejects_status_change(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])

    response = client.patch(f"/usuarios/{created['id']}", json={"status": "inativo"})

    assert response.status_code == 422
    assert "status" in response.json()["detail"]


def test_codigo_interno_duplicate_in_same_empresa_is_rejected(client):
    empresa = create_empresa(client)
    create_usuario(client, empresa["id"], codigoInterno="USR-DUP")

    response = client.post("/usuarios", json=usuario_payload(empresa["id"], codigoInterno="USR-DUP"))

    assert response.status_code == 409
    assert response.json() == {"detail": "codigoInterno já cadastrado para esta Empresa"}


def test_email_duplicate_in_same_empresa_is_rejected_after_normalization(client):
    empresa = create_empresa(client)
    create_usuario(client, empresa["id"], email="hudson@empresa.com")

    response = client.post("/usuarios", json=usuario_payload(empresa["id"], email=" Hudson@Empresa.COM "))

    assert response.status_code == 409
    assert response.json() == {"detail": "email já cadastrado para esta Empresa"}


def test_same_email_is_allowed_in_different_empresas(client):
    empresa_a = create_empresa(client, codigoInterno="EMP-A")
    empresa_b = create_empresa(client, codigoInterno="EMP-B")

    first = create_usuario(client, empresa_a["id"], email="hudson@empresa.com")
    second = create_usuario(client, empresa_b["id"], email=" Hudson@Empresa.COM ")

    assert first["email"] == "hudson@empresa.com"
    assert second["email"] == "hudson@empresa.com"
    assert first["empresaId"] != second["empresaId"]


def test_inativar_usuario(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])

    response = client.post(
        f"/usuarios/{created['id']}/inativar",
        json={"motivoInativacao": "saida operacional", "actorUsuarioId": created["id"]},
    )

    assert response.status_code == 200
    usuario = response.json()
    assert usuario["status"] == "inativo"
    assert usuario["inativadoAt"]
    assert usuario["inativadoPorUsuarioId"] == created["id"]
    assert usuario["motivoInativacao"] == "saida operacional"


def test_reativar_usuario(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])
    client.post(f"/usuarios/{created['id']}/inativar", json={"motivoInativacao": "teste"})

    response = client.post(f"/usuarios/{created['id']}/reativar")

    assert response.status_code == 200
    usuario = response.json()
    assert usuario["status"] == "ativo"
    assert usuario["inativadoAt"] is None
    assert usuario["inativadoPorUsuarioId"] is None
    assert usuario["motivoInativacao"] is None


def test_bloquear_usuario(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])

    response = client.post(f"/usuarios/{created['id']}/bloquear")

    assert response.status_code == 200
    assert response.json()["status"] == "bloqueado"


def test_desbloquear_usuario(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])
    client.post(f"/usuarios/{created['id']}/bloquear")

    response = client.post(f"/usuarios/{created['id']}/desbloquear")

    assert response.status_code == 200
    assert response.json()["status"] == "ativo"


def test_invalid_transitions_are_rejected(client):
    empresa = create_empresa(client)
    active = create_usuario(client, empresa["id"], codigoInterno="USR-A")
    inactive = create_usuario(client, empresa["id"], codigoInterno="USR-I")
    blocked = create_usuario(client, empresa["id"], codigoInterno="USR-B")
    client.post(f"/usuarios/{inactive['id']}/inativar", json={"motivoInativacao": "teste"})
    client.post(f"/usuarios/{blocked['id']}/bloquear")

    reactivate_active = client.post(f"/usuarios/{active['id']}/reativar")
    inactivate_inactive = client.post(f"/usuarios/{inactive['id']}/inativar", json={"motivoInativacao": "teste"})
    block_blocked = client.post(f"/usuarios/{blocked['id']}/bloquear")
    unblock_active = client.post(f"/usuarios/{active['id']}/desbloquear")

    assert reactivate_active.status_code == 409
    assert reactivate_active.json() == {"detail": "Usuário já está ativo"}
    assert inactivate_inactive.status_code == 409
    assert inactivate_inactive.json() == {"detail": "Usuário já está inativo"}
    assert block_blocked.status_code == 409
    assert block_blocked.json() == {"detail": "Usuário já está bloqueado"}
    assert unblock_active.status_code == 409
    assert unblock_active.json() == {"detail": "Somente usuário bloqueado pode ser desbloqueado"}


def test_delete_route_does_not_exist(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"])

    response = client.delete(f"/usuarios/{created['id']}")

    assert response.status_code == 405


def test_emits_user_events_with_required_audit_payload(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"], codigoInterno="USR-EVENTOS")
    client.patch(f"/usuarios/{created['id']}", json={"nome": "Nome Alterado"})
    client.post(f"/usuarios/{created['id']}/inativar", json={"motivoInativacao": "teste"})
    client.post(f"/usuarios/{created['id']}/reativar")
    client.post(f"/usuarios/{created['id']}/bloquear")
    client.post(f"/usuarios/{created['id']}/desbloquear")

    user_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "usuario"]
    event_types = [evento.tipo for evento in user_events]

    assert event_types == [
        DomainEventType.USUARIO_CRIADO.value,
        DomainEventType.USUARIO_ALTERADO.value,
        DomainEventType.USUARIO_INATIVADO.value,
        DomainEventType.USUARIO_REATIVADO.value,
        DomainEventType.USUARIO_BLOQUEADO.value,
        DomainEventType.USUARIO_DESBLOQUEADO.value,
    ]
    assert all(evento.empresa_id == empresa["id"] for evento in user_events)
    assert all(evento.entidade_id == created["id"] for evento in user_events)
    for evento in user_events:
        assert evento.payload["empresa_id"] == empresa["id"]
        assert evento.payload["usuario_id"] == created["id"]
        assert evento.payload["timestamp"]
        assert "email" not in evento.payload
        assert "documento" not in evento.payload


def test_event_payload_does_not_include_full_email_on_update(client):
    empresa = create_empresa(client)
    created = create_usuario(client, empresa["id"], email="hudson@empresa.com")

    client.patch(f"/usuarios/{created['id']}", json={"email": "novo@empresa.com"})

    user_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "usuario"]
    for evento in user_events:
        assert "hudson@empresa.com" not in str(evento.payload)
        assert "novo@empresa.com" not in str(evento.payload)
        assert "email" not in evento.payload


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_create_rolls_back_when_event_publish_fails(session_factory):
    empresa = persist_empresa(session_factory)
    service = UsuarioService(event_publisher=FailingPublisher())
    data = UsuarioCreate(
        empresaId=empresa.id,
        codigoInterno="USR-ROLLBACK",
        nome="Usuario Rollback",
        email="rollback@empresa.com",
        perfilBase="operador",
    )

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_usuario(db, data)

    assert usuarios(session_factory) == []
    assert eventos(session_factory) == []
