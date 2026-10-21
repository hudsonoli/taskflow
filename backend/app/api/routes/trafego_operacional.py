"""Tráfego V2 — Fase 2: métricas OPERACIONAIS (somente leitura).

`GET /trafego/operacional/agora`, `GET /trafego/operacional/gargalos` e `GET /trafego/operacional/fluxo` (estado atual por definição de etapa, com cards). TEMPO OPERACIONAL ≠ TEMPO PESSOAL: as duas rotas leem `demanda_status_intervalos`; nenhuma lê `sessoes_trabalho`.
`GET /trafego/operacional/carga` (11B.2B-B): carga SEMANAL planejada × capacidade (estimativa + janela planejada × expediente); não lê `sessoes_trabalho` nem `demanda_status_intervalos`.

## Autorização (sem permissão nova)
`require_trafego_gerenciar()` — a MESMA dependency que protege `/sessoes-trabalho` (piso `perfil_base ∈ {admin, gestor}` + permissão `trafego.gerenciar`; operador nunca passa, nem com concessão). Tenant:
a empresa vem SEMPRE do token; nenhum parâmetro de empresa existe nestas rotas.
"""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.permissoes import require_trafego_gerenciar
from app.models.usuario import Usuario
from app.schemas.trafego_carga import TrafegoCargaRead
from app.schemas.trafego_fluxo import TrafegoOperacionalFluxoRead
from app.schemas.trafego_operacional import TrafegoOperacionalAgoraRead, TrafegoOperacionalGargalosRead
from app.services.carga_operacional_service import (
    LIMITE_MAXIMO as CARGA_LIMITE_MAXIMO,
    LIMITE_PADRAO as CARGA_LIMITE_PADRAO,
    AlvoNaoEncontradoError,
    CargaOperacionalService,
    FiltroInvalidoError,
    SemanaPassadaNaoSuportadaError,
)
from app.services.trafego_operacional_service import (
    FLUXO_LIMITE_DEFINICOES_MAXIMO,
    FLUXO_LIMITE_DEFINICOES_PADRAO,
    FLUXO_LIMITE_ITENS_MAXIMO,
    FLUXO_LIMITE_ITENS_PADRAO,
    FLUXO_PERIODO_DIAS_PADRAO,
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
carga_service = CargaOperacionalService()


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


@router.get("/fluxo", response_model=TrafegoOperacionalFluxoRead, response_model_by_alias=True)
def fluxo_operacional(
    periodo_dias: int = Query(default=FLUXO_PERIODO_DIAS_PADRAO, ge=1, le=90, alias="periodoDias", description="Janela (dias, até agora) das métricas de TEMPO. WIP e itens são sempre o estado atual."),
    departamento_id: str | None = Query(default=None, alias="departamentoId", description="Só definições cujo conjunto de departamentos inclui este; métricas, itens e totais respeitam o mesmo filtro."),
    limite_definicoes: int = Query(default=FLUXO_LIMITE_DEFINICOES_PADRAO, ge=1, le=FLUXO_LIMITE_DEFINICOES_MAXIMO, alias="limiteDefinicoes"),
    limite_itens_por_definicao: int = Query(default=FLUXO_LIMITE_ITENS_PADRAO, ge=1, le=FLUXO_LIMITE_ITENS_MAXIMO, alias="limiteItensPorDefinicao"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_trafego_gerenciar()),
) -> TrafegoOperacionalFluxoRead:
    """Fluxo POR ETAPA: Demandas abertas agrupadas pela DEFINIÇÃO semântica da etapa atual (identidade do servidor, a mesma de Gargalos), com métricas operacionais, totais reais e cards. Somente leitura."""
    return service.fluxo(
        db,
        empresa_id=current_user.empresa_id,
        periodo_dias=periodo_dias,
        departamento_id=_uuid_opcional(departamento_id, "departamentoId"),
        limite_definicoes=limite_definicoes,
        limite_itens=limite_itens_por_definicao,
    )


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


@router.get("/carga", response_model=TrafegoCargaRead, response_model_by_alias=True)
def carga_operacional(
    semana: date | None = Query(default=None, description="Qualquer dia da semana desejada (YYYY-MM-DD); normalizado para a segunda-feira no fuso da empresa. Omitido = semana atual."),
    departamento_id: str | None = Query(default=None, alias="departamentoId"),
    usuario_id: str | None = Query(default=None, alias="usuarioId"),
    detalhe: str | None = Query(default=None, description="`usuario` ou `departamento`: devolve as etapas que compõem o número (exige o id correspondente)."),
    limite: int = Query(default=CARGA_LIMITE_PADRAO, ge=1, le=CARGA_LIMITE_MAXIMO),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_trafego_gerenciar()),
) -> TrafegoCargaRead:
    """Carga SEMANAL planejada × capacidade por pessoa e departamento (v1: semana atual e futuras). Somente leitura; filtros recortam o resultado sem recalcular a divisão."""
    try:
        return carga_service.carga(
            db,
            empresa_id=current_user.empresa_id,
            semana=semana,
            departamento_id=_uuid_opcional(departamento_id, "departamentoId"),
            usuario_id=_uuid_opcional(usuario_id, "usuarioId"),
            detalhe=detalhe,
            limite=limite,
        )
    except SemanaPassadaNaoSuportadaError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": exc.codigo, "message": str(exc)}) from exc
    except FiltroInvalidoError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": exc.codigo, "message": str(exc)}) from exc
    except AlvoNaoEncontradoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
