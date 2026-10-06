"""Personalização visual da Empresa (logo, cores, tema) — singleton por Empresa, aplicada a todos
os usuários dela. Dois routers:

- `/configuracoes/personalizacao` (administrativo): mesma autoridade de `/configuracoes/email`
  (`require_admin_or_gestor` + senha em dia). A Empresa vem SEMPRE do token — nenhum `empresaId` é
  aceito do cliente.
- `/personalizacao/publica` (sem autenticação): o branding precisa existir antes do login. Devolve
  SOMENTE cores, tema e a existência/versão do logo — nenhum id, path ou configuração interna — e
  código de empresa desconhecido recebe os padrões (não revela quais códigos existem).
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.configuracao_personalizacao import PersonalizacaoRead, PersonalizacaoUpdate
from app.services.configuracao_personalizacao_service import (
    LOGO_MAX_BYTES,
    ConfiguracaoPersonalizacaoService,
    PersonalizacaoLogoInvalidoError,
    PersonalizacaoLogoMuitoGrandeError,
    PersonalizacaoLogoNaoEncontradoError,
)

router = APIRouter(
    prefix="/configuracoes/personalizacao",
    tags=["configuracoes-personalizacao"],
    dependencies=[Depends(get_current_user_password_ready)],
)
router_publico = APIRouter(prefix="/personalizacao", tags=["personalizacao-publica"])
personalizacao_service = ConfiguracaoPersonalizacaoService()


def handle_logo_error(exc: Exception) -> None:
    if isinstance(exc, PersonalizacaoLogoMuitoGrandeError):
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    if isinstance(exc, PersonalizacaoLogoInvalidoError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if isinstance(exc, PersonalizacaoLogoNaoEncontradoError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=PersonalizacaoRead)
def get_personalizacao(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    return personalizacao_service.get_ou_default(db, empresa_id=current_user.empresa_id)


@router.patch("", response_model=PersonalizacaoRead)
def atualizar_personalizacao(
    payload: PersonalizacaoUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    return personalizacao_service.atualizar(db, empresa_id=current_user.empresa_id, payload=payload)


@router.delete("", response_model=PersonalizacaoRead)
def restaurar_padrao_personalizacao(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    """Restaurar padrão: remove logo, cores e tema personalizados desta Empresa."""
    return personalizacao_service.restaurar_padrao(db, empresa_id=current_user.empresa_id)


@router.post("/logo", response_model=PersonalizacaoRead)
def enviar_logo(
    arquivo: UploadFile = File(...),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    # Lê no máximo LIMITE + 1 byte: basta para saber que estourou, sem trazer um upload gigante
    # inteiro para a memória.
    conteudo = arquivo.file.read(LOGO_MAX_BYTES + 1)
    try:
        return personalizacao_service.salvar_logo(
            db,
            empresa_id=current_user.empresa_id,
            conteudo=conteudo,
            nome_arquivo=arquivo.filename,
            content_type=arquivo.content_type,
        )
    except Exception as exc:
        handle_logo_error(exc)


@router.delete("/logo", response_model=PersonalizacaoRead)
def remover_logo(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    return personalizacao_service.remover_logo(db, empresa_id=current_user.empresa_id)


@router_publico.get("/publica", response_model=PersonalizacaoRead)
def get_personalizacao_publica(
    empresa_codigo: str = Query(alias="empresaCodigo", min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    return personalizacao_service.get_publico(db, empresa_codigo=empresa_codigo)


@router_publico.get("/publica/logo")
def get_logo_publico(
    empresa_codigo: str = Query(alias="empresaCodigo", min_length=1, max_length=64),
    v: str | None = Query(default=None, max_length=32),
    db: Session = Depends(get_db),
):
    """Serve o logo com Content-Type canônico (do banco, gravado a partir dos bytes validados),
    `nosniff` e sem expor o caminho interno. URL com a versão correta (`v`) é imutável e pode ser
    guardada para sempre; sem versão (ou versão antiga) o navegador precisa revalidar."""
    try:
        caminho, mime, versao = personalizacao_service.ler_logo_publico(db, empresa_codigo=empresa_codigo)
    except PersonalizacaoLogoNaoEncontradoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo não encontrado") from exc
    cache = "public, max-age=31536000, immutable" if v and v == versao else "no-cache"
    return FileResponse(
        caminho,
        media_type=mime,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": cache, "Content-Disposition": "inline"},
    )
