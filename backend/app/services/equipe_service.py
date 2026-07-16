from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.equipe import Equipe
from app.repositories.equipe_repository import EquipeRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.equipe import EquipeCreate, EquipeResponse, EquipeUpdate
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import STATUS_ARQUIVADA as EMPRESA_STATUS_ARQUIVADA
from app.services.empresa_service import STATUS_INATIVA as EMPRESA_STATUS_INATIVA

STATUS_ATIVA = "ativa"
STATUS_INATIVA = "inativa"
STATUS_ARQUIVADA = "arquivada"


class EquipeNotFoundError(ValueError):
    pass


class EquipeConflictError(ValueError):
    pass


class EquipeInvalidTransitionError(ValueError):
    pass


class EquipeInvalidEmpresaError(ValueError):
    pass


class EquipeInvalidDataError(ValueError):
    pass


class EquipeService:
    def __init__(
        self,
        repository: EquipeRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or EquipeRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def create_equipe(
        self,
        db: Session,
        data: EquipeCreate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Equipe:
        empresa_id = str(data.empresa_id)
        codigo_interno = self._normalize_codigo_interno(data.codigo_interno)
        nome = self._normalize_nome(data.nome)
        descricao = self._normalize_descricao(data.descricao)
        self._ensure_required("codigoInterno", codigo_interno)
        self._ensure_required("nome", nome)
        now = datetime.now(timezone.utc)
        equipe = Equipe(
            id=str(uuid4()),
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            nome=nome,
            descricao=descricao,
            status=STATUS_ATIVA,
            inativado_at=None,
            motivo_inativacao=None,
            inativado_por_usuario_id=None,
            created_at=now,
            updated_at=now,
        )

        try:
            self._ensure_empresa_accepts_equipe(db, empresa_id)
            self._ensure_codigo_interno_available(db, empresa_id, equipe.codigo_interno)
            self._ensure_nome_available(db, empresa_id, equipe.nome)
            self.repository.create(db, equipe)
            self._publish_event(db, equipe, DomainEventType.EQUIPE_CRIADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(equipe)
            return equipe
        except Exception:
            db.rollback()
            raise

    def list_equipes(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        busca: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Equipe]:
        return self.repository.list(db, empresa_id=empresa_id, status=status, busca=busca, limit=limit, offset=offset)

    def get_equipe(self, db: Session, equipe_id: str) -> Equipe:
        equipe = self.repository.get_by_id(db, equipe_id)
        if equipe is None:
            raise EquipeNotFoundError("Equipe não encontrada")
        return equipe

    def update_equipe(
        self,
        db: Session,
        equipe_id: str,
        data: EquipeUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Equipe:
        try:
            equipe = self.get_equipe(db, equipe_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "codigo_interno" in updates:
                codigo_interno = self._normalize_codigo_interno(updates["codigo_interno"])
                self._ensure_required("codigoInterno", codigo_interno)
                if codigo_interno != equipe.codigo_interno:
                    self._ensure_codigo_interno_available(
                        db,
                        equipe.empresa_id,
                        codigo_interno,
                        exclude_id=equipe.id,
                    )
                    equipe.codigo_interno = codigo_interno
                    changed_fields.append("codigoInterno")

            if "nome" in updates:
                nome = self._normalize_nome(updates["nome"])
                self._ensure_required("nome", nome)
                if nome != equipe.nome:
                    self._ensure_nome_available(db, equipe.empresa_id, nome, exclude_id=equipe.id)
                    equipe.nome = nome
                    changed_fields.append("nome")

            if "descricao" in updates:
                descricao = self._normalize_descricao(updates["descricao"])
                if descricao != equipe.descricao:
                    equipe.descricao = descricao
                    changed_fields.append("descricao")

            if changed_fields:
                now = datetime.now(timezone.utc)
                equipe.updated_at = now
                self.repository.update(db, equipe)
                self._publish_event(
                    db,
                    equipe,
                    DomainEventType.EQUIPE_ALTERADA,
                    actor_usuario_id,
                    occurred_at=now,
                    campos_alterados=changed_fields,
                )

            db.commit()
            db.refresh(equipe)
            return equipe
        except Exception:
            db.rollback()
            raise

    def inativar_equipe(
        self,
        db: Session,
        equipe_id: str,
        *,
        motivo_inativacao: str | None = None,
        actor_usuario_id: str | None = None,
    ) -> Equipe:
        try:
            equipe = self.get_equipe(db, equipe_id)
            if equipe.status == STATUS_INATIVA:
                raise EquipeInvalidTransitionError("Equipe já está inativa")
            if equipe.status == STATUS_ARQUIVADA:
                raise EquipeInvalidTransitionError("Equipe arquivada não pode ser inativada")

            now = datetime.now(timezone.utc)
            equipe.status = STATUS_INATIVA
            equipe.updated_at = now
            equipe.inativado_at = now
            equipe.motivo_inativacao = self._normalize_descricao(motivo_inativacao)
            equipe.inativado_por_usuario_id = actor_usuario_id
            self.repository.update(db, equipe)
            self._publish_event(db, equipe, DomainEventType.EQUIPE_INATIVADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(equipe)
            return equipe
        except Exception:
            db.rollback()
            raise

    def reativar_equipe(
        self,
        db: Session,
        equipe_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Equipe:
        try:
            equipe = self.get_equipe(db, equipe_id)
            if equipe.status == STATUS_ATIVA:
                raise EquipeInvalidTransitionError("Equipe já está ativa")
            if equipe.status == STATUS_ARQUIVADA:
                raise EquipeInvalidTransitionError("Equipe arquivada não pode ser reativada")

            now = datetime.now(timezone.utc)
            equipe.status = STATUS_ATIVA
            equipe.updated_at = now
            equipe.inativado_at = None
            equipe.motivo_inativacao = None
            equipe.inativado_por_usuario_id = None
            self.repository.update(db, equipe)
            self._publish_event(db, equipe, DomainEventType.EQUIPE_REATIVADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(equipe)
            return equipe
        except Exception:
            db.rollback()
            raise

    def to_response(self, equipe: Equipe) -> EquipeResponse:
        return EquipeResponse(
            id=equipe.id,
            empresaId=equipe.empresa_id,
            codigoInterno=equipe.codigo_interno,
            nome=equipe.nome,
            descricao=equipe.descricao,
            status=equipe.status,
            inativadoAt=equipe.inativado_at,
            motivoInativacao=equipe.motivo_inativacao,
            inativadoPorUsuarioId=equipe.inativado_por_usuario_id,
            createdAt=equipe.created_at,
            updatedAt=equipe.updated_at,
        )

    def _ensure_empresa_accepts_equipe(self, db: Session, empresa_id: str) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None:
            raise EquipeInvalidEmpresaError("Empresa não encontrada")
        if empresa.status == EMPRESA_STATUS_INATIVA:
            raise EquipeInvalidEmpresaError("Empresa inativa não permite criação de Equipe")
        if empresa.status == EMPRESA_STATUS_ARQUIVADA:
            raise EquipeInvalidEmpresaError("Empresa arquivada não permite criação de Equipe")

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
            raise EquipeConflictError("codigoInterno já cadastrado para esta Empresa")

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
            raise EquipeConflictError("nome já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        equipe: Equipe,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        occurred_at: datetime | None = None,
        campos_alterados: list[str] | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": equipe.empresa_id,
            "equipe_id": equipe.id,
            "timestamp": timestamp.isoformat(),
            "actor_usuario_id": actor_usuario_id,
        }
        if campos_alterados is not None:
            payload["campos_alterados"] = campos_alterados

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=equipe.empresa_id,
            entidade_tipo="equipe",
            entidade_id=equipe.id,
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
            raise EquipeInvalidDataError(f"{field} é obrigatório")
