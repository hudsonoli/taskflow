"""Região APROXIMADA do visitante a partir dos cabeçalhos de localização da Cloudflare (Fase 7E.2).

## Fonte

O domínio já está atrás da Cloudflare. Com o Managed Transform **"Add visitor location headers"** habilitado (Dashboard → domínio →
Rules → Transform Rules → Managed Transforms), a Cloudflare acrescenta à requisição `CF-IPCity`, `CF-Region`, `CF-Region-Code` e
`CF-IPCountry`. Não há banco local, chave de licença nem consulta externa: o login não chama ninguém, só lê a requisição.

## Cadeia e confiança

`Cloudflare → NPM → BFF (Next.js) → API`. O BFF NÃO repassa `CF-*` do navegador: ele valida, decodifica e envia à API cabeçalhos internos
controlados (`X-Taskflow-CF-City`, `-Region`, `-Region-Code`, `-Country`), com o valor em percent-encoding (transporte ASCII). A API só lê
esses cabeçalhos — e `CF-*` diretos — quando o peer imediato é um proxy confiável (`TRUSTED_PROXY_CIDRS`); de conexão não confiável
são IGNORADOS (anti-spoofing), exatamente como o IP.

## Privacidade (coleta mínima)

Só texto de região (`Cidade, UF, País`). Latitude, longitude, CEP, fuso e qualquer objeto geográfico bruto NUNCA são lidos nem
persistidos. Sem os cabeçalhos (Managed Transform desligado), IP não público ou valor malformado: região `None` ("Não disponível") — o
login nunca é afetado.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from urllib.parse import unquote

from starlette.requests import Request

from app.core.cliente_ip import IPNetwork, conexao_de_proxy_confiavel, ip_publico

# Cabeçalhos internos (BFF → API) e os da própria Cloudflare (quando a API é alcançada direto por um proxy confiável).
CABECALHOS_CIDADE = ("x-taskflow-cf-city", "cf-ipcity")
CABECALHOS_REGIAO = ("x-taskflow-cf-region", "cf-region")
CABECALHOS_CODIGO_REGIAO = ("x-taskflow-cf-region-code", "cf-region-code")
CABECALHOS_PAIS = ("x-taskflow-cf-country", "cf-ipcountry")

MAX_TEXTO = 80
_CODIGO_PAIS = re.compile(r"^[A-Za-z]{2}$")
_CODIGO_REGIAO = re.compile(r"^[A-Za-z0-9-]{1,6}$")
_CONTROLE = re.compile(r"[\x00-\x1f\x7f-\x9f  <>]")
# Cloudflare usa XX = sem informação de país e T1 = rede Tor: não são países.
_PAIS_SEM_INFORMACAO = frozenset({"XX", "T1"})

# Nomes amigáveis (pt-BR) dos países mais prováveis; os demais caem no código ISO (ex.: "NP"), nunca num nome inventado.
NOMES_PAISES: Mapping[str, str] = {
    "BR": "Brasil", "US": "Estados Unidos", "PT": "Portugal", "AR": "Argentina", "CL": "Chile", "UY": "Uruguai", "PY": "Paraguai",
    "BO": "Bolívia", "PE": "Peru", "CO": "Colômbia", "VE": "Venezuela", "EC": "Equador", "MX": "México", "CA": "Canadá",
    "CU": "Cuba", "DO": "República Dominicana", "PA": "Panamá", "CR": "Costa Rica", "GT": "Guatemala", "ES": "Espanha",
    "FR": "França", "DE": "Alemanha", "IT": "Itália", "GB": "Reino Unido", "IE": "Irlanda", "NL": "Países Baixos", "BE": "Bélgica",
    "CH": "Suíça", "AT": "Áustria", "LU": "Luxemburgo", "SE": "Suécia", "NO": "Noruega", "DK": "Dinamarca", "FI": "Finlândia",
    "IS": "Islândia", "PL": "Polônia", "CZ": "Tchéquia", "HU": "Hungria", "RO": "Romênia", "BG": "Bulgária", "GR": "Grécia",
    "UA": "Ucrânia", "RU": "Rússia", "TR": "Turquia", "IL": "Israel", "AE": "Emirados Árabes Unidos", "SA": "Arábia Saudita",
    "EG": "Egito", "ZA": "África do Sul", "AO": "Angola", "MZ": "Moçambique", "CV": "Cabo Verde", "NG": "Nigéria", "MA": "Marrocos",
    "IN": "Índia", "CN": "China", "JP": "Japão", "KR": "Coreia do Sul", "SG": "Singapura", "HK": "Hong Kong", "TW": "Taiwan",
    "TH": "Tailândia", "VN": "Vietnã", "ID": "Indonésia", "PH": "Filipinas", "MY": "Malásia", "AU": "Austrália", "NZ": "Nova Zelândia",
}


def _reparar_utf8_lido_como_latin1(texto: str) -> str:
    """Servidores HTTP leem os bytes do cabeçalho como latin1: um UTF-8 cru chega como "BrasÃ­lia". Se o texto só tem caracteres até U+00FF
    e, relido como latin1→UTF-8, é UTF-8 válido, devolve a versão correta; "Brasília"/"São Paulo" (já corretos) não são UTF-8 válido e ficam."""
    if not any("" <= c <= "ÿ" for c in texto) or any(ord(c) > 0xFF for c in texto):
        return texto
    try:
        return texto.encode("latin-1").decode("utf-8")
    except UnicodeDecodeError:
        return texto


def decodificar_texto(bruto: str | None) -> str | None:
    """Valor de cabeçalho → texto limpo (percent-encoding UTF-8 decodificado, sem controle/`<>`, espaços colapsados, limitado). Vazio → `None`."""
    if not isinstance(bruto, str):
        return None
    try:
        texto = unquote(bruto.strip(), errors="strict")
    except UnicodeDecodeError:
        return None
    texto = _reparar_utf8_lido_como_latin1(texto)
    texto = " ".join(_CONTROLE.sub(" ", texto).split())
    return texto[:MAX_TEXTO] or None


def codigo_pais(bruto: str | None) -> str | None:
    texto = decodificar_texto(bruto)
    if texto is None or not _CODIGO_PAIS.match(texto):
        return None
    codigo = texto.upper()
    return None if codigo in _PAIS_SEM_INFORMACAO else codigo


def codigo_regiao(bruto: str | None) -> str | None:
    texto = decodificar_texto(bruto)
    return texto.upper() if texto is not None and _CODIGO_REGIAO.match(texto) else None


def formatar_regiao(cidade: str | None, regiao: str | None, regiao_codigo: str | None, pais: str | None) -> str | None:
    """`Cidade, UF, Brasil` | `UF, Brasil` | `Brasil`; fora do Brasil `Cidade, Região, País` com fallback progressivo. Nada → `None`."""
    pais_codigo = codigo_pais(pais)
    pais_nome = NOMES_PAISES.get(pais_codigo, pais_codigo) if pais_codigo else None
    cidade_texto = decodificar_texto(cidade)
    regiao_nome = decodificar_texto(regiao)
    uf = codigo_regiao(regiao_codigo)
    # Brasil: a sigla da UF (DF, SP…) quando existe; nos demais países, o NOME da região.
    if pais_codigo == "BR":
        regiao_final = uf or regiao_nome
    else:
        regiao_final = regiao_nome or uf

    partes: list[str] = []
    for parte in (cidade_texto, regiao_final, pais_nome):
        if parte and not (partes and partes[-1].casefold() == parte.casefold()):  # "Lisboa, Lisboa, Portugal" → "Lisboa, Portugal"
            partes.append(parte)
    return ", ".join(partes) if partes else None


def _primeiro(request: Request, nomes: Sequence[str]) -> str | None:
    for nome in nomes:
        valor = request.headers.get(nome)
        if valor:
            return valor
    return None


def regiao_da_requisicao(request: Request, ip: str | None, redes_confiaveis: Sequence[IPNetwork] | None = None) -> str | None:
    """Região aproximada do visitante, ou `None`. NUNCA levanta exceção. Só lê cabeçalhos de uma conexão de proxy confiável e só para IP público."""
    try:
        if redes_confiaveis is None:
            from app.core.config import get_settings

            redes_confiaveis = get_settings().trusted_proxy_networks
        peer = request.client.host if request.client else None
        if not conexao_de_proxy_confiavel(peer, redes_confiaveis) or not ip_publico(ip):
            return None
        return formatar_regiao(
            _primeiro(request, CABECALHOS_CIDADE),
            _primeiro(request, CABECALHOS_REGIAO),
            _primeiro(request, CABECALHOS_CODIGO_REGIAO),
            _primeiro(request, CABECALHOS_PAIS),
        )
    except Exception:
        return None
