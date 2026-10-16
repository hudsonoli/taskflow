"""Tráfego V2 — Fase 2: métricas OPERACIONAIS (somente leitura).

`GET /trafego/operacional/agora` e `GET /trafego/operacional/gargalos`. TEMPO OPERACIONAL ≠ TEMPO PESSOAL: as duas rotas leem `demanda_status_intervalos`; nenhuma lê `sessoes_trabalho`.

## Autorização (sem permissão nova)
`require_trafego_gerenciar()` — a MESMA dependency que protege `/sessoes-trabalho` (piso `perfil_base ∈ {admin, gestor}` + permissão `trafego.gerenciar`; operador nunca passa, nem com concessão). Tenant:
a empresa vem SEMPRE do token; nenhum parâmetro de empresa existe nestas rotas.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.permissoes import require_trafego_gerenciar
from app.models.usuario import Usuario
from app.schemas.trafego_operacional import TrafegoOperacionalAgoraRead, TrafegoOperacionalGargalosRead
from app.services.trafego_operacional_service import (
    LIMITE_MAXIMO,
    LIMITE_PADRAO,
    EtapaNaoEncontradaError,
    PeriodoInvalidoError,
    TrafegoOperacionalService,
)

router = APIRouter(
    prefix="/trafego/operacional",
    tags=["trafego-operacional"],
    dependencies=[Depends(get_current_user_password_ready)],
)
service = TrafegoOperacionalService()


def _com_timezone(valor: datetime | None, campo: str) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is None or valor.tzinfo.utcoffset(valor) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{campo} deve incluir timezone")
    return valor.astimezone(timezone.utc)


def _uuid_opcional(valor: str | None, campo: str) -> str | None:
    if valor is None:
        return None
    try:
        UUID(valor)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{campo} inválido: não é um UUID") from exc
    return valor


@router.get("/agora", response_model=TrafegoOperacionalAgoraRead, response_model_by_alias=True)
def agora_operacional(
    limite: int = Query(default=LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_trafego_gerenciar()),
) -> TrafegoOperacionalAgoraRead:
    """Estado ATUAL + triagem: KPIs do escopo (planejada, em_execucao, pausada, bloqueada, aguardando_cliente) e a lista "em execução agora" (estado da DEMANDA — não é executor)."""
    return service.agora(db, empresa_id=current_user.empresa_id, limite=limite)


@router.get("/gargalos", response_model=TrafegoOperacionalGargalosRead, response_model_by_alias=True)
def gargalos_operacionais(
    inicio: datetime | None = Query(default=None),
    fim: datetime | None = Query(default=None),
    departamento_id: str | None = Query(default=None, alias="departamentoId"),
    cliente_id: str | None = Query(default=None, alias="clienteId"),
    projeto_id: str | None = Query(default=None, alias="projetoId"),
    workflow_etapa_id: str | None = Query(default=None, alias="workflowEtapaId"),
    limite: int = Query(default=LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_trafego_gerenciar()),
) -> TrafegoOperacionalGargalosRead:
    """Tempo operacional por etapa e estado no período (padrão: últimos 30 dias; máximo 90) + fila/WIP atual. Datas com timezone."""
    try:
        return service.gargalos(
            db,
            empresa_id=current_user.empresa_id,
            inicio=_com_timezone(inicio, "inicio"),
            fim=_com_timezone(fim, "fim"),
            departamento_id=_uuid_opcional(departamento_id, "departamentoId"),
            cliente_id=_uuid_opcional(cliente_id, "clienteId"),
            projeto_id=_uuid_opcional(projeto_id, "projetoId"),
            workflow_etapa_id=_uuid_opcional(workflow_etapa_id, "workflowEtapaId"),
            limite=limite,
        )
    except PeriodoInvalidoError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except EtapaNaoEncontradaError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
