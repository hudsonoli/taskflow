from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.usuario_cargo import UsuarioCargo
from app.repositories.cargo_repository import CargoRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_cargo_repository import UsuarioCargoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario_cargo import (
    UsuarioCargoCreate,
    UsuarioCargoEncerrar,
    UsuarioCargoResponse,
    UsuarioCargoUpdate,
)
from app.services.cargo_service import STATUS_ATIVA as CARGO_STATUS_ATIVA
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import STATUS_ATIVA as EMPRESA_STATUS_ATIVA
from app.services.usuario_service import STATUS_ATIVO as USUARIO_STATUS_ATIVO

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"


class UsuarioCargoNotFoundError(ValueError):
    pass


class UsuarioCargoConflictError(ValueError):
    pass


class UsuarioCargoInvalidDataError(ValueError):
    pass


class UsuarioCargoInvalidTransitionError(ValueError):
    pass


class UsuarioCargoService:
    def __init__(
        self,
        repository: UsuarioCargoRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        cargo_repository: CargoRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or UsuarioCargoRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.cargo_repository = cargo_repository or CargoRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def vincular_usuario_cargo(
        self,
        db: Session,
        data: UsuarioCargoCreate,
        *,
        actor_usuario_id: str,
    ) -> UsuarioCargo:
        empresa_id = str(data.empresa_id)
        usuario_id = str(data.usuario_id)
        cargo_id = str(data.cargo_id)
        now = datetime.now(timezone.utc)
        vinculo = UsuarioCargo(
            id=str(uuid4()),
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            cargo_id=cargo_id,
            principal=data.principal,
            status=STATUS_ATIVO,
            inicio_em=now,
            fim_em=None,
            motivo_encerramento=None,
            criado_por_usuario_id=actor_usuario_id,
            encerrado_por_usuario_id=None,
            created_at=now,
            updated_at=now,
        )

        try:
            self._ensure_payload_entities_active(db, empresa_id, usuario_id, cargo_id)
            self._ensure_no_active_duplicate(db, empresa_id, usuario_id, cargo_id)
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
                    DomainEventType.USUARIO_CARGO_ALTERADO,
                    actor_usuario_id,
                    campos_alterados=["principal"],
                    occurred_at=now,
                )
            self._publish_event(
                db,
                vinculo,
                DomainEventType.USUARIO_CARGO_VINCULADO,
                actor_usuario_id,
                campos_alterados=[],
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
        cargo_id: str | None = None,
        status: str | None = None,
        principal: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UsuarioCargo]:
        self._ensure_filter_entities_belong_to_empresa(db, empresa_id, usuario_id, cargo_id)
        return self.repository.list_by_empresa(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            cargo_id=cargo_id,
            status=status,
            principal=principal,
            limit=limit,
            offset=offset,
        )

    def obter_vinculo(self, db: Session, vinculo_id: str) -> UsuarioCargo:
        vinculo = self.repository.get_by_id(db, vinculo_id)
        if vinculo is None:
            raise UsuarioCargoNotFoundError("Vínculo não encontrado")
        return vinculo

    def alterar_vinculo(
        self,
        db: Session,
        vinculo_id: str,
        data: UsuarioCargoUpdate,
        *,
        actor_usuario_id: str,
    ) -> UsuarioCargo:
        try:
            vinculo = self.obter_vinculo(db, vinculo_id)
            if vinculo.status != STATUS_ATIVO:
                raise UsuarioCargoInvalidTransitionError("Vínculo inativo não pode ser alterado")

            updates = data.model_dump(exclude_unset=True, by_alias=False)
            changed_fields: list[str] = []
            now = datetime.now(timezone.utc)
            previous_principal = None

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
                        DomainEventType.USUARIO_CARGO_ALTERADO,
                        actor_usuario_id,
                        campos_alterados=["principal"],
                        occurred_at=now,
                    )
                self._publish_event(
                    db,
                    vinculo,
                    DomainEventType.USUARIO_CARGO_ALTERADO,
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
        data: UsuarioCargoEncerrar,
        *,
        actor_usuario_id: str,
    ) -> UsuarioCargo:
        try:
            vinculo = self.obter_vinculo(db, vinculo_id)
            if vinculo.status != STATUS_ATIVO:
                raise UsuarioCargoInvalidTransitionError("Vínculo já está inativo")

            now = datetime.now(timezone.utc)
            fim_em = now
            if fim_em < self._as_utc(vinculo.inicio_em):
                fim_em = self._as_utc(vinculo.inicio_em)

            vinculo.status = STATUS_INATIVO
            vinculo.fim_em = fim_em
            vinculo.motivo_encerramento = self._normalize_motivo(data.motivo_encerramento)
            vinculo.principal = False
            vinculo.encerrado_por_usuario_id = actor_usuario_id
            vinculo.updated_at = now
            self.repository.encerrar(db, vinculo)
            self._publish_event(
                db,
                vinculo,
                DomainEventType.USUARIO_CARGO_ENCERRADO,
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

    def to_response(self, vinculo: UsuarioCargo) -> UsuarioCargoResponse:
        return UsuarioCargoResponse(
            id=vinculo.id,
            empresaId=vinculo.empresa_id,
            usuarioId=vinculo.usuario_id,
            cargoId=vinculo.cargo_id,
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
        cargo_id: str,
    ) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
            raise UsuarioCargoInvalidDataError("Empresa não encontrada ou inativa")

        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id or usuario.status != USUARIO_STATUS_ATIVO:
            raise UsuarioCargoInvalidDataError("Usuário não encontrado ou inativo")

        cargo = self.cargo_repository.get_by_id(db, cargo_id)
        if cargo is None or cargo.empresa_id != empresa_id or cargo.status != CARGO_STATUS_ATIVA:
            raise UsuarioCargoInvalidDataError("Cargo não encontrado ou inativo")

    def _ensure_filter_entities_belong_to_empresa(
        self,
        db: Session,
        empresa_id: str,
        usuario_id: str | None,
        cargo_id: str | None,
    ) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
            raise UsuarioCargoInvalidDataError("Empresa não encontrada ou inativa")

        if usuario_id is not None:
            usuario = self.usuario_repository.get_by_id(db, usuario_id)
            if usuario is None or usuario.empresa_id != empresa_id or usuario.status != USUARIO_STATUS_ATIVO:
                raise UsuarioCargoInvalidDataError("Usuário não encontrado ou inativo")

        if cargo_id is not None:
            cargo = self.cargo_repository.get_by_id(db, cargo_id)
            if cargo is None or cargo.empresa_id != empresa_id or cargo.status != CARGO_STATUS_ATIVA:
                raise UsuarioCargoInvalidDataError("Cargo não encontrado ou inativo")

    def _ensure_no_active_duplicate(
        self,
        db: Session,
        empresa_id: str,
        usuario_id: str,
        cargo_id: str,
    ) -> None:
        existing = self.repository.get_active_by_usuario_cargo(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            cargo_id=cargo_id,
        )
        if existing is not None:
            raise UsuarioCargoConflictError("Vínculo ativo já existe para Usuário e Cargo")

    def _publish_event(
        self,
        db: Session,
        vinculo: UsuarioCargo,
        tipo: DomainEventType,
        actor_usuario_id: str,
        *,
        campos_alterados: list[str],
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": vinculo.empresa_id,
            "usuario_cargo_id": vinculo.id,
            "usuario_id": vinculo.usuario_id,
            "cargo_id": vinculo.cargo_id,
            "timestamp": timestamp.isoformat(),
            "actor_usuario_id": actor_usuario_id,
            "campos_alterados": campos_alterados,
        }

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=vinculo.empresa_id,
            entidade_tipo="usuario_cargo",
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
