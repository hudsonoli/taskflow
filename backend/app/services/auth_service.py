from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import AuthTokenError, create_access_token, hash_password, verify_google_id_token, verify_password
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
from app.services.usuario_permissao_service import UsuarioPermissaoService
from app.services.usuario_service import STATUS_ATIVO as USUARIO_STATUS_ATIVO

INVALID_CREDENTIALS_MESSAGE = "Credenciais inválidas"
# Mesma mensagem para TODO motivo de recusa do login Google (usuário inexistente, inativo,
# bloqueado, sub já vinculado a outro usuário, outro sub já vinculado a este usuário,
# cross-tenant, domínio Workspace fora da allowlist, conflito de concorrência) — nunca
# diferenciar, para não revelar se um e-mail existe ou qual regra específica barrou o acesso.
GOOGLE_ACCESS_DENIED_MESSAGE = "Acesso não autorizado."


class AuthInvalidCredentialsError(ValueError):
    pass


class AuthUnauthorizedError(ValueError):
    pass


class AuthPasswordValidationError(ValueError):
    pass


class AuthGoogleAccessDeniedError(ValueError):
    """Identidade Google autêntica (token válido), mas sem autorização no TaskFloww — sempre
    403 genérico no router, nunca diferenciado (ver GOOGLE_ACCESS_DENIED_MESSAGE)."""

    pass


class AuthService:
    def __init__(
        self,
        usuario_repository: UsuarioRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        credencial_repository: UsuarioCredencialRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
        settings: Settings | None = None,
        usuario_permissao_service: UsuarioPermissaoService | None = None,
    ) -> None:
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.credencial_repository = credencial_repository or UsuarioCredencialRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()
        self.settings = settings or get_settings()
        # Fase 2G.10A — só usado para preencher AuthMeResponse.permissoes (informativo).
        self.usuario_permissao_service = usuario_permissao_service or UsuarioPermissaoService()

    def login(
        self,
        db: Session,
        *,
        empresa_codigo: str,
        email: str,
        senha: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AccessTokenResponse:
        empresa_codigo_normalizado = self._normalize_empresa_codigo(empresa_codigo)
        email_normalizado = self._normalize_email(email)
        now = datetime.now(timezone.utc)
        empresa: Empresa | None = None
        usuario: Usuario | None = None
        credencial: UsuarioCredencial | None = None

        try:
            empresa = self.empresa_repository.get_by_codigo_interno(db, empresa_codigo_normalizado)
            if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
                self._publish_login_falha(db, empresa=empresa, usuario=None, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            usuario = self.usuario_repository.get_by_email(db, empresa_id=empresa.id, email=email_normalizado)
            if usuario is None or not self._usuario_can_authenticate(usuario):
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            credencial = self.credencial_repository.get_by_usuario_id(db, usuario.id)
            if credencial is None:
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            if self._is_locked(credencial, now):
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            lock_expired = self._lock_expired(credencial, now)
            if lock_expired:
                credencial.tentativas_falhas = 0
                credencial.bloqueado_ate = None

            if not verify_password(senha, credencial.senha_hash):
                self._register_failed_attempt(db, credencial, now)
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                db.commit()
                raise AuthInvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

            credencial.tentativas_falhas = 0
            credencial.bloqueado_ate = None
            credencial.updated_at = now
            self.credencial_repository.update(db, credencial)
            self._publish_login_sucesso(db, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
            token = create_access_token(
                sub=usuario.id,
                empresa_id=usuario.empresa_id,
                perfil_base=usuario.perfil_base,
                settings=self.settings,
                now=now,
            )
            db.commit()
            return AccessTokenResponse(accessToken=token, mustChangePassword=credencial.senha_deve_ser_alterada)
        except AuthInvalidCredentialsError:
            raise
        except Exception:
            db.rollback()
            raise

    def login_google(
        self,
        db: Session,
        *,
        empresa_codigo: str,
        email: str,
        id_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AccessTokenResponse:
        """Login Google Workspace para usuário PRÉ-CADASTRADO — nunca cria usuário novo.

        Camadas de validação, nessa ordem:
        1. Token/identidade (assinatura, issuer, audience, expiração via `verify_google_id_token`;
           `email_verified`, `sub`/`email` presentes, `hd` quando a allowlist está configurada)
           — falha aqui é `AuthUnauthorizedError` (401): o token em si não é confiável o
           bastante pra decidir qualquer coisa sobre autorização. Aplicada SEMPRE, independente
           de já existir vínculo ou não.
        2. Autorização TaskFloww (empresa ativa, usuário existe/ativo/`acesso_sistema`, sem
           conflito de vínculo, sem cross-tenant) — falha aqui é `AuthGoogleAccessDeniedError`
           (403 genérico): a identidade É confiável, só não está autorizada.

        `google_sub` é a chave preferencial: login com sub já vinculado NUNCA recompara
        e-mail digitado com o claim (ver bloco abaixo) — só o primeiro vínculo depende disso,
        porque é o único momento em que o e-mail decide a quem vincular o sub. Depois do
        vínculo, o e-mail salvo no TaskFloww (ou mesmo o e-mail real da conta Google) pode
        divergir do que foi digitado sem quebrar o login.
        """
        empresa_codigo_normalizado = self._normalize_empresa_codigo(empresa_codigo)
        email_digitado = self._normalize_email(email)
        now = datetime.now(timezone.utc)

        try:
            claims = verify_google_id_token(id_token, settings=self.settings)
        except AuthTokenError as exc:
            raise AuthUnauthorizedError("Token Google inválido") from exc

        sub = claims.get("sub")
        email_claim = claims.get("email")
        if not claims.get("email_verified") or not sub or not email_claim:
            raise AuthUnauthorizedError("Token Google inválido")

        if self.settings.google_workspace_allowed_domain:
            if claims.get("hd") != self.settings.google_workspace_allowed_domain:
                raise AuthUnauthorizedError("Token Google inválido")

        try:
            empresa = self.empresa_repository.get_by_codigo_interno(db, empresa_codigo_normalizado)
            if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
                self._publish_login_falha(db, empresa=empresa, usuario=None, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                db.commit()
                raise AuthGoogleAccessDeniedError(GOOGLE_ACCESS_DENIED_MESSAGE)

            usuario = self.usuario_repository.get_by_google_sub(db, sub)
            if usuario is not None:
                # Login seguinte: sub já vinculado é a identidade primária — e-mail digitado
                # NUNCA é recomparado aqui, e NUNCA cai pra busca por e-mail. Cross-tenant
                # nunca é aceito, mesmo que a mesma conta Google exista em outra empresa.
                if usuario.empresa_id != empresa.id:
                    self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                    db.commit()
                    raise AuthGoogleAccessDeniedError(GOOGLE_ACCESS_DENIED_MESSAGE)
            else:
                # Primeiro vínculo: aqui, e SÓ aqui, o e-mail digitado precisa bater com o
                # claim do Google — é o que ancora a quem o sub será vinculado.
                email_claim_normalizado = self._normalize_email(email_claim)
                if email_claim_normalizado != email_digitado:
                    self._publish_login_falha(db, empresa=empresa, usuario=None, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                    db.commit()
                    raise AuthGoogleAccessDeniedError(GOOGLE_ACCESS_DENIED_MESSAGE)

                usuario = self.usuario_repository.get_by_email(db, empresa_id=empresa.id, email=email_claim_normalizado)
                if usuario is None:
                    self._publish_login_falha(db, empresa=empresa, usuario=None, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                    db.commit()
                    raise AuthGoogleAccessDeniedError(GOOGLE_ACCESS_DENIED_MESSAGE)
                if usuario.google_sub is not None:
                    # Já vinculado a OUTRO sub — nunca revincula/sobrescreve automaticamente.
                    self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                    db.commit()
                    raise AuthGoogleAccessDeniedError(GOOGLE_ACCESS_DENIED_MESSAGE)

            if not self._usuario_can_authenticate(usuario):
                self._publish_login_falha(db, empresa=empresa, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
                db.commit()
                raise AuthGoogleAccessDeniedError(GOOGLE_ACCESS_DENIED_MESSAGE)

            if usuario.google_sub is None:
                usuario.google_sub = sub
                usuario.google_linked_at = now
            # `foto_url` vazia recebe a foto do Google em QUALQUER login (não só o primeiro
            # vínculo) — nunca sobrescreve uma foto já definida, em nenhum dos dois casos.
            picture = claims.get("picture")
            if picture and not usuario.foto_url:
                usuario.foto_url = picture
            usuario.google_given_name = claims.get("given_name")
            usuario.google_family_name = claims.get("family_name")
            usuario.google_locale = claims.get("locale")
            usuario.last_google_login_at = now
            usuario.updated_at = now
            db.flush()

            self._publish_login_sucesso(db, usuario=usuario, occurred_at=now, ip_address=ip_address, user_agent=user_agent)
            token = create_access_token(
                sub=usuario.id,
                empresa_id=usuario.empresa_id,
                perfil_base=usuario.perfil_base,
                settings=self.settings,
                now=now,
            )
            credencial = self.credencial_repository.get_by_usuario_id(db, usuario.id)
            db.commit()
            return AccessTokenResponse(accessToken=token, mustChangePassword=bool(credencial and credencial.senha_deve_ser_alterada))
        except AuthGoogleAccessDeniedError:
            # Toda recusa de negócio já publicou o evento de falha e commitou antes de chegar
            # aqui — mesmo padrão de `login()` (AuthInvalidCredentialsError): nada a reverter.
            raise
        except IntegrityError:
            # Corrida de dois primeiros-logins concorrentes pro mesmo `sub` — a UNIQUE
            # constraint pega, nunca vira 500 nem revela detalhe (ver migration 0035).
            db.rollback()
            raise AuthGoogleAccessDeniedError(GOOGLE_ACCESS_DENIED_MESSAGE)
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

    def me(self, db: Session, usuario: Usuario) -> AuthMeResponse:
        credencial = self.credencial_repository.get_by_usuario_id(db, usuario.id)
        permissoes = self.usuario_permissao_service.obter_permissoes_efetivas(db, usuario)
        return AuthMeResponse(
            usuarioId=usuario.id,
            empresaId=usuario.empresa_id,
            nome=usuario.nome,
            perfilBase=usuario.perfil_base,
            acessoSistema=usuario.acesso_sistema,
            status=usuario.status,
            mustChangePassword=bool(credencial and credencial.senha_deve_ser_alterada),
            permissoes=permissoes,
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
            credencial.senha_deve_ser_alterada = False
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
        deve_alterar_senha: bool = False,
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
                    senha_deve_ser_alterada=deve_alterar_senha,
                    created_at=now,
                    updated_at=now,
                )
                self.credencial_repository.create(db, credencial)
            else:
                credencial.senha_hash = senha_hash
                credencial.senha_alterada_em = now
                credencial.tentativas_falhas = 0
                credencial.bloqueado_ate = None
                credencial.senha_deve_ser_alterada = deve_alterar_senha
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

    def _publish_login_sucesso(
        self,
        db: Session,
        *,
        usuario: Usuario,
        occurred_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._publish_auth_event(
            db,
            tipo=DomainEventType.AUTH_LOGIN_SUCESSO,
            empresa_id=usuario.empresa_id,
            entidade_id=usuario.id,
            usuario_id=usuario.id,
            payload={
                "empresa_id": usuario.empresa_id,
                "usuario_id": usuario.id,
                "nome": usuario.nome,
                "timestamp": occurred_at.isoformat(),
                "resultado": "sucesso",
                "ip_address": ip_address,
                "user_agent": user_agent,
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
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if empresa is None:
            return

        payload = {
            "empresa_id": empresa.id,
            "timestamp": occurred_at.isoformat(),
            "resultado": "falha",
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        entidade_id = empresa.id
        usuario_id = None
        if usuario is not None:
            payload["usuario_id"] = usuario.id
            payload["nome"] = usuario.nome
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
