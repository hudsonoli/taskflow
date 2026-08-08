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

    def __post_init__(self) -> None:
        # Falha no boot, não na primeira emissão de código: um APP_TIMEZONE inválido só
        # apareceria muito depois, ao gerar um codigo_referencia.
        try:
            ZoneInfo(self.app_timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"APP_TIMEZONE inválido: {self.app_timezone!r}") from exc
        if self.auth_access_token_expire_minutes <= 0:
            raise ValueError("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES deve ser positivo")
        if self.auth_max_failed_attempts <= 0:
            raise ValueError("AUTH_MAX_FAILED_ATTEMPTS deve ser positivo")
        if self.auth_lockout_minutes <= 0:
            raise ValueError("AUTH_LOCKOUT_MINUTES deve ser positivo")
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
