import re
import unicodedata
from collections.abc import Callable

_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


def slugify(texto: str) -> str:
    sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    slug = _NAO_ALFANUMERICO.sub("-", sem_acentos.lower()).strip("-")
    return slug or "grupo"


def gerar_codigo_interno(nome: str, *, existe_conflito: Callable[[str], bool]) -> str:
    """Gera um `codigoInterno` a partir do nome (slugify), com sufixo numérico em colisão.
    `existe_conflito` decide se um candidato já está em uso (delegado pro caller, que sabe
    consultar o banco — mantém este helper sem dependência de sessão/repositório)."""
    base = slugify(nome)
    candidato = base
    sufixo = 2
    while existe_conflito(candidato):
        candidato = f"{base}-{sufixo}"
        sufixo += 1
    return candidato
