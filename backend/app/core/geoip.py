"""Região APROXIMADA de um IP público (Fase 7E) — GeoIP LOCAL/offline, opcional, nunca no caminho de falha do login.

## Por que local

O login não pode depender de terceiro (latência, indisponibilidade, limite de uso) nem enviar o IP de cada usuário a um serviço
externo (LGPD: IP é dado pessoal). Por isso a única fonte suportada é uma base `.mmdb` (MaxMind GeoLite2-City ou compatível) lida
do disco, indicada por `GEOIP_DB_PATH`. **Nenhuma base é baixada nem embutida**: sem `GEOIP_DB_PATH` (ou sem o pacote `maxminddb`)
a região simplesmente não existe e a tela mostra "Não disponível".

## Regras

- IP privado, loopback, link-local, reservado ou CGNAT (`not is_global`) NUNCA é consultado — a região fica `None`;
- qualquer falha do leitor (base ausente, corrompida, IP inválido) vira `None`; nunca exceção, nunca 500, nunca bloqueio de login;
- só texto de região (`Cidade, UF, País` / `UF, País` / `País`): sem latitude/longitude, sem precisão de rua.
"""

from __future__ import annotations

import ipaddress
import logging
from collections.abc import Mapping
from functools import lru_cache
from typing import Any, Protocol

logger = logging.getLogger(__name__)

IDIOMAS = ("pt-BR", "pt", "en")


class LeitorGeoIP(Protocol):
    """Contrato mínimo do leitor (o `maxminddb.Reader` já o cumpre): `get(ip) -> dict | None`."""

    def get(self, ip_address: str) -> Mapping[str, Any] | None: ...


def _nome(registro: Mapping[str, Any] | None) -> str | None:
    if not isinstance(registro, Mapping):
        return None
    nomes = registro.get("names")
    if isinstance(nomes, Mapping):
        for idioma in IDIOMAS:
            valor = nomes.get(idioma)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
    return None


def formatar_regiao(registro: Mapping[str, Any] | None) -> str | None:
    """Registro do GeoIP → `Brasília, DF, Brasil` | `DF, Brasil` | `Brasil`. Sem país nem cidade → `None`."""
    if not isinstance(registro, Mapping):
        return None
    cidade = _nome(registro.get("city"))
    pais_registro = registro.get("country") if isinstance(registro.get("country"), Mapping) else registro.get("registered_country")
    pais = _nome(pais_registro)
    subdivisoes = registro.get("subdivisions")
    uf = None
    if isinstance(subdivisoes, list) and subdivisoes and isinstance(subdivisoes[0], Mapping):
        iso = subdivisoes[0].get("iso_code")
        uf = iso.strip() if isinstance(iso, str) and iso.strip() else _nome(subdivisoes[0])
    partes = [parte for parte in (cidade, uf, pais) if parte]
    return ", ".join(partes) if partes else None


def ip_consultavel(ip: str | None) -> bool:
    """Só IP público e global é consultado (privado/loopback/link-local/reservado/CGNAT → não)."""
    if not ip:
        return False
    try:
        endereco = ipaddress.ip_address(ip)
        return endereco.is_global and not endereco.is_multicast
    except ValueError:
        return False


@lru_cache(maxsize=1)
def _leitor_padrao() -> LeitorGeoIP | None:
    """Leitor da base configurada em `GEOIP_DB_PATH`, aberto uma vez. Sem configuração ou sem o pacote → `None` (região indisponível)."""
    from app.core.config import get_settings

    caminho = get_settings().geoip_db_path
    if not caminho:
        return None
    try:
        import maxminddb  # type: ignore[import-not-found]  # dependência OPCIONAL: só necessária se houver uma base .mmdb

        return maxminddb.open_database(caminho)
    except Exception:  # base ausente/corrompida ou pacote não instalado — o login segue sem região
        logger.warning("GeoIP indisponível (GEOIP_DB_PATH configurado, mas a base não pôde ser aberta).")
        return None


def regiao_do_ip(ip: str | None, leitor: LeitorGeoIP | None = None) -> str | None:
    """Região aproximada do IP, ou `None`. NUNCA levanta exceção."""
    try:
        if not ip_consultavel(ip):
            return None
        leitor = leitor if leitor is not None else _leitor_padrao()
        if leitor is None:
            return None
        return formatar_regiao(leitor.get(ip))  # type: ignore[arg-type]
    except Exception:
        return None
