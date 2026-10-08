"""Administração da Plataforma — `/plataforma/*` (Fase 1B).

Autoridade separada do RBAC tenant: todas as rotas daqui (exceto `POST /sessao` e `GET /acesso`, que partem da sessão
TENANT do próprio usuário) exigem `require_platform_admin` — token `tipo="plataforma"` + linha ativa em
`administradores_plataforma`, reconferida a cada requisição. Nenhuma rota usa `get_current_user`/perfil tenant, e o
token de plataforma não entra em nenhuma rota tenant.

Escopo: cadastro/edição/(in)ativação de empresas, branding de qualquer empresa, usuários (metadados) e criação de
Gestor. NÃO há suporte/impersonação, nem DELETE de empresa (empresa nunca é apagada). Ver aviso
SEGUNDO_TENANT_GO_LIVE_BLOQUEADO em `app/services/plataforma_service.py`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.routes.configuracao_personalizacao import handle_logo_error
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.plataforma import ContextoPlataforma, require_platform_admin
from app.models.usuario import Usuario
from app.schemas.configuracao_personalizacao import PersonalizacaoRead, PersonalizacaoUpdate
from app.schemas.empresa import EmpresaCreate, EmpresaInativar, EmpresaUpdate
from app.schemas.plataforma_dashboard import PlataformaDashboardRead
from app.schemas.plataforma import (
    PlataformaAcessoRead,
    PlataformaEmpresaRead,
    PlataformaGestorCreate,
    PlataformaGestorCriadoRead,
    PlataformaMeRead,
    PlataformaSessaoRead,
    PlataformaUsuarioRead,
)
from app.services.configuracao_personalizacao_service import LOGO_MAX_BYTES, PersonalizacaoLogoNaoEncontradoError
from app.services.empresa_service import (
    EmpresaConflictError,
    EmpresaHospedaPlataformaError,
    EmpresaInvalidTransitionError,
    EmpresaNotFoundError,
)
from app.services.plataforma_dashboard_service import PlataformaDashboardService
from app.services.plataforma_service import (
    PlataformaAcessoNegadoError,
    PlataformaGestorSenhaError,
    PlataformaService,
    PlataformaUsuarioNaoElegivelError,
    PlataformaUsuarioNaoEncontradoError,
)
from app.services.usuario_service import UsuarioArquivadoConflictError, UsuarioConflictError, UsuarioInvalidEmpresaError

router = APIRouter(prefix="/plataforma", tags=["plataforma"])
plataforma_service = PlataformaService()
plataforma_dashboard_service = PlataformaDashboardService()


def _tratar_erro(exc: Exception) -> None:
    if isinstance(exc, (EmpresaNotFoundError, PlataformaUsuarioNaoEncontradoError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PlataformaUsuarioNaoElegivelError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, (EmpresaConflictError, EmpresaInvalidTransitionError, EmpresaHospedaPlataformaError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, (UsuarioConflictError, UsuarioArquivadoConflictError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um usuário com este e-mail nesta empresa.") from exc
    if isinstance(exc, UsuarioInvalidEmpresaError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, PlataformaGestorSenhaError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    raise exc


# --------------------------------------------------------------------------------------
# Sessão de plataforma — parte da sessão TENANT (tf_session) do próprio usuário
# --------------------------------------------------------------------------------------


@router.get("/acesso", response_model=PlataformaAcessoRead)
def acesso(current_user: Usuario = Depends(get_current_user_password_ready), db: Session = Depends(get_db)):
    """Fonte de verdade da UI para mostrar (ou não) a entrada "Administração da Plataforma" — nunca e-mail/perfil."""
    return PlataformaAcessoRead(administradorPlataforma=plataforma_service.administrador_ativo_de(db, current_user) is not None)


@router.post("/sessao", response_model=PlataformaSessaoRead)
def iniciar_sessao(current_user: Usuario = Depends(get_current_user_password_ready), db: Session = Depends(get_db)):
    """Troca a sessão tenant válida por um token de plataforma curto. Quem não é administrador ativo recebe 403."""
    try:
        return plataforma_service.emitir_sessao(db, current_user)
    except PlataformaAcessoNegadoError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado") from exc


@router.get("/me", response_model=PlataformaMeRead)
def me(ctx: ContextoPlataforma = Depends(require_platform_admin)):
    return plataforma_service.me(ctx.administrador, ctx.usuario)


# --------------------------------------------------------------------------------------
# Dashboard (métricas agregadas de adoção/uso — nenhum conteúdo operacional)
# --------------------------------------------------------------------------------------


@router.get("/dashboard", response_model=PlataformaDashboardRead)
def dashboard(ctx: ContextoPlataforma = Depends(require_platform_admin), db: Session = Depends(get_db)):
    """Resumo global + uso por empresa + "precisa de atenção". Só contagens e datas de acesso: nunca nomes de usuários,
    clientes, demandas, comentários ou documentos. Exclusivo do Administrador da Plataforma."""
    return plataforma_dashboard_service.montar(db)


# --------------------------------------------------------------------------------------
# Empresas
# --------------------------------------------------------------------------------------


@router.get("/empresas", response_model=list[PlataformaEmpresaRead])
def listar_empresas(
    status_empresa: str | None = Query(default=None, alias="status", pattern="^(ativa|inativa|arquivada)$"),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    return plataforma_service.listar_empresas(db, status=status_empresa, search=search, limit=limit, offset=offset)


@router.post("/empresas", response_model=PlataformaEmpresaRead, status_code=status.HTTP_201_CREATED)
def criar_empresa(
    dados: EmpresaCreate,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.criar_empresa(db, dados, ator=ctx.usuario)
    except Exception as exc:
        _tratar_erro(exc)


@router.get("/empresas/{empresa_id}", response_model=PlataformaEmpresaRead)
def obter_empresa(
    empresa_id: UUID,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.obter_empresa(db, str(empresa_id))
    except Exception as exc:
        _tratar_erro(exc)


@router.patch("/empresas/{empresa_id}", response_model=PlataformaEmpresaRead)
def atualizar_empresa(
    empresa_id: UUID,
    dados: EmpresaUpdate,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.atualizar_empresa(db, str(empresa_id), dados, ator=ctx.usuario)
    except Exception as exc:
        _tratar_erro(exc)


@router.post("/empresas/{empresa_id}/inativar", response_model=PlataformaEmpresaRead)
def inativar_empresa(
    empresa_id: UUID,
    dados: EmpresaInativar | None = None,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.inativar_empresa(
            db, str(empresa_id), motivo=dados.motivo_inativacao if dados else None, ator=ctx.usuario
        )
    except Exception as exc:
        _tratar_erro(exc)


@router.post("/empresas/{empresa_id}/reativar", response_model=PlataformaEmpresaRead)
def reativar_empresa(
    empresa_id: UUID,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.reativar_empresa(db, str(empresa_id), ator=ctx.usuario)
    except Exception as exc:
        _tratar_erro(exc)


# --------------------------------------------------------------------------------------
# Personalização (branding) de qualquer empresa — mesmo serviço e mesma validação do tenant
# --------------------------------------------------------------------------------------


@router.get("/empresas/{empresa_id}/personalizacao", response_model=PersonalizacaoRead)
def obter_personalizacao(
    empresa_id: UUID,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.obter_personalizacao(db, str(empresa_id))
    except Exception as exc:
        _tratar_erro(exc)


@router.patch("/empresas/{empresa_id}/personalizacao", response_model=PersonalizacaoRead)
def atualizar_personalizacao(
    empresa_id: UUID,
    dados: PersonalizacaoUpdate,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.atualizar_personalizacao(db, str(empresa_id), dados, ator=ctx.usuario)
    except Exception as exc:
        _tratar_erro(exc)


@router.delete("/empresas/{empresa_id}/personalizacao", response_model=PersonalizacaoRead)
def restaurar_personalizacao(
    empresa_id: UUID,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.restaurar_personalizacao(db, str(empresa_id), ator=ctx.usuario)
    except Exception as exc:
        _tratar_erro(exc)


@router.get("/empresas/{empresa_id}/personalizacao/logo")
def obter_logo(
    empresa_id: UUID,
    v: str | None = Query(default=None, max_length=32),
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Bytes do logo da empresa (pré-visualização no painel). Content-Type canônico gravado do upload validado,
    `nosniff` e nenhum caminho interno exposto — a mesma resposta do endpoint público do tenant."""
    try:
        caminho, mime, versao = plataforma_service.ler_logo(db, str(empresa_id))
    except EmpresaNotFoundError as exc:
        _tratar_erro(exc)
    except PersonalizacaoLogoNaoEncontradoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo não encontrado") from exc
    cache = "private, max-age=31536000, immutable" if v and v == versao else "no-cache"
    return FileResponse(
        caminho,
        media_type=mime,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": cache, "Content-Disposition": "inline"},
    )


@router.post("/empresas/{empresa_id}/personalizacao/logo", response_model=PersonalizacaoRead)
def enviar_logo(
    empresa_id: UUID,
    arquivo: UploadFile = File(...),
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    # Mesmas validações do tenant (PNG/GIF por bytes reais, limite de tamanho, chave de storage gerada): a leitura é
    # limitada a LIMITE + 1 byte, o suficiente para saber que estourou sem trazer um upload gigante para a memória.
    conteudo = arquivo.file.read(LOGO_MAX_BYTES + 1)
    try:
        return plataforma_service.enviar_logo(
            db,
            str(empresa_id),
            conteudo=conteudo,
            nome_arquivo=arquivo.filename,
            content_type=arquivo.content_type,
            ator=ctx.usuario,
        )
    except Exception as exc:
        if isinstance(exc, EmpresaNotFoundError):
            _tratar_erro(exc)
        handle_logo_error(exc)


@router.delete("/empresas/{empresa_id}/personalizacao/logo", response_model=PersonalizacaoRead)
def remover_logo(
    empresa_id: UUID,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.remover_logo(db, str(empresa_id), ator=ctx.usuario)
    except Exception as exc:
        _tratar_erro(exc)


# --------------------------------------------------------------------------------------
# Usuários da empresa (metadados) e Gestor
# --------------------------------------------------------------------------------------


@router.get("/empresas/{empresa_id}/usuarios", response_model=list[PlataformaUsuarioRead])
def listar_usuarios(
    empresa_id: UUID,
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    try:
        return plataforma_service.listar_usuarios(db, str(empresa_id), search=search, limit=limit, offset=offset)
    except Exception as exc:
        _tratar_erro(exc)


@router.get("/empresas/{empresa_id}/candidatos-gestor", response_model=list[PlataformaUsuarioRead])
def listar_candidatos_gestor(
    empresa_id: UUID,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Usuários da PRÓPRIA empresa que podem ser promovidos a Gestor (Usuário ativo, com acesso, sem conta de sistema)."""
    try:
        return plataforma_service.listar_candidatos_gestor(db, str(empresa_id))
    except Exception as exc:
        _tratar_erro(exc)


@router.post("/empresas/{empresa_id}/usuarios/{usuario_id}/promover-gestor", response_model=PlataformaUsuarioRead)
def promover_gestor(
    empresa_id: UUID,
    usuario_id: UUID,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Promove um Usuário existente da empresa a Gestor. Usuário de outra empresa → 404 (nunca promove cross-tenant)."""
    try:
        return plataforma_service.promover_gestor(db, str(empresa_id), str(usuario_id), ator=ctx.usuario)
    except Exception as exc:
        _tratar_erro(exc)


@router.post(
    "/empresas/{empresa_id}/gestores", response_model=PlataformaGestorCriadoRead, status_code=status.HTTP_201_CREATED
)
def criar_gestor(
    empresa_id: UUID,
    dados: PlataformaGestorCreate,
    ctx: ContextoPlataforma = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Cria um Gestor da empresa (perfil forçado `gestor`, troca de senha obrigatória). A `senhaTemporaria` só existe
    NESTA resposta."""
    try:
        resposta = plataforma_service.criar_gestor(db, str(empresa_id), dados, ator=ctx.usuario)
    except Exception as exc:
        _tratar_erro(exc)
    return resposta
