from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_checklist_item import DemandaChecklistItem
from app.repositories.demanda_checklist_repository import DemandaChecklistRepository
from app.schemas.demanda_checklist import (
    DemandaChecklistItemCreate,
    DemandaChecklistItemRead,
    DemandaChecklistItemUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "demanda"


class DemandaChecklistItemNotFoundError(ValueError):
    """Item inexistente **ou de outra Demanda**. Um erro único pelos dois casos — mesmo
    raciocínio de `DemandaNotFoundError`: não confirmar a existência de um item de uma
    Demanda que quem pediu não pode ver."""


class DemandaChecklistReordenarInvalidoError(ValueError):
    """A lista enviada não é exatamente o conjunto de ids já existentes da Demanda."""


class DemandaChecklistService:
    """Recebe a Demanda **já resolvida no escopo de quem chama** (a rota busca via
    `DemandaService.get_demanda`) — este service nunca decide acesso, só valida que o item
    pedido pertence a ela."""

    def __init__(
        self,
        repository: DemandaChecklistRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or DemandaChecklistRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def list_itens(self, db: Session, demanda_id: str) -> list[DemandaChecklistItem]:
        return self.repository.list_by_demanda(db, demanda_id)

    def _get_item_da_demanda(self, db: Session, demanda_id: str, item_id: str) -> DemandaChecklistItem:
        item = self.repository.get_by_id(db, item_id)
        if item is None or item.demanda_id != demanda_id:
            raise DemandaChecklistItemNotFoundError("Item de checklist não encontrado")
        return item

    def criar_item(
        self,
        db: Session,
        demanda: Demanda,
        data: DemandaChecklistItemCreate,
        *,
        actor_usuario_id: str | None,
    ) -> DemandaChecklistItem:
        try:
            now = agora_utc()
            item = DemandaChecklistItem(
                id=str(uuid4()),
                demanda_id=demanda.id,
                texto=data.texto,
                ordem=self.repository.proxima_ordem(db, demanda.id),
                concluido=False,
                criado_por_usuario_id=actor_usuario_id,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, item)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_CHECKLIST_ITEM_CRIADO, actor_usuario_id,
                extra_payload={"itemId": item.id, "texto": item.texto}, occurred_at=now,
            )
            db.commit()
            db.refresh(item)
            return item
        except Exception:
            db.rollback()
            raise

    def atualizar_item(
        self,
        db: Session,
        demanda: Demanda,
        item_id: str,
        data: DemandaChecklistItemUpdate,
        *,
        actor_usuario_id: str | None,
    ) -> DemandaChecklistItem:
        try:
            item = self._get_item_da_demanda(db, demanda.id, item_id)
            now = agora_utc()
            eventos: list[tuple[DomainEventType, dict]] = []

            if data.texto is not None and data.texto != item.texto:
                item.texto = data.texto
                eventos.append(
                    (DomainEventType.DEMANDA_CHECKLIST_ITEM_ALTERADO, {"itemId": item.id, "texto": item.texto})
                )

            # Idempotente: reenviar o mesmo valor de `concluido` não gera evento nem toque em
            # updated_at — só uma mudança real de estado é fato novo.
            if data.concluido is not None and data.concluido != item.concluido:
                item.concluido = data.concluido
                if data.concluido:
                    item.concluido_em = now
                    item.concluido_por_usuario_id = actor_usuario_id
                    eventos.append((DomainEventType.DEMANDA_CHECKLIST_ITEM_CONCLUIDO, {"itemId": item.id}))
                else:
                    item.concluido_em = None
                    item.concluido_por_usuario_id = None
                    eventos.append((DomainEventType.DEMANDA_CHECKLIST_ITEM_REABERTO, {"itemId": item.id}))

            if eventos:
                item.updated_at = now
                self.repository.update(db, item)
                for tipo, payload in eventos:
                    self._publish_event(
                        db, demanda, tipo, actor_usuario_id, extra_payload=payload, occurred_at=now
                    )

            db.commit()
            db.refresh(item)
            return item
        except Exception:
            db.rollback()
            raise

    def excluir_item(
        self, db: Session, demanda: Demanda, item_id: str, *, actor_usuario_id: str | None
    ) -> None:
        try:
            item = self._get_item_da_demanda(db, demanda.id, item_id)
            now = agora_utc()
            self.repository.delete(db, item)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_CHECKLIST_ITEM_EXCLUIDO, actor_usuario_id,
                extra_payload={"itemId": item_id}, occurred_at=now,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    def reordenar(
        self, db: Session, demanda: Demanda, item_ids: list[str], *, actor_usuario_id: str | None
    ) -> list[DemandaChecklistItem]:
        """Sem evento de domínio — reordenar não altera conteúdo, e a instrução da fase só
        pede eventos para criação/alteração/conclusão/reabertura/exclusão."""
        try:
            atuais = self.repository.list_by_demanda(db, demanda.id)
            if {item.id for item in atuais} != set(item_ids) or len(item_ids) != len(atuais):
                raise DemandaChecklistReordenarInvalidoError(
                    "A lista precisa conter exatamente os itens já existentes desta demanda, sem repetição"
                )

            por_id = {item.id: item for item in atuais}
            now = agora_utc()
            for nova_ordem, item_id in enumerate(item_ids):
                item = por_id[item_id]
                if item.ordem != nova_ordem:
                    item.ordem = nova_ordem
                    item.updated_at = now
                    self.repository.update(db, item)

            db.commit()
            return self.repository.list_by_demanda(db, demanda.id)
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def to_read(item: DemandaChecklistItem) -> DemandaChecklistItemRead:
        return DemandaChecklistItemRead(
            id=item.id,
            demandaId=item.demanda_id,
            texto=item.texto,
            ordem=item.ordem,
            concluido=item.concluido,
            concluidoEm=item.concluido_em,
            concluidoPorUsuarioId=item.concluido_por_usuario_id,
            criadoPorUsuarioId=item.criado_por_usuario_id,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )

    def _publish_event(
        self, db: Session, demanda: Demanda, tipo: DomainEventType, actor_usuario_id: str | None,
        *, extra_payload: dict | None = None, occurred_at=None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": demanda.empresa_id,
            "demanda_id": demanda.id,
            "codigo_referencia": demanda.codigo_referencia,
            "timestamp": timestamp.isoformat(),
        }
        if extra_payload:
            payload.update(extra_payload)
        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=demanda.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=demanda.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )
