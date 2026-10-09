"""IP ORIGINAL do cliente de uma requisição HTTP (Fase 7E) — fonte única, sem confiar cegamente em cabeçalho.

## O problema

Atrás de um reverse proxy, `request.client.host` é o IP do PROXY (em produção, o IP interno do container do frontend/BFF), não o do
usuário. O IP real só chega em `X-Forwarded-For`, que qualquer cliente pode escrever — aceitá-lo de qualquer origem permite forjar
a auditoria de acesso.

## A regra

- o cabeçalho só é considerado quando a conexão IMEDIATA (o *peer*) vem de um proxy confiável (`TRUSTED_PROXY_CIDRS`); caso
  contrário vale `request.client.host` e o `X-Forwarded-For` é ignorado (anti-spoofing);
- com proxy confiável, percorre-se a cadeia da DIREITA para a ESQUERDA: cada salto confiável "entrega" o endereço de quem falou
  com ele; o primeiro endereço NÃO confiável é o cliente. Nunca `split(",")[0]` — o item mais à esquerda é justamente o que o
  cliente controla;
- só IPs válidos (IPv4/IPv6); porta, colchetes, zona IPv6 e IPv4-mapeado são normalizados; entrada inválida interrompe a cadeia (fica o
  último salto confiável conhecido) e a cadeia é limitada;
- o resultado é sempre um IP normalizado (ou `None`) — nunca a lista inteira, a porta ou texto arbitrário.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable, Sequence

from starlette.requests import Request

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

# Cadeias reais têm 1–3 saltos; um limite evita trabalho com cabeçalho absurdo.
MAX_SALTOS = 10


def normalizar_ip(valor: str | None) -> IPAddress | None:
    """Texto → IP, aceitando `1.2.3.4`, `1.2.3.4:5678`, `[::1]:443`, `fe80::1%eth0`, `::ffff:1.2.3.4`. Inválido → `None`."""
    if not valor:
        return None
    texto = valor.strip().strip('"')
    if not texto or len(texto) > 64:
        return None
    if texto.startswith("["):  # [v6]:porta ou [v6]
        fim = texto.find("]")
        if fim == -1:
            return None
        texto = texto[1:fim]
    elif texto.count(":") == 1:  # v4:porta
        texto = texto.split(":", 1)[0]
    texto = texto.split("%", 1)[0]  # zona do IPv6 (fe80::1%eth0)
    try:
        endereco = ipaddress.ip_address(texto)
    except ValueError:
        return None
    if isinstance(endereco, ipaddress.IPv6Address) and endereco.ipv4_mapped is not None:
        return endereco.ipv4_mapped
    return endereco


def parse_redes_confiaveis(cidrs: Iterable[str]) -> tuple[IPNetwork, ...]:
    """CSV/lista de CIDRs (ou IPs soltos) → redes. Valor inválido falha no boot (configuração errada não pode abrir confiança)."""
    redes: list[IPNetwork] = []
    for bruto in cidrs:
        item = bruto.strip()
        if item:
            redes.append(ipaddress.ip_network(item, strict=False))
    return tuple(redes)


def _confiavel(endereco: IPAddress, redes: Sequence[IPNetwork]) -> bool:
    return any(endereco.version == rede.version and endereco in rede for rede in redes)


def resolver_ip_cliente(
    peer: str | None, x_forwarded_for: str | None, redes_confiaveis: Sequence[IPNetwork]
) -> str | None:
    """IP original do cliente a partir do peer imediato e do `X-Forwarded-For`. Função pura (testável sem HTTP)."""
    atual = normalizar_ip(peer)
    if atual is None:
        return None
    if not x_forwarded_for or not _confiavel(atual, redes_confiaveis):
        return str(atual)  # conexão direta (ou de origem não confiável): o cabeçalho é ignorado

    saltos = [parte for parte in x_forwarded_for.split(",")][-MAX_SALTOS:]
    for bruto in reversed(saltos):
        anterior = normalizar_ip(bruto)
        if anterior is None:
            break  # entrada inválida: não adivinha — fica com o último salto conhecido
        atual = anterior
        if not _confiavel(atual, redes_confiaveis):
            break  # primeiro endereço não confiável = o cliente
    return str(atual)


def resolver_ip_cliente_da_requisicao(request: Request, redes_confiaveis: Sequence[IPNetwork] | None = None) -> str | None:
    """Helper central usado pelas rotas de login — NÃO duplicar esta lógica nas rotas."""
    if redes_confiaveis is None:
        from app.core.config import get_settings

        redes_confiaveis = get_settings().trusted_proxy_networks
    peer = request.client.host if request.client else None
    return resolver_ip_cliente(peer, request.headers.get("x-forwarded-for"), redes_confiaveis)
