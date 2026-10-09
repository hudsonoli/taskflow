"""Navegador e sistema operacional a partir do `User-Agent` da requisição HTTP (Fase 7E) — parser pequeno, local, sem dependência.

Lê-se SEMPRE o cabeçalho real da requisição, nunca um campo enviado no corpo pelo frontend. Só o suficiente para auditoria de
acesso: nome do navegador (+ versão principal) e nome do sistema operacional.

Decisões de precisão (não inventar o que o User-Agent não diz):
- a ordem importa: Edge/Opera/Samsung/Chrome-iOS contêm "Chrome" ou "Safari" na string, então são testados antes;
- Windows 10 e 11 têm o MESMO `Windows NT 10.0` no User-Agent: mostra-se só "Windows";
- a versão do SO em User-Agents modernos é congelada (macOS 10_15_7, Android reduzido): por isso o sistema vai sem versão;
- iPhone/iPad entram como "iOS" (antes de macOS, pois dizem "like Mac OS X"); Android antes de Linux; ChromeOS antes de Linux;
- User-Agent de robô/biblioteca (curl, node, python…) ou ausente → sem navegador (a interface mostra "Desconhecido").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Limite defensivo: User-Agent legítimo tem poucas centenas de caracteres.
MAX_USER_AGENT = 1024

# (nome, regex com a versão principal). Ordem = prioridade.
_NAVEGADORES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Edge", re.compile(r"\b(?:Edg|EdgA|EdgiOS|Edge)/(\d+)")),
    ("Opera", re.compile(r"\b(?:OPR|OPT|Opera)/(\d+)")),
    ("Samsung Internet", re.compile(r"\bSamsungBrowser/(\d+)")),
    ("Firefox", re.compile(r"\b(?:Firefox|FxiOS)/(\d+)")),
    ("Chrome", re.compile(r"\b(?:Chrome|CriOS)/(\d+)")),
    ("Safari", re.compile(r"\bVersion/(\d+)[\d.]*(?: Mobile/\S+)? Safari/")),
)
_SAFARI_SEM_VERSAO = re.compile(r"\bSafari/\d+")
_ROBO = re.compile(r"\b(?:bot|crawler|spider|curl|wget|python-requests|python-httpx|node-fetch|undici|axios|okhttp|go-http-client)\b", re.I)

_SISTEMAS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("iOS", re.compile(r"\b(?:iPhone|iPad|iPod)\b")),
    ("Android", re.compile(r"\bAndroid\b")),
    ("ChromeOS", re.compile(r"\bCrOS\b")),
    ("Windows", re.compile(r"\bWindows\b")),
    ("macOS", re.compile(r"\bMacintosh\b|\bMac OS X\b")),
    ("Linux", re.compile(r"\b(?:Linux|X11|Ubuntu|Fedora|Debian)\b")),
)


@dataclass(frozen=True)
class InfoUserAgent:
    navegador_nome: str | None = None
    navegador_versao: str | None = None  # versão principal ("153"), quando determinável
    sistema_nome: str | None = None
    sistema_versao: str | None = None  # sempre None: User-Agent moderno não dá versão confiável do SO

    @property
    def navegador(self) -> str | None:
        """Rótulo para a tela: `Chrome 153`, ou só `Chrome` se a versão não puder ser determinada."""
        if not self.navegador_nome:
            return None
        return f"{self.navegador_nome} {self.navegador_versao}" if self.navegador_versao else self.navegador_nome

    @property
    def sistema(self) -> str | None:
        return self.sistema_nome


def parse_user_agent(user_agent: str | None) -> InfoUserAgent:
    """User-Agent → navegador + sistema operacional. Nunca levanta: ausente/malformado/gigante → tudo `None`."""
    if not user_agent or not isinstance(user_agent, str):
        return InfoUserAgent()
    texto = user_agent.strip()[:MAX_USER_AGENT]
    if not texto:
        return InfoUserAgent()

    navegador_nome: str | None = None
    navegador_versao: str | None = None
    if not _ROBO.search(texto):
        for nome, padrao in _NAVEGADORES:
            achado = padrao.search(texto)
            if achado:
                navegador_nome, navegador_versao = nome, achado.group(1)
                break
        else:
            if _SAFARI_SEM_VERSAO.search(texto) and "Chrome" not in texto:
                navegador_nome = "Safari"  # sem `Version/`: melhor "Safari" do que "Desconhecido"

    sistema_nome = next((nome for nome, padrao in _SISTEMAS if padrao.search(texto)), None)
    return InfoUserAgent(navegador_nome, navegador_versao, sistema_nome, None)
