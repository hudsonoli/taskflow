from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.event_types import DomainEventType
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_credencial_repository import UsuarioCredencialRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import AccessTokenResponse, AuthMeResponse
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import STATUS_ATIVA as EMPRESA_STATUS_ATIVA
from app.services.usuario_service import STATUS_ATIVO as USUARIO_STATUS_ATIVO

INVALID_CREDENTIALS_MESSAGE = "Credenciais inválidas"


class AuthInvalidCredentialsError(ValueError):
    pass


class AuthUnauthorizedError(ValueError):
    pass


class AuthPasswordValidationError(ValueError):
    pass


class AuthService:
    def __init__(
        self,
        usuario_repository: UsuarioRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        credencial_repository: UsuarioCredencialRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.credencial_repository = credencial_repository or UsuarioCredencialRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()
        self.settings = settings or get_settings()

    def login(self, db: Session, *, empresa_codigo: str, email: str, senha: str) -> AccessTokenResponse:
        empresa_codigo_normalizado = self._normalize_empresa_codigo(empresa_codigo)
        email_normalizado = self._normalize_email(email)
        now = datetime.now(timezone.utc)
        empresa: Empresa | None = None
        usuario: Usuario | None = None
        credencial: UsuarioCredencial | None = None

        try:
            empresa = self.empresa_repository.get_by_codigo_interno(db, empresa_codigo_normalizado)
            if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
                self._publish_login_falha(db, empresa=empresa, usuario=None, occurred_at=now)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            usuario = self.usuario_repository.get_by_email(db, empresa_id=empresa.id, email=email_normalizado)
            if usuario is None or not self._usuario_can_authenticate(usuario):
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            credencial = self.credencial_repository.get_by_usuario_id(db, usuario.id)
            if credencial is None:
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            if self._is_locked(credencial, now):
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            lock_expired = self._lock_expired(credencial, now)
            if lock_expired:
                credencial.tentativas_falhas = 0
                credencial.bloqueado_ate = None

            if not verify_password(senha, credencial.senha_hash):
                self._register_failed_attempt(db, credencial, now)
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            credencial.tentativas_falhas = 0
            credencial.bloqueado_ate = None
            credencial.updated_at = now
            self.credencial_repository.update(db, credencial)
            self._publish_login_sucesso(db, usuario=usuario, occurred_at=now)
            token = create_access_token(
                sub=usuario.id,
                empresa_id=usuario.empresa_id,
                perfil_base=usuario.perfil_base,
                settings=self.settings,
                now=now,
            )
            db.commit()
            return AccessTokenResponse(accessToken=token)
        except AuthInvalidCredentialsError:
            raise
        except Exception:
            db.rollback()
            raise

    def get_current_user_from_token(self, db: Session, token: str) -> Usuario:
        from app.core.security import AuthTokenError, decode_access_token

        try:
            claims = decode_access_token(token, settings=self.settings)
        except AuthTokenError as exc:
            raise AuthUnauthorizedError("Token inválido") from exc

        usuario = self.usuario_repository.get_by_id(db, claims["sub"])
        if usuario is None:
            raise AuthUnauthorizedError("Token inválido")

        empresa = self.empresa_repository.get_by_id(db, usuario.empresa_id)
        if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
            raise AuthUnauthorizedError("Token inválido")
        if not self._usuario_can_authenticate(usuario):
            raise AuthUnauthorizedError("Token inválido")

        return usuario

    def me(self, usuario: Usuario) -> AuthMeResponse:
        return AuthMeResponse(
            usuarioId=usuario.id,
            empresaId=usuario.empresa_id,
            nome=usuario.nome,
            perfilBase=usuario.perfil_base,
            acessoSistema=usuario.acesso_sistema,
            status=usuario.status,
        )

    def alterar_senha(
        self,
        db: Session,
        *,
        usuario: Usuario,
        senha_atual: str,
        nova_senha: str,
        confirmacao_senha: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        try:
            self._validate_new_password(senha_atual, nova_senha, confirmacao_senha)
            credencial = self.credencial_repository.get_by_usuario_id(db, usuario.id)
            if credencial is None or not verify_password(senha_atual, credencial.senha_hash):
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            credencial.senha_hash = hash_password(nova_senha)
            credencial.senha_alterada_em = now
            credencial.tentativas_falhas = 0
            credencial.bloqueado_ate = None
            credencial.updated_at = now
            self.credencial_repository.update(db, credencial)
            self._publish_senha_alterada(db, usuario=usuario, occurred_at=now)
            db.commit()
        except Exception:
            db.rollback()
            raise

    def definir_senha_usuario(
        self,
        db: Session,
        *,
        empresa_codigo: str,
        email: str,
        senha: str,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        empresa_codigo_normalizado = self._normalize_empresa_codigo(empresa_codigo)
        email_normalizado = self._normalize_email(email)
        now = datetime.now(timezone.utc)

        try:
            if not senha or len(senha) < 8:
                raise AuthPasswordValidationError("Senha deve ter pelo menos 8 caracteres")

            empresa = self.empresa_repository.get_by_codigo_interno(db, empresa_codigo_normalizado)
            if empresa is None:
                raise AuthInvalidCredentialsError("Empresa ou usuário não encontrado")

            usuario = self.usuario_repository.get_by_email(db, empresa_id=empresa.id, email=email_normalizado)
            if usuario is None:
                raise AuthInvalidCredentialsError("Empresa ou usuário não encontrado")

            credencial = self.credencial_repository.get_by_usuario_id(db, usuario.id)
            senha_hash = hash_password(senha)
            if credencial is None:
                credencial = UsuarioCredencial(
                    id=str(uuid4()),
                    usuario_id=usuario.id,
                    senha_hash=senha_hash,
                    senha_definida_em=now,
                    senha_alterada_em=None,
                    tentativas_falhas=0,
                    bloqueado_ate=None,
                    created_at=now,
                    updated_at=now,
                )
                self.credencial_repository.create(db, credencial)
            else:
                credencial.senha_hash = senha_hash
                credencial.senha_alterada_em = now
                credencial.tentativas_falhas = 0
                credencial.bloqueado_ate = None
                credencial.updated_at = now
                self.credencial_repository.update(db, credencial)

            self._publish_senha_definida(db, usuario=usuario, actor_usuario_id=actor_usuario_id, occurred_at=now)
            db.commit()
            return usuario
        except Exception:
            db.rollback()
            raise

    def _register_failed_attempt(self, db: Session, credencial: UsuarioCredencial, now: datetime) -> None:
        credencial.tentativas_falhas += 1
        if credencial.tentativas_falhas >= self.settings.auth_max_failed_attempts:
            credencial.bloqueado_ate = now + timedelta(minutes=self.settings.auth_lockout_minutes)
        credencial.updated_at = now
        self.credencial_repository.update(db, credencial)

    def _publish_login_sucesso(self, db: Session, *, usuario: Usuario, occurred_at: datetime) -> None:
        self._publish_auth_event(
            db,
            tipo=DomainEventType.AUTH_LOGIN_SUCESSO,
            empresa_id=usuario.empresa_id,
            entidade_id=usuario.id,
            usuario_id=usuario.id,
            payload={
                "empresa_id": usuario.empresa_id,
                "usuario_id": usuario.id,
                "timestamp": occurred_at.isoformat(),
                "resultado": "sucesso",
            },
            occurred_at=occurred_at,
        )

    def _publish_login_falha(
        self,
        db: Session,
        *,
        empresa: Empresa | None,
        usuario: Usuario | None,
        occurred_at: datetime,
    ) -> None:
        if empresa is None:
            return

        payload = {
            "empresa_id": empresa.id,
            "timestamp": occurred_at.isoformat(),
            "resultado": "falha",
        }
        entidade_id = empresa.id
        usuario_id = None
        if usuario is not None:
            payload["usuario_id"] = usuario.id
            entidade_id = usuario.id
            usuario_id = usuario.id

        self._publish_auth_event(
            db,
            tipo=DomainEventType.AUTH_LOGIN_FALHA,
            empresa_id=empresa.id,
            entidade_id=entidade_id,
            usuario_id=usuario_id,
            payload=payload,
            occurred_at=occurred_at,
        )

    def _publish_senha_definida(
        self,
        db: Session,
        *,
        usuario: Usuario,
        actor_usuario_id: str | None,
        occurred_at: datetime,
    ) -> None:
        self._publish_auth_event(
            db,
            tipo=DomainEventType.AUTH_SENHA_DEFINIDA,
            empresa_id=usuario.empresa_id,
            entidade_id=usuario.id,
            usuario_id=actor_usuario_id,
            payload={
                "empresa_id": usuario.empresa_id,
                "usuario_id": usuario.id,
                "timestamp": occurred_at.isoformat(),
                "actor_usuario_id": actor_usuario_id,
                "resultado": "sucesso",
            },
            occurred_at=occurred_at,
        )

    def _publish_senha_alterada(self, db: Session, *, usuario: Usuario, occurred_at: datetime) -> None:
        self._publish_auth_event(
            db,
            tipo=DomainEventType.AUTH_SENHA_ALTERADA,
            empresa_id=usuario.empresa_id,
            entidade_id=usuario.id,
            usuario_id=usuario.id,
            payload={
                "empresa_id": usuario.empresa_id,
                "usuario_id": usuario.id,
                "timestamp": occurred_at.isoformat(),
                "actor_usuario_id": usuario.id,
                "resultado": "sucesso",
            },
            occurred_at=occurred_at,
        )

    def _publish_auth_event(
        self,
        db: Session,
        *,
        tipo: DomainEventType,
        empresa_id: str,
        entidade_id: str,
        usuario_id: str | None,
        payload: dict,
        occurred_at: datetime,
    ) -> None:
        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=empresa_id,
            entidade_tipo="auth",
            entidade_id=entidade_id,
            usuario_id=usuario_id,
            payload=payload,
            occurred_at=occurred_at,
        )

    @staticmethod
    def _normalize_empresa_codigo(empresa_codigo: str) -> str:
        return empresa_codigo.strip().upper()

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _usuario_can_authenticate(usuario: Usuario) -> bool:
        return usuario.status == USUARIO_STATUS_ATIVO and usuario.acesso_sistema is True

    @staticmethod
    def _is_locked(credencial: UsuarioCredencial, now: datetime) -> bool:
        bloqueado_ate = AuthService._as_utc(credencial.bloqueado_ate)
        return bloqueado_ate is not None and bloqueado_ate > now

    @staticmethod
    def _lock_expired(credencial: UsuarioCredencial, now: datetime) -> bool:
        bloqueado_ate = AuthService._as_utc(credencial.bloqueado_ate)
        return bloqueado_ate is not None and bloqueado_ate <= now

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate_new_password(senha_atual: str, nova_senha: str, confirmacao_senha: str) -> None:
        if not nova_senha or len(nova_senha) < 8:
            raise AuthPasswordValidationError("Nova senha deve ter pelo menos 8 caracteres")
        if nova_senha != confirmacao_senha:
            raise AuthPasswordValidationError("Confirmação de senha não confere")
        if nova_senha == senha_atual:
            raise AuthPasswordValidationError("Nova senha deve ser diferente da senha atual")
