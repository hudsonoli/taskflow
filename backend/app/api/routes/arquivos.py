"""Gerenciador central de Arquivos (migration 0036) — visão transversal sobre
`demanda_arquivos`, sem duplicação física: o mesmo registro que aparece dentro da Demanda
(`/demandas/{id}/arquivos`) aparece aqui, só com o contexto (Cliente/Projeto/Demanda/
Usuário) já resolvido na mesma consulta.

Escopo idêntico ao de Demanda — arquivo só aparece se a Demanda-mãe estiver no escopo de
quem pede (`resolver_escopo_demanda` + `DemandaRepository._predicado_escopo`, aplicados
dentro do SQL por `DemandaArquivoRepository.list_central`, nunca filtrados depois)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.escopo import resolver_escopo_demanda
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.usuario import Usuario
from app.schemas.demanda_arquivo import ArquivoCentralRead
from app.services.demanda_arquivo_service import DemandaArquivoService

router = APIRouter(
    prefix="/arquivos",
    tags=["arquivos"],
    dependencies=[Depends(get_current_user_password_ready)],
)
arquivo_service = DemandaArquivoService()


def _normalize_datetime(value: datetime | None) -> datetime | None:
    """Mesmo padrão de app/api/routes/eventos.py e sessoes_trabalho.py — duplicado de
    propósito (um helper compartilhado não existe ainda pra isso no projeto; ver
    diagnóstico do Gerenciador de Arquivos, item 24)."""
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filtros de data devem incluir timezone",
        )
    return value.astimezone(timezone.utc)


@router.get("", response_model=list[ArquivoCentralRead])
def listar_arquivos_central(
    search: str | None = Query(default=None),
    cliente_id: str | None = Query(default=None, alias="clienteId"),
    projeto_id: str | None = Query(default=None, alias="projetoId"),
    demanda_id: str | None = Query(default=None, alias="demandaId"),
    tipo: str | None = Query(default=None),
    status_layout: str | None = Query(default=None, alias="status"),
    usuario_id: str | None = Query(default=None, alias="usuarioId"),
    data_inicio: datetime | None = Query(default=None, alias="dataInicio"),
    data_fim: datetime | None = Query(default=None, alias="dataFim"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    escopo = resolver_escopo_demanda(db, current_user)
    return arquivo_service.list_central(
        db,
        escopo=escopo,
        search=search,
        cliente_id=cliente_id,
        projeto_id=projeto_id,
        demanda_id=demanda_id,
        tipo=tipo,
        status_layout=status_layout,
        usuario_id=usuario_id,
        data_inicio=_normalize_datetime(data_inicio),
        data_fim=_normalize_datetime(data_fim),
        limit=limit,
        offset=offset,
        ocultar_remetente_de_sistema=not current_user.is_system_account,
    )
