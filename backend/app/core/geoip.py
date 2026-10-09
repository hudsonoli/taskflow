"""Região APROXIMADA de um IP público (Fases 7E/7E.1) — GeoIP LOCAL (MaxMind GeoLite2-City, `.mmdb`), opcional, nunca bloqueia o login.

## Por que local

O login não pode depender de terceiro (latência, indisponibilidade, limite de uso) nem enviar o IP de cada usuário a um serviço
externo (LGPD: IP é dado pessoal). A única fonte é um arquivo `.mmdb` lido do disco, indicado por `GEOIP_DB_PATH`. **O arquivo não
é versionado nem baixado pela aplicação** (a licença MaxMind é do administrador — ver docs/geoip-e-proxy-confiavel.md).

## Regras

- sem `GEOIP_DB_PATH`, arquivo ausente ou inválido: GeoIP DESABILITADO (aviso seguro no log, sem caminho nem dado de usuário); o
  boot e o login seguem normalmente e a região fica `None` ("Não disponível" na tela);
- IP privado, loopback, link-local, multicast, reservado, não especificado ou CGNAT NUNCA é consultado — a região fica `None`;
- qualquer falha de leitura vira `None`: nunca exceção, nunca 500;
- persiste-se SÓ o texto formatado (`Brasília, DF, Brasil`): nada do registro bruto (latitude, longitude, raio de precisão, CEP, ASN);
- o leitor é aberto UMA vez por processo (carga preguiçosa, mmap) e fechado no shutdown. Trocar o `.mmdb` exige reiniciar a API
  (decisão desta fase: sem observador de arquivo).
"""

from __future__ import annotations

import ipaddress
import logging
import os
import threading
from collections.abc import Mapping
from functools import lru_cache
from typing import Any, Protocol

logger = logging.getLogger(__name__)

IDIOMAS = ("pt-BR", "pt", "en")


class LeitorGeoIP(Protocol):
    """Contrato mínimo do leitor (o `maxminddb.Reader` já o cumpre): `get(ip) -> dict | None`."""

    def get(self, ip_address: str) -> Mapping[str, Any] | None: ...


# --------------------------------------------------------------------------------------
# Formatação (pura) — só texto de região, nunca coordenadas
# --------------------------------------------------------------------------------------


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


def _codigo(registro: Mapping[str, Any] | None) -> str | None:
    if not isinstance(registro, Mapping):
        return None
    iso = registro.get("iso_code")
    return iso.strip() if isinstance(iso, str) and iso.strip() else None


def formatar_regiao(registro: Mapping[str, Any] | None) -> str | None:
    """Registro do GeoIP → `Cidade, UF, Brasil` | `UF, Brasil` | `Brasil`; fora do Brasil `Cidade, Região, País` com fallback
    progressivo. Sem nada confiável → `None`. Nunca devolve coordenada, CEP nem dado do registro bruto."""
    if not isinstance(registro, Mapping):
        return None
    pais_registro = registro.get("country") if isinstance(registro.get("country"), Mapping) else registro.get("registered_country")
    pais = _nome(pais_registro)
    brasil = _codigo(pais_registro) == "BR"
    if brasil:
        pais = "Brasil"

    cidade = _nome(registro.get("city"))
    subdivisoes = registro.get("subdivisions")
    primeira = subdivisoes[0] if isinstance(subdivisoes, list) and subdivisoes and isinstance(subdivisoes[0], Mapping) else None
    # Brasil: a sigla da UF (DF, SP…) quando existe — nunca "Federal District"; nos demais países, o nome da região.
    regiao = (_codigo(primeira) or _nome(primeira)) if brasil else (_nome(primeira) or _codigo(primeira))

    partes: list[str] = []
    for parte in (cidade, regiao, pais):
        if parte and not (partes and partes[-1].casefold() == parte.casefold()):  # "Lisboa, Lisboa, Portugal" → "Lisboa, Portugal"
            partes.append(parte)
    return ", ".join(partes) if partes else None


def ip_consultavel(ip: str | None) -> bool:
    """Só IP público e global é consultado: privado, loopback, link-local, multicast, reservado, não especificado e CGNAT → não."""
    if not ip:
        return False
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return endereco.is_global and not endereco.is_multicast and not endereco.is_unspecified


# --------------------------------------------------------------------------------------
# Provider (carga preguiçosa e segura do .mmdb)
# --------------------------------------------------------------------------------------


def _abrir_maxmind(caminho: str) -> LeitorGeoIP:
    import maxminddb  # biblioteca mínima de leitura de .mmdb (dependência de runtime)

    return maxminddb.open_database(caminho)


class GeoIPProvider:
    """Entrada: IP normalizado. Saída: região formatada ou `None`. Nunca levanta exceção para o chamador."""

    def __init__(self, caminho: str | None, *, abrir=_abrir_maxmind) -> None:
        self._caminho = (caminho or "").strip() or None
        self._abrir = abrir
        self._leitor: LeitorGeoIP | None = None
        self._carregado = False
        self._lock = threading.Lock()

    def inicializar(self) -> None:
        """Abre a base uma única vez (idempotente). Qualquer problema → GeoIP desabilitado, com aviso SEM caminho nem dado."""
        if self._carregado:
            return
        with self._lock:
            if self._carregado:
                return
            self._carregado = True
            if not self._caminho:
                logger.info("GeoIP desabilitado: GEOIP_DB_PATH não configurado.")
                return
            if not os.path.isfile(self._caminho):
                logger.warning("GeoIP desabilitado: arquivo da base não encontrado.")
                return
            try:
                self._leitor = self._abrir(self._caminho)
                logger.info("GeoIP database loaded.")
            except Exception:  # base corrompida/incompatível ou pacote ausente: o boot e o login seguem sem região
                self._leitor = None
                logger.warning("GeoIP desabilitado: a base não pôde ser aberta (arquivo inválido).")

    @property
    def configurado(self) -> bool:
        return self._caminho is not None

    @property
    def base_disponivel(self) -> bool:
        self.inicializar()
        return self._leitor is not None

    def regiao(self, ip: str | None) -> str | None:
        try:
            if not ip_consultavel(ip):
                return None
            self.inicializar()
            if self._leitor is None:
                return None
            return formatar_regiao(self._leitor.get(ip))  # type: ignore[arg-type]
        except Exception:
            return None

    def fechar(self) -> None:
        with self._lock:
            leitor, self._leitor = self._leitor, None
            self._carregado = False
        close = getattr(leitor, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                logger.warning("GeoIP: falha ao fechar a base.")


@lru_cache(maxsize=1)
def geoip_provider() -> GeoIPProvider:
    """Provider do processo, criado a partir de `GEOIP_DB_PATH` (a base só é aberta no primeiro uso ou em `inicializar`)."""
    from app.core.config import get_settings

    return GeoIPProvider(get_settings().geoip_db_path)


def reiniciar_geoip() -> None:
    """Fecha a base e descarta o provider (shutdown da API; testes)."""
    if geoip_provider.cache_info().currsize:
        geoip_provider().fechar()
    geoip_provider.cache_clear()


def status_geoip() -> dict[str, bool]:
    """Diagnóstico interno, sem caminho nem segredo: `GEOIP_ENABLED` (há configuração) e `GEOIP_DATABASE_AVAILABLE` (base aberta)."""
    provider = geoip_provider()
    return {"GEOIP_ENABLED": provider.configurado, "GEOIP_DATABASE_AVAILABLE": provider.base_disponivel}


def regiao_do_ip(ip: str | None, leitor: LeitorGeoIP | None = None) -> str | None:
    """Região aproximada do IP, ou `None`. NUNCA levanta exceção. `leitor` injeta uma fonte (testes); sem ele vale o provider do processo."""
    try:
        if leitor is not None:
            return formatar_regiao(leitor.get(ip)) if ip_consultavel(ip) else None  # type: ignore[arg-type]
        return geoip_provider().regiao(ip)
    except Exception:
        return None
