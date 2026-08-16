from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.escopo import PERFIS_VISAO_TOTAL
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_comentario import DemandaComentario
from app.models.usuario import Usuario
from app.repositories.demanda_comentario_repository import DemandaComentarioRepository
from app.schemas.demanda_comentario import (
    DemandaComentarioCreate,
    DemandaComentarioRead,
    DemandaComentarioUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "demanda"


class DemandaComentarioNotFoundError(ValueError):
    """Comentário inexistente **ou de outra Demanda**. Mesmo raciocínio de
    `DemandaChecklistItemNotFoundError` — um erro único para não confirmar a existência de um
    comentário de uma Demanda que quem pediu não pode ver."""


class DemandaComentarioNaoAutorizadoError(PermissionError):
    """Editar comentário alheio (ninguém pode, nem admin/gestor) ou excluir sem ser autor
    nem admin/gestor. Vira 403 na rota."""


class DemandaComentarioService:
    """Recebe a Demanda **já resolvida no escopo de quem chama** — mesma divisão de
    responsabilidade de `DemandaChecklistService`.

    ## Autoria

    Editar o TEXTO é restrito ao próprio autor, sempre — inclusive admin/gestor não editam
    comentário alheio, porque reescrever o conteúdo de outra pessoa corromperia a autoria do
    que foi dito. Excluir é permitido ao autor OU a admin/gestor (moderação): apagar não
    reescreve nada, e o evento de domínio preserva quem era o autor mesmo após o hard delete.
    """

    def __init__(
        self,
        repository: DemandaComentarioRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or DemandaComentarioRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def list_comentarios(self, db: Session, demanda_id: str) -> list[DemandaComentario]:
        return self.repository.list_by_demanda(db, demanda_id)

    def _get_comentario_da_demanda(
        self, db: Session, demanda_id: str, comentario_id: str
    ) -> DemandaComentario:
        comentario = self.repository.get_by_id(db, comentario_id)
        if comentario is None or comentario.demanda_id != demanda_id:
            raise DemandaComentarioNotFoundError("Comentário não encontrado")
        return comentario

    def criar_comentario(
        self, db: Session, demanda: Demanda, data: DemandaComentarioCreate, *, autor: Usuario
    ) -> DemandaComentario:
        try:
            now = agora_utc()
            comentario = DemandaComentario(
                id=str(uuid4()),
                demanda_id=demanda.id,
                autor_usuario_id=autor.id,
                texto=data.texto,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, comentario)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_COMENTARIO_CRIADO, autor.id,
                extra_payload={"comentarioId": comentario.id}, occurred_at=now,
            )
            db.commit()
            db.refresh(comentario)
            return comentario
        except Exception:
            db.rollback()
            raise

    def editar_comentario(
        self,
        db: Session,
        demanda: Demanda,
        comentario_id: str,
        data: DemandaComentarioUpdate,
        *,
        current_user: Usuario,
    ) -> DemandaComentario:
        try:
            comentario = self._get_comentario_da_demanda(db, demanda.id, comentario_id)
            if comentario.autor_usuario_id != current_user.id:
                raise DemandaComentarioNaoAutorizadoError(
                    "Somente o autor pode editar o próprio comentário"
                )

            if data.texto == comentario.texto:
                return comentario

            now = agora_utc()
            comentario.texto = data.texto
            comentario.updated_at = now
            comentario.editado_em = now
            self.repository.update(db, comentario)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_COMENTARIO_EDITADO, current_user.id,
                extra_payload={"comentarioId": comentario.id}, occurred_at=now,
            )
            db.commit()
            db.refresh(comentario)
            return comentario
        except Exception:
            db.rollback()
            raise

    def excluir_comentario(
        self, db: Session, demanda: Demanda, comentario_id: str, *, current_user: Usuario
    ) -> None:
        try:
            comentario = self._get_comentario_da_demanda(db, demanda.id, comentario_id)
            eh_autor = comentario.autor_usuario_id == current_user.id
            eh_moderador = current_user.perfil_base in PERFIS_VISAO_TOTAL
            if not (eh_autor or eh_moderador):
                raise DemandaComentarioNaoAutorizadoError(
                    "Somente o autor ou admin/gestor podem excluir este comentário"
                )

            now = agora_utc()
            autor_original = comentario.autor_usuario_id
            self.repository.delete(db, comentario)
            # `autorUsuarioId` só é necessário aqui: em criado/editado o ator SEMPRE é o
            # autor (o próprio Evento.usuario_id já cobre isso). Em removido, o ator pode
            # ser um moderador diferente do autor original — sem o payload, essa informação
            # se perderia com a linha física apagada.
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_COMENTARIO_REMOVIDO, current_user.id,
                extra_payload={"comentarioId": comentario_id, "autorUsuarioId": autor_original},
                occurred_at=now,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def to_read(comentario: DemandaComentario) -> DemandaComentarioRead:
        return DemandaComentarioRead(
            id=comentario.id,
            demandaId=comentario.demanda_id,
            autorUsuarioId=comentario.autor_usuario_id,
            texto=comentario.texto,
            createdAt=comentario.created_at,
            updatedAt=comentario.updated_at,
            editadoEm=comentario.editado_em,
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
