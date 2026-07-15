from typing import Any

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.evento import Evento
from app.models.sessao_trabalho import SessaoTrabalho
from app.services.sessao_trabalho_service import (
    MOTIVO_AGUARDANDO_CLIENTE,
    MOTIVO_BLOQUEIO,
    MOTIVO_CANCELAMENTO,
    MOTIVO_CONCLUSAO,
    MOTIVO_MUDANCA_ETAPA,
    MOTIVO_PAUSA,
    SessaoTrabalhoService,
    ensure_utc,
)

DEMANDA_STATUS_ENCERRAMENTO = {
    "pausada": MOTIVO_PAUSA,
    "bloqueada": MOTIVO_BLOQUEIO,
    "aguardando_cliente": MOTIVO_AGUARDANDO_CLIENTE,
    "concluida": MOTIVO_CONCLUSAO,
    "cancelada": MOTIVO_CANCELAMENTO,
}


class TrafegoEventHandler:
    def __init__(self, sessao_service: SessaoTrabalhoService | None = None) -> None:
        self.sessao_service = sessao_service or SessaoTrabalhoService()

    def handle(self, db: Session, evento: Evento) -> SessaoTrabalho | None:
        if evento.tipo == DomainEventType.DEMANDA_STATUS_ALTERADO.value:
            return self._handle_demanda_status_alterado(db, evento)
        if evento.tipo in {
            DomainEventType.WORKFLOW_ETAPA_AVANCADA.value,
            DomainEventType.WORKFLOW_ETAPA_RETROCEDIDA.value,
        }:
            return self._handle_workflow_mudanca_etapa(db, evento)
        if evento.tipo == DomainEventType.WORKFLOW_ETAPA_BLOQUEADA.value:
            return self._handle_workflow_bloqueio(db, evento)
        return None

    def _handle_demanda_status_alterado(self, db: Session, evento: Evento) -> SessaoTrabalho | None:
        if evento.entidade_tipo != "demanda":
            return None
        demanda_id = self._resolve_demanda_id(evento)
        if demanda_id is None:
            return None

        payload = evento.payload
        status_novo = payload.get("statusNovo")
        usuario_id = self._payload_str(payload, "usuarioId") or evento.usuario_id
        departamento_id = self._payload_str(payload, "departamentoId")

        if status_novo == "em_execucao":
            if not usuario_id and not departamento_id:
                return None
            return self.sessao_service.open_session(
                db,
                empresa_id=evento.empresa_id,
                agencia_id=evento.agencia_id,
                demanda_id=demanda_id,
                workflow_etapa_id=self._payload_str(payload, "workflowEtapaId") or self._payload_str(payload, "etapaId"),
                usuario_id=usuario_id,
                departamento_id=departamento_id,
                allow_usuario_and_departamento=bool(payload.get("permitirUsuarioEDepartamento")),
                evento_inicio_id=evento.id,
                inicio_em=ensure_utc(evento.occurred_at),
            )

        motivo = DEMANDA_STATUS_ENCERRAMENTO.get(str(status_novo))
        if not motivo:
            return None
        return self.sessao_service.close_active_equivalent(
            db,
            demanda_id=demanda_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            evento_fim_id=evento.id,
            fim_em=ensure_utc(evento.occurred_at),
            motivo_encerramento=motivo,
        )

    def _handle_workflow_mudanca_etapa(self, db: Session, evento: Evento) -> SessaoTrabalho | None:
        payload = evento.payload
        demanda_id = self._payload_str(payload, "demandaId")
        if not demanda_id:
            return None

        usuario_origem_id = self._payload_str(payload, "usuarioOrigemId") or self._payload_str(payload, "usuarioId") or evento.usuario_id
        departamento_origem_id = self._payload_str(payload, "departamentoOrigemId") or self._payload_str(payload, "departamentoId")
        result = self.sessao_service.close_active_equivalent(
            db,
            demanda_id=demanda_id,
            usuario_id=usuario_origem_id,
            departamento_id=departamento_origem_id,
            evento_fim_id=evento.id,
            fim_em=ensure_utc(evento.occurred_at),
            motivo_encerramento=MOTIVO_MUDANCA_ETAPA,
        )

        if payload.get("iniciarExecucao") is not True:
            return result

        etapa_destino_id = self._payload_str(payload, "etapaDestinoId")
        usuario_destino_id = self._payload_str(payload, "usuarioDestinoId") or self._payload_str(payload, "usuarioId") or evento.usuario_id
        departamento_destino_id = self._payload_str(payload, "departamentoDestinoId") or self._payload_str(payload, "departamentoId")
        if not etapa_destino_id or (not usuario_destino_id and not departamento_destino_id):
            return result

        return self.sessao_service.open_session(
            db,
            empresa_id=evento.empresa_id,
            agencia_id=evento.agencia_id,
            demanda_id=demanda_id,
            workflow_etapa_id=etapa_destino_id,
            usuario_id=usuario_destino_id,
            departamento_id=departamento_destino_id,
            allow_usuario_and_departamento=bool(payload.get("permitirUsuarioEDepartamento")),
            evento_inicio_id=evento.id,
            inicio_em=ensure_utc(evento.occurred_at),
        )

    def _handle_workflow_bloqueio(self, db: Session, evento: Evento) -> SessaoTrabalho | None:
        payload = evento.payload
        demanda_id = self._payload_str(payload, "demandaId")
        if not demanda_id:
            return None
        usuario_id = self._payload_str(payload, "usuarioId") or evento.usuario_id
        departamento_id = self._payload_str(payload, "departamentoId")
        return self.sessao_service.close_active_equivalent(
            db,
            demanda_id=demanda_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            evento_fim_id=evento.id,
            fim_em=ensure_utc(evento.occurred_at),
            motivo_encerramento=MOTIVO_BLOQUEIO,
        )

    def _resolve_demanda_id(self, evento: Evento) -> str | None:
        payload_demanda_id = self._payload_str(evento.payload, "demandaId")
        if payload_demanda_id and payload_demanda_id != evento.entidade_id:
            return None
        return evento.entidade_id

    def _payload_str(self, payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        return value if isinstance(value, str) and value else None
