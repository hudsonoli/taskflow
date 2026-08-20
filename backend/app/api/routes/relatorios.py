"""Agregações para os Relatórios operacionais — leitura, admin/gestor (mesma fronteira de
`/eventos`, que hoje é quem realmente conhece contagem de evento por tipo/entidade).

`GET /relatorios/demandas/ajustes` existe porque Ajustes internos/Ajustes cliente/Refações
(Fase 2F.4) somem desde a Fase 2E.4, quando o `historico[]` embutido em Demanda saiu e os
eventos reais (`demanda.ajuste_interno_registrado` etc.) passaram a viver só em `eventos`, sem
endpoint agregado para lê-los por Projeto.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.relatorio import RelatorioAjustesProjetoRead
from app.services.projeto_service import ProjetoNotFoundError
from app.services.relatorio_service import RelatorioService

router = APIRouter(
    prefix="/relatorios",
    tags=["relatorios"],
    dependencies=[Depends(get_current_user_password_ready)],
)
relatorio_service = RelatorioService()


@router.get("/demandas/ajustes", response_model=RelatorioAjustesProjetoRead)
def get_ajustes_por_projeto(
    projeto_id: UUID = Query(alias="projetoId"),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        return relatorio_service.ajustes_por_projeto(
            db, empresa_id=current_user.empresa_id, projeto_id=str(projeto_id)
        )
    except ProjetoNotFoundError as exc:
        # Mesmo 404 para UUID inexistente e para Projeto de outra empresa — nunca 403, para
        # não confirmar a outro tenant que um UUID existe (ver RelatorioService).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
