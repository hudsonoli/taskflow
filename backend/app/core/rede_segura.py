"""Validação de destino de conexão de saída (Fase 2G.7B1) — mitigação SSRF-like pro endpoint
de teste de SMTP (`POST /configuracoes/email/testar`).

Salvar a configuração antes de testar (em vez de aceitar host/porta/credencial arbitrários no
corpo do teste) já reduz bastante a superfície — mas não elimina SSRF: o endpoint ainda faz
uma conexão de saída de verdade para `smtp_host`, que é dado configurável pelo próprio Cliente
da Empresa (admin/gestor). Este módulo resolve o host e recusa endereços que nunca deveriam
ser alvo de uma conexão de saída disparada pelo servidor.

## O que é bloqueado, e por quê

`loopback` (127.0.0.1/::1 — serviços internos do próprio host), `link-local` (169.254.0.0/16,
inclui o endpoint de metadados de nuvem 169.254.169.254), `multicast`, `unspecified`
(0.0.0.0/::) e `reserved` (inclui 255.255.255.255) — nenhuma dessas categorias é um destino
SMTP legítimo em nenhum cenário real.

## O que é DELIBERADAMENTE PERMITIDO

Endereços privados RFC1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) e ULA IPv6 (fc00::/7,
exceto os já cobertos acima) **não são bloqueados** — um relay SMTP interno da própria rede da
Empresa (ex.: um Exchange on-premises, um relay de outra VM na mesma VPC) é um uso legítimo e
comum. Bloquear RFC1918 genericamente quebraria esse caso sem necessidade real de segurança
adicional (quem já teria acesso à rede privada da Empresa para configurar isto já teria
acesso equivalente por outros meios).

## Risco residual: TOCTOU / DNS rebinding — documentado, não eliminado

Esta função resolve e valida o host UMA VEZ. A conexão SMTP real (em
`configuracao_email_smtp_service.py`) é feita pelo hostname original, não pelo IP validado
aqui — ou seja, entre a validação e a conexão de fato, `smtplib`/o resolver do SO faz uma
SEGUNDA resolução DNS independente. Um atacante controlando o DNS do host configurado
poderia, em tese, responder um IP seguro na primeira consulta (a desta função) e um IP
interno na segunda (a do `connect()` real) — DNS rebinding clássico.

Eliminar isso completamente exigiria conectar pelo IP já validado mantendo o hostname
original só para SNI/verificação de certificado TLS (viável, mas não trivial com a API de
alto nível de `smtplib`, e um bug nessa parte quebraria TLS pra qualquer host legítimo).
Decisão desta fase: aceitar esse risco residual e documentá-lo explicitamente (autorizado
pelo kickoff da Fase 2G.7B1, item 20) em vez de implementar uma proteção parcial/frágil que
passe a falsa sensação de estar completa. Quem configura `smtp_host` já é admin/gestor da
própria Empresa — o cenário de exploração exige controlar o DNS do host que a própria Empresa
está digitando na sua própria configuração, uma barra bem mais alta que SSRF genérico.
"""

from __future__ import annotations

import ipaddress
import socket


class HostNaoResolvidoError(RuntimeError):
    """Falha de DNS ao resolver o host configurado — motivo seguro para o resultado do teste
    (`dns_falhou`), nunca a exceção crua do resolver."""


class HostBloqueadoError(RuntimeError):
    """Todos os endereços resolvidos para o host caem em uma categoria bloqueada (loopback,
    link-local, multicast, unspecified, reservado). Motivo seguro: `host_bloqueado` — nunca
    inclui o IP resolvido na mensagem (não amplia exposição de topologia interna à resposta
    da API, por instrução explícita da Fase 2G.7B1)."""


def _endereco_bloqueado(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved


def validar_host_smtp_resolvivel(host: str) -> None:
    """Levanta `HostNaoResolvidoError`/`HostBloqueadoError` se o host não puder ser usado como
    alvo de teste de conexão. Não retorna o IP resolvido — quem chama conecta pelo HOSTNAME
    original (ver docstring do módulo sobre o risco residual de TOCTOU), esta função só serve
    de gate prévio."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise HostNaoResolvidoError(f"DNS não resolveu o host configurado") from exc

    enderecos = {info[4][0] for info in infos}
    if not enderecos:
        raise HostNaoResolvidoError("DNS não resolveu nenhum endereço para o host configurado")

    algum_permitido = False
    for endereco in enderecos:
        # `%scope` em endereços IPv6 link-local (ex.: fe80::1%eth0) não é aceito por
        # ip_address — removido antes de parsear; não afeta a classificação (link-local já
        # seria bloqueado de qualquer forma).
        endereco_sem_escopo = endereco.split("%", 1)[0]
        ip = ipaddress.ip_address(endereco_sem_escopo)
        if not _endereco_bloqueado(ip):
            algum_permitido = True
            break

    if not algum_permitido:
        raise HostBloqueadoError("Host resolve apenas para endereços não permitidos")
