from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.usuario_departamento import UsuarioDepartamento
from app.repositories.departamento_repository import DepartamentoRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_departamento_repository import UsuarioDepartamentoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario_departamento import (
    UsuarioDepartamentoCreate,
    UsuarioDepartamentoEncerrar,
    UsuarioDepartamentoResponse,
    UsuarioDepartamentoUpdate,
)
from app.services.departamento_service import STATUS_ATIVA as DEPARTAMENTO_STATUS_ATIVA
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import STATUS_ATIVA as EMPRESA_STATUS_ATIVA
from app.services.usuario_service import STATUS_ATIVO as USUARIO_STATUS_ATIVO

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
PAPEL_HEAD = "head"


class UsuarioDepartamentoNotFoundError(ValueError):
    pass


class UsuarioDepartamentoConflictError(ValueError):
    pass


class UsuarioDepartamentoInvalidDataError(ValueError):
    pass


class UsuarioDepartamentoInvalidTransitionError(ValueError):
    pass


class UsuarioDepartamentoService:
    def __init__(
        self,
        repository: UsuarioDepartamentoRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        departamento_repository: DepartamentoRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or UsuarioDepartamentoRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.departamento_repository = departamento_repository or DepartamentoRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def vincular_usuario_departamento(
        self,
        db: Session,
        data: UsuarioDepartamentoCreate,
        *,
        actor_usuario_id: str,
    ) -> UsuarioDepartamento:
        empresa_id = str(data.empresa_id)
        usuario_id = str(data.usuario_id)
        departamento_id = str(data.departamento_id)
        now = datetime.now(timezone.utc)
        vinculo = UsuarioDepartamento(
            id=str(uuid4()),
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            papel=data.papel,
            principal=data.principal,
            status=STATUS_ATIVO,
            inicio_em=data.inicio_em,
            fim_em=None,
            motivo_encerramento=None,
            criado_por_usuario_id=actor_usuario_id,
            encerrado_por_usuario_id=None,
            created_at=now,
            updated_at=now,
        )

        try:
            self._ensure_payload_entities_active(db, empresa_id, usuario_id, departamento_id)
            self._ensure_no_active_duplicate(db, empresa_id, usuario_id, departamento_id)
            self._ensure_head_available(db, empresa_id, departamento_id, vinculo.papel)
            previous_principal = None
            if vinculo.principal:
                previous_principal = self.repository.get_active_principal_by_usuario(
                    db,
                    empresa_id=empresa_id,
                    usuario_id=usuario_id,
                )
                if previous_principal is not None:
                    previous_principal.principal = False
                    previous_principal.updated_at = now
                    self.repository.update(db, previous_principal)

            self.repository.create(db, vinculo)

            if previous_principal is not None:
                self._publish_event(
                    db,
                    previous_principal,
                    DomainEventType.USUARIO_DEPARTAMENTO_ALTERADO,
                    actor_usuario_id,
                    campos_alterados=["principal"],
                    occurred_at=now,
                )
            self._publish_event(
                db,
                vinculo,
                DomainEventType.USUARIO_DEPARTAMENTO_VINCULADO,
                actor_usuario_id,
                occurred_at=now,
            )
            db.commit()
            db.refresh(vinculo)
            return vinculo
        except Exception:
            db.rollback()
            raise

    def listar_vinculos(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        papel: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UsuarioDepartamento]:
        self._ensure_filter_entities_belong_to_empresa(db, empresa_id, usuario_id, departamento_id)
        return self.repository.list_by_empresa(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            papel=papel,
            status=status,
            limit=limit,
            offset=offset,
        )

    def obter_vinculo(self, db: Session, vinculo_id: str) -> UsuarioDepartamento:
        vinculo = self.repository.get_by_id(db, vinculo_id)
        if vinculo is None:
            raise UsuarioDepartamentoNotFoundError("Vínculo não encontrado")
        return vinculo

    def alterar_vinculo(
        self,
        db: Session,
        vinculo_id: str,
        data: UsuarioDepartamentoUpdate,
        *,
        actor_usuario_id: str,
    ) -> UsuarioDepartamento:
        try:
            vinculo = self.obter_vinculo(db, vinculo_id)
            if vinculo.status != STATUS_ATIVO:
                raise UsuarioDepartamentoInvalidTransitionError("Vínculo inativo não pode ser alterado")

            updates = data.model_dump(exclude_unset=True, by_alias=False)
            changed_fields: list[str] = []
            now = datetime.now(timezone.utc)
            previous_principal = None

            if "papel" in updates and updates["papel"] != vinculo.papel:
                self._ensure_head_available(
                    db,
                    vinculo.empresa_id,
                    vinculo.departamento_id,
                    updates["papel"],
                    exclude_id=vinculo.id,
                )
                vinculo.papel = updates["papel"]
                changed_fields.append("papel")

            if "principal" in updates and updates["principal"] != vinculo.principal:
                if updates["principal"] is True:
                    previous_principal = self.repository.get_active_principal_by_usuario(
                        db,
                        empresa_id=vinculo.empresa_id,
                        usuario_id=vinculo.usuario_id,
                    )
                    if previous_principal is not None and previous_principal.id != vinculo.id:
                        previous_principal.principal = False
                        previous_principal.updated_at = now
                        self.repository.update(db, previous_principal)
                vinculo.principal = updates["principal"]
                changed_fields.append("principal")

            if changed_fields:
                vinculo.updated_at = now
                self.repository.update(db, vinculo)
                if previous_principal is not None and previous_principal.id != vinculo.id:
                    self._publish_event(
                        db,
                        previous_principal,
                        DomainEventType.USUARIO_DEPARTAMENTO_ALTERADO,
                        actor_usuario_id,
                        campos_alterados=["principal"],
                        occurred_at=now,
                    )
                self._publish_event(
                    db,
                    vinculo,
                    DomainEventType.USUARIO_DEPARTAMENTO_ALTERADO,
                    actor_usuario_id,
                    campos_alterados=changed_fields,
                    occurred_at=now,
                )

            db.commit()
            db.refresh(vinculo)
            return vinculo
        except Exception:
            db.rollback()
            raise

    def encerrar_vinculo(
        self,
        db: Session,
        vinculo_id: str,
        data: UsuarioDepartamentoEncerrar,
        *,
        actor_usuario_id: str,
    ) -> UsuarioDepartamento:
        try:
            vinculo = self.obter_vinculo(db, vinculo_id)
            if vinculo.status != STATUS_ATIVO:
                raise UsuarioDepartamentoInvalidTransitionError("Vínculo já está inativo")
            if data.fim_em < self._as_utc(vinculo.inicio_em):
                raise UsuarioDepartamentoInvalidDataError("fimEm não pode ser anterior a inicioEm")

            now = datetime.now(timezone.utc)
            vinculo.status = STATUS_INATIVO
            vinculo.fim_em = data.fim_em
            vinculo.motivo_encerramento = self._normalize_motivo(data.motivo_encerramento)
            vinculo.principal = False
            vinculo.encerrado_por_usuario_id = actor_usuario_id
            vinculo.updated_at = now
            self.repository.encerrar(db, vinculo)
            self._publish_event(
                db,
                vinculo,
                DomainEventType.USUARIO_DEPARTAMENTO_ENCERRADO,
                actor_usuario_id,
                campos_alterados=["status", "fim_em", "principal", "encerrado_por_usuario_id"],
                occurred_at=now,
            )
            db.commit()
            db.refresh(vinculo)
            return vinculo
        except Exception:
            db.rollback()
            raise

    def to_response(self, vinculo: UsuarioDepartamento) -> UsuarioDepartamentoResponse:
        return UsuarioDepartamentoResponse(
            id=vinculo.id,
            empresaId=vinculo.empresa_id,
            usuarioId=vinculo.usuario_id,
            departamentoId=vinculo.departamento_id,
            papel=vinculo.papel,
            principal=vinculo.principal,
            status=vinculo.status,
            inicioEm=vinculo.inicio_em,
            fimEm=vinculo.fim_em,
            motivoEncerramento=vinculo.motivo_encerramento,
            criadoPorUsuarioId=vinculo.criado_por_usuario_id,
            encerradoPorUsuarioId=vinculo.encerrado_por_usuario_id,
            createdAt=vinculo.created_at,
            updatedAt=vinculo.updated_at,
        )

    def _ensure_payload_entities_active(
        self,
        db: Session,
        empresa_id: str,
        usuario_id: str,
        departamento_id: str,
    ) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
            raise UsuarioDepartamentoInvalidDataError("Empresa não encontrada ou inativa")

        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id or usuario.status != USUARIO_STATUS_ATIVO:
            raise UsuarioDepartamentoInvalidDataError("Usuário não encontrado ou inativo")

        departamento = self.departamento_repository.get_by_id(db, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id or departamento.status != DEPARTAMENTO_STATUS_ATIVA:
            raise UsuarioDepartamentoInvalidDataError("Departamento não encontrado ou inativo")

    def _ensure_filter_entities_belong_to_empresa(
        self,
        db: Session,
        empresa_id: str,
        usuario_id: str | None,
        departamento_id: str | None,
    ) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
            raise UsuarioDepartamentoInvalidDataError("Empresa não encontrada ou inativa")

        if usuario_id is not None:
            usuario = self.usuario_repository.get_by_id(db, usuario_id)
            if usuario is None or usuario.empresa_id != empresa_id:
                raise UsuarioDepartamentoInvalidDataError("Usuário não encontrado ou inativo")

        if departamento_id is not None:
            departamento = self.departamento_repository.get_by_id(db, departamento_id)
            if departamento is None or departamento.empresa_id != empresa_id:
                raise UsuarioDepartamentoInvalidDataError("Departamento não encontrado ou inativo")

    def _ensure_no_active_duplicate(
        self,
        db: Session,
        empresa_id: str,
        usuario_id: str,
        departamento_id: str,
    ) -> None:
        existing = self.repository.get_active_by_usuario_departamento(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
        )
        if existing is not None:
            raise UsuarioDepartamentoConflictError("Vínculo ativo já existe para Usuário e Departamento")

    def _ensure_head_available(
        self,
        db: Session,
        empresa_id: str,
        departamento_id: str,
        papel: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        if papel != PAPEL_HEAD:
            return
        existing = self.repository.get_active_head_by_departamento(
            db,
            empresa_id=empresa_id,
            departamento_id=departamento_id,
        )
        if existing is not None and existing.id != exclude_id:
            raise UsuarioDepartamentoConflictError("Departamento já possui Head ativo")

    def _publish_event(
        self,
        db: Session,
        vinculo: UsuarioDepartamento,
        tipo: DomainEventType,
        actor_usuario_id: str,
        *,
        campos_alterados: list[str] | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": vinculo.empresa_id,
            "usuario_departamento_id": vinculo.id,
            "usuario_id": vinculo.usuario_id,
            "departamento_id": vinculo.departamento_id,
            "timestamp": timestamp.isoformat(),
            "actor_usuario_id": actor_usuario_id,
        }
        if campos_alterados is not None:
            payload["campos_alterados"] = campos_alterados

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=vinculo.empresa_id,
            entidade_tipo="usuario_departamento",
            entidade_id=vinculo.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalize_motivo(motivo: str | None) -> str | None:
        if motivo is None:
            return None
        normalized = " ".join(motivo.strip().split())
        return normalized or None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
