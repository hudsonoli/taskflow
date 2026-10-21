"""Capacidade individual de um Usuário (11B.2D-A): jornada semanal própria opcional e ausências por data.

Leitura: `usuarios.visualizar`. Escrita: `usuarios.editar` + regra de alvo de `app/core/autoridade_usuarios` (mesma do PATCH de Usuário). Usuário de outra empresa = 404. Sem UI nesta fase.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.autoridade_usuarios import AutoridadeUsuarioError
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.permissoes import require_permissao
from app.models.usuario import Usuario
from app.schemas.usuario_capacidade import AusenciaRead, AusenciaUpdate, AusenciaWrite, JornadaRead, JornadaWrite
from app.services.usuario_capacidade_service import (
    CapacidadeInvalidaError,
    ContaDeSistemaSemCapacidadeError,
    UsuarioCapacidadeNaoEncontradoError,
    UsuarioCapacidadeService,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios-capacidade"], dependencies=[Depends(get_current_user_password_ready)])
service = UsuarioCapacidadeService()


def _erro(exc: Exception) -> HTTPException:
    if isinstance(exc, UsuarioCapacidadeNaoEncontradoError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (AutoridadeUsuarioError, ContaDeSistemaSemCapacidadeError)):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, CapacidadeInvalidaError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    raise exc


# ── jornada ──────────────────────────────────────────────────────────────────────────────────────────────────────


@router.get("/{usuario_id}/jornada", response_model=JornadaRead, response_model_by_alias=True)
def obter_jornada(usuario_id: UUID, current_user: Usuario = Depends(require_permissao("usuarios.visualizar")), db: Session = Depends(get_db)):
    """Jornada da pessoa. `personalizada=false` = usa o expediente da empresa (e `dias` mostra essa semana)."""
    try:
        return service.obter_jornada(db, current_user, str(usuario_id))
    except Exception as exc:
        raise _erro(exc) from exc


@router.put("/{usuario_id}/jornada", response_model=JornadaRead, response_model_by_alias=True)
def substituir_jornada(usuario_id: UUID, payload: JornadaWrite, current_user: Usuario = Depends(require_permissao("usuarios.editar")), db: Session = Depends(get_db)):
    """Cria ou substitui a grade inteira da jornada personalizada. Dia não enviado = fechado."""
    try:
        return service.substituir_jornada(db, current_user, str(usuario_id), payload)
    except Exception as exc:
        raise _erro(exc) from exc


@router.delete("/{usuario_id}/jornada", response_model=JornadaRead, response_model_by_alias=True)
def usar_expediente_da_empresa(usuario_id: UUID, current_user: Usuario = Depends(require_permissao("usuarios.editar")), db: Session = Depends(get_db)):
    """"Usar expediente da empresa": remove a jornada personalizada. A capacidade volta ao fallback sem copiar nada."""
    try:
        return service.remover_jornada(db, current_user, str(usuario_id))
    except Exception as exc:
        raise _erro(exc) from exc


# ── ausências ────────────────────────────────────────────────────────────────────────────────────────────────────


@router.get("/{usuario_id}/ausencias", response_model=list[AusenciaRead], response_model_by_alias=True)
def listar_ausencias(
    usuario_id: UUID,
    desde: date | None = Query(default=None, description="Só ausências que terminam em/depois desta data"),
    ate: date | None = Query(default=None, description="Só ausências que começam em/antes desta data"),
    current_user: Usuario = Depends(require_permissao("usuarios.visualizar")),
    db: Session = Depends(get_db),
):
    try:
        return service.listar_ausencias(db, current_user, str(usuario_id), desde=desde, ate=ate)
    except Exception as exc:
        raise _erro(exc) from exc


@router.post("/{usuario_id}/ausencias", response_model=AusenciaRead, response_model_by_alias=True, status_code=status.HTTP_201_CREATED)
def criar_ausencia(usuario_id: UUID, payload: AusenciaWrite, current_user: Usuario = Depends(require_permissao("usuarios.editar")), db: Session = Depends(get_db)):
    try:
        return service.criar_ausencia(db, current_user, str(usuario_id), payload)
    except Exception as exc:
        raise _erro(exc) from exc


@router.patch("/{usuario_id}/ausencias/{ausencia_id}", response_model=AusenciaRead, response_model_by_alias=True)
def editar_ausencia(
    usuario_id: UUID, ausencia_id: UUID, payload: AusenciaUpdate, current_user: Usuario = Depends(require_permissao("usuarios.editar")), db: Session = Depends(get_db)
):
    try:
        return service.editar_ausencia(db, current_user, str(usuario_id), str(ausencia_id), payload)
    except Exception as exc:
        raise _erro(exc) from exc


@router.delete("/{usuario_id}/ausencias/{ausencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_ausencia(usuario_id: UUID, ausencia_id: UUID, current_user: Usuario = Depends(require_permissao("usuarios.editar")), db: Session = Depends(get_db)):
    """Remoção física; o histórico fica nos eventos `usuario.ausencia_*` (mesmo padrão dos dias especiais do expediente)."""
    try:
        service.remover_ausencia(db, current_user, str(usuario_id), str(ausencia_id))
    except Exception as exc:
        raise _erro(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
