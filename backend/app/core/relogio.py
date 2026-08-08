"""Fonte única do "agora" de negócio.

Existe para que o ano gravado em `codigo_referencia` seja determinístico e auditável: um
registro criado às 23:30 de 31/12 em São Paulo pertence ao ano corrente da empresa, não ao
ano seguinte em UTC. Nenhum código de domínio deve chamar `datetime.now()` diretamente para
decidir ano de referência — sempre passar por aqui.

Persistência continua em UTC (`agora_utc`); o fuso da aplicação serve para as decisões de
calendário (que dia é hoje, que ano é este).
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def fuso_aplicacao() -> ZoneInfo:
    """Fuso oficial configurado em APP_TIMEZONE (validado no boot, ver Settings)."""
    return ZoneInfo(get_settings().app_timezone)


def agora_utc() -> datetime:
    """Instante atual em UTC — usar para gravar em colunas timestamptz."""
    return datetime.now(timezone.utc)


def agora_local() -> datetime:
    """Instante atual no fuso da aplicação — usar para decisões de calendário."""
    return agora_utc().astimezone(fuso_aplicacao())


def ano_corrente() -> int:
    """Ano de referência oficial (4 dígitos), no fuso da aplicação."""
    return agora_local().year
