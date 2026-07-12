from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.repositories.evento_repository import EventoRepository
from app.schemas.timeline import TimelineItem
from app.services.evento_service import ensure_utc

Mapper = Callable[[dict[str, Any]], tuple[str, str]]


def humanize_value(value: Any, *, field_name: str | None = None) -> str:
    if value is None:
        return ""
    if field_name and field_name.lower().endswith("id"):
        return str(value)
    if not isinstance(value, str):
        return str(value)

    normalized = value.strip()
    known_values = {
        "baixa": "Baixa",
        "media": "Média",
        "alta": "Alta",
        "em_execucao": "Em execução",
        "aguardando_cliente": "Aguardando cliente",
        "planejamento": "Planejamento",
        "ativo": "Ativo",
        "pausado": "Pausado",
        "pausada": "Pausada",
        "bloqueada": "Bloqueada",
        "concluido": "Concluído",
        "concluida": "Concluída",
        "cancelado": "Cancelado",
        "cancelada": "Cancelada",
    }
    if normalized.lower() in known_values:
        return known_values[normalized.lower()]
    if "_" in normalized:
        return normalized.replace("_", " ").capitalize()
    return normalized


def map_projeto_criado(_: dict[str, Any]) -> tuple[str, str]:
    return "Projeto criado", "Projeto criado."


def map_projeto_status_alterado(payload: dict[str, Any]) -> tuple[str, str]:
    status_anterior = humanize_value(payload.get("statusAnterior"))
    status_novo = humanize_value(payload.get("statusNovo"))
    return "Projeto alterado", f"Status alterado de {status_anterior} para {status_novo}."


def map_demanda_prioridade_alterada(payload: dict[str, Any]) -> tuple[str, str]:
    prioridade_anterior = humanize_value(payload.get("prioridadeAnterior"))
    prioridade_nova = humanize_value(payload.get("prioridadeNova"))
    return "Prioridade alterada", f"Prioridade alterada de {prioridade_anterior} para {prioridade_nova}."


def map_workflow_etapa_avancada(payload: dict[str, Any]) -> tuple[str, str]:
    etapa_origem = humanize_value(payload.get("etapaOrigemNome"))
    etapa_destino = humanize_value(payload.get("etapaDestinoNome"))
    return "Workflow", f"Movido de {etapa_origem} para {etapa_destino}."


TIMELINE_MAPPERS: dict[str, Mapper] = {
    "projeto.criado": map_projeto_criado,
    "projeto.status_alterado": map_projeto_status_alterado,
    "demanda.prioridade_alterada": map_demanda_prioridade_alterada,
    "workflow.etapa_avancada": map_workflow_etapa_avancada,
}


class TimelineService:
    def __init__(self, repository: EventoRepository | None = None) -> None:
        self.repository = repository or EventoRepository()

    def list_timeline(
        self,
        db: Session,
        *,
        empresa_id: str | None = None,
        entidade_tipo: str | None = None,
        entidade_id: str | None = None,
        tipo: str | None = None,
        usuario_id: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TimelineItem]:
        eventos = self.repository.list(
            db,
            empresa_id=empresa_id,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            tipo=tipo,
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=limit,
            offset=offset,
        )
        return [self.to_timeline_item(evento) for evento in eventos]

    def to_timeline_item(self, evento: Evento) -> TimelineItem:
        mapper = TIMELINE_MAPPERS.get(evento.tipo)
        titulo, descricao = mapper(evento.payload) if mapper else ("Evento", "Evento registrado.")
        return TimelineItem(
            id=evento.id,
            tipo=evento.tipo,
            titulo=titulo,
            descricao=descricao,
            usuarioId=evento.usuario_id,
            empresaId=evento.empresa_id,
            entidadeTipo=evento.entidade_tipo,
            entidadeId=evento.entidade_id,
            occurredAt=ensure_utc(evento.occurred_at),
            createdAt=ensure_utc(evento.created_at),
            payload=evento.payload,
            metadata=evento.metadata_,
        )
