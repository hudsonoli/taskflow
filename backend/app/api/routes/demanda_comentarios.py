from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.escopo_leitura import EscopoLeitura, demanda_com_acesso_de_leitura, escopo_para_leitura
from app.core.escopo import EscopoNaoAutorizadoError, resolver_escopo_criador
from app.core.identidade_sistema import ids_de_contas_de_sistema
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.demanda import Demanda
from app.models.usuario import Usuario
from app.schemas.demanda_comentario import (
    DemandaComentarioCreate,
    DemandaComentarioRead,
    DemandaComentarioUpdate,
    MencionavelRead,
)
from app.services.comentario_mencao_service import MencaoInvalidaError
from app.services.demanda_comentario_service import (
    DemandaComentarioNaoAutorizadoError,
    DemandaComentarioNotFoundError,
    DemandaComentarioService,
)
from app.services.demanda_service import DemandaNotFoundError, DemandaService

# Mesmo critério de acesso de checklist/arquivos (Fase 2E.3): comentário é operacional,
# aberto a qualquer autenticado dentro do escopo da própria Demanda. A regra de autoria
# (só o autor edita; autor ou admin/gestor excluem) é decidida no service, não aqui.
router = APIRouter(
    prefix="/demandas",
    tags=["demanda-comentarios"],
    dependencies=[Depends(get_current_user_password_ready)],
)
demanda_service = DemandaService()
comentario_service = DemandaComentarioService()


def handle_comentario_error(exc: Exception) -> None:
    if isinstance(exc, (DemandaNotFoundError, DemandaComentarioNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, DemandaComentarioNaoAutorizadoError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, MencaoInvalidaError):
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
    # `escopo_leitura` só é passado pelos GET (leitura pela Pauta global); escrita usa sempre o escopo-base.
    # `leitura=True` (só o GET da lista): além do escopo-base, vale o escopo DERIVADO da etapa atual do Workflow (Fase 8C.1).
    if leitura:
        return demanda_com_acesso_de_leitura(db, current_user, str(demanda_id), demanda_service, escopo_leitura)[0]
    escopo = escopo_para_leitura(db, current_user, escopo_leitura)
    return demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)


def _demanda_para_comentar(demanda_id: UUID, current_user: Usuario, db: Session) -> tuple[Demanda, bool]:
    """Comentar é COLABORAÇÃO, não gestão: vale o escopo-base e, por último, a AUTORIA — quem solicitou a Demanda acompanha e pode comentar depois de ela passar para outro
    departamento (mesma empresa, individual). Devolve `(demanda, so_criador)`; `so_criador` verdadeiro quando só a autoria deu acesso. Nenhuma outra escrita (PATCH, workflow,
    responsáveis, esforço, arquivos…) consulta este escopo."""
    try:
        return demanda_service.get_demanda(db, str(demanda_id), escopo=escopo_para_leitura(db, current_user, None)), False
    except DemandaNotFoundError:
        return demanda_service.get_demanda(db, str(demanda_id), escopo=resolver_escopo_criador(current_user)), True


def _read_com_mencoes(db: Session, comentario) -> DemandaComentarioRead:
    mencoes = comentario_service.mencao_service.listar_por_comentarios(db, [comentario.id])
    return comentario_service.to_read(comentario, mencoes=mencoes.get(comentario.id))


def _pode_ler_a_demanda(db: Session, demanda_id: str):
    """Predicado de menção: o usuário LÊ esta Demanda pelas mesmas regras do detalhe (escopo-base, escopo derivado do Workflow ou autoria). A menção nunca concede acesso."""

    def pode_ler(usuario: Usuario) -> bool:
        try:
            demanda_com_acesso_de_leitura(db, usuario, demanda_id, demanda_service, None)
            return True
        except (DemandaNotFoundError, EscopoNaoAutorizadoError):
            return False

    return pode_ler


@router.get("/{demanda_id}/mencionaveis", response_model=list[MencionavelRead])
def listar_mencionaveis(
    demanda_id: UUID,
    q: str = Query(default="", max_length=80),
    limit: int = Query(default=8, ge=1, le=20),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Autocomplete de @menção: só quem pode ser mencionado NESTA tarefa (mesma empresa, ativo, com acesso a ela). Quem pode comentar pode buscar."""
    try:
        demanda, _ = _demanda_para_comentar(demanda_id, current_user, db)
        return comentario_service.mencao_service.buscar_mencionaveis(
            db, empresa_id=demanda.empresa_id, autor_id=current_user.id, consulta=q, limite=limit, pode_ler=_pode_ler_a_demanda(db, demanda.id)
        )
    except Exception as exc:
        handle_comentario_error(exc)


@router.get("/{demanda_id}/comentarios", response_model=list[DemandaComentarioRead])
def listar_comentarios(
    demanda_id: UUID,
    escopo: EscopoLeitura | None = Query(default=None),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda = _demanda_no_escopo(demanda_id, current_user, db, escopo, leitura=True)
        comentarios = comentario_service.list_comentarios(db, demanda.id)
        sistema = (
            set()
            if current_user.is_system_account
            else ids_de_contas_de_sistema(db, (comentario.autor_usuario_id for comentario in comentarios))
        )
        mencoes = comentario_service.mencao_service.listar_por_comentarios(db, [comentario.id for comentario in comentarios])
        return [
            comentario_service.to_read(comentario, autor_sistema=comentario.autor_usuario_id in sistema, mencoes=mencoes.get(comentario.id))
            for comentario in comentarios
        ]
    except Exception as exc:
        handle_comentario_error(exc)


@router.post(
    "/{demanda_id}/comentarios", response_model=DemandaComentarioRead, status_code=status.HTTP_201_CREATED
)
def criar_comentario(
    demanda_id: UUID,
    payload: DemandaComentarioCreate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda, so_criador = _demanda_para_comentar(demanda_id, current_user, db)
        # O comentário do SOLICITANTE não é a "primeira resposta" da operação ao cliente: não fixa `sla_primeira_resposta_em`.
        comentario = comentario_service.criar_comentario(
            db, demanda, payload, autor=current_user, fixar_primeira_resposta=not so_criador, pode_ler=_pode_ler_a_demanda(db, demanda.id)
        )
        return _read_com_mencoes(db, comentario)
    except Exception as exc:
        handle_comentario_error(exc)


@router.patch("/{demanda_id}/comentarios/{comentario_id}", response_model=DemandaComentarioRead)
def editar_comentario(
    demanda_id: UUID,
    comentario_id: UUID,
    payload: DemandaComentarioUpdate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda, _ = _demanda_para_comentar(demanda_id, current_user, db)  # a regra "só o autor edita" é do service
        comentario = comentario_service.editar_comentario(
            db, demanda, str(comentario_id), payload, current_user=current_user, pode_ler=_pode_ler_a_demanda(db, demanda.id)
        )
        return _read_com_mencoes(db, comentario)
    except Exception as exc:
        handle_comentario_error(exc)


@router.delete("/{demanda_id}/comentarios/{comentario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_comentario(
    demanda_id: UUID,
    comentario_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        demanda, _ = _demanda_para_comentar(demanda_id, current_user, db)  # a regra "autor ou admin/gestor exclui" é do service
        comentario_service.excluir_comentario(db, demanda, str(comentario_id), current_user=current_user)
    except Exception as exc:
        handle_comentario_error(exc)
