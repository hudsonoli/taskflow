from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.agencia import Agencia
from app.repositories.agencia_repository import AgenciaRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.agencia import AgenciaCreate, AgenciaResponse, AgenciaUpdate
from app.services.empresa_service import STATUS_ARQUIVADA as EMPRESA_STATUS_ARQUIVADA
from app.services.empresa_service import STATUS_INATIVA as EMPRESA_STATUS_INATIVA
from app.services.domain_event_publisher import DomainEventPublisher

STATUS_ATIVA = "ativa"
STATUS_INATIVA = "inativa"
STATUS_ARQUIVADA = "arquivada"


class AgenciaNotFoundError(ValueError):
    pass


class AgenciaConflictError(ValueError):
    pass


class AgenciaInvalidTransitionError(ValueError):
    pass


class AgenciaInvalidEmpresaError(ValueError):
    pass


class AgenciaService:
    def __init__(
        self,
        repository: AgenciaRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or AgenciaRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def create_agencia(
        self,
        db: Session,
        data: AgenciaCreate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Agencia:
        empresa_id = str(data.empresa_id)
        codigo_interno = self._normalize_codigo_interno(data.codigo_interno)
        nome = self._normalize_nome(data.nome)
        sigla = self._normalize_sigla(data.sigla)
        descricao = self._normalize_descricao(data.descricao)
        now = datetime.now(timezone.utc)
        agencia = Agencia(
            id=str(uuid4()),
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            nome=nome,
            sigla=sigla,
            descricao=descricao,
            status=STATUS_ATIVA,
            created_at=now,
            updated_at=now,
            inativado_at=None,
            motivo_inativacao=None,
            inativado_por_usuario_id=None,
        )

        try:
            self._ensure_empresa_accepts_agencia(db, empresa_id)
            self._ensure_codigo_interno_available(db, empresa_id, agencia.codigo_interno)
            self._ensure_nome_available(db, empresa_id, agencia.nome)
            self.repository.create(db, agencia)
            self._publish_event(db, agencia, DomainEventType.AGENCIA_CRIADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(agencia)
            return agencia
        except Exception:
            db.rollback()
            raise

    def list_agencias(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Agencia]:
        return self.repository.list(db, empresa_id=empresa_id, status=status, limit=limit, offset=offset)

    def get_agencia(self, db: Session, agencia_id: str) -> Agencia:
        agencia = self.repository.get_by_id(db, agencia_id)
        if agencia is None:
            raise AgenciaNotFoundError("Agência não encontrada")
        return agencia

    def update_agencia(
        self,
        db: Session,
        agencia_id: str,
        data: AgenciaUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Agencia:
        try:
            agencia = self.get_agencia(db, agencia_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "codigo_interno" in updates:
                codigo_interno = self._normalize_codigo_interno(updates["codigo_interno"])
                if codigo_interno != agencia.codigo_interno:
                    self._ensure_codigo_interno_available(
                        db,
                        agencia.empresa_id,
                        codigo_interno,
                        exclude_id=agencia.id,
                    )
                    agencia.codigo_interno = codigo_interno
                    changed_fields.append("codigoInterno")

            if "nome" in updates:
                nome = self._normalize_nome(updates["nome"])
                if nome != agencia.nome:
                    self._ensure_nome_available(db, agencia.empresa_id, nome, exclude_id=agencia.id)
                    agencia.nome = nome
                    changed_fields.append("nome")

            if "sigla" in updates:
                sigla = self._normalize_sigla(updates["sigla"])
                if sigla != agencia.sigla:
                    agencia.sigla = sigla
                    changed_fields.append("sigla")

            if "descricao" in updates:
                descricao = self._normalize_descricao(updates["descricao"])
                if descricao != agencia.descricao:
                    agencia.descricao = descricao
                    changed_fields.append("descricao")

            if changed_fields:
                now = datetime.now(timezone.utc)
                agencia.updated_at = now
                self.repository.update(db, agencia)
                self._publish_event(db, agencia, DomainEventType.AGENCIA_ALTERADA, actor_usuario_id, occurred_at=now)

            db.commit()
            db.refresh(agencia)
            return agencia
        except Exception:
            db.rollback()
            raise

    def inativar_agencia(
        self,
        db: Session,
        agencia_id: str,
        *,
        motivo_inativacao: str | None = None,
        actor_usuario_id: str | None = None,
    ) -> Agencia:
        try:
            agencia = self.get_agencia(db, agencia_id)
            if agencia.status == STATUS_INATIVA:
                raise AgenciaInvalidTransitionError("Agência já está inativa")
            if agencia.status == STATUS_ARQUIVADA:
                raise AgenciaInvalidTransitionError("Agência arquivada não pode ser inativada")

            now = datetime.now(timezone.utc)
            agencia.status = STATUS_INATIVA
            agencia.updated_at = now
            agencia.inativado_at = now
            agencia.motivo_inativacao = motivo_inativacao
            agencia.inativado_por_usuario_id = actor_usuario_id
            self.repository.update(db, agencia)
            self._publish_event(db, agencia, DomainEventType.AGENCIA_INATIVADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(agencia)
            return agencia
        except Exception:
            db.rollback()
            raise

    def reativar_agencia(
        self,
        db: Session,
        agencia_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Agencia:
        try:
            agencia = self.get_agencia(db, agencia_id)
            if agencia.status == STATUS_ATIVA:
                raise AgenciaInvalidTransitionError("Agência já está ativa")
            if agencia.status == STATUS_ARQUIVADA:
                raise AgenciaInvalidTransitionError("Agência arquivada não pode ser reativada")

            now = datetime.now(timezone.utc)
            agencia.status = STATUS_ATIVA
            agencia.updated_at = now
            agencia.inativado_at = None
            agencia.motivo_inativacao = None
            agencia.inativado_por_usuario_id = None
            self.repository.update(db, agencia)
            self._publish_event(db, agencia, DomainEventType.AGENCIA_REATIVADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(agencia)
            return agencia
        except Exception:
            db.rollback()
            raise

    def to_response(self, agencia: Agencia) -> AgenciaResponse:
        return AgenciaResponse(
            id=agencia.id,
            empresaId=agencia.empresa_id,
            codigoInterno=agencia.codigo_interno,
            nome=agencia.nome,
            sigla=agencia.sigla,
            descricao=agencia.descricao,
            status=agencia.status,
            createdAt=agencia.created_at,
            updatedAt=agencia.updated_at,
            inativadoAt=agencia.inativado_at,
            motivoInativacao=agencia.motivo_inativacao,
            inativadoPorUsuarioId=agencia.inativado_por_usuario_id,
        )

    def _ensure_empresa_accepts_agencia(self, db: Session, empresa_id: str) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None:
            raise AgenciaInvalidEmpresaError("Empresa não encontrada")
        if empresa.status == EMPRESA_STATUS_INATIVA:
            raise AgenciaInvalidEmpresaError("Empresa inativa não permite criação de Agência")
        if empresa.status == EMPRESA_STATUS_ARQUIVADA:
            raise AgenciaInvalidEmpresaError("Empresa arquivada não permite criação de Agência")

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
            raise AgenciaConflictError("codigoInterno já cadastrado para esta Empresa")

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
            raise AgenciaConflictError("nome já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        agencia: Agencia,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": agencia.empresa_id,
            "agencia_id": agencia.id,
            "timestamp": timestamp.isoformat(),
            "actor_usuario_id": actor_usuario_id,
        }

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=agencia.empresa_id,
            entidade_tipo="agencia",
            entidade_id=agencia.id,
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
    def _normalize_sigla(sigla: str) -> str:
        return sigla.strip().upper()

    @staticmethod
    def _normalize_descricao(descricao: str | None) -> str | None:
        if descricao is None:
            return None
        normalized = " ".join(descricao.strip().split())
        return normalized or None
