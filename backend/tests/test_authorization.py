from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa, require_profiles
from conftest import make_usuario


def test_require_profiles_allows_matching_profile():
    user = make_usuario(str(uuid4()), perfil_base="admin")
    dependency = require_profiles("admin")

    assert dependency(user) is user


def test_require_profiles_rejects_different_profile():
    user = make_usuario(str(uuid4()), perfil_base="operador")
    dependency = require_profiles("admin", "gestor")

    with pytest.raises(HTTPException) as exc:
        dependency(user)

    assert exc.value.status_code == 403


def test_ensure_same_empresa_rejects_explicit_divergence():
    user = make_usuario(str(uuid4()), perfil_base="admin")

    with pytest.raises(HTTPException) as exc:
        ensure_same_empresa(str(uuid4()), user)

    assert exc.value.status_code == 403


def test_ensure_resource_empresa_masks_other_tenant_as_404():
    user = make_usuario(str(uuid4()), perfil_base="admin")

    with pytest.raises(HTTPException) as exc:
        ensure_resource_empresa(str(uuid4()), user)

    assert exc.value.status_code == 404
