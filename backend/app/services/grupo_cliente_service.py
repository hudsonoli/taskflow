from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.slugify import gerar_codigo_interno
from app.domain.event_types import DomainEventType
from app.models.grupo_cliente import GrupoCliente
from app.repositories.grupo_cliente_repository import GrupoClienteRepository
from app.schemas.grupo_cliente import (
    GrupoClienteCreate,
    GrupoClienteDiretorioRead,
    GrupoClienteRead,
    GrupoClienteUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

# Padrão de arquivamento — contrato completo em docs/padrao-arquivamento.md. Diferença
# proposital deste domínio: só dois status (sem "inativo"), e a unicidade de nome vale
# entre ativos E arquivados (não só entre ativos) — ver _ensure_nome_disponivel.

STATUS_ATIVO = "ativo"
STATUS_ARQUIVADO = "arquivado"


class GrupoClienteNotFoundError(ValueError):
    pass


class GrupoClienteConflictError(ValueError):
    pass


class GrupoClienteArquivadoConflictError(ValueError):
    """Nome já pertence a um grupo arquivado — ver docs/padrao-arquivamento.md. Carrega o ID
    do registro arquivado pra a UI oferecer restaurar em vez de só mostrar um erro."""

    def __init__(self, message: str, *, grupo_cliente_arquivado_id: str) -> None:
        super().__init__(message)
        self.grupo_cliente_arquivado_id = grupo_cliente_arquivado_id


class GrupoClienteInvalidTransitionError(ValueError):
    pass


class GrupoClienteService:
    def __init__(
        self,
        repository: GrupoClienteRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or GrupoClienteRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def create_grupo_cliente(
        self,
        db: Session,
        data: GrupoClienteCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str,
    ) -> GrupoCliente:
        """Rota pública — sempre gera `codigoInterno` automaticamente. Nunca aceita um
        valor de fora (ver GrupoClienteCreate, que não tem esse campo)."""
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
            cor_identificacao=data.cor_identificacao,
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            actor_usuario_id=actor_usuario_id,
        )

    def create_grupo_cliente_com_codigo_legado(
        self,
        db: Session,
        *,
        nome: str,
        cor_identificacao: str,
        empresa_id: str,
        codigo_interno: str,
        actor_usuario_id: str | None = None,
    ) -> GrupoCliente:
        """Uso interno só do script de seed/importador — nunca exposta via rota HTTP.
        Idempotente: se `codigo_interno` já existe (qualquer status), retorna o registro
        existente sem criar duplicado."""
        existing = self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=codigo_interno)
        if existing is not None:
            return existing
        return self._criar(
            db,
            nome=nome,
            cor_identificacao=cor_identificacao,
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            actor_usuario_id=actor_usuario_id,
        )

    def _criar(
        self,
        db: Session,
        *,
        nome: str,
        cor_identificacao: str,
        empresa_id: str,
        codigo_interno: str,
        actor_usuario_id: str,
    ) -> GrupoCliente:
        now = datetime.now(timezone.utc)
        nome_normalizado = self._normalizar_nome(nome)
        grupo = GrupoCliente(
            id=str(uuid4()),
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            nome=nome,
            nome_normalizado=nome_normalizado,
            cor_identificacao=cor_identificacao,
            status=STATUS_ATIVO,
            created_at=now,
            updated_at=now,
        )

        try:
            self._ensure_nome_disponivel(db, empresa_id, nome_normalizado)
            self.repository.create(db, grupo)
            self._publish_event(db, grupo, DomainEventType.GRUPO_CLIENTE_CRIADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(grupo)
            return grupo
        except IntegrityError:
            # Corrida entre duas criações concorrentes com o mesmo nome/codigoInterno: os
            # checks acima passaram pras duas antes de qualquer uma commitar.
            db.rollback()
            existing = self.repository.get_by_nome_normalizado(
                db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
            ) or self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=codigo_interno)
            if existing is not None and existing.status == STATUS_ARQUIVADO:
                raise GrupoClienteArquivadoConflictError(
                    "Já existe um grupo arquivado com este nome/código interno",
                    grupo_cliente_arquivado_id=existing.id,
                ) from None
            raise GrupoClienteConflictError("nome ou codigoInterno já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def list_grupos_cliente(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GrupoCliente]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[GrupoCliente]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    def get_grupo_cliente(self, db: Session, grupo_id: str) -> GrupoCliente:
        grupo = self.repository.get_by_id(db, grupo_id)
        if grupo is None:
            raise GrupoClienteNotFoundError("Grupo de cliente não encontrado")
        return grupo

    def update_grupo_cliente(
        self,
        db: Session,
        grupo_id: str,
        data: GrupoClienteUpdate,
        *,
        actor_usuario_id: str,
    ) -> GrupoCliente:
        try:
            grupo = self.get_grupo_cliente(db, grupo_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "nome" in updates and updates["nome"] != grupo.nome:
                nome_normalizado = self._normalizar_nome(updates["nome"])
                if nome_normalizado != grupo.nome_normalizado:
                    self._ensure_nome_disponivel(db, grupo.empresa_id, nome_normalizado, exclude_id=grupo.id)
                grupo.nome = updates["nome"]
                grupo.nome_normalizado = nome_normalizado
                changed_fields.append("nome")

            if "cor_identificacao" in updates and updates["cor_identificacao"] != grupo.cor_identificacao:
                grupo.cor_identificacao = updates["cor_identificacao"]
                changed_fields.append("corIdentificacao")

            if changed_fields:
                now = datetime.now(timezone.utc)
                grupo.updated_at = now
                self.repository.update(db, grupo)
                self._publish_event(
                    db,
                    grupo,
                    DomainEventType.GRUPO_CLIENTE_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(grupo)
            return grupo
        except Exception:
            db.rollback()
            raise

    def arquivar_grupo_cliente(
        self,
        db: Session,
        grupo_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> GrupoCliente:
        try:
            grupo = self.get_grupo_cliente(db, grupo_id)
            if grupo.status == STATUS_ARQUIVADO:
                raise GrupoClienteInvalidTransitionError("Grupo de cliente já está arquivado")

            now = datetime.now(timezone.utc)
            grupo.status_anterior_arquivamento = grupo.status
            grupo.status = STATUS_ARQUIVADO
            grupo.updated_at = now
            grupo.arquivado_at = now
            grupo.arquivado_por_usuario_id = actor_usuario_id
            grupo.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, grupo)
            self._publish_event(db, grupo, DomainEventType.GRUPO_CLIENTE_ARQUIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(grupo)
            return grupo
        except Exception:
            db.rollback()
            raise

    def restaurar_grupo_cliente(
        self,
        db: Session,
        grupo_id: str,
        *,
        actor_usuario_id: str,
    ) -> GrupoCliente:
        """Restaura sempre pra "ativo" — único status não-arquivado que existe pra este
        domínio. Não precisa checar conflito de nome no momento da restauração: a unicidade
        de nome já vale entre ativos e arquivados (constraint de banco), então nenhum outro
        registro pode ter ocupado esse nome enquanto este estava arquivado."""
        try:
            grupo = self.get_grupo_cliente(db, grupo_id)
            if grupo.status != STATUS_ARQUIVADO:
                raise GrupoClienteInvalidTransitionError("Somente grupo de cliente arquivado pode ser restaurado")

            now = datetime.now(timezone.utc)
            grupo.status = STATUS_ATIVO
            grupo.updated_at = now
            grupo.restaurado_at = now
            grupo.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, grupo)
            self._publish_event(db, grupo, DomainEventType.GRUPO_CLIENTE_RESTAURADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(grupo)
            return grupo
        except Exception:
            db.rollback()
            raise

    def to_read(self, grupo: GrupoCliente) -> GrupoClienteRead:
        return GrupoClienteRead(
            id=grupo.id,
            empresaId=grupo.empresa_id,
            codigoInterno=grupo.codigo_interno,
            nome=grupo.nome,
            corIdentificacao=grupo.cor_identificacao,
            status=grupo.status,
            createdAt=grupo.created_at,
            updatedAt=grupo.updated_at,
            arquivadoAt=grupo.arquivado_at,
            arquivadoPorUsuarioId=grupo.arquivado_por_usuario_id,
            motivoArquivamento=grupo.motivo_arquivamento,
            restauradoAt=grupo.restaurado_at,
            restauradoPorUsuarioId=grupo.restaurado_por_usuario_id,
            statusAnteriorArquivamento=grupo.status_anterior_arquivamento,
        )

    def to_diretorio_read(self, grupo: GrupoCliente) -> GrupoClienteDiretorioRead:
        return GrupoClienteDiretorioRead(
            id=grupo.id,
            codigoInterno=grupo.codigo_interno,
            nome=grupo.nome,
            corIdentificacao=grupo.cor_identificacao,
            status=grupo.status,
        )

    def _ensure_nome_disponivel(
        self,
        db: Session,
        empresa_id: str,
        nome_normalizado: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        """Unicidade vale entre ativos E arquivados — conflito com QUALQUER status sempre
        retorna GrupoClienteArquivadoConflictError (oferece restaurar), nunca cria."""
        existing = self.repository.get_by_nome_normalizado(db, empresa_id=empresa_id, nome_normalizado=nome_normalizado)
        if existing is not None and existing.id != exclude_id:
            if existing.status == STATUS_ARQUIVADO:
                raise GrupoClienteArquivadoConflictError(
                    "nome já pertence a um grupo de cliente arquivado",
                    grupo_cliente_arquivado_id=existing.id,
                )
            raise GrupoClienteConflictError("nome já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        grupo: GrupoCliente,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": grupo.empresa_id,
            "grupo_cliente_id": grupo.id,
            "timestamp": timestamp.isoformat(),
            "status": grupo.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=grupo.empresa_id,
            entidade_tipo="grupo_cliente",
            entidade_id=grupo.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
