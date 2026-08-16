"""Histórico operacional de uma Demanda — leitura de `eventos`, escopada pela Demanda.

## Por que não é `GET /eventos`

`GET /eventos` é a trilha de auditoria administrativa (`require_admin_or_gestor`) — mostra
TODO evento da empresa, de qualquer entidade, para quem administra. Esta rota é outra coisa:
o histórico operacional de UMA Demanda específica, para quem tem acesso a ela — inclusive
Operador comum, que nunca deve alcançar `/eventos` global (ver
app/api/routes/eventos.py e docs da Fase 2E.4).

Reaproveita a mesma resolução de escopo de checklist/arquivos/comentários
(`resolver_escopo_demanda`): quem pode ver a Demanda, vê o histórico dela. Cross-tenant ou
fora do escopo é 404, nunca a lista de outra empresa nem 403 (que confirmaria a existência).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.escopo import resolver_escopo_demanda
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.usuario import Usuario
from app.schemas.demanda_historico import DemandaHistoricoEventoRead
from app.services.demanda_historico_service import DemandaHistoricoService
from app.services.demanda_service import DemandaNotFoundError, DemandaService

router = APIRouter(
    prefix="/demandas",
    tags=["demanda-historico"],
    dependencies=[Depends(get_current_user_password_ready)],
)
demanda_service = DemandaService()
historico_service = DemandaHistoricoService()


@router.get("/{demanda_id}/historico", response_model=list[DemandaHistoricoEventoRead])
def listar_historico(
    demanda_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        escopo = resolver_escopo_demanda(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
    except DemandaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    eventos = historico_service.listar(db, empresa_id=current_user.empresa_id, demanda_id=demanda.id)
    return [historico_service.to_read(evento) for evento in eventos]
