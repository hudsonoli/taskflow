"""Configuração administrativa de Regra de Expediente — singleton por Empresa (Fase 2G.3).

Sem POST/DELETE/list/{id} para a REGRA em si: é singleton, não coleção — GET sempre lê (criando o padrão inicial
na primeira vez, se ainda não existir) e PATCH sempre edita o único registro da Empresa do
usuário autenticado. Leitura operacional enxuta (usada por Kanban/UX, sem exigir admin/gestor)
fica em app/api/routes/expediente.py, rota separada — ver docstring de lá.

Fase Expediente 1: os DIAS ESPECIAIS (feriado, recesso, trabalho excepcional, "ignorado") são uma coleção dentro da regra — cadastro MANUAL em
`/regra-expediente/dias-especiais`. Nenhum endpoint deste módulo bloqueia acesso nem pausa trabalho; a importação automática de feriados é de outra fase.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.regra_expediente import (
    DiaEspecialRead,
    DiaEspecialUpdate,
    DiaEspecialWrite,
    RegraExpedienteRead,
    RegraExpedienteUpdate,
)
from app.services.regra_expediente_service import (
    DiaEspecialConflitoError,
    DiaEspecialNaoEditavelError,
    DiaEspecialNaoEncontradoError,
    RegraExpedienteInvalidaError,
    RegraExpedienteService,
)

router = APIRouter(
    prefix="/regra-expediente",
    tags=["regra-expediente"],
    dependencies=[Depends(get_current_user_password_ready)],
)
regra_expediente_service = RegraExpedienteService()


@router.get("", response_model=RegraExpedienteRead)
def get_regra_expediente(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    regra = regra_expediente_service.get_ou_criar(db, empresa_id=current_user.empresa_id)
    return regra_expediente_service.to_read(db, regra)


@router.patch("", response_model=RegraExpedienteRead)
def update_regra_expediente(
    payload: RegraExpedienteUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        regra = regra_expediente_service.atualizar(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
    except RegraExpedienteInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return regra_expediente_service.to_read(db, regra)


# ── dias especiais ───────────────────────────────────────────────────────────────────────────────────────────────


def _traduzir_dia_especial(exc: Exception) -> HTTPException:
    if isinstance(exc, DiaEspecialNaoEncontradoError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, DiaEspecialConflitoError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/dias-especiais", response_model=list[DiaEspecialRead])
def list_dias_especiais(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    return regra_expediente_service.listar_dias_especiais(db, empresa_id=current_user.empresa_id)


@router.post("/dias-especiais", response_model=DiaEspecialRead, status_code=status.HTTP_201_CREATED)
def create_dia_especial(
    payload: DiaEspecialWrite,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        return regra_expediente_service.criar_dia_especial(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
    except (DiaEspecialConflitoError, DiaEspecialNaoEditavelError) as exc:
        raise _traduzir_dia_especial(exc) from exc


@router.patch("/dias-especiais/{dia_especial_id}", response_model=DiaEspecialRead)
def update_dia_especial(
    dia_especial_id: UUID,
    payload: DiaEspecialUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        return regra_expediente_service.atualizar_dia_especial(
            db, str(dia_especial_id), payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
    except (DiaEspecialNaoEncontradoError, DiaEspecialNaoEditavelError) as exc:
        raise _traduzir_dia_especial(exc) from exc


@router.delete("/dias-especiais/{dia_especial_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dia_especial(
    dia_especial_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        regra_expediente_service.remover_dia_especial(
            db, str(dia_especial_id), empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
    except (DiaEspecialNaoEncontradoError, DiaEspecialNaoEditavelError) as exc:
        raise _traduzir_dia_especial(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
