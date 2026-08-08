"""Segredos nunca têm valor padrão no código-fonte.

`BOOTSTRAP_DEFAULT_PASSWORD` é a senha inicial de TODAS as contas migradas de uma vez — uma
credencial compartilhada. Um fallback hardcoded viraria segredo versionado, e o histórico do
Git é permanente. Estes testes travam isso: se alguém reintroduzir um default, quebram.
"""

from __future__ import annotations

import inspect

import pytest

from app.core import config as config_module
from app.core.config import DEV_INSECURE_AUTH_SECRET, Settings

# Segredo fictício usado onde o teste precisa de um valor "real". Não é credencial de
# nenhum ambiente — existe só para ser diferente de DEV_INSECURE_AUTH_SECRET.
SEGREDO_FICTICIO = "x" * 48


def _settings_sem_cache(monkeypatch, **env) -> Settings:
    """Instancia Settings direto, sem o lru_cache de get_settings().

    `config.py` chama `load_dotenv()` no import, então o `backend/.env` da máquina já
    populou o ambiente antes daqui. Por isso todo teste declara explicitamente as variáveis
    que lhe importam — inclusive as que quer AUSENTES, via `delenv`. Nenhum caso depende do
    conteúdo do .env local.
    """
    for chave, valor in env.items():
        if valor is None:
            monkeypatch.delenv(chave, raising=False)
        else:
            monkeypatch.setenv(chave, valor)
    return Settings()


# --------------------------------------------------------------------------------------

def test_configuracao_presente_funciona_normalmente(monkeypatch) -> None:
    settings = _settings_sem_cache(monkeypatch, BOOTSTRAP_DEFAULT_PASSWORD="uma-senha-qualquer")
    assert settings.bootstrap_default_password == "uma-senha-qualquer"


def test_configuracao_ausente_nao_gera_senha_padrao(monkeypatch) -> None:
    """Sem a variável, o valor é None — nunca uma senha inventada."""
    settings = _settings_sem_cache(monkeypatch, BOOTSTRAP_DEFAULT_PASSWORD=None)
    assert settings.bootstrap_default_password is None


def test_seed_falha_explicitamente_sem_a_variavel(monkeypatch) -> None:
    """O caminho que exige a senha para com mensagem clara, sem criar nada."""
    from app.cli import seed_usuarios

    monkeypatch.delenv("BOOTSTRAP_DEFAULT_PASSWORD", raising=False)
    config_module.get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="BOOTSTRAP_DEFAULT_PASSWORD não configurada"):
        seed_usuarios.seed_usuarios(output=lambda *_: None)

    config_module.get_settings.cache_clear()


def test_codigo_fonte_nao_carrega_senha_hardcoded() -> None:
    """Guarda contra regressão: nenhum default literal em bootstrap_default_password.

    Lê o fonte de config.py em vez de confiar só no comportamento — é o texto versionado
    que vaza para o histórico, e é ele que precisa estar limpo.
    """
    fonte = inspect.getsource(config_module)
    linha = next(
        (linha for linha in fonte.splitlines() if "BOOTSTRAP_DEFAULT_PASSWORD" in linha),
        None,
    )
    assert linha is not None, "campo sumiu — este teste precisa ser revisto"
    # A asserção é sobre a FORMA da chamada, não sobre um valor específico: `os.getenv`
    # com um único argumento não tem como devolver default nenhum. Escrever aqui a senha
    # que queremos proibir a colocaria no histórico do Git — justamente o que este teste
    # existe para impedir.
    assert linha.strip() == 'default_factory=lambda: os.getenv("BOOTSTRAP_DEFAULT_PASSWORD")', (
        f"os.getenv de BOOTSTRAP_DEFAULT_PASSWORD não pode ter segundo argumento: {linha.strip()!r}"
    )


# --------------------------------------------------------------------------------------
# Produção nunca sobe com o segredo de desenvolvimento
#
# `DEV_INSECURE_AUTH_SECRET` está versionado — é público por construção. Sem a guarda, um
# deploy sem AUTH_SECRET_KEY assinaria JWT com ele, e qualquer um com acesso ao repositório
# forjaria token de qualquer usuário. Fora de produção o fallback segue permitido.
# --------------------------------------------------------------------------------------

def test_desenvolvimento_sem_segredo_usa_fallback(monkeypatch) -> None:
    """Fora de produção nada muda: o fallback de desenvolvimento continua valendo."""
    settings = _settings_sem_cache(monkeypatch, APP_ENV="development", AUTH_SECRET_KEY=None)
    assert settings.auth_secret_key == DEV_INSECURE_AUTH_SECRET


def test_producao_com_segredo_real_inicializa(monkeypatch) -> None:
    settings = _settings_sem_cache(
        monkeypatch, APP_ENV="production", AUTH_SECRET_KEY=SEGREDO_FICTICIO
    )
    assert settings.auth_secret_key == SEGREDO_FICTICIO
    assert settings.app_env == "production"


@pytest.mark.parametrize("app_env", ["production", "prod", "PRODUCTION", " Production "])
def test_producao_sem_segredo_falha(monkeypatch, app_env: str) -> None:
    """Ausente é inválido — em qualquer grafia de produção."""
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY deve ser definida"):
        _settings_sem_cache(monkeypatch, APP_ENV=app_env, AUTH_SECRET_KEY=None)


def test_producao_com_segredo_vazio_falha(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY deve ser definida"):
        _settings_sem_cache(monkeypatch, APP_ENV="production", AUTH_SECRET_KEY="")


def test_producao_com_segredo_de_dev_explicito_falha(monkeypatch) -> None:
    """Definir a variável não basta: o valor não pode ser o segredo público de dev."""
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY deve ser definida"):
        _settings_sem_cache(
            monkeypatch, APP_ENV="production", AUTH_SECRET_KEY=DEV_INSECURE_AUTH_SECRET
        )


def test_mensagem_de_erro_nao_vaza_o_segredo(monkeypatch) -> None:
    """A exceção sobe para log e stack trace — não pode carregar o valor."""
    with pytest.raises(RuntimeError) as exc:
        _settings_sem_cache(
            monkeypatch, APP_ENV="production", AUTH_SECRET_KEY=DEV_INSECURE_AUTH_SECRET
        )
    mensagem = str(exc.value)
    assert DEV_INSECURE_AUTH_SECRET not in mensagem
    assert SEGREDO_FICTICIO not in mensagem
    assert mensagem == "AUTH_SECRET_KEY deve ser definida explicitamente em produção."
