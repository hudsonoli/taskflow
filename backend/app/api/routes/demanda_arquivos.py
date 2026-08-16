"""Arquivos de Demanda — metadado em banco, conteúdo em disco (Fase 2E.3).

Substitui `uploads.py`: aquele router servia o conteúdo por caminho estático montado em
`/uploads/**` (`app.mount(..., StaticFiles(...))`, em `app/main.py`), acessível **sem token
nenhum** por quem soubesse a URL — ver docs/pendencias-arquiteturais.md, item 9. O mount foi
removido; baixar um arquivo agora exige o endpoint abaixo, que resolve a Demanda no escopo de
quem pede antes de tocar em disco. Não há mais caminho público para arquivo de Demanda.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.escopo import resolver_escopo_demanda
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.demanda import Demanda
from app.models.usuario import Usuario
from app.schemas.demanda_arquivo import DemandaArquivoRead
from app.services.demanda_arquivo_service import (
    DemandaArquivoExtensaoInvalidaError,
    DemandaArquivoMuitoGrandeError,
    DemandaArquivoNotFoundError,
    DemandaArquivoService,
    DemandaArquivoVazioError,
)
from app.services.demanda_service import DemandaNotFoundError, DemandaService

# Mesmo critério de acesso de checklist (ver app/api/routes/demanda_checklist.py): arquivo é
# operacional, aberto a qualquer autenticado dentro do escopo da própria Demanda.
router = APIRouter(
    prefix="/demandas",
    tags=["demanda-arquivos"],
    dependencies=[Depends(get_current_user_password_ready)],
)
demanda_service = DemandaService()
arquivo_service = DemandaArquivoService()


def handle_arquivo_error(exc: Exception) -> None:
    if isinstance(exc, (DemandaNotFoundError, DemandaArquivoNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(
        exc, (DemandaArquivoExtensaoInvalidaError, DemandaArquivoVazioError, DemandaArquivoMuitoGrandeError)
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


def _demanda_no_escopo(demanda_id: UUID, current_user: Usuario, db: Session) -> Demanda:
    escopo = resolver_escopo_demanda(db, current_user)
    return demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)


@router.get("/{demanda_id}/arquivos", response_model=list[DemandaArquivoRead])
def listar_arquivos(
    demanda_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        arquivos = arquivo_service.listar(db, demanda.id)
        return [arquivo_service.to_read(arquivo) for arquivo in arquivos]
    except Exception as exc:
        handle_arquivo_error(exc)


@router.post(
    "/{demanda_id}/arquivos", response_model=DemandaArquivoRead, status_code=status.HTTP_201_CREATED
)
async def upload_arquivo(
    demanda_id: UUID,
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        arquivo = await arquivo_service.upload(db, demanda, file, actor_usuario_id=current_user.id)
        return arquivo_service.to_read(arquivo)
    except Exception as exc:
        handle_arquivo_error(exc)


@router.get("/{demanda_id}/arquivos/{arquivo_id}/download")
def download_arquivo(
    demanda_id: UUID,
    arquivo_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Único caminho de leitura de conteúdo. Resolve a Demanda no escopo de quem pede,
    confirma que o arquivo pertence a ela e só então lê o caminho — sempre reconstruído a
    partir de `demanda_id`/`nome_fisico` já validados, nunca de entrada do cliente."""
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        arquivo, caminho = arquivo_service.obter_para_download(db, demanda, str(arquivo_id))
        return FileResponse(
            path=caminho,
            media_type=arquivo.content_type or "application/octet-stream",
            filename=arquivo.nome_original,
            content_disposition_type="inline",
        )
    except Exception as exc:
        handle_arquivo_error(exc)


@router.delete("/{demanda_id}/arquivos/{arquivo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_arquivo(
    demanda_id: UUID,
    arquivo_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        arquivo_service.excluir(db, demanda, str(arquivo_id), actor_usuario_id=current_user.id)
    except Exception as exc:
        handle_arquivo_error(exc)
