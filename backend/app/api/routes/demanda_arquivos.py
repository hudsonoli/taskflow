"""Arquivos de Demanda — metadado em banco, conteúdo em disco (Fase 2E.3).

Substitui `uploads.py`: aquele router servia o conteúdo por caminho estático montado em
`/uploads/**` (`app.mount(..., StaticFiles(...))`, em `app/main.py`), acessível **sem token
nenhum** por quem soubesse a URL — ver docs/pendencias-arquiteturais.md, item 9. O mount foi
removido; baixar um arquivo agora exige o endpoint abaixo, que resolve a Demanda no escopo de
quem pede antes de tocar em disco. Não há mais caminho público para arquivo de Demanda.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.escopo_leitura import EscopoLeitura, demanda_com_acesso_de_workflow, escopo_para_leitura
from app.core.identidade_sistema import ids_de_contas_de_sistema
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.domain.aprovacao_externa import ArquivoVinculadoAprovacaoExternaError
from app.models.demanda import Demanda
from app.models.usuario import Usuario
from app.schemas.demanda_arquivo import (
    DemandaArquivoLinkCreate,
    DemandaArquivoRead,
    DemandaArquivoStatusLayoutUpdate,
)
from app.services.demanda_arquivo_service import (
    DemandaArquivoConteudoInvalidoError,
    DemandaArquivoExtensaoInvalidaError,
    DemandaArquivoMuitoGrandeError,
    DemandaArquivoNotFoundError,
    DemandaArquivoSemConteudoFisicoError,
    DemandaArquivoService,
    DemandaArquivoStatusLayoutForaDeTipoError,
    DemandaArquivoStatusLayoutInvalidoError,
    DemandaArquivoTipoInvalidoError,
    DemandaArquivoUrlInvalidaError,
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
    if isinstance(exc, ArquivoVinculadoAprovacaoExternaError):
        # Fase 9B: evidência de aprovação externa (em aberto ou decidida) não se exclui
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": exc.codigo, "message": str(exc)}
        ) from exc
    if isinstance(exc, (DemandaNotFoundError, DemandaArquivoNotFoundError, DemandaArquivoSemConteudoFisicoError)):
        # Link sem conteúdo físico recebe o mesmo 404 de "arquivo não encontrado" pelo
        # endpoint de download — não existe conteúdo pra baixar, mesma família de resposta.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(
        exc,
        (
            DemandaArquivoExtensaoInvalidaError,
            DemandaArquivoVazioError,
            DemandaArquivoMuitoGrandeError,
            DemandaArquivoConteudoInvalidoError,
            DemandaArquivoTipoInvalidoError,
            DemandaArquivoUrlInvalidaError,
            DemandaArquivoStatusLayoutForaDeTipoError,
            DemandaArquivoStatusLayoutInvalidoError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


def _demanda_no_escopo(
    demanda_id: UUID,
    current_user: Usuario,
    db: Session,
    escopo_leitura: EscopoLeitura | None = None,
    *,
    leitura: bool = False,
) -> Demanda:
    # `escopo_leitura` só é passado pelos GET (lista e download, leitura pela Pauta global); escrita usa sempre o escopo-base.
    # `leitura=True` (só GET de lista/download): além do escopo-base, vale o escopo DERIVADO da etapa atual do Workflow (Fase 8C.1).
    if leitura:
        return demanda_com_acesso_de_workflow(db, current_user, str(demanda_id), demanda_service, escopo_leitura)[0]
    escopo = escopo_para_leitura(db, current_user, escopo_leitura)
    return demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)


@router.get("/{demanda_id}/arquivos", response_model=list[DemandaArquivoRead])
def listar_arquivos(
    demanda_id: UUID,
    escopo: EscopoLeitura | None = Query(default=None),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db, escopo, leitura=True)
        arquivos = arquivo_service.listar(db, demanda.id)
        sistema = (
            set()
            if current_user.is_system_account
            else ids_de_contas_de_sistema(db, (arquivo.enviado_por_usuario_id for arquivo in arquivos))
        )
        return [
            arquivo_service.to_read(arquivo, remetente_sistema=arquivo.enviado_por_usuario_id in sistema)
            for arquivo in arquivos
        ]
    except Exception as exc:
        handle_arquivo_error(exc)


@router.post(
    "/{demanda_id}/arquivos", response_model=DemandaArquivoRead, status_code=status.HTTP_201_CREATED
)
async def upload_arquivo(
    demanda_id: UUID,
    file: UploadFile = File(...),
    # multipart, não JSON — por isso Form(), não um schema Pydantic no corpo. Default "anexo"
    # preserva 100% o contrato de quem já chama sem mandar `tipo` (frontend atual, testes
    # legados). "link" nunca é aceito aqui — ver DemandaArquivoService.upload.
    tipo: str = Form(default="anexo"),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        arquivo = await arquivo_service.upload(db, demanda, file, tipo=tipo, actor_usuario_id=current_user.id)
        return arquivo_service.to_read(arquivo)
    except Exception as exc:
        handle_arquivo_error(exc)


@router.post(
    "/{demanda_id}/arquivos/link", response_model=DemandaArquivoRead, status_code=status.HTTP_201_CREATED
)
def criar_link(
    demanda_id: UUID,
    payload: DemandaArquivoLinkCreate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Registro `tipo='link'` — mesmo escopo/tenant/autorização do upload físico, sem
    tocar em disco. Endpoint separado de propósito: nada do fluxo de arquivo físico
    (extensão, assinatura, tamanho, nome_fisico) se aplica aqui."""
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        arquivo = arquivo_service.criar_link(
            db,
            demanda,
            titulo=payload.titulo,
            url=payload.url,
            descricao=payload.descricao,
            actor_usuario_id=current_user.id,
        )
        return arquivo_service.to_read(arquivo)
    except Exception as exc:
        handle_arquivo_error(exc)


@router.patch("/{demanda_id}/arquivos/{arquivo_id}", response_model=DemandaArquivoRead)
def atualizar_status_layout(
    demanda_id: UUID,
    arquivo_id: UUID,
    payload: DemandaArquivoStatusLayoutUpdate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Só altera `statusLayout`, só em arquivo `tipo='layout'` — não é um update genérico de
    arquivo (ver DemandaArquivoService.atualizar_status_layout)."""
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db)
        arquivo = arquivo_service.atualizar_status_layout(
            db,
            demanda,
            str(arquivo_id),
            status_layout=payload.status_layout,
            actor_usuario_id=current_user.id,
        )
        return arquivo_service.to_read(arquivo)
    except Exception as exc:
        handle_arquivo_error(exc)


@router.get("/{demanda_id}/arquivos/{arquivo_id}/download")
def download_arquivo(
    demanda_id: UUID,
    arquivo_id: UUID,
    escopo: EscopoLeitura | None = Query(default=None),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Único caminho de leitura de conteúdo. Resolve a Demanda no escopo de quem pede,
    confirma que o arquivo pertence a ela e só então lê o caminho — sempre reconstruído a
    partir de `demanda_id`/`nome_fisico` já validados, nunca de entrada do cliente.

    Fase S1-B: `media_type`/disposition vêm de `resolver_download_seguro`, que valida a
    assinatura real dos bytes contra a extensão — nunca de `arquivo.content_type` — e
    protegem igualmente uploads novos e registros legados (ver docstring do helper).
    `X-Content-Type-Options: nosniff` em toda resposta: mesmo com o MIME já correto, evita
    que um navegador mais antigo tente adivinhar outro tipo por conta própria."""
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db, escopo, leitura=True)
        arquivo, caminho = arquivo_service.obter_para_download(db, demanda, str(arquivo_id))
        media_type, inline = arquivo_service.resolver_download_seguro(arquivo.nome_fisico, caminho)
        return FileResponse(
            path=caminho,
            media_type=media_type,
            filename=arquivo.nome_original,
            content_disposition_type="inline" if inline else "attachment",
            headers={"X-Content-Type-Options": "nosniff"},
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
