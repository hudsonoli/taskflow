"""Trilha de auditoria — leitura restrita a admin/gestor.

## Por que este módulo tem dependência de autenticação explícita

Até esta correção o router inteiro respondia **sem token nenhum**: um `GET /eventos` anônimo
devolvia a auditoria completa da empresa, incluindo `auth.login_sucesso` com nome, UUID e
horário de cada pessoa. O gate existia só em `AcessosView.tsx`, no navegador — que é UX, não
segurança.

Duas barreiras, não uma:

1. **autenticação + perfil** — a trilha de auditoria é administrativa, como a tela que a
   consome;
2. **empresa vinda do token** — `empresaId` deixou de ser escolha do cliente. Passar o id de
   outra empresa devolve 403 em vez de ser ignorado em silêncio: ignorar faria o chamador
   crer que recebeu o que pediu.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_profiles
from app.models.usuario import Usuario
from app.schemas.evento import EventoCreate, EventoRead
from app.services.evento_service import EventoService

router = APIRouter(
    prefix="/eventos",
    tags=["eventos"],
    dependencies=[Depends(get_current_user_password_ready)],
)
evento_service = EventoService()

require_admin_or_gestor = require_profiles("admin", "gestor")


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filtros de data devem incluir timezone",
        )
    return value.astimezone(timezone.utc)


def _empresa_do_token(empresa_id: str | None, current_user: Usuario) -> str:
    """A empresa vem SEMPRE do token. O parâmetro só é aceito se coincidir.

    Recusar explicitamente é melhor que sobrescrever: quem passou outro id fez uma pergunta
    diferente da que seria respondida.
    """
    if empresa_id is not None and empresa_id != current_user.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="empresaId não corresponde à empresa da sessão",
        )
    return current_user.empresa_id


@router.post("", response_model=EventoRead, status_code=status.HTTP_201_CREATED)
def create_evento(
    evento: EventoCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    # Escrita na auditoria com `empresaId` livre permitiria forjar evento em outra empresa.
    _empresa_do_token(evento.empresa_id, current_user)
    created = evento_service.create_evento(db, evento)
    return evento_service.to_read(created)


@router.get("/{evento_id}", response_model=EventoRead)
def get_evento(
    evento_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    evento = evento_service.get_evento(db, str(evento_id))
    # Evento de outra empresa é 404, nunca 403: 403 confirmaria que o registro existe.
    if evento is None or evento.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
    return evento_service.to_read(evento)


@router.get("", response_model=list[EventoRead])
def list_eventos(
    empresa_id: str | None = Query(default=None, alias="empresaId"),
    entidade_tipo: str | None = Query(default=None, alias="entidadeTipo"),
    entidade_id: str | None = Query(default=None, alias="entidadeId"),
    tipo: str | None = None,
    correlation_id: UUID | None = Query(default=None, alias="correlationId"),
    data_inicio: datetime | None = Query(default=None, alias="dataInicio"),
    data_fim: datetime | None = Query(default=None, alias="dataFim"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    eventos = evento_service.list_eventos(
        db,
        empresa_id=_empresa_do_token(empresa_id, current_user),
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        tipo=tipo,
        correlation_id=str(correlation_id) if correlation_id else None,
        data_inicio=normalize_datetime(data_inicio),
        data_fim=normalize_datetime(data_fim),
        limit=limit,
        offset=offset,
    )
    return [evento_service.to_read(evento) for evento in eventos]
