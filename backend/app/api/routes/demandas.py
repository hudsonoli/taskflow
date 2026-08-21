from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.escopo import (
    EscopoDemanda,
    EscopoNaoAutorizadoError,
    EscopoSolicitado,
    resolver_escopo_demanda,
)
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_profiles
from app.models.usuario import Usuario
from app.schemas.demanda import (
    DemandaAjusteRegistrar,
    DemandaArquivar,
    DemandaConclusaoEmailRegistrar,
    DemandaCreate,
    DemandaDiretorioRead,
    DemandaRead,
    DemandaUpdate,
)
from app.schemas.demanda_historico import DemandaHistoricoEventoRead
from app.services.demanda_historico_service import DemandaHistoricoService
from app.services.demanda_service import (
    DemandaClienteInvalidoError,
    DemandaDepartamentoInvalidoError,
    DemandaForaDeExpedienteError,
    DemandaInvalidTransitionError,
    DemandaMotivoBloqueioObrigatorioError,
    DemandaNotFoundError,
    DemandaProjetoInvalidoError,
    DemandaService,
    DemandaUsuarioInvalidoError,
    DemandaWorkflowModeloInvalidoError,
)

router = APIRouter(
    prefix="/demandas",
    tags=["demandas"],
    dependencies=[Depends(get_current_user_password_ready)],
)
demanda_service = DemandaService()
historico_service = DemandaHistoricoService()

# Demanda é o primeiro domínio OPERACIONAL: ao contrário de Cliente, Projeto e Fornecedor,
# ler/criar/editar é aberto a qualquer autenticado — sempre dentro do escopo resolvido.
# Arquivar e restaurar seguem restritos a admin/gestor, como nos cadastros.
require_admin_or_gestor = require_profiles("admin", "gestor")


def handle_demanda_error(exc: Exception) -> None:
    if isinstance(exc, DemandaNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, EscopoNaoAutorizadoError):
        # 403 e NÃO lista vazia: lista vazia esconderia erro de permissão atrás de um
        # resultado que parece legítimo.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, DemandaForaDeExpedienteError):
        # 409 estruturado — a interface só apresenta; a janela vem do servidor para não haver
        # duas fontes da mesma regra.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "FORA_DE_EXPEDIENTE",
                "message": str(exc),
                "expediente": {
                    # Janela de HOJE — pode vir tudo `None` quando o dia não é útil (ver
                    # docstring de DemandaForaDeExpedienteError, Fase 2G.3).
                    "manhaInicio": exc.dia_hoje.manha_inicio,
                    "manhaFim": exc.dia_hoje.manha_fim,
                    "tardeInicio": exc.dia_hoje.tarde_inicio,
                    "tardeFim": exc.dia_hoje.tarde_fim,
                    "toleranciaRetomadaMinutos": exc.tolerancia_retomada_minutos,
                },
            },
        ) from exc
    if isinstance(exc, DemandaInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(
        exc,
        (
            DemandaMotivoBloqueioObrigatorioError,
            DemandaClienteInvalidoError,
            DemandaProjetoInvalidoError,
            DemandaUsuarioInvalidoError,
            DemandaDepartamentoInvalidoError,
            DemandaWorkflowModeloInvalidoError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


def _escopo(
    db: Session, current_user: Usuario, solicitado: EscopoSolicitado | None = None
) -> EscopoDemanda:
    try:
        return resolver_escopo_demanda(db, current_user, solicitado)
    except Exception as exc:
        handle_demanda_error(exc)
        raise  # inalcançável — handle_demanda_error sempre levanta


@router.post("", response_model=DemandaRead, status_code=status.HTTP_201_CREATED)
def create_demanda(
    payload: DemandaCreate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        criada = demanda_service.create_demanda(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
        return demanda_service.to_read(db, criada)
    except Exception as exc:
        handle_demanda_error(exc)


@router.get("", response_model=list[DemandaRead])
def list_demandas(
    status_demanda: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    cliente_id: UUID | None = Query(default=None, alias="clienteId"),
    projeto_id: UUID | None = Query(default=None, alias="projetoId"),
    departamento_id: UUID | None = Query(default=None, alias="departamentoId"),
    escopo_solicitado: EscopoSolicitado | None = Query(default=None, alias="escopo"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """**Sem parâmetro nenhum já vem escopado.** `escopo=` só estreita, nunca amplia."""
    escopo = _escopo(db, current_user, escopo_solicitado)
    demandas = demanda_service.list_demandas(
        db,
        escopo=escopo,
        status=status_demanda,
        search=search,
        cliente_id=str(cliente_id) if cliente_id else None,
        projeto_id=str(projeto_id) if projeto_id else None,
        departamento_id=str(departamento_id) if departamento_id else None,
        limit=limit,
        offset=offset,
    )
    return demanda_service.to_read_lote(db, demandas)


@router.get("/diretorio", response_model=list[DemandaDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Escopado como a listagem, e sem as arquivadas — arquivada não é opção de vínculo novo."""
    escopo = _escopo(db, current_user)
    demandas = demanda_service.list_demandas(db, escopo=escopo, limit=200)
    return [DemandaDiretorioRead.model_validate(demanda) for demanda in demandas]


@router.get("/{demanda_id}", response_model=DemandaRead)
def get_demanda(
    demanda_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Fora da empresa **ou fora do escopo** → 404. Conhecer o UUID não autoriza nada."""
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        return demanda_service.to_read(db, demanda)
    except Exception as exc:
        handle_demanda_error(exc)


@router.patch("/{demanda_id}", response_model=DemandaRead)
def update_demanda(
    demanda_id: UUID,
    payload: DemandaUpdate,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """A resolução escopada acontece ANTES de qualquer escrita — fora do escopo é 404 e nada
    é persistido."""
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        atualizada = demanda_service.update_demanda(
            db, demanda, payload, actor_usuario_id=current_user.id
        )
        return demanda_service.to_read(db, atualizada)
    except Exception as exc:
        handle_demanda_error(exc)


# "Excluir" = arquivar (soft-delete permanente). Nunca há delete físico de demanda.
@router.post("/{demanda_id}/arquivar", response_model=DemandaRead)
def arquivar_demanda(
    demanda_id: UUID,
    payload: DemandaArquivar,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        # O escopo se SOMA ao perfil: admin/gestor têm visão total, então na prática só a
        # empresa filtra — mas a checagem fica aqui para a regra não depender do perfil.
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        arquivada = demanda_service.arquivar_demanda(
            db,
            demanda,
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return demanda_service.to_read(db, arquivada)
    except Exception as exc:
        handle_demanda_error(exc)


@router.post("/{demanda_id}/restaurar", response_model=DemandaRead)
def restaurar_demanda(
    demanda_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        restaurada = demanda_service.restaurar_demanda(
            db, demanda, actor_usuario_id=current_user.id
        )
        return demanda_service.to_read(db, restaurada)
    except Exception as exc:
        handle_demanda_error(exc)


# Ajuste e conclusão-por-e-mail (Fase 2E.4) são operacionais como checklist/arquivos/
# comentários (ver instrução da fase, item 13 da 2E.3, reaplicado aqui): qualquer
# autenticado com escopo sobre a Demanda aciona, sem gate de perfil — ao contrário de
# arquivar/restaurar, que seguem admin/gestor.


@router.post(
    "/{demanda_id}/ajustes", response_model=DemandaHistoricoEventoRead, status_code=status.HTTP_201_CREATED
)
def registrar_ajuste(
    demanda_id: UUID,
    payload: DemandaAjusteRegistrar,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Não muda nenhum campo da Demanda — só produz uma entrada na timeline (ver
    DemandaService.registrar_ajuste)."""
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        evento = demanda_service.registrar_ajuste(
            db, demanda, payload.tipo, actor_usuario_id=current_user.id
        )
        return historico_service.to_read(evento)
    except Exception as exc:
        handle_demanda_error(exc)


@router.post("/{demanda_id}/conclusao-email", response_model=DemandaRead)
def registrar_conclusao_email(
    demanda_id: UUID,
    payload: DemandaConclusaoEmailRegistrar,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        atualizada = demanda_service.registrar_conclusao_email(
            db, demanda, enviado=payload.enviado, actor_usuario_id=current_user.id
        )
        return demanda_service.to_read(db, atualizada)
    except Exception as exc:
        handle_demanda_error(exc)
