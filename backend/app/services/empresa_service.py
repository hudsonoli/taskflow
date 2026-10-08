from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from sqlalchemy import select

from app.core.empresa_slug import slug_a_partir_do_codigo
from app.domain.event_types import DomainEventType
from app.models.administrador_plataforma import AdministradorPlataforma
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.empresa import EmpresaCreate, EmpresaRead, EmpresaUpdate
from app.services.domain_event_publisher import DomainEventPublisher

STATUS_ATIVA = "ativa"
STATUS_INATIVA = "inativa"
STATUS_ARQUIVADA = "arquivada"


class EmpresaNotFoundError(ValueError):
    pass


class EmpresaConflictError(ValueError):
    pass


class EmpresaInvalidTransitionError(ValueError):
    pass


class EmpresaHospedaPlataformaError(ValueError):
    """A empresa hospeda a conta de um Administrador da Plataforma ATIVO: inativá-la tiraria o login dele (o token tenant
    é recusado para empresa inativa) e, com isso, a própria autoridade da plataforma. Fica protegida enquanto essa
    autoridade existir; no futuro a conta poderá migrar para uma empresa própria da plataforma."""


class EmpresaService:
    def __init__(
        self,
        repository: EmpresaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or EmpresaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def create_empresa(
        self,
        db: Session,
        data: EmpresaCreate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Empresa:
        now = datetime.now(timezone.utc)
        empresa = Empresa(
            id=str(uuid4()),
            nome=data.nome,
            nome_fantasia=(data.nome_fantasia or None),
            documento=self._normalize_documento(data.documento),
            codigo_interno=data.codigo_interno,
            slug=self._resolver_slug_novo(db, data),
            status=STATUS_ATIVA,
            created_at=now,
            updated_at=now,
            inativado_at=None,
            inativado_por_usuario_id=None,
            motivo_inativacao=None,
        )

        try:
            self._ensure_codigo_interno_available(db, empresa.codigo_interno)
            self._ensure_slug_available(db, empresa.slug)
            self._ensure_documento_available(db, empresa.documento)
            self.repository.create(db, empresa)
            self._publish_event(db, empresa, DomainEventType.EMPRESA_CRIADA, actor_usuario_id)
            db.commit()
            db.refresh(empresa)
            return empresa
        except Exception:
            db.rollback()
            raise

    def list_empresas(
        self,
        db: Session,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Empresa]:
        return self.repository.list(db, status=status, limit=limit, offset=offset)

    def get_empresa(self, db: Session, empresa_id: str) -> Empresa:
        empresa = self.repository.get_by_id(db, empresa_id)
        if empresa is None:
            raise EmpresaNotFoundError("Empresa não encontrada")
        return empresa

    def update_empresa(
        self,
        db: Session,
        empresa_id: str,
        data: EmpresaUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Empresa:
        try:
            empresa = self.get_empresa(db, empresa_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "nome" in updates and updates["nome"] != empresa.nome:
                empresa.nome = updates["nome"]
                changed_fields.append("nome")

            if "nome_fantasia" in updates:
                fantasia = updates["nome_fantasia"] or None
                if fantasia != empresa.nome_fantasia:
                    empresa.nome_fantasia = fantasia
                    changed_fields.append("nomeFantasia")

            if "slug" in updates and updates["slug"] is not None and updates["slug"] != empresa.slug:
                self._ensure_slug_available(db, updates["slug"], exclude_id=empresa.id)
                empresa.slug = updates["slug"]
                changed_fields.append("slug")

            if "documento" in updates:
                documento = self._normalize_documento(updates["documento"])
                if documento != empresa.documento:
                    self._ensure_documento_available(db, documento, exclude_id=empresa.id)
                    empresa.documento = documento
                    changed_fields.append("documento")

            if "codigo_interno" in updates and updates["codigo_interno"] != empresa.codigo_interno:
                self._ensure_codigo_interno_available(db, updates["codigo_interno"], exclude_id=empresa.id)
                empresa.codigo_interno = updates["codigo_interno"]
                changed_fields.append("codigoInterno")

            if changed_fields:
                empresa.updated_at = datetime.now(timezone.utc)
                self.repository.update(db, empresa)
                self._publish_event(
                    db,
                    empresa,
                    DomainEventType.EMPRESA_ALTERADA,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                )

            db.commit()
            db.refresh(empresa)
            return empresa
        except Exception:
            db.rollback()
            raise

    def inativar_empresa(
        self,
        db: Session,
        empresa_id: str,
        *,
        motivo_inativacao: str | None = None,
        actor_usuario_id: str | None = None,
    ) -> Empresa:
        try:
            empresa = self.get_empresa(db, empresa_id)
            if empresa.status == STATUS_INATIVA:
                raise EmpresaInvalidTransitionError("Empresa já está inativa")
            if empresa.status == STATUS_ARQUIVADA:
                raise EmpresaInvalidTransitionError("Empresa arquivada não pode ser inativada")
            self._ensure_nao_hospeda_plataforma(db, empresa)

            now = datetime.now(timezone.utc)
            empresa.status = STATUS_INATIVA
            empresa.updated_at = now
            empresa.inativado_at = now
            empresa.inativado_por_usuario_id = actor_usuario_id
            empresa.motivo_inativacao = motivo_inativacao
            self.repository.update(db, empresa)
            self._publish_event(db, empresa, DomainEventType.EMPRESA_INATIVADA, actor_usuario_id)
            db.commit()
            db.refresh(empresa)
            return empresa
        except Exception:
            db.rollback()
            raise

    def reativar_empresa(
        self,
        db: Session,
        empresa_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Empresa:
        try:
            empresa = self.get_empresa(db, empresa_id)
            if empresa.status == STATUS_ATIVA:
                raise EmpresaInvalidTransitionError("Empresa já está ativa")
            if empresa.status == STATUS_ARQUIVADA:
                raise EmpresaInvalidTransitionError("Empresa arquivada não pode ser reativada")

            empresa.status = STATUS_ATIVA
            empresa.updated_at = datetime.now(timezone.utc)
            empresa.inativado_at = None
            empresa.inativado_por_usuario_id = None
            empresa.motivo_inativacao = None
            self.repository.update(db, empresa)
            self._publish_event(db, empresa, DomainEventType.EMPRESA_REATIVADA, actor_usuario_id)
            db.commit()
            db.refresh(empresa)
            return empresa
        except Exception:
            db.rollback()
            raise

    def to_read(self, empresa: Empresa) -> EmpresaRead:
        return EmpresaRead(
            id=empresa.id,
            nome=empresa.nome,
            nomeFantasia=empresa.nome_fantasia,
            documento=empresa.documento,
            codigoInterno=empresa.codigo_interno,
            slug=empresa.slug,
            status=empresa.status,
            createdAt=empresa.created_at,
            updatedAt=empresa.updated_at,
            inativadoAt=empresa.inativado_at,
            inativadoPorUsuarioId=empresa.inativado_por_usuario_id,
            motivoInativacao=empresa.motivo_inativacao,
        )

    def _ensure_codigo_interno_available(
        self,
        db: Session,
        codigo_interno: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existing = self.repository.get_by_codigo_interno(db, codigo_interno)
        if existing is not None and existing.id != exclude_id:
            raise EmpresaConflictError("codigoInterno já cadastrado")

    def _resolver_slug_novo(self, db: Session, data: EmpresaCreate) -> str:
        if data.slug:
            return data.slug
        return slug_a_partir_do_codigo(data.codigo_interno, em_uso=lambda candidato: self.repository.get_by_slug(db, candidato) is not None)

    def _ensure_slug_available(self, db: Session, slug: str, *, exclude_id: str | None = None) -> None:
        existing = self.repository.get_by_slug(db, slug)
        if existing is not None and existing.id != exclude_id:
            raise EmpresaConflictError("slug já cadastrado")

    @staticmethod
    def _ensure_nao_hospeda_plataforma(db: Session, empresa: Empresa) -> None:
        hospeda = db.scalar(
            select(AdministradorPlataforma.id)
            .join(Usuario, Usuario.id == AdministradorPlataforma.usuario_id)
            .where(AdministradorPlataforma.ativo.is_(True), Usuario.empresa_id == empresa.id)
            .limit(1)
        )
        if hospeda is not None:
            raise EmpresaHospedaPlataformaError(
                "Esta empresa hospeda um Administrador da Plataforma ativo e não pode ser inativada."
            )

    def _ensure_documento_available(
        self,
        db: Session,
        documento: str | None,
        *,
        exclude_id: str | None = None,
    ) -> None:
        if documento is None:
            return
        existing = self.repository.get_by_documento(db, documento)
        if existing is not None and existing.id != exclude_id:
            raise EmpresaConflictError("documento já cadastrado")

    def _publish_event(
        self,
        db: Session,
        empresa: Empresa,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
    ) -> None:
        payload = {
            "nome": empresa.nome,
            "codigoInterno": empresa.codigo_interno,
            "slug": empresa.slug,
            "status": empresa.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=empresa.id,
            entidade_tipo="empresa",
            entidade_id=empresa.id,
            usuario_id=actor_usuario_id,
            payload=payload,
        )

    @staticmethod
    def _normalize_documento(documento: str | None) -> str | None:
        if documento is None:
            return None
        normalized = documento.strip()
        return normalized or None
