"""Gerenciador central de Arquivos (migration 0036) — visão transversal sobre
`demanda_arquivos`, sem duplicação física: o mesmo registro que aparece dentro da Demanda
(`/demandas/{id}/arquivos`) aparece aqui, só com o contexto (Cliente/Projeto/Demanda/
Usuário) já resolvido na mesma consulta.

Escopo idêntico ao de Demanda — arquivo só aparece se a Demanda-mãe estiver no escopo de
quem pede (`resolver_escopo_demanda` + `DemandaRepository._predicado_escopo`, aplicados
dentro do SQL por `DemandaArquivoRepository.list_central`, nunca filtrados depois)."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.core.escopo import resolver_escopo_demanda
from app.core.filtros_lista import parse_csv_enum, parse_csv_uuids
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.usuario import Usuario
from app.repositories.demanda_arquivo_repository import FiltrosCentral
from app.schemas.arquivo_lote import (
    ArquivosLoteExclusaoRead,
    ArquivosLoteResumoRead,
    ArquivosLoteSelecao,
)
from app.schemas.demanda_arquivo import ArquivoCentralRead
from app.services.arquivo_lote_service import (
    ArquivoLoteFisicoAusenteError,
    ArquivoLoteLimiteError,
    ArquivoLoteNaoEncontradoError,
    ArquivoLoteService,
)
from app.services.demanda_arquivo_service import DemandaArquivoService

TIPOS_ARQUIVO = ("anexo", "layout", "link")
STATUS_LAYOUT_ARQUIVO = ("novo", "aprovado", "reprovado", "solicitar_alteracao")

router = APIRouter(
    prefix="/arquivos",
    tags=["arquivos"],
    dependencies=[Depends(get_current_user_password_ready)],
)
arquivo_service = DemandaArquivoService()
lote_service = ArquivoLoteService(arquivo_service=arquivo_service)


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


# ======================================================================================
# Operações em lote (Fase 8B) — seleção por IDs explícitos ou "todos os resultados do filtro".
# Sempre o escopo-BASE (o mesmo de `GET /arquivos`): tenant do token, escopo da Demanda e filtros aplicados no SQL. POST com corpo
# (nunca centenas de IDs na URL).
# ======================================================================================


def _filtros_da_selecao(selecao: ArquivosLoteSelecao) -> FiltrosCentral:
    """MESMOS parsers de `GET /arquivos` (CSV → UUID/enum, 422 em valor inválido): o universo do lote é o da listagem."""
    f = selecao.filtros
    contexto = selecao.contexto
    campos: dict = {
        "contexto_cliente_id": str(contexto.cliente_id) if contexto and contexto.cliente_id else None,
        "contexto_projeto_id": str(contexto.projeto_id) if contexto and contexto.projeto_id else None,
        "contexto_demanda_id": str(contexto.demanda_id) if contexto and contexto.demanda_id else None,
    }
    if f is not None:
        campos.update(
            search=f.search,
            cliente_ids=parse_csv_uuids(f.cliente_id, "clienteId"),
            projeto_ids=parse_csv_uuids(f.projeto_id, "projetoId"),
            demanda_ids=parse_csv_uuids(f.demanda_id, "demandaId"),
            tipos=parse_csv_enum(f.tipo, "tipo", TIPOS_ARQUIVO),
            status_layouts=parse_csv_enum(f.status, "status", STATUS_LAYOUT_ARQUIVO),
            usuario_ids=parse_csv_uuids(f.usuario_id, "usuarioId"),
            cliente_ids_excluir=parse_csv_uuids(f.cliente_id_excluir, "clienteIdExcluir"),
            projeto_ids_excluir=parse_csv_uuids(f.projeto_id_excluir, "projetoIdExcluir"),
            demanda_ids_excluir=parse_csv_uuids(f.demanda_id_excluir, "demandaIdExcluir"),
            tipos_excluir=parse_csv_enum(f.tipo_excluir, "tipoExcluir", TIPOS_ARQUIVO),
            status_layouts_excluir=parse_csv_enum(f.status_excluir, "statusExcluir", STATUS_LAYOUT_ARQUIVO),
            usuario_ids_excluir=parse_csv_uuids(f.usuario_id_excluir, "usuarioIdExcluir"),
            data_inicio=_normalize_datetime(f.data_inicio),
            data_fim=_normalize_datetime(f.data_fim),
        )
    return FiltrosCentral(**campos)


def _parametros_da_selecao(selecao: ArquivosLoteSelecao) -> dict:
    return {
        "filtros": _filtros_da_selecao(selecao),
        "ids": [str(i) for i in selecao.ids] if selecao.mode == "ids" else None,
        "excluir_ids": [str(i) for i in selecao.excluded_ids],
    }


def _tratar_erro_lote(exc: Exception) -> None:
    if isinstance(exc, ArquivoLoteNaoEncontradoError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ArquivoLoteLimiteError):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail={"code": "LIMITE_EXCEDIDO", "message": str(exc)}
        ) from exc
    if isinstance(exc, ArquivoLoteFisicoAusenteError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ARQUIVO_FISICO_AUSENTE", "message": str(exc), "quantidade": exc.quantidade},
        ) from exc
    raise exc


@router.post("/resumo-lote", response_model=ArquivosLoteResumoRead)
def resumo_lote(
    selecao: ArquivosLoteSelecao,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Quantos arquivos a seleção cobre (e quantos são links, o tamanho e os tetos). Em `all_filtered` agrega no SQL."""
    try:
        escopo = resolver_escopo_demanda(db, current_user)
        return lote_service.resumo(db, escopo=escopo, **_parametros_da_selecao(selecao))
    except Exception as exc:
        _tratar_erro_lote(exc)


def _remover_temporario(caminho: Path) -> None:
    caminho.unlink(missing_ok=True)


@router.post("/download-lote")
def download_lote(
    selecao: ArquivosLoteSelecao,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """ZIP dos arquivos selecionados (`application/zip`, `attachment`). Links não têm conteúdo e ficam de fora (contagem em
    `X-Lote-Links-Ignorados`). Qualquer ID não autorizado → 404 sem ZIP; arquivo físico ausente → 409 sem ZIP; acima dos tetos → 413."""
    try:
        escopo = resolver_escopo_demanda(db, current_user)
        zip_ = lote_service.preparar_zip(db, escopo=escopo, **_parametros_da_selecao(selecao))
    except Exception as exc:
        _tratar_erro_lote(exc)
    return FileResponse(
        path=zip_.caminho,
        media_type="application/zip",
        filename=zip_.nome,
        content_disposition_type="attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "X-Lote-Arquivos": str(zip_.arquivos),
            "X-Lote-Links-Ignorados": str(zip_.links_ignorados),
        },
        background=BackgroundTask(_remover_temporario, zip_.caminho),
    )


@router.post("/excluir-lote", response_model=ArquivosLoteExclusaoRead)
def excluir_lote(
    selecao: ArquivosLoteSelecao,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Mesma regra da exclusão individual (autenticado + Demanda no escopo-base), aplicada a TODOS antes de alterar qualquer coisa:
    se um não for autorizado, nenhum é excluído. Registros e eventos saem numa só transação; os arquivos físicos depois."""
    try:
        escopo = resolver_escopo_demanda(db, current_user)
        return lote_service.excluir(
            db, escopo=escopo, actor_usuario_id=current_user.id, **_parametros_da_selecao(selecao)
        )
    except Exception as exc:
        _tratar_erro_lote(exc)
