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
from app.core.filtros_lista import parse_csv_enum, parse_csv_uuids
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.usuario import Usuario
from app.schemas.demanda_arquivo import ArquivoCentralRead
from app.services.demanda_arquivo_service import DemandaArquivoService

TIPOS_ARQUIVO = ("anexo", "layout", "link")
STATUS_LAYOUT_ARQUIVO = ("novo", "aprovado", "reprovado", "solicitar_alteracao")

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
    cliente_id_excluir: str | None = Query(default=None, alias="clienteIdExcluir"),
    projeto_id_excluir: str | None = Query(default=None, alias="projetoIdExcluir"),
    demanda_id_excluir: str | None = Query(default=None, alias="demandaIdExcluir"),
    tipo_excluir: str | None = Query(default=None, alias="tipoExcluir"),
    status_layout_excluir: str | None = Query(default=None, alias="statusExcluir"),
    usuario_id_excluir: str | None = Query(default=None, alias="usuarioIdExcluir"),
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
        cliente_ids=parse_csv_uuids(cliente_id, "clienteId"),
        projeto_ids=parse_csv_uuids(projeto_id, "projetoId"),
        demanda_ids=parse_csv_uuids(demanda_id, "demandaId"),
        tipos=parse_csv_enum(tipo, "tipo", TIPOS_ARQUIVO),
        status_layouts=parse_csv_enum(status_layout, "status", STATUS_LAYOUT_ARQUIVO),
        usuario_ids=parse_csv_uuids(usuario_id, "usuarioId"),
        cliente_ids_excluir=parse_csv_uuids(cliente_id_excluir, "clienteIdExcluir"),
        projeto_ids_excluir=parse_csv_uuids(projeto_id_excluir, "projetoIdExcluir"),
        demanda_ids_excluir=parse_csv_uuids(demanda_id_excluir, "demandaIdExcluir"),
        tipos_excluir=parse_csv_enum(tipo_excluir, "tipoExcluir", TIPOS_ARQUIVO),
        status_layouts_excluir=parse_csv_enum(status_layout_excluir, "statusExcluir", STATUS_LAYOUT_ARQUIVO),
        usuario_ids_excluir=parse_csv_uuids(usuario_id_excluir, "usuarioIdExcluir"),
        data_inicio=_normalize_datetime(data_inicio),
        data_fim=_normalize_datetime(data_fim),
        limit=limit,
        offset=offset,
        ocultar_remetente_de_sistema=not current_user.is_system_account,
    )
