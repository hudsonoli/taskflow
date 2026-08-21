"""Leitura operacional do expediente vigente — aberta a qualquer autenticado (Fase 2G.3).

Diferente de `/regra-expediente` (admin/gestor, edita a configuração), esta rota só informa o
ESTADO atual calculado pelo servidor: `dentroExpediente`, o instante usado no cálculo (já no
fuso da aplicação) e a tolerância de retomada. Existe para o frontend operacional (Kanban,
capacidade de Meu Departamento) parar de calcular expediente no relógio do navegador — a
mesma razão de `esta_dentro_expediente` já ser aplicada no servidor para bloquear
`em_execucao` (ver app/core/expediente.py). Nunca devolve a regra inteira: quem pode ver
`ativo`/janelas por dia é admin/gestor, em /regra-expediente.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.usuario import Usuario
from app.schemas.regra_expediente import EstadoExpedienteRead
from app.services.regra_expediente_service import RegraExpedienteService

router = APIRouter(prefix="/expediente", tags=["expediente"])
regra_expediente_service = RegraExpedienteService()


@router.get("/estado", response_model=EstadoExpedienteRead)
def get_estado_expediente(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    return regra_expediente_service.to_estado_read(db, empresa_id=current_user.empresa_id)
