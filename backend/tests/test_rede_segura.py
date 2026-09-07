"""Validação SSRF-like de host de destino (Fase 2G.7B1) — app/core/rede_segura.py.

Função pura, sem rede real: monkeypatcha `socket.getaddrinfo` pra controlar exatamente o
que cada host "resolve" para, sem depender de DNS de verdade nem de conectividade."""

from __future__ import annotations

import socket

import pytest

from app.core.rede_segura import HostBloqueadoError, HostNaoResolvidoError, validar_host_smtp_resolvivel


def _getaddrinfo_fake(enderecos: list[str]):
    def _fake(host, port):
        # Formato mínimo compatível com o que validar_host_smtp_resolvivel lê: info[4][0].
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (endereco, 0)) for endereco in enderecos]

    return _fake


@pytest.mark.parametrize(
    "endereco",
    [
        "127.0.0.1",  # loopback
        "::1",  # loopback IPv6
        "169.254.169.254",  # link-local — inclui o endpoint de metadados de nuvem
        "224.0.0.1",  # multicast
        "ff02::1",  # multicast IPv6
        "0.0.0.0",  # unspecified
        "::",  # unspecified IPv6
        "255.255.255.255",  # broadcast/reservado
    ],
)
def test_enderecos_bloqueados(monkeypatch: pytest.MonkeyPatch, endereco: str) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo_fake([endereco]))
    with pytest.raises(HostBloqueadoError):
        validar_host_smtp_resolvivel("host.exemplo.com")


@pytest.mark.parametrize("endereco", ["10.0.0.5", "172.16.0.5", "192.168.1.5"])
def test_enderecos_privados_rfc1918_permitidos(monkeypatch: pytest.MonkeyPatch, endereco: str) -> None:
    """Deliberadamente PERMITIDO — relay SMTP interno legítimo (Fase 2G.7A, item 20)."""
    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo_fake([endereco]))
    validar_host_smtp_resolvivel("relay-interno.exemplo.com")  # não levanta


def test_endereco_publico_permitido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo_fake(["8.8.8.8"]))
    validar_host_smtp_resolvivel("smtp.publico.exemplo.com")  # não levanta


def test_dns_nao_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake(host, port):
        raise socket.gaierror("nome não existe")

    monkeypatch.setattr(socket, "getaddrinfo", _fake)
    with pytest.raises(HostNaoResolvidoError):
        validar_host_smtp_resolvivel("nao-existe.invalido")


def test_pelo_menos_um_endereco_permitido_ja_libera(monkeypatch: pytest.MonkeyPatch) -> None:
    """Host com múltiplos IPs (ex.: round-robin) — basta UM endereço permitido para o host
    passar; a conexão real feita depois usa a resolução do próprio smtplib (ver risco
    residual documentado em app/core/rede_segura.py), este gate é só um filtro prévio."""
    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo_fake(["127.0.0.1", "8.8.8.8"]))
    validar_host_smtp_resolvivel("host-misto.exemplo.com")  # não levanta


def test_todos_os_enderecos_bloqueados_levanta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo_fake(["127.0.0.1", "169.254.1.1"]))
    with pytest.raises(HostBloqueadoError):
        validar_host_smtp_resolvivel("host-todo-bloqueado.exemplo.com")
