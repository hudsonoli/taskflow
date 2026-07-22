import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Taskfloww API"))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str | None = field(default_factory=lambda: os.getenv("DATABASE_URL"))
    redis_url: str | None = field(default_factory=lambda: os.getenv("REDIS_URL"))
    auth_secret_key: str | None = field(default_factory=lambda: os.getenv("AUTH_SECRET_KEY"))
    auth_algorithm: str = field(default_factory=lambda: os.getenv("AUTH_ALGORITHM", "HS256"))
    auth_access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    )
    auth_max_failed_attempts: int = field(default_factory=lambda: int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5")))
    auth_lockout_minutes: int = field(default_factory=lambda: int(os.getenv("AUTH_LOCKOUT_MINUTES", "15")))
    # Fase 12B.1 — consulta externa de CNPJ/CEP (app/services/providers/).
    # URL base e timeout configuráveis via env var — é exatamente o ponto
    # de troca de provedor sem alterar código (documentado em
    # docs/arquitetura-taskfloww/12b1-clientes-cnpj-cep-tarefas.md).
    company_registry_base_url: str = field(
        default_factory=lambda: os.getenv("COMPANY_REGISTRY_BASE_URL", "https://brasilapi.com.br/api/cnpj/v1")
    )
    company_registry_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("COMPANY_REGISTRY_TIMEOUT_SECONDS", "5.0"))
    )
    postal_code_base_url: str = field(
        default_factory=lambda: os.getenv("POSTAL_CODE_BASE_URL", "https://viacep.com.br/ws")
    )
    postal_code_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("POSTAL_CODE_TIMEOUT_SECONDS", "5.0"))
    )

    def __post_init__(self) -> None:
        if self.auth_access_token_expire_minutes <= 0:
            raise ValueError("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES deve ser positivo")
        if self.auth_max_failed_attempts <= 0:
            raise ValueError("AUTH_MAX_FAILED_ATTEMPTS deve ser positivo")
        if self.auth_lockout_minutes <= 0:
            raise ValueError("AUTH_LOCKOUT_MINUTES deve ser positivo")
        if self.company_registry_timeout_seconds <= 0:
            raise ValueError("COMPANY_REGISTRY_TIMEOUT_SECONDS deve ser positivo")
        if self.postal_code_timeout_seconds <= 0:
            raise ValueError("POSTAL_CODE_TIMEOUT_SECONDS deve ser positivo")


@lru_cache
def get_settings() -> Settings:
    return Settings()
