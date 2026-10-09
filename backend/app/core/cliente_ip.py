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

## Cloudflare (Fase 7E.2)

Com o domínio atrás da Cloudflare, o IP público do visitante chega em `CF-Connecting-IP` (a Cloudflare o sobrescreve na borda); o
`X-Real-IP`/`X-Forwarded-For` do proxy da origem trazem só o IP da borda da Cloudflare. O BFF (Next.js) sanitiza e repassa um único
IP válido em `X-Taskflow-Client-IP`. Prioridade, SEMPRE condicionada a o peer imediato ser um proxy confiável: (1) `X-Taskflow-Client-IP`,
(2) `CF-Connecting-IP`, (3) cadeia do `X-Forwarded-For`, (4) o próprio peer. Cada candidato precisa conter UM IP válido (lista, texto ou
porta inválida são descartados — nunca "o primeiro item"). De conexão não confiável, todos os cabeçalhos são ignorados.
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


def conexao_de_proxy_confiavel(peer: str | None, redes_confiaveis: Sequence[IPNetwork]) -> bool:
    """O peer imediato pertence às redes de proxy confiáveis? É o portão de TODO cabeçalho encaminhado (IP e região)."""
    endereco = normalizar_ip(peer)
    return endereco is not None and _confiavel(endereco, redes_confiaveis)


def ip_publico(ip: str | None) -> bool:
    """Só IP público e global tem região: privado, loopback, link-local, multicast, reservado, não especificado e CGNAT → não."""
    endereco = normalizar_ip(ip)
    return endereco is not None and endereco.is_global and not endereco.is_multicast and not endereco.is_unspecified


def resolver_ip_cliente(
    peer: str | None,
    x_forwarded_for: str | None,
    redes_confiaveis: Sequence[IPNetwork],
    *,
    ip_encaminhado: Iterable[str | None] = (),
) -> str | None:
    """IP original do cliente a partir do peer imediato, dos cabeçalhos dedicados (`ip_encaminhado`, em ordem de prioridade:
    `X-Taskflow-Client-IP`, `CF-Connecting-IP`) e do `X-Forwarded-For`. Função pura (testável sem HTTP)."""
    atual = normalizar_ip(peer)
    if atual is None:
        return None
    if not _confiavel(atual, redes_confiaveis):
        return str(atual)  # conexão direta (ou de origem não confiável): TODOS os cabeçalhos são ignorados
    for candidato in ip_encaminhado:  # cabeçalho dedicado com UM IP válido vence a cadeia
        endereco = normalizar_ip(candidato)
        if endereco is not None:
            return str(endereco)
    if not x_forwarded_for:
        return str(atual)

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
    return resolver_ip_cliente(
        peer,
        request.headers.get("x-forwarded-for"),
        redes_confiaveis,
        ip_encaminhado=(request.headers.get("x-taskflow-client-ip"), request.headers.get("cf-connecting-ip")),
    )
