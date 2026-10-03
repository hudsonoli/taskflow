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

from app.core.escopo import resolver_escopo_demanda
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.relatorio import (
    RelatorioAjustesProjetoRead,
    RelatorioAnaliseProjetoRead,
    RelatorioColaboradorOpcaoRead,
    RelatorioFatiaRead,
    RelatorioPecasProjetoRead,
    RelatorioPerformanceColaboradorRead,
    RelatorioPontoSemanalRead,
    RelatorioSerieBarraRead,
)
from app.services.cliente_service import ClienteNotFoundError
from app.services.projeto_service import ProjetoNotFoundError
from app.services.relatorio_service import ColaboradorNotFoundError, RelatorioService

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


# D4A — Relatórios de Projeto server-side. Mesma autorização de `/demandas/ajustes`
# (`require_admin_or_gestor`, a que o menu de Relatórios já pressupunha): operador recebe 403,
# nunca um relatório escopado parcial. O escopo de Demanda é o normal de quem pede, resolvido
# pelo mecanismo único (`resolver_escopo_demanda`) — para admin/gestor, visão total.
@router.get("/projetos/analise", response_model=RelatorioAnaliseProjetoRead)
def get_analise_projeto(
    projeto_id: UUID = Query(alias="projetoId"),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    escopo = resolver_escopo_demanda(db, current_user)
    try:
        return relatorio_service.analise_projeto(db, escopo=escopo, projeto_id=str(projeto_id))
    except ProjetoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/projetos/pecas", response_model=RelatorioPecasProjetoRead)
def get_pecas_projeto(
    projeto_id: UUID = Query(alias="projetoId"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    escopo = resolver_escopo_demanda(db, current_user)
    try:
        return relatorio_service.pecas_projeto(
            db, escopo=escopo, projeto_id=str(projeto_id), limit=limit, offset=offset
        )
    except ProjetoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# D4B — Performance de colaborador e gráficos de Relatórios. Mesma autorização e mesmo escopo
# do D4A (`require_admin_or_gestor` + `resolver_escopo_demanda`); empresa sempre do token.
@router.get("/colaboradores", response_model=list[RelatorioColaboradorOpcaoRead])
def list_colaboradores(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    return relatorio_service.listar_colaboradores(db, empresa_id=current_user.empresa_id)


@router.get("/colaboradores/performance", response_model=RelatorioPerformanceColaboradorRead)
def get_performance_colaborador(
    colaborador_id: UUID = Query(alias="colaboradorId"),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    escopo = resolver_escopo_demanda(db, current_user)
    try:
        return relatorio_service.performance_colaborador(db, escopo=escopo, colaborador_id=str(colaborador_id))
    except ColaboradorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/graficos/abertas-por-projeto", response_model=list[RelatorioFatiaRead])
def get_abertas_por_projeto(
    cliente_id: UUID = Query(alias="clienteId"),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    escopo = resolver_escopo_demanda(db, current_user)
    try:
        return relatorio_service.abertas_por_projeto(db, escopo=escopo, cliente_id=str(cliente_id))
    except ClienteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/graficos/volume-por-colaborador", response_model=list[RelatorioSerieBarraRead])
def get_volume_por_projeto_e_colaborador(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    escopo = resolver_escopo_demanda(db, current_user)
    return relatorio_service.volume_por_projeto_e_colaborador(db, escopo=escopo)


@router.get("/graficos/volume-semanal", response_model=list[RelatorioPontoSemanalRead])
def get_volume_semanal(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    escopo = resolver_escopo_demanda(db, current_user)
    return relatorio_service.volume_semanal(db, escopo=escopo)
