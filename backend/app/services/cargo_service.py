from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.cargo import Cargo
from app.repositories.cargo_repository import CargoRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.cargo import CargoCreate, CargoResponse, CargoUpdate
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import STATUS_ARQUIVADA as EMPRESA_STATUS_ARQUIVADA
from app.services.empresa_service import STATUS_INATIVA as EMPRESA_STATUS_INATIVA

STATUS_ATIVA = "ativa"
STATUS_INATIVA = "inativa"
STATUS_ARQUIVADA = "arquivada"


class CargoNotFoundError(ValueError):
    pass


class CargoConflictError(ValueError):
    pass


class CargoInvalidTransitionError(ValueError):
    pass


class CargoInvalidEmpresaError(ValueError):
    pass


class CargoInvalidDataError(ValueError):
    pass


class CargoService:
    def __init__(
        self,
        repository: CargoRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or CargoRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def create_cargo(
        self,
        db: Session,
        data: CargoCreate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Cargo:
        empresa_id = str(data.empresa_id)
        codigo_interno = self._normalize_codigo_interno(data.codigo_interno)
        nome = self._normalize_nome(data.nome)
        descricao = self._normalize_descricao(data.descricao)
        self._ensure_required("codigoInterno", codigo_interno)
        self._ensure_required("nome", nome)
        now = datetime.now(timezone.utc)
        cargo = Cargo(
            id=str(uuid4()),
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            nome=nome,
            descricao=descricao,
            status=STATUS_ATIVA,
            created_at=now,
            updated_at=now,
            inativado_at=None,
            motivo_inativacao=None,
            inativado_por_usuario_id=None,
        )

        try:
            self._ensure_empresa_accepts_cargo(db, empresa_id)
            self._ensure_codigo_interno_available(db, empresa_id, cargo.codigo_interno)
            self._ensure_nome_available(db, empresa_id, cargo.nome)
            self.repository.create(db, cargo)
            self._publish_event(db, cargo, DomainEventType.CARGO_CRIADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(cargo)
            return cargo
        except Exception:
            db.rollback()
            raise

    def list_cargos(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        busca: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Cargo]:
        return self.repository.list(db, empresa_id=empresa_id, status=status, busca=busca, limit=limit, offset=offset)

    def get_cargo(self, db: Session, cargo_id: str) -> Cargo:
        cargo = self.repository.get_by_id(db, cargo_id)
        if cargo is None:
            raise CargoNotFoundError("Cargo não encontrado")
        return cargo

    def update_cargo(
        self,
        db: Session,
        cargo_id: str,
        data: CargoUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Cargo:
        try:
            cargo = self.get_cargo(db, cargo_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "codigo_interno" in updates:
                codigo_interno = self._normalize_codigo_interno(updates["codigo_interno"])
                self._ensure_required("codigoInterno", codigo_interno)
                if codigo_interno != cargo.codigo_interno:
                    self._ensure_codigo_interno_available(
                        db,
                        cargo.empresa_id,
                        codigo_interno,
                        exclude_id=cargo.id,
                    )
                    cargo.codigo_interno = codigo_interno
                    changed_fields.append("codigoInterno")

            if "nome" in updates:
                nome = self._normalize_nome(updates["nome"])
                self._ensure_required("nome", nome)
                if nome != cargo.nome:
                    self._ensure_nome_available(db, cargo.empresa_id, nome, exclude_id=cargo.id)
                    cargo.nome = nome
                    changed_fields.append("nome")

            if "descricao" in updates:
                descricao = self._normalize_descricao(updates["descricao"])
                if descricao != cargo.descricao:
                    cargo.descricao = descricao
                    changed_fields.append("descricao")

            if changed_fields:
                now = datetime.now(timezone.utc)
                cargo.updated_at = now
                self.repository.update(db, cargo)
                self._publish_event(
                    db,
                    cargo,
                    DomainEventType.CARGO_ALTERADO,
                    actor_usuario_id,
                    occurred_at=now,
                    campos_alterados=changed_fields,
                )

            db.commit()
            db.refresh(cargo)
            return cargo
        except Exception:
            db.rollback()
            raise

    def inativar_cargo(
        self,
        db: Session,
        cargo_id: str,
        *,
        motivo_inativacao: str | None = None,
        actor_usuario_id: str | None = None,
    ) -> Cargo:
        try:
            cargo = self.get_cargo(db, cargo_id)
            if cargo.status == STATUS_INATIVA:
                raise CargoInvalidTransitionError("Cargo já está inativo")
            if cargo.status == STATUS_ARQUIVADA:
                raise CargoInvalidTransitionError("Cargo arquivado não pode ser inativado")

            now = datetime.now(timezone.utc)
            cargo.status = STATUS_INATIVA
            cargo.updated_at = now
            cargo.inativado_at = now
            cargo.motivo_inativacao = self._normalize_descricao(motivo_inativacao)
            cargo.inativado_por_usuario_id = actor_usuario_id
            self.repository.update(db, cargo)
            self._publish_event(db, cargo, DomainEventType.CARGO_INATIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(cargo)
            return cargo
        except Exception:
            db.rollback()
            raise

    def reativar_cargo(
        self,
        db: Session,
        cargo_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Cargo:
        try:
            cargo = self.get_cargo(db, cargo_id)
            if cargo.status == STATUS_ATIVA:
                raise CargoInvalidTransitionError("Cargo já está ativo")
            if cargo.status == STATUS_ARQUIVADA:
                raise CargoInvalidTransitionError("Cargo arquivado não pode ser reativado")

            now = datetime.now(timezone.utc)
            cargo.status = STATUS_ATIVA
            cargo.updated_at = now
            cargo.inativado_at = None
            cargo.motivo_inativacao = None
            cargo.inativado_por_usuario_id = None
            self.repository.update(db, cargo)
            self._publish_event(db, cargo, DomainEventType.CARGO_REATIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(cargo)
            return cargo
        except Exception:
            db.rollback()
            raise

    def to_response(self, cargo: Cargo) -> CargoResponse:
        return CargoResponse(
            id=cargo.id,
            empresaId=cargo.empresa_id,
            codigoInterno=cargo.codigo_interno,
            nome=cargo.nome,
            descricao=cargo.descricao,
            status=cargo.status,
            createdAt=cargo.created_at,
            updatedAt=cargo.updated_at,
            inativadoAt=cargo.inativado_at,
            motivoInativacao=cargo.motivo_inativacao,
            inativadoPorUsuarioId=cargo.inativado_por_usuario_id,
        )

    def _ensure_empresa_accepts_cargo(self, db: Session, empresa_id: str) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None:
            raise CargoInvalidEmpresaError("Empresa não encontrada")
        if empresa.status == EMPRESA_STATUS_INATIVA:
            raise CargoInvalidEmpresaError("Empresa inativa não permite criação de Cargo")
        if empresa.status == EMPRESA_STATUS_ARQUIVADA:
            raise CargoInvalidEmpresaError("Empresa arquivada não permite criação de Cargo")

    def _ensure_codigo_interno_available(
        self,
        db: Session,
        empresa_id: str,
        codigo_interno: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existing = self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=codigo_interno)
        if existing is not None and existing.id != exclude_id:
            raise CargoConflictError("codigoInterno já cadastrado para esta Empresa")

    def _ensure_nome_available(
        self,
        db: Session,
        empresa_id: str,
        nome: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existing = self.repository.get_by_nome(db, empresa_id=empresa_id, nome=nome)
        if existing is not None and existing.id != exclude_id:
            raise CargoConflictError("nome já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        cargo: Cargo,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        occurred_at: datetime | None = None,
        campos_alterados: list[str] | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": cargo.empresa_id,
            "cargo_id": cargo.id,
            "timestamp": timestamp.isoformat(),
            "actor_usuario_id": actor_usuario_id,
        }
        if campos_alterados is not None:
            payload["campos_alterados"] = campos_alterados

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=cargo.empresa_id,
            entidade_tipo="cargo",
            entidade_id=cargo.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalize_codigo_interno(codigo_interno: str) -> str:
        return codigo_interno.strip().upper()

    @staticmethod
    def _normalize_nome(nome: str) -> str:
        return " ".join(nome.strip().split())

    @staticmethod
    def _normalize_descricao(descricao: str | None) -> str | None:
        if descricao is None:
            return None
        normalized = " ".join(descricao.strip().split())
        return normalized or None

    @staticmethod
    def _ensure_required(field: str, value: str) -> None:
        if not value:
            raise CargoInvalidDataError(f"{field} é obrigatório")
