from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cli.definir_senha_usuario import main
from app.core.security import verify_password
from app.db.base import Base
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial


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


def persist_user(session_factory):
    now = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid4()),
        nome="Empresa CLI",
        documento=uuid4().hex,
        codigo_interno="BOX",
        status="ativa",
        created_at=now,
        updated_at=now,
        inativado_at=None,
        inativado_por_usuario_id=None,
        motivo_inativacao=None,
    )
    usuario = Usuario(
        id=str(uuid4()),
        empresa_id=empresa.id,
        codigo_interno="USR-CLI",
        nome="Admin CLI",
        email="admin@empresa.com",
        perfil_base="admin",
        acesso_sistema=True,
        status="ativo",
        created_at=now,
        updated_at=now,
        inativado_at=None,
        inativado_por_usuario_id=None,
        motivo_inativacao=None,
    )
    with session_factory() as db:
        db.add_all([empresa, usuario])
        db.commit()
        db.refresh(usuario)
        return usuario


def outputs():
    lines: list[str] = []
    return lines, lines.append


def password_reader(values):
    values = list(values)

    def read(prompt):
        return values.pop(0)

    return read


def test_cli_defines_password_without_printing_secret_or_hash(session_factory):
    user = persist_user(session_factory)
    lines, output = outputs()

    exit_code = main(
        ["--empresa-codigo", "BOX", "--email", "admin@empresa.com"],
        session_factory=session_factory,
        password_reader=password_reader(["SenhaCli123", "SenhaCli123"]),
        output=output,
    )

    assert exit_code == 0
    assert lines == ["Senha definida com sucesso."]
    joined = " ".join(lines)
    assert "SenhaCli123" not in joined
    assert "argon2" not in joined.lower()

    with session_factory() as db:
        credential = db.scalars(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == user.id)).one()
        assert verify_password("SenhaCli123", credential.senha_hash)
        event_types = [evento.tipo for evento in db.scalars(select(Evento)).all()]
        assert "auth.senha_definida" in event_types


def test_cli_rejects_confirmation_mismatch_without_creating_credential(session_factory):
    user = persist_user(session_factory)
    lines, output = outputs()

    exit_code = main(
        ["--empresa-codigo", "BOX", "--email", "admin@empresa.com"],
        session_factory=session_factory,
        password_reader=password_reader(["SenhaCli123", "OutraSenha123"]),
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: confirmação de senha não confere."]
    with session_factory() as db:
        assert db.scalars(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == user.id)).first() is None


def test_cli_does_not_create_user_or_company_for_unknown_user(session_factory):
    persist_user(session_factory)
    lines, output = outputs()

    exit_code = main(
        ["--empresa-codigo", "BOX", "--email", "naoexiste@empresa.com"],
        session_factory=session_factory,
        password_reader=password_reader(["SenhaCli123", "SenhaCli123"]),
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: Empresa ou usuário não encontrado"]
    with session_factory() as db:
        assert db.query(Usuario).count() == 1
        assert db.query(Empresa).count() == 1
        assert db.query(UsuarioCredencial).count() == 0
