from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.repositories.evento_repository import EventoRepository
from app.schemas.demanda_historico import DemandaHistoricoEventoRead

TIPO_ENTIDADE = "demanda"


class DemandaHistoricoService:
    """Lê a timeline de uma Demanda direto de `eventos` — sem tabela própria. Todo evento já
    publicado com `entidade_tipo="demanda"`/`entidade_id=demanda.id` (criação, edição,
    status, bloqueio, vínculos, checklist, arquivos, comentários, ajustes, workflow
    aplicado...) aparece aqui automaticamente, sem exigir alteração quando um domínio novo
    passar a publicar eventos da Demanda.

    Não usa `GET /eventos` nem `EventoService` — filtra direto pelo repository, porque a
    trilha de auditoria administrativa (`/eventos`) e o histórico operacional de uma Demanda
    são autorizações diferentes (ver docstring de app/api/routes/demanda_historico.py).
    """

    def __init__(self, repository: EventoRepository | None = None) -> None:
        self.repository = repository or EventoRepository()

    def listar(
        self, db: Session, *, empresa_id: str, demanda_id: str, limit: int = 200
    ) -> list[Evento]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=demanda_id,
            limit=limit,
        )

    @staticmethod
    def to_read(evento: Evento) -> DemandaHistoricoEventoRead:
        return DemandaHistoricoEventoRead(
            id=evento.id,
            tipo=evento.tipo,
            usuarioId=evento.usuario_id,
            occurredAt=evento.occurred_at,
            dados=evento.payload,
        )
