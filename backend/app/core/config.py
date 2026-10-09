import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

# Carrega backend/.env (se existir) antes de qualquer os.getenv abaixo. Silencioso se o
# arquivo não existir (produção real deve injetar variáveis de ambiente diretamente).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_SQLITE_URL = "sqlite:///./taskfloww.db"
DEV_INSECURE_AUTH_SECRET = "dev-insecure-secret-change-me"

# Valores de APP_ENV que caracterizam produção. O fallback inseguro de AUTH_SECRET_KEY
# continua valendo fora daqui — em produção ele é recusado no boot (ver __post_init__).
AMBIENTES_PRODUCAO = frozenset({"production", "prod", "producao", "produção"})


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Taskfloww API"))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    # Fuso oficial da aplicação — fonte única do "agora" de negócio (ver app/core/relogio.py).
    # Define, entre outras coisas, o ano gravado em codigo_referencia: um registro criado às
    # 23:30 de 31/12 em São Paulo já seria 01/01 em UTC. Quando existir fuso por empresa,
    # este é o ponto a evoluir — não espalhar datetime.now() pelo código.
    app_timezone: str = field(default_factory=lambda: os.getenv("APP_TIMEZONE", "America/Sao_Paulo"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL))
    auth_secret_key: str = field(default_factory=lambda: os.getenv("AUTH_SECRET_KEY", DEV_INSECURE_AUTH_SECRET))
    auth_algorithm: str = field(default_factory=lambda: os.getenv("AUTH_ALGORITHM", "HS256"))
    auth_access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    )
    # Sessão de PLATAFORMA (token `tipo="plataforma"`, cookie `tf_platform`): curta, como a sessão tenant.
    platform_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("PLATFORM_TOKEN_EXPIRE_MINUTES", "30"))
    )
    auth_max_failed_attempts: int = field(default_factory=lambda: int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5")))
    auth_lockout_minutes: int = field(default_factory=lambda: int(os.getenv("AUTH_LOCKOUT_MINUTES", "15")))
    empresa_codigo: str = field(default_factory=lambda: os.getenv("EMPRESA_CODIGO", "DEMO"))
    empresa_nome: str = field(default_factory=lambda: os.getenv("EMPRESA_NOME", "Agência Demo"))
    bootstrap_owner_name: str | None = field(default_factory=lambda: os.getenv("BOOTSTRAP_OWNER_NAME"))
    bootstrap_owner_email: str | None = field(default_factory=lambda: os.getenv("BOOTSTRAP_OWNER_EMAIL"))
    bootstrap_owner_password: str | None = field(default_factory=lambda: os.getenv("BOOTSTRAP_OWNER_PASSWORD"))
    # Sem valor padrão de propósito: é a senha inicial de TODAS as contas migradas de uma
    # vez, ou seja, uma credencial compartilhada. Um fallback no código-fonte viraria
    # segredo versionado e permanente no histórico do Git. Quem precisa dela valida a
    # presença e falha explicitamente — ver app/cli/seed_usuarios.py.
    bootstrap_default_password: str | None = field(
        default_factory=lambda: os.getenv("BOOTSTRAP_DEFAULT_PASSWORD")
    )
    # Chave mestra Fernet pra criptografar `ConfiguracaoEmail.smtp_senha_criptografada` (Fase
    # 2G.7B1) — nunca persistida, só variável de ambiente. Deliberadamente SEM validação aqui
    # e SEM guarda de produção em __post_init__ (ao contrário de auth_secret_key): a ausência
    # não pode derrubar o boot de toda a aplicação por uma feature que a Empresa pode nunca
    # usar. Quem precisa dela de verdade (salvar/descriptografar senha, testar conexão) valida
    # a presença e o formato na hora, em ConfiguracaoEmailCryptoService — nunca aqui.
    email_config_encryption_key: str | None = field(
        default_factory=lambda: os.getenv("EMAIL_CONFIG_ENCRYPTION_KEY")
    )
    # URL pública do frontend (ex.: https://taskflow.exemplo.com.br), usada SÓ para montar links
    # enviados por e-mail (recuperação de senha). Sempre configurada — nunca derivada de Host/
    # Origin/Referer da requisição, que o cliente controla. Ausente = o e-mail de recuperação
    # simplesmente não é enviado (ver AuthService.solicitar_redefinicao_senha). Não é segredo.
    app_public_url: str | None = field(default_factory=lambda: os.getenv("APP_PUBLIC_URL"))
    # Login Google Workspace — client_id é público (vai para o navegador), não é segredo.
    # Sem client secret: o fluxo de ID Token (Google Identity Services) não precisa dele.
    google_oauth_client_id: str | None = field(default_factory=lambda: os.getenv("GOOGLE_OAUTH_CLIENT_ID"))
    # Opcional: quando definido, exige que o claim `hd` do token bata exatamente com este
    # domínio — ver AuthService.login_google. Ausente = sem checagem extra de domínio (o
    # usuário já precisa existir pré-cadastrado de qualquer forma).
    google_workspace_allowed_domain: str | None = field(
        default_factory=lambda: os.getenv("GOOGLE_WORKSPACE_ALLOWED_DOMAIN")
    )

    # Fase 7E — proxies cuja palavra sobre o IP do cliente (`X-Forwarded-For`) é aceita. Só a conexão IMEDIATA vinda destas redes
    # habilita o cabeçalho; de qualquer outra origem ele é ignorado (anti-spoofing) — ver app/core/cliente_ip.py. O padrão são os
    # ranges privados/loopback: a API nunca é publicada na internet (só o proxy/BFF na rede Docker a alcança). Em outra topologia,
    # fixe a sub-rede exata (ex.: TRUSTED_PROXY_CIDRS=172.18.0.0/16). Valor inválido falha no boot.
    trusted_proxy_cidrs: str = field(
        default_factory=lambda: os.getenv("TRUSTED_PROXY_CIDRS", "").strip()
        or "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,fc00::/7"
    )
    @property
    def trusted_proxy_networks(self):
        from app.core.cliente_ip import parse_redes_confiaveis

        return parse_redes_confiaveis(self.trusted_proxy_cidrs.split(","))

    def __post_init__(self) -> None:
        # Falha no boot, não na primeira emissão de código: um APP_TIMEZONE inválido só
        # apareceria muito depois, ao gerar um codigo_referencia.
        try:
            ZoneInfo(self.app_timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"APP_TIMEZONE inválido: {self.app_timezone!r}") from exc
        if self.auth_access_token_expire_minutes <= 0:
            raise ValueError("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES deve ser positivo")
        if self.platform_token_expire_minutes <= 0:
            raise ValueError("PLATFORM_TOKEN_EXPIRE_MINUTES deve ser positivo")
        if self.auth_max_failed_attempts <= 0:
            raise ValueError("AUTH_MAX_FAILED_ATTEMPTS deve ser positivo")
        if self.auth_lockout_minutes <= 0:
            raise ValueError("AUTH_LOCKOUT_MINUTES deve ser positivo")
        try:
            self.trusted_proxy_networks  # valida os CIDRs no boot: confiança mal configurada não pode passar em silêncio
        except ValueError as exc:
            raise ValueError(f"TRUSTED_PROXY_CIDRS inválido: {exc}") from exc
        # Fail-fast: produção nunca pode assinar JWT com o segredo de desenvolvimento, que
        # é público (está versionado logo acima). Sem esta guarda, um deploy sem
        # AUTH_SECRET_KEY sobe silenciosamente e qualquer um com acesso ao repositório
        # consegue forjar token de qualquer usuário. Fora de produção o fallback continua
        # valendo — só aqui ele é recusado. A mensagem nunca cita o valor do segredo.
        if self.app_env.strip().lower() in AMBIENTES_PRODUCAO:
            if not self.auth_secret_key or self.auth_secret_key == DEV_INSECURE_AUTH_SECRET:
                raise RuntimeError("AUTH_SECRET_KEY deve ser definida explicitamente em produção.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
