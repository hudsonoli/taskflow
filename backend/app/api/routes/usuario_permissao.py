from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa
from app.dependencies.permissoes import require_permissoes_gerenciar
from app.models.usuario import Usuario
from app.schemas.usuario_permissao import PermissaoAdminItem, UsuarioPermissaoOverrideWrite
from app.services.usuario_permissao_service import UsuarioPermissaoService
from app.services.usuario_service import UsuarioNotFoundError, UsuarioService

# Fase 2G.10C-C1 — administração de exceções individuais de permissão. Todos os endpoints
# exigem require_permissoes_gerenciar() (permissao "permissoes.gerenciar" + piso fixo
# perfil_base == admin — ver app/dependencies/permissoes.py). Sub-recurso de Usuário, mesmo
# padrão de demanda_checklist.py/demanda_arquivos.py (arquivo próprio, registrado à parte em
# main.py, com seu próprio gate de senha em dia — routers do FastAPI não herdam
# `dependencies` de outro router só por compartilhar prefixo de path).
router = APIRouter(
    prefix="/usuarios/{usuario_id}/permissoes",
    tags=["usuario_permissao"],
    dependencies=[Depends(get_current_user_password_ready)],
)
usuario_service = UsuarioService()
usuario_permissao_service = UsuarioPermissaoService()

STATUS_ARQUIVADO = "arquivado"
_ACESSO_NEGADO = "Acesso negado"


def _buscar_usuario_alvo(db: Session, usuario_id: str, current_user: Usuario) -> Usuario:
    """Mesmo padrão de app/api/routes/usuarios.py: não encontrado OU de outro tenant vira
    404 — nunca 403 (não revela a um admin de outro tenant que aquele ID existe)."""
    try:
        usuario = usuario_service.get_usuario(db, usuario_id)
    except UsuarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    ensure_resource_empresa(usuario.empresa_id, current_user)
    return usuario


def _bloquear_self(usuario_id: str, current_user: Usuario) -> None:
    """PUT/DELETE do próprio usuário — nunca GET (ver docstring do router). Mesmo texto e
    código de inativar_usuario/bloquear_usuario/excluir_usuario em routes/usuarios.py."""
    if usuario_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ACESSO_NEGADO)


def _bloquear_arquivado(usuario: Usuario) -> None:
    """Usuário arquivado: histórico continua visível (GET), mas não recebe nova
    mutação — mesmo código (409) de UsuarioInvalidTransitionError, erro de ESTADO do
    recurso, não de autorização (por isso não é 403)."""
    if usuario.status == STATUS_ARQUIVADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário arquivado não aceita alteração de permissões",
        )


@router.get("", response_model=list[PermissaoAdminItem])
def get_permissoes_usuario(
    usuario_id: str,
    current_user: Usuario = Depends(require_permissoes_gerenciar()),
    db: Session = Depends(get_db),
):
    usuario = _buscar_usuario_alvo(db, usuario_id, current_user)
    return usuario_permissao_service.montar_visao_administrativa(db, usuario)


@router.put("/{permissao}", response_model=PermissaoAdminItem)
def definir_permissao_usuario(
    usuario_id: str,
    permissao: str,
    payload: UsuarioPermissaoOverrideWrite,
    current_user: Usuario = Depends(require_permissoes_gerenciar()),
    db: Session = Depends(get_db),
):
    _bloquear_self(usuario_id, current_user)
    usuario = _buscar_usuario_alvo(db, usuario_id, current_user)
    _bloquear_arquivado(usuario)

    try:
        override = usuario_permissao_service.definir_override(
            db,
            usuario=usuario,
            permissao=permissao,
            efeito=payload.efeito,
            motivo=payload.motivo,
            concedido_por_usuario_id=current_user.id,
        )
    except ValueError as exc:
        # PermissaoInvalidaError (validar_permissao_existente) — chave fora do catálogo.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    itens = usuario_permissao_service.montar_visao_administrativa(db, usuario)
    return next(item for item in itens if item.permissao == override.permissao)


@router.delete("/{permissao}", status_code=status.HTTP_204_NO_CONTENT)
def remover_permissao_usuario(
    usuario_id: str,
    permissao: str,
    current_user: Usuario = Depends(require_permissoes_gerenciar()),
    db: Session = Depends(get_db),
):
    _bloquear_self(usuario_id, current_user)
    usuario = _buscar_usuario_alvo(db, usuario_id, current_user)
    _bloquear_arquivado(usuario)

    try:
        usuario_permissao_service.remover_override(
            db, usuario=usuario, permissao=permissao, actor_usuario_id=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # 204 mesmo se não havia linha (idempotente) — remover_override já não publica evento
    # nesse caso.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
