from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.usuario import Usuario
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.services.empresa_service import STATUS_ARQUIVADA as EMPRESA_STATUS_ARQUIVADA
from app.services.empresa_service import STATUS_INATIVA as EMPRESA_STATUS_INATIVA
from app.services.domain_event_publisher import DomainEventPublisher

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_BLOQUEADO = "bloqueado"
STATUS_ARQUIVADO = "arquivado"


class UsuarioNotFoundError(ValueError):
    pass


class UsuarioConflictError(ValueError):
    pass


class UsuarioInvalidTransitionError(ValueError):
    pass


class UsuarioInvalidEmpresaError(ValueError):
    pass


class UsuarioService:
    def __init__(
        self,
        repository: UsuarioRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or UsuarioRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def create_usuario(
        self,
        db: Session,
        data: UsuarioCreate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        empresa_id = str(data.empresa_id)
        email = self._normalize_email(data.email)
        now = datetime.now(timezone.utc)
        usuario = Usuario(
            id=str(uuid4()),
            empresa_id=empresa_id,
            codigo_interno=data.codigo_interno,
            nome=data.nome,
            email=email,
            perfil_base=data.perfil_base,
            acesso_sistema=data.acesso_sistema,
            status=STATUS_ATIVO,
            created_at=now,
            updated_at=now,
            inativado_at=None,
            inativado_por_usuario_id=None,
            motivo_inativacao=None,
        )

        try:
            self._ensure_empresa_accepts_usuario(db, empresa_id)
            self._ensure_codigo_interno_available(db, empresa_id, usuario.codigo_interno)
            self._ensure_email_available(db, empresa_id, usuario.email)
            self.repository.create(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_CRIADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def list_usuarios(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        perfil_base: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Usuario]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            status=status,
            perfil_base=perfil_base,
            search=search,
            limit=limit,
            offset=offset,
        )

    def get_usuario(self, db: Session, usuario_id: str) -> Usuario:
        usuario = self.repository.get_by_id(db, usuario_id)
        if usuario is None:
            raise UsuarioNotFoundError("Usuário não encontrado")
        return usuario

    def update_usuario(
        self,
        db: Session,
        usuario_id: str,
        data: UsuarioUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "codigo_interno" in updates and updates["codigo_interno"] != usuario.codigo_interno:
                self._ensure_codigo_interno_available(
                    db,
                    usuario.empresa_id,
                    updates["codigo_interno"],
                    exclude_id=usuario.id,
                )
                usuario.codigo_interno = updates["codigo_interno"]
                changed_fields.append("codigoInterno")

            if "nome" in updates and updates["nome"] != usuario.nome:
                usuario.nome = updates["nome"]
                changed_fields.append("nome")

            if "email" in updates:
                email = self._normalize_email(updates["email"])
                if email != usuario.email:
                    self._ensure_email_available(db, usuario.empresa_id, email, exclude_id=usuario.id)
                    usuario.email = email
                    changed_fields.append("email")

            if "perfil_base" in updates and updates["perfil_base"] != usuario.perfil_base:
                usuario.perfil_base = updates["perfil_base"]
                changed_fields.append("perfilBase")

            if "acesso_sistema" in updates and updates["acesso_sistema"] != usuario.acesso_sistema:
                usuario.acesso_sistema = updates["acesso_sistema"]
                changed_fields.append("acessoSistema")

            if changed_fields:
                now = datetime.now(timezone.utc)
                usuario.updated_at = now
                self.repository.update(db, usuario)
                self._publish_event(
                    db,
                    usuario,
                    DomainEventType.USUARIO_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def inativar_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        motivo_inativacao: str | None = None,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            if usuario.status == STATUS_INATIVO:
                raise UsuarioInvalidTransitionError("Usuário já está inativo")
            if usuario.status == STATUS_ARQUIVADO:
                raise UsuarioInvalidTransitionError("Usuário arquivado não pode ser inativado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_INATIVO
            usuario.updated_at = now
            usuario.inativado_at = now
            usuario.inativado_por_usuario_id = actor_usuario_id
            usuario.motivo_inativacao = motivo_inativacao
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_INATIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def reativar_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            if usuario.status == STATUS_ATIVO:
                raise UsuarioInvalidTransitionError("Usuário já está ativo")
            if usuario.status == STATUS_BLOQUEADO:
                raise UsuarioInvalidTransitionError("Usuário bloqueado deve ser desbloqueado")
            if usuario.status == STATUS_ARQUIVADO:
                raise UsuarioInvalidTransitionError("Usuário arquivado não pode ser reativado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_ATIVO
            usuario.updated_at = now
            usuario.inativado_at = None
            usuario.inativado_por_usuario_id = None
            usuario.motivo_inativacao = None
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_REATIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def bloquear_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            if usuario.status == STATUS_BLOQUEADO:
                raise UsuarioInvalidTransitionError("Usuário já está bloqueado")
            if usuario.status == STATUS_ARQUIVADO:
                raise UsuarioInvalidTransitionError("Usuário arquivado não pode ser bloqueado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_BLOQUEADO
            usuario.updated_at = now
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_BLOQUEADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def desbloquear_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            if usuario.status != STATUS_BLOQUEADO:
                raise UsuarioInvalidTransitionError("Somente usuário bloqueado pode ser desbloqueado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_ATIVO
            usuario.updated_at = now
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_DESBLOQUEADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def to_read(self, usuario: Usuario) -> UsuarioRead:
        return UsuarioRead(
            id=usuario.id,
            empresaId=usuario.empresa_id,
            codigoInterno=usuario.codigo_interno,
            nome=usuario.nome,
            email=usuario.email,
            perfilBase=usuario.perfil_base,
            acessoSistema=usuario.acesso_sistema,
            status=usuario.status,
            createdAt=usuario.created_at,
            updatedAt=usuario.updated_at,
            inativadoAt=usuario.inativado_at,
            inativadoPorUsuarioId=usuario.inativado_por_usuario_id,
            motivoInativacao=usuario.motivo_inativacao,
        )

    def _ensure_empresa_accepts_usuario(self, db: Session, empresa_id: str) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None:
            raise UsuarioInvalidEmpresaError("Empresa não encontrada")
        if empresa.status == EMPRESA_STATUS_INATIVA:
            raise UsuarioInvalidEmpresaError("Empresa inativa não permite criação de usuário")
        if empresa.status == EMPRESA_STATUS_ARQUIVADA:
            raise UsuarioInvalidEmpresaError("Empresa arquivada não permite criação de usuário")

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
            raise UsuarioConflictError("codigoInterno já cadastrado para esta Empresa")

    def _ensure_email_available(
        self,
        db: Session,
        empresa_id: str,
        email: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existing = self.repository.get_by_email(db, empresa_id=empresa_id, email=email)
        if existing is not None and existing.id != exclude_id:
            raise UsuarioConflictError("email já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        usuario: Usuario,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": usuario.empresa_id,
            "usuario_id": usuario.id,
            "timestamp": timestamp.isoformat(),
            "perfil_base": usuario.perfil_base,
            "status": usuario.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=usuario.empresa_id,
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
