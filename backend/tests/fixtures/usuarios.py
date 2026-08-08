"""Fixtures de usuário — um por perfil_base, cada um com credencial conhecida (senha em
texto puro exposta via SENHA_CONHECIDA, pra login real no /auth/login) e
`senha_deve_ser_alterada=False` (senão o fluxo de troca obrigatória bloquearia as rotas)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial

SENHA_CONHECIDA = "SenhaConhecidaTeste123!"


def _criar_usuario_com_credencial(
    db_session: Session,
    *,
    empresa: Empresa,
    perfil_base: str,
    email_prefixo: str,
) -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"{email_prefixo}-{sufixo}",
        nome=f"Usuário {perfil_base.capitalize()} de Teste",
        email=f"{email_prefixo}-{sufixo}@teste.taskfloww.local",
        perfil_base=perfil_base,
        acesso_sistema=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(usuario)
    db_session.flush()

    credencial = UsuarioCredencial(
        id=str(uuid.uuid4()),
        usuario_id=usuario.id,
        senha_hash=hash_password(SENHA_CONHECIDA),
        senha_definida_em=agora,
        senha_deve_ser_alterada=False,
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(credencial)
    db_session.flush()
    return usuario


@pytest.fixture()
def usuario_admin(db_session: Session, empresa: Empresa) -> Usuario:
    return _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="admin", email_prefixo="admin")


@pytest.fixture()
def usuario_gestor(db_session: Session, empresa: Empresa) -> Usuario:
    return _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="gestor", email_prefixo="gestor")


@pytest.fixture()
def usuario_operador(db_session: Session, empresa: Empresa) -> Usuario:
    return _criar_usuario_com_credencial(
        db_session, empresa=empresa, perfil_base="operador", email_prefixo="operador"
    )
