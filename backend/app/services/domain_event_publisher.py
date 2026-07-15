from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.event_types import EVENT_TYPES, DomainEventType
from app.models.evento import Evento
from app.schemas.evento import EventoCreate
from app.services.evento_service import EventoService

SENSITIVE_KEYS = {
    "senha",
    "password",
    "token",
    "accesstoken",
    "access_token",
    "refreshtoken",
    "refresh_token",
    "cpf",
    "cnpj",
    "dadosbancarios",
    "dados_bancarios",
    "contabancaria",
    "conta_bancaria",
    "agenciabancaria",
    "agencia_bancaria",
    "pix",
    "chavepix",
    "chave_pix",
    "secret",
    "authorization",
}


def normalize_key(key: str) -> str:
    return key.replace("-", "_").lower()


def contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = normalize_key(str(key))
            compact_key = normalized_key.replace("_", "")
            if normalized_key in SENSITIVE_KEYS or compact_key in SENSITIVE_KEYS:
                return True
            if contains_sensitive_key(item):
                return True
    if isinstance(value, list):
        return any(contains_sensitive_key(item) for item in value)
    return False


class DomainEventPublisher:
    def __init__(self, evento_service: EventoService | None = None) -> None:
        self.evento_service = evento_service or EventoService()

    def publish(
        self,
        db: Session,
        *,
        tipo: DomainEventType | str,
        empresa_id: str,
        entidade_tipo: str,
        entidade_id: str,
        payload: dict[str, Any],
        agencia_id: str | None = None,
        usuario_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: UUID | str | None = None,
        causation_id: UUID | str | None = None,
        occurred_at: datetime | None = None,
    ) -> Evento:
        event_type = tipo.value if isinstance(tipo, DomainEventType) else tipo
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Tipo de evento não catalogado: {event_type}")
        if contains_sensitive_key(payload):
            raise ValueError("Payload contém chave sensível proibida")
        if metadata is not None and contains_sensitive_key(metadata):
            raise ValueError("Metadata contém chave sensível proibida")

        evento = EventoCreate(
            empresaId=empresa_id,
            agenciaId=agencia_id,
            tipo=event_type,
            entidadeTipo=entidade_tipo,
            entidadeId=entidade_id,
            usuarioId=usuario_id,
            correlationId=correlation_id,
            causationId=causation_id,
            payload=payload,
            metadata=metadata,
            occurredAt=occurred_at,
        )
        return self.evento_service.create_evento(db, evento, commit=False)
