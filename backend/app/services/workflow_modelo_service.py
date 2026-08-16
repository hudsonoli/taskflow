from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referencias import gerar_proxima_referencia
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.workflow_modelo import WorkflowModelo
from app.models.workflow_modelo_etapa import WorkflowModeloEtapa
from app.models.workflow_modelo_etapa_responsavel import WorkflowModeloEtapaResponsavel
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.workflow_modelo_repository import WorkflowModeloRepository
from app.schemas.workflow_modelo import (
    WorkflowModeloCreate,
    WorkflowModeloEtapaRead,
    WorkflowModeloEtapaWrite,
    WorkflowModeloRead,
    WorkflowModeloUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "workflow_modelo"

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_ARQUIVADO = "arquivado"

# Mesmo conjunto usado em Departamento/Projeto/Demanda: um usuário nestes estados não pode
# ser DEFINIDO como responsável novo de uma etapa. Vínculo histórico não é afetado.
STATUS_USUARIO_INVALIDO_COMO_RESPONSAVEL = {"arquivado", "inativo", "bloqueado"}


class WorkflowModeloNotFoundError(ValueError):
    pass


class WorkflowModeloConflictError(ValueError):
    pass


class WorkflowModeloArquivadoConflictError(ValueError):
    """Nome já pertence a um modelo arquivado — a UI oferece restaurar em vez de mostrar
    erro de duplicidade (ver docs/padrao-arquivamento.md)."""

    def __init__(self, message: str, *, workflow_modelo_arquivado_id: str) -> None:
        super().__init__(message)
        self.workflow_modelo_arquivado_id = workflow_modelo_arquivado_id


class WorkflowModeloInvalidTransitionError(ValueError):
    pass


class WorkflowModeloResponsavelInvalidoError(ValueError):
    """Responsável de etapa inexistente, de outra empresa ou em status que não aceita novo
    vínculo."""


class WorkflowModeloService:
    def __init__(
        self,
        repository: WorkflowModeloRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or WorkflowModeloRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_workflow_modelo(
        self,
        db: Session,
        data: WorkflowModeloCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str,
    ) -> WorkflowModelo:
        from app.core.slugify import gerar_codigo_interno

        codigo_interno = gerar_codigo_interno(
            data.nome,
            existe_conflito=lambda candidato: self.repository.get_by_codigo_interno(
                db, empresa_id=empresa_id, codigo_interno=candidato
            )
            is not None,
        )
        return self._criar(
            db,
            nome=data.nome,
            etapas_data=data.etapas,
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            actor_usuario_id=actor_usuario_id,
        )

    def _criar(
        self,
        db: Session,
        *,
        nome: str,
        etapas_data: list[WorkflowModeloEtapaWrite],
        empresa_id: str,
        codigo_interno: str,
        actor_usuario_id: str,
    ) -> WorkflowModelo:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(nome)

        try:
            self._ensure_nome_disponivel(db, empresa_id, nome_normalizado)
            usuario_ids = {str(uid) for etapa in etapas_data for uid in etapa.usuario_responsavel_ids}
            self._ensure_responsaveis_validos(db, empresa_id, usuario_ids)

            # Contador, entidade e evento na MESMA transação: se a criação falhar abaixo, o
            # incremento da sequência sofre rollback junto e o número não é queimado.
            referencia = gerar_proxima_referencia(db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE)

            workflow_modelo = WorkflowModelo(
                id=str(uuid4()),
                empresa_id=empresa_id,
                codigo_interno=codigo_interno,
                codigo_referencia=referencia.codigo_referencia,
                ano_referencia=referencia.ano_referencia,
                sequencial_referencia=referencia.sequencial_referencia,
                nome=nome,
                nome_normalizado=nome_normalizado,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, workflow_modelo)
            self._substituir_etapas(db, workflow_modelo, etapas_data, now=now)
            self._publish_event(
                db, workflow_modelo, DomainEventType.WORKFLOW_MODELO_CRIADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(workflow_modelo)
            return workflow_modelo
        except IntegrityError:
            # Corrida: dois inserts concorrentes passaram pelos checks antes de qualquer
            # commit. Reconsulta para distinguir conflito comum de conflito-arquivado.
            db.rollback()
            existente = self.repository.get_by_nome_normalizado(
                db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
            ) or self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=codigo_interno)
            if existente is not None and existente.status == STATUS_ARQUIVADO:
                raise WorkflowModeloArquivadoConflictError(
                    "Já existe um modelo de workflow arquivado com este nome",
                    workflow_modelo_arquivado_id=existente.id,
                ) from None
            raise WorkflowModeloConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_workflow_modelos(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowModelo]:
        return self.repository.list(
            db, empresa_id=empresa_id, status=status, search=search, limit=limit, offset=offset
        )

    def get_workflow_modelo(self, db: Session, workflow_modelo_id: str) -> WorkflowModelo:
        workflow_modelo = self.repository.get_by_id(db, workflow_modelo_id)
        if workflow_modelo is None:
            raise WorkflowModeloNotFoundError("Modelo de workflow não encontrado")
        return workflow_modelo

    # ----------------------------------------------------------------------------------
    # Alteração e ciclo de vida
    # ----------------------------------------------------------------------------------

    def update_workflow_modelo(
        self,
        db: Session,
        workflow_modelo_id: str,
        data: WorkflowModeloUpdate,
        *,
        actor_usuario_id: str,
    ) -> WorkflowModelo:
        try:
            workflow_modelo = self.get_workflow_modelo(db, workflow_modelo_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            now = agora_utc()

            if "nome" in updates and updates["nome"] != workflow_modelo.nome:
                nome_normalizado = self._normalizar_nome(updates["nome"])
                if nome_normalizado != workflow_modelo.nome_normalizado:
                    self._ensure_nome_disponivel(
                        db, workflow_modelo.empresa_id, nome_normalizado, exclude_id=workflow_modelo.id
                    )
                workflow_modelo.nome = updates["nome"]
                workflow_modelo.nome_normalizado = nome_normalizado
                changed_fields.append("nome")

            if updates.get("etapas") is not None:
                usuario_ids = {str(uid) for etapa in data.etapas for uid in etapa.usuario_responsavel_ids}
                self._ensure_responsaveis_validos(db, workflow_modelo.empresa_id, usuario_ids)
                self._substituir_etapas(db, workflow_modelo, data.etapas, now=now)
                changed_fields.append("etapas")

            if "status" in updates and updates["status"] != workflow_modelo.status:
                if workflow_modelo.status == STATUS_ARQUIVADO:
                    raise WorkflowModeloInvalidTransitionError(
                        "Modelo de workflow arquivado deve ser restaurado antes de mudar de status"
                    )
                workflow_modelo.status = updates["status"]
                changed_fields.append("status")

            if changed_fields:
                workflow_modelo.updated_at = now
                self.repository.update(db, workflow_modelo)
                self._publish_event(
                    db,
                    workflow_modelo,
                    DomainEventType.WORKFLOW_MODELO_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(workflow_modelo)
            return workflow_modelo
        except IntegrityError:
            db.rollback()
            raise WorkflowModeloConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def arquivar_workflow_modelo(
        self,
        db: Session,
        workflow_modelo_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> WorkflowModelo:
        """Arquivar não apaga etapas nem responsáveis — só passa a recusar novos vínculos a
        este modelo (ex.: seleção no cadastro de tarefas, quando existir)."""
        try:
            workflow_modelo = self.get_workflow_modelo(db, workflow_modelo_id)
            if workflow_modelo.status == STATUS_ARQUIVADO:
                raise WorkflowModeloInvalidTransitionError("Modelo de workflow já está arquivado")

            now = agora_utc()
            workflow_modelo.status_anterior_arquivamento = workflow_modelo.status
            workflow_modelo.status = STATUS_ARQUIVADO
            workflow_modelo.updated_at = now
            workflow_modelo.arquivado_at = now
            workflow_modelo.arquivado_por_usuario_id = actor_usuario_id
            workflow_modelo.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, workflow_modelo)
            self._publish_event(
                db, workflow_modelo, DomainEventType.WORKFLOW_MODELO_ARQUIVADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(workflow_modelo)
            return workflow_modelo
        except Exception:
            db.rollback()
            raise

    def restaurar_workflow_modelo(
        self,
        db: Session,
        workflow_modelo_id: str,
        *,
        actor_usuario_id: str,
    ) -> WorkflowModelo:
        """Restaura sempre para `ativo` — mesmo comportamento de Departamento. Não precisa
        checar conflito de nome: a unicidade vale entre todos os status."""
        try:
            workflow_modelo = self.get_workflow_modelo(db, workflow_modelo_id)
            if workflow_modelo.status != STATUS_ARQUIVADO:
                raise WorkflowModeloInvalidTransitionError("Somente modelo de workflow arquivado pode ser restaurado")

            now = agora_utc()
            workflow_modelo.status = STATUS_ATIVO
            workflow_modelo.updated_at = now
            workflow_modelo.restaurado_at = now
            workflow_modelo.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, workflow_modelo)
            self._publish_event(
                db, workflow_modelo, DomainEventType.WORKFLOW_MODELO_RESTAURADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(workflow_modelo)
            return workflow_modelo
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, db: Session, workflow_modelo: WorkflowModelo) -> WorkflowModeloRead:
        etapas = self.repository.list_etapas(db, workflow_modelo.id)
        responsaveis_por_etapa = self.repository.get_responsavel_ids_por_etapa(db, [etapa.id for etapa in etapas])
        etapas_read = [
            WorkflowModeloEtapaRead(
                id=etapa.id,
                ordem=etapa.ordem,
                nome=etapa.nome,
                tipo=etapa.tipo,
                quantidadeAntesDeadline=etapa.quantidade_antes_deadline,
                unidadePrazo=etapa.unidade_prazo,
                usuarioResponsavelIds=responsaveis_por_etapa.get(etapa.id, []),
            )
            for etapa in etapas
        ]
        return WorkflowModeloRead(
            id=workflow_modelo.id,
            empresaId=workflow_modelo.empresa_id,
            codigoInterno=workflow_modelo.codigo_interno,
            codigoReferencia=workflow_modelo.codigo_referencia,
            anoReferencia=workflow_modelo.ano_referencia,
            sequencialReferencia=workflow_modelo.sequencial_referencia,
            nome=workflow_modelo.nome,
            status=workflow_modelo.status,
            etapas=etapas_read,
            createdAt=workflow_modelo.created_at,
            updatedAt=workflow_modelo.updated_at,
            arquivadoAt=workflow_modelo.arquivado_at,
            arquivadoPorUsuarioId=workflow_modelo.arquivado_por_usuario_id,
            motivoArquivamento=workflow_modelo.motivo_arquivamento,
            restauradoAt=workflow_modelo.restaurado_at,
            restauradoPorUsuarioId=workflow_modelo.restaurado_por_usuario_id,
            statusAnteriorArquivamento=workflow_modelo.status_anterior_arquivamento,
        )

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _substituir_etapas(
        self,
        db: Session,
        workflow_modelo: WorkflowModelo,
        etapas_data: list[WorkflowModeloEtapaWrite],
        *,
        now: datetime,
    ) -> None:
        etapa_objetos = [
            WorkflowModeloEtapa(
                id=str(uuid4()),
                workflow_modelo_id=workflow_modelo.id,
                ordem=index,
                nome=etapa_data.nome,
                tipo=etapa_data.tipo,
                quantidade_antes_deadline=etapa_data.quantidade_antes_deadline,
                unidade_prazo=etapa_data.unidade_prazo,
                created_at=now,
                updated_at=now,
            )
            for index, etapa_data in enumerate(etapas_data, start=1)
        ]
        self.repository.replace_etapas(db, workflow_modelo_id=workflow_modelo.id, etapas=etapa_objetos)

        responsavel_rows = [
            WorkflowModeloEtapaResponsavel(
                workflow_modelo_etapa_id=etapa_objeto.id, usuario_id=str(uid), created_at=now
            )
            for etapa_objeto, etapa_data in zip(etapa_objetos, etapas_data)
            for uid in etapa_data.usuario_responsavel_ids
        ]
        self.repository.create_etapa_responsaveis(db, responsavel_rows)

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
                raise WorkflowModeloArquivadoConflictError(
                    "nome já pertence a um modelo de workflow arquivado",
                    workflow_modelo_arquivado_id=existente.id,
                )
            raise WorkflowModeloConflictError("nome já cadastrado para esta Empresa")

    def _ensure_responsaveis_validos(self, db: Session, empresa_id: str, usuario_ids: set[str]) -> None:
        """Cada responsável de etapa precisa existir, ser da MESMA empresa e estar apto a
        receber o vínculo. Cross-tenant é tratado aqui como responsável inválido — não vaza
        a existência de usuário de outra empresa."""
        for usuario_id in usuario_ids:
            usuario = self.usuario_repository.get_by_id(db, usuario_id)
            if usuario is None or usuario.empresa_id != empresa_id:
                raise WorkflowModeloResponsavelInvalidoError("Responsável de etapa não encontrado nesta empresa")
            if usuario.status in STATUS_USUARIO_INVALIDO_COMO_RESPONSAVEL:
                raise WorkflowModeloResponsavelInvalidoError(
                    f"Usuário com status '{usuario.status}' não pode ser definido como responsável de etapa"
                )

    def _publish_event(
        self,
        db: Session,
        workflow_modelo: WorkflowModelo,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": workflow_modelo.empresa_id,
            "workflow_modelo_id": workflow_modelo.id,
            "codigo_referencia": workflow_modelo.codigo_referencia,
            "timestamp": timestamp.isoformat(),
            "status": workflow_modelo.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=workflow_modelo.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=workflow_modelo.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
