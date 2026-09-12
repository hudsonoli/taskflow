from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import ensure_resource_empresa, ensure_same_empresa
from app.dependencies.permissoes import require_permissao
from app.models.usuario import Usuario
from app.schemas.usuario import (
    UsuarioCreate,
    UsuarioDiretorioRead,
    UsuarioExcluir,
    UsuarioInativar,
    UsuarioRead,
    UsuarioUpdate,
)
from app.services.usuario_permissao_service import UsuarioPermissaoService
from app.services.usuario_service import (
    UsuarioArquivadoConflictError,
    UsuarioConflictError,
    UsuarioDepartamentoInvalidoError,
    UsuarioInvalidEmpresaError,
    UsuarioInvalidTransitionError,
    UsuarioNotFoundError,
    UsuarioService,
    UsuarioSystemAccountProtegidoError,
)

# Gate único pra todas as rotas: autenticado + senha em dia (ver
# get_current_user_password_ready). As rotas específicas ainda aplicam seu próprio
# controle de acesso (require_permissao) por cima disso — exceto /me e /diretorio, que
# ficam abertas a qualquer autenticado (ver docstrings das duas rotas abaixo).
router = APIRouter(prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(get_current_user_password_ready)])
usuario_service = UsuarioService()
# Fase 2G.10A — só usado para preencher UsuarioRead.permissoes em GET /usuarios/me
# (informativo). Nenhuma outra rota deste arquivo o usa.
usuario_permissao_service = UsuarioPermissaoService()

PATCH_ALLOWED_FIELDS = {
    "codigoInterno",
    "nome",
    "email",
    "perfilBase",
    "acessoSistema",
    "telefone",
    "cpf",
    "dataNascimento",
    "cep",
    "bairro",
    "enderecoCompleto",
    "cidade",
    "uf",
    "contatos",
    "departamentoId",
    "cargo",
    "fotoUrl",
    "liderDepartamento",
    "valorRecebidoMensalCentavos",
    "horasTrabalhoAproximadas",
    "observacoes",
    "corIdentificacao",
}


def handle_usuario_error(exc: Exception) -> None:
    if isinstance(exc, ValidationError):
        # O PATCH recebe dict cru e valida à mão (ver update_usuario), então o
        # ValidationError do Pydantic não passa pelo tratamento automático do FastAPI e
        # viraria 500. Reemitido como RequestValidationError pra sair no MESMO formato 422
        # de qualquer outra falha de schema — é o que garante que `departamentoId` com nome
        # textual seja recusado explicitamente, e não engolido.
        raise RequestValidationError(exc.errors()) from exc
    if isinstance(exc, UsuarioNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, UsuarioArquivadoConflictError):
        # Ver docs/padrao-arquivamento.md — código padronizado + ID do arquivado pra UI
        # oferecer restaurar.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "USUARIO_ARQUIVADO_EXISTENTE",
                "usuarioArquivadoId": exc.usuario_arquivado_id,
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, UsuarioConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, UsuarioDepartamentoInvalidoError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, UsuarioInvalidEmpresaError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, UsuarioInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, UsuarioSystemAccountProtegidoError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def create_usuario(
    usuario: UsuarioCreate,
    current_user: Usuario = Depends(require_permissao("usuarios.criar")),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(usuario.empresa_id, current_user)
    try:
        created = usuario_service.create_usuario(db, usuario, actor_usuario_id=current_user.id)
        return usuario_service.to_read(created)
    except Exception as exc:
        handle_usuario_error(exc)


@router.get("", response_model=list[UsuarioRead])
def list_usuarios(
    empresa_id: UUID = Query(alias="empresaId"),
    status_usuario: str | None = Query(default=None, alias="status"),
    perfil_base: str | None = Query(default=None, alias="perfilBase"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_permissao("usuarios.visualizar")),
    db: Session = Depends(get_db),
):
    ensure_same_empresa(empresa_id, current_user)
    usuarios = usuario_service.list_usuarios(
        db,
        empresa_id=str(empresa_id),
        status=status_usuario,
        perfil_base=perfil_base,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [usuario_service.to_read(usuario) for usuario in usuarios]


@router.get("/me", response_model=UsuarioRead)
def get_me(
    # Aberto a qualquer autenticado — consultar o próprio registro nunca dependeu de
    # usuarios.visualizar (self-service já é o comportamento atual, fora de escopo desta
    # onda). Continua fora do enforcement por permissão.
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    usuario = usuario_service.get_me(db, current_user.id)
    leitura = usuario_service.to_read(usuario)
    # Fase 2G.10A — só em /me: ver nota em UsuarioRead.permissoes.
    permissoes = usuario_permissao_service.obter_permissoes_efetivas(db, usuario)
    return leitura.model_copy(update={"permissoes": permissoes})


@router.get("/diretorio", response_model=list[UsuarioDiretorioRead])
def list_diretorio(
    status_usuario: str | None = Query(default=None, alias="status"),
    departamento_id: str | None = Query(default=None, alias="departamentoId"),
    search: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    # Aberto a qualquer autenticado — usado como seletor (ex.: responsável de Demanda),
    # mesmo padrão de /diretorio nos outros cadastros. Continua fora do enforcement por
    # permissão.
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    usuarios = usuario_service.list_diretorio(
        db,
        empresa_id=current_user.empresa_id,
        status=status_usuario,
        departamento_id=departamento_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [usuario_service.to_diretorio_read(usuario) for usuario in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioRead)
def get_usuario(
    usuario_id: UUID,
    current_user: Usuario = Depends(require_permissao("usuarios.visualizar")),
    db: Session = Depends(get_db),
):
    try:
        usuario = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(usuario.empresa_id, current_user)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.patch("/{usuario_id}", response_model=UsuarioRead)
def update_usuario(
    usuario_id: UUID,
    payload: dict[str, Any] = Body(...),
    current_user: Usuario = Depends(require_permissao("usuarios.editar")),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
    except Exception as exc:
        handle_usuario_error(exc)

    unexpected_fields = set(payload) - PATCH_ALLOWED_FIELDS
    if unexpected_fields:
        fields = ", ".join(sorted(unexpected_fields))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos não permitidos no PATCH de Usuário: {fields}",
        )

    try:
        data = UsuarioUpdate.model_validate(payload)
        usuario = usuario_service.update_usuario(db, str(usuario_id), data, actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/inativar", response_model=UsuarioRead)
def inativar_usuario(
    usuario_id: UUID,
    payload: UsuarioInativar | None = None,
    current_user: Usuario = Depends(require_permissao("usuarios.suspender")),
    db: Session = Depends(get_db),
):
    if str(usuario_id) == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.inativar_usuario(
            db,
            str(usuario_id),
            motivo_inativacao=payload.motivo_inativacao if payload else None,
            actor_usuario_id=current_user.id,
        )
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/reativar", response_model=UsuarioRead)
def reativar_usuario(
    usuario_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    current_user: Usuario = Depends(require_permissao("usuarios.suspender")),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.reativar_usuario(db, str(usuario_id), actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/bloquear", response_model=UsuarioRead)
def bloquear_usuario(
    usuario_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    current_user: Usuario = Depends(require_permissao("usuarios.suspender")),
    db: Session = Depends(get_db),
):
    if str(usuario_id) == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.bloquear_usuario(db, str(usuario_id), actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/desbloquear", response_model=UsuarioRead)
def desbloquear_usuario(
    usuario_id: UUID,
    actor_usuario_id: str | None = Body(default=None, embed=True, alias="actorUsuarioId"),
    current_user: Usuario = Depends(require_permissao("usuarios.suspender")),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.desbloquear_usuario(db, str(usuario_id), actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/excluir", response_model=UsuarioRead)
def excluir_usuario(
    usuario_id: UUID,
    payload: UsuarioExcluir,
    current_user: Usuario = Depends(require_permissao("usuarios.suspender")),
    db: Session = Depends(get_db),
):
    if str(usuario_id) == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.excluir_usuario(
            db,
            str(usuario_id),
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)


@router.post("/{usuario_id}/restaurar", response_model=UsuarioRead)
def restaurar_usuario(
    usuario_id: UUID,
    current_user: Usuario = Depends(require_permissao("usuarios.suspender")),
    db: Session = Depends(get_db),
):
    try:
        existing = usuario_service.get_usuario(db, str(usuario_id))
        ensure_resource_empresa(existing.empresa_id, current_user)
        usuario = usuario_service.restaurar_usuario(db, str(usuario_id), actor_usuario_id=current_user.id)
        return usuario_service.to_read(usuario)
    except Exception as exc:
        handle_usuario_error(exc)
