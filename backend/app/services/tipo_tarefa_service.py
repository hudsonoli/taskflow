from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.tipo_tarefa import TipoTarefa
from app.repositories.tipo_tarefa_repository import TipoTarefaRepository
from app.schemas.tipo_tarefa import (
    TipoTarefaCreate,
    TipoTarefaDiretorioRead,
    TipoTarefaRead,
    TipoTarefaUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "tipo_tarefa"

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_ARQUIVADO = "arquivado"


class TipoTarefaNotFoundError(ValueError):
    pass


class TipoTarefaConflictError(ValueError):
    pass


class TipoTarefaArquivadoConflictError(ValueError):
    """Nome já pertence a um Tipo de Tarefa arquivado — a UI oferece restaurar em vez de
    mostrar erro de duplicidade (ver docs/padrao-arquivamento.md)."""

    def __init__(self, message: str, *, tipo_tarefa_arquivado_id: str) -> None:
        super().__init__(message)
        self.tipo_tarefa_arquivado_id = tipo_tarefa_arquivado_id


class TipoTarefaInvalidTransitionError(ValueError):
    pass


class TipoTarefaService:
    def __init__(
        self,
        repository: TipoTarefaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or TipoTarefaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_tipo_tarefa(
        self,
        db: Session,
        data: TipoTarefaCreate,
        *,
        empresa_id: str,
        # `None` só para o seed (app/cli/seed_tipos_tarefa.py) — roda fora de uma sessão HTTP
        # autenticada e não tem actor real. A rota sempre passa `current_user.id`.
        actor_usuario_id: str | None,
    ) -> TipoTarefa:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(data.nome)

        try:
            self._ensure_nome_disponivel(db, empresa_id, nome_normalizado)

            tipo_tarefa = TipoTarefa(
                id=str(uuid4()),
                empresa_id=empresa_id,
                nome=data.nome,
                nome_normalizado=nome_normalizado,
                descricao=data.descricao,
                ordem=data.ordem,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, tipo_tarefa)
            self._publish_event(
                db, tipo_tarefa, DomainEventType.TIPO_TAREFA_CRIADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(tipo_tarefa)
            return tipo_tarefa
        except IntegrityError:
            # Corrida: dois inserts concorrentes passaram pelo check antes de qualquer commit.
            db.rollback()
            existente = self.repository.get_by_nome_normalizado(
                db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
            )
            if existente is not None and existente.status == STATUS_ARQUIVADO:
                raise TipoTarefaArquivadoConflictError(
                    "Já existe um Tipo de Tarefa arquivado com este nome",
                    tipo_tarefa_arquivado_id=existente.id,
                ) from None
            raise TipoTarefaConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_tipos_tarefa(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TipoTarefa]:
        return self.repository.list(
            db, empresa_id=empresa_id, status=status, search=search, limit=limit, offset=offset
        )

    def get_tipo_tarefa(self, db: Session, tipo_tarefa_id: str) -> TipoTarefa:
        tipo_tarefa = self.repository.get_by_id(db, tipo_tarefa_id)
        if tipo_tarefa is None:
            raise TipoTarefaNotFoundError("Tipo de Tarefa não encontrado")
        return tipo_tarefa

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[TipoTarefa]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    # ----------------------------------------------------------------------------------
    # Alteração e ciclo de vida
    # ----------------------------------------------------------------------------------

    def update_tipo_tarefa(
        self,
        db: Session,
        tipo_tarefa_id: str,
        data: TipoTarefaUpdate,
        *,
        actor_usuario_id: str,
    ) -> TipoTarefa:
        try:
            tipo_tarefa = self.get_tipo_tarefa(db, tipo_tarefa_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            now = agora_utc()

            if "nome" in updates and updates["nome"] != tipo_tarefa.nome:
                nome_normalizado = self._normalizar_nome(updates["nome"])
                if nome_normalizado != tipo_tarefa.nome_normalizado:
                    self._ensure_nome_disponivel(
                        db, tipo_tarefa.empresa_id, nome_normalizado, exclude_id=tipo_tarefa.id
                    )
                tipo_tarefa.nome = updates["nome"]
                tipo_tarefa.nome_normalizado = nome_normalizado
                changed_fields.append("nome")

            if "descricao" in updates and updates["descricao"] != tipo_tarefa.descricao:
                tipo_tarefa.descricao = updates["descricao"]
                changed_fields.append("descricao")

            if "ordem" in updates and updates["ordem"] != tipo_tarefa.ordem:
                tipo_tarefa.ordem = updates["ordem"]
                changed_fields.append("ordem")

            if "status" in updates and updates["status"] != tipo_tarefa.status:
                if tipo_tarefa.status == STATUS_ARQUIVADO:
                    raise TipoTarefaInvalidTransitionError(
                        "Tipo de Tarefa arquivado deve ser restaurado antes de mudar de status"
                    )
                tipo_tarefa.status = updates["status"]
                changed_fields.append("status")

            if changed_fields:
                tipo_tarefa.updated_at = now
                self.repository.update(db, tipo_tarefa)
                self._publish_event(
                    db,
                    tipo_tarefa,
                    DomainEventType.TIPO_TAREFA_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(tipo_tarefa)
            return tipo_tarefa
        except IntegrityError:
            db.rollback()
            raise TipoTarefaConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def arquivar_tipo_tarefa(
        self,
        db: Session,
        tipo_tarefa_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> TipoTarefa:
        """Arquivar não apaga nada — só passa a recusar novo vínculo a este Tipo de Tarefa
        (ex.: novo item de Modelo de Campanha). Referência histórica já salva continua
        resolvendo pelo nome denormalizado no consumidor."""
        try:
            tipo_tarefa = self.get_tipo_tarefa(db, tipo_tarefa_id)
            if tipo_tarefa.status == STATUS_ARQUIVADO:
                raise TipoTarefaInvalidTransitionError("Tipo de Tarefa já está arquivado")

            now = agora_utc()
            tipo_tarefa.status_anterior_arquivamento = tipo_tarefa.status
            tipo_tarefa.status = STATUS_ARQUIVADO
            tipo_tarefa.updated_at = now
            tipo_tarefa.arquivado_at = now
            tipo_tarefa.arquivado_por_usuario_id = actor_usuario_id
            tipo_tarefa.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, tipo_tarefa)
            self._publish_event(
                db, tipo_tarefa, DomainEventType.TIPO_TAREFA_ARQUIVADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(tipo_tarefa)
            return tipo_tarefa
        except Exception:
            db.rollback()
            raise

    def restaurar_tipo_tarefa(
        self,
        db: Session,
        tipo_tarefa_id: str,
        *,
        actor_usuario_id: str,
    ) -> TipoTarefa:
        """Restaura sempre para `ativo` — mesmo comportamento de WorkflowModelo/Departamento.
        Não precisa checar conflito de nome: a unicidade vale entre todos os status."""
        try:
            tipo_tarefa = self.get_tipo_tarefa(db, tipo_tarefa_id)
            if tipo_tarefa.status != STATUS_ARQUIVADO:
                raise TipoTarefaInvalidTransitionError("Somente Tipo de Tarefa arquivado pode ser restaurado")

            now = agora_utc()
            tipo_tarefa.status = STATUS_ATIVO
            tipo_tarefa.updated_at = now
            tipo_tarefa.restaurado_at = now
            tipo_tarefa.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, tipo_tarefa)
            self._publish_event(
                db, tipo_tarefa, DomainEventType.TIPO_TAREFA_RESTAURADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(tipo_tarefa)
            return tipo_tarefa
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, tipo_tarefa: TipoTarefa) -> TipoTarefaRead:
        return TipoTarefaRead(
            id=tipo_tarefa.id,
            empresaId=tipo_tarefa.empresa_id,
            nome=tipo_tarefa.nome,
            descricao=tipo_tarefa.descricao,
            ordem=tipo_tarefa.ordem,
            status=tipo_tarefa.status,
            createdAt=tipo_tarefa.created_at,
            updatedAt=tipo_tarefa.updated_at,
            arquivadoAt=tipo_tarefa.arquivado_at,
            arquivadoPorUsuarioId=tipo_tarefa.arquivado_por_usuario_id,
            motivoArquivamento=tipo_tarefa.motivo_arquivamento,
            restauradoAt=tipo_tarefa.restaurado_at,
            restauradoPorUsuarioId=tipo_tarefa.restaurado_por_usuario_id,
            statusAnteriorArquivamento=tipo_tarefa.status_anterior_arquivamento,
        )

    def to_diretorio_read(self, tipo_tarefa: TipoTarefa) -> TipoTarefaDiretorioRead:
        return TipoTarefaDiretorioRead(id=tipo_tarefa.id, nome=tipo_tarefa.nome)

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _ensure_nome_disponivel(
        self,
        db: Session,
        empresa_id: str,
        nome_normalizado: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existente = self.repository.get_by_nome_normalizado(
            db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
        )
        if existente is not None and existente.id != exclude_id:
            if existente.status == STATUS_ARQUIVADO:
                raise TipoTarefaArquivadoConflictError(
                    "nome já pertence a um Tipo de Tarefa arquivado",
                    tipo_tarefa_arquivado_id=existente.id,
                )
            raise TipoTarefaConflictError("nome já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        tipo_tarefa: TipoTarefa,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": tipo_tarefa.empresa_id,
            "tipo_tarefa_id": tipo_tarefa.id,
            "timestamp": timestamp.isoformat(),
            "status": tipo_tarefa.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=tipo_tarefa.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=tipo_tarefa.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
