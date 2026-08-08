"""Fixture de empresa — base pra todo teste que precisa de um tenant válido."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.empresa import Empresa


@pytest.fixture()
def empresa(db_session: Session) -> Empresa:
    agora = datetime.now(timezone.utc)
    entidade = Empresa(
        id=str(uuid.uuid4()),
        nome="Empresa de Teste",
        documento=None,
        # Maiúsculo: AuthService._normalize_empresa_codigo() faz .upper() no código
        # informado no login — armazenar já normalizado evita falso-negativo no login real.
        codigo_interno=f"EMPRESA-TESTE-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(entidade)
    db_session.flush()
    return entidade


@pytest.fixture()
def outra_empresa(db_session: Session) -> Empresa:
    """Segunda empresa — usada nos testes de isolamento multiempresa (404 cross-tenant)."""
    agora = datetime.now(timezone.utc)
    entidade = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa de Teste",
        documento=None,
        codigo_interno=f"OUTRA-EMPRESA-TESTE-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(entidade)
    db_session.flush()
    return entidade
