"""Configuração administrativa de Regra de Expediente — singleton por Empresa (Fase 2G.3).

Sem POST/DELETE/list/{id}: é singleton, não coleção — GET sempre lê (criando o padrão inicial
na primeira vez, se ainda não existir) e PATCH sempre edita o único registro da Empresa do
usuário autenticado. Leitura operacional enxuta (usada por Kanban/UX, sem exigir admin/gestor)
fica em app/api/routes/expediente.py, rota separada — ver docstring de lá.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.regra_expediente import RegraExpedienteRead, RegraExpedienteUpdate
from app.services.regra_expediente_service import RegraExpedienteService

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
    regra = regra_expediente_service.atualizar(
        db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
    )
    return regra_expediente_service.to_read(db, regra)
