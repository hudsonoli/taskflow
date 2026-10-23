"""Pauta operacional por ETAPA (P1_PAUTA_COLABORADOR) — `GET /pauta/operacional`, somente leitura.

Autorização = a da Pauta global (`pode_visualizar_pauta_global`: Atendimento, Head ou Gestão/Admin; operador comum recebe 403). Tenant sempre do token. Sem permissão nova e sem escrita.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.escopo import pode_visualizar_pauta_global
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.usuario import Usuario
from app.schemas.pauta_operacional import PautaOperacionalRead
from app.services.pauta_operacional_service import PautaOperacionalService, PeriodoInvalidoError

router = APIRouter(prefix="/pauta", tags=["pauta-operacional"], dependencies=[Depends(get_current_user_password_ready)])
service = PautaOperacionalService()

_PRIORIDADES = {"baixa", "media", "alta"}
_MAX_VALORES = 50


def _lista_uuid(valor: str | None, campo: str) -> list[str]:
    """CSV de UUIDs (a mesma convenção dos filtros da lista de Demandas)."""
    if not valor:
        return []
    itens = [parte.strip() for parte in valor.split(",") if parte.strip()]
    if len(itens) > _MAX_VALORES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{campo}: no máximo {_MAX_VALORES} valores")
    for item in itens:
        try:
            UUID(item)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{campo} inválido: não é um UUID") from exc
    return itens


@router.get("/operacional", response_model=PautaOperacionalRead, response_model_by_alias=True)
def pauta_operacional(
    inicio: date | None = Query(default=None, description="Início do período (data do calendário da empresa). Padrão: segunda-feira da semana atual."),
    fim: date | None = Query(default=None, description="Fim do período, inclusivo. Padrão: 4 semanas a partir do início. Máximo de 92 dias."),
    usuario_ids: str | None = Query(default=None, alias="usuarioIds", description="CSV. Responsabilidade EFETIVA da etapa (não o responsável geral bruto)."),
    departamento_ids: str | None = Query(default=None, alias="departamentoIds", description="CSV. Departamento da responsabilidade EFETIVA da etapa."),
    cliente_ids: str | None = Query(default=None, alias="clienteIds"),
    projeto_ids: str | None = Query(default=None, alias="projetoIds"),
    prioridades: str | None = Query(default=None, description="CSV de baixa|media|alta."),
    busca: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user_password_ready),
) -> PautaOperacionalRead:
    """Itens por ETAPA com responsabilidade efetiva e janela planejada (geometria = só o planejamento; prazo é informação)."""
    if not pode_visualizar_pauta_global(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A Pauta global é restrita a Atendimento, Heads e Gestão")
    prioridades_lista = [parte.strip() for parte in (prioridades or "").split(",") if parte.strip()]
    if any(valor not in _PRIORIDADES for valor in prioridades_lista):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="prioridades inválidas")
    try:
        return service.pauta(
            db,
            empresa_id=current_user.empresa_id,
            inicio=inicio,
            fim=fim,
            usuario_ids=_lista_uuid(usuario_ids, "usuarioIds"),
            departamento_ids=_lista_uuid(departamento_ids, "departamentoIds"),
            cliente_ids=_lista_uuid(cliente_ids, "clienteIds"),
            projeto_ids=_lista_uuid(projeto_ids, "projetoIds"),
            prioridades=prioridades_lista,
            busca=busca,
        )
    except PeriodoInvalidoError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
