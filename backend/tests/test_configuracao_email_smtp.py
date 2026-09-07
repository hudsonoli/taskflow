"""Teste de conexão SMTP (Fase 2G.7B1) — app/services/configuracao_email_smtp_service.py.

Tudo mockado via `smtp_factory`/`smtp_ssl_factory` injetáveis — nenhum teste aqui abre
socket real nem depende de internet/DNS de verdade. `validar_host_smtp_resolvivel` também é
monkeypatchada quando não é o alvo do teste (os testes de SSRF em si ficam em
test_rede_segura.py)."""

from __future__ import annotations

import smtplib
import socket
import ssl

import pytest

from app.core import rede_segura
from app.services import configuracao_email_smtp_service as smtp_service_module
from app.services.configuracao_email_smtp_service import (
    ConfiguracaoEmailSmtpService,
    MOTIVO_AUTENTICACAO_INVALIDA,
    MOTIVO_CONEXAO_RECUSADA,
    MOTIVO_CONFIGURACAO_INCOMPLETA,
    MOTIVO_DNS_FALHOU,
    MOTIVO_HOST_BLOQUEADO,
    MOTIVO_SUCESSO,
    MOTIVO_TIMEOUT,
    MOTIVO_TLS_INVALIDO,
    ParametrosTesteSmtp,
)


class FakeSmtpCliente:
    """Simula a interface de `smtplib.SMTP`/`SMTP_SSL` que o service usa. `sendmail`/
    `send_message` levantam se chamados — é a garantia de que V1 nunca envia e-mail (item
    AE)."""

    def __init__(self, *, falha_starttls: Exception | None = None, falha_login: Exception | None = None):
        self.chamadas: list[str] = []
        self._falha_starttls = falha_starttls
        self._falha_login = falha_login

    def ehlo(self):
        self.chamadas.append("ehlo")

    def starttls(self, context=None):
        self.chamadas.append("starttls")
        if self._falha_starttls:
            raise self._falha_starttls

    def login(self, usuario, senha):
        self.chamadas.append(f"login:{usuario}:{senha}")
        if self._falha_login:
            raise self._falha_login

    def sendmail(self, *args, **kwargs):  # pragma: no cover — nunca deve ser chamado
        raise AssertionError("sendmail nunca deveria ser chamado — V1 só testa conectividade")

    def send_message(self, *args, **kwargs):  # pragma: no cover — nunca deve ser chamado
        raise AssertionError("send_message nunca deveria ser chamado — V1 só testa conectividade")

    def quit(self):
        self.chamadas.append("quit")

    def close(self):
        self.chamadas.append("close")


def _service_sem_ssrf_gate(monkeypatch: pytest.MonkeyPatch, **kwargs) -> ConfiguracaoEmailSmtpService:
    """A maioria destes testes quer exercitar smtplib, não o gate SSRF (já coberto em
    test_rede_segura.py) — libera o gate por padrão.

    IMPORTANTE: `configuracao_email_smtp_service.py` faz `from app.core.rede_segura import
    validar_host_smtp_resolvivel` — isso copia a referência pro namespace DELE no momento do
    import. Monkeypatchar `rede_segura.validar_host_smtp_resolvivel` não afeta esse nome já
    vinculado; é preciso patchar o nome no módulo que efetivamente o usa."""
    monkeypatch.setattr(smtp_service_module, "validar_host_smtp_resolvivel", lambda host: None)
    return ConfiguracaoEmailSmtpService(**kwargs)


def _parametros(**overrides) -> ParametrosTesteSmtp:
    base = dict(
        smtp_host="smtp.exemplo.com",
        smtp_port=587,
        smtp_usuario=None,
        smtp_senha=None,
        usar_tls=False,
        usar_ssl=False,
    )
    base.update(overrides)
    return ParametrosTesteSmtp(**base)


# --------------------------------------------------------------------------------------
# V-X: conexões bem-sucedidas
# --------------------------------------------------------------------------------------


def test_v_conexao_simples_sucesso(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = FakeSmtpCliente()
    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=lambda host, port, timeout=None: cliente)

    resultado = service.testar(_parametros())

    assert resultado.sucesso is True
    assert resultado.motivo == MOTIVO_SUCESSO
    assert cliente.chamadas == ["ehlo", "quit"]  # sem starttls, sem login, sem sendmail


def test_w_starttls_sucesso(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = FakeSmtpCliente()
    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=lambda host, port, timeout=None: cliente)

    resultado = service.testar(_parametros(usar_tls=True))

    assert resultado.sucesso is True
    assert cliente.chamadas == ["ehlo", "starttls", "ehlo", "quit"]  # EHLO -> STARTTLS -> EHLO de novo


def test_x_ssl_implicito_sucesso(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = FakeSmtpCliente()
    service = _service_sem_ssrf_gate(
        monkeypatch, smtp_ssl_factory=lambda host, port, timeout=None, context=None: cliente
    )

    resultado = service.testar(_parametros(usar_ssl=True, smtp_port=465))

    assert resultado.sucesso is True
    assert cliente.chamadas == ["ehlo", "quit"]  # sem starttls — já veio implícito da conexão


def test_com_usuario_e_senha_autentica(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = FakeSmtpCliente()
    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=lambda host, port, timeout=None: cliente)

    resultado = service.testar(_parametros(smtp_usuario="user@exemplo.com", smtp_senha="segredo"))

    assert resultado.sucesso is True
    assert "login:user@exemplo.com:segredo" in cliente.chamadas


# --------------------------------------------------------------------------------------
# Y-AC: falhas mapeadas
# --------------------------------------------------------------------------------------


def test_y_autenticacao_invalida(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = FakeSmtpCliente(falha_login=smtplib.SMTPAuthenticationError(535, b"bad credentials"))
    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=lambda host, port, timeout=None: cliente)

    resultado = service.testar(_parametros(smtp_usuario="user@exemplo.com", smtp_senha="errada"))

    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_AUTENTICACAO_INVALIDA
    assert "errada" not in resultado.mensagem


def test_z_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def _factory_timeout(host, port, timeout=None):
        raise TimeoutError("timed out")

    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=_factory_timeout)
    resultado = service.testar(_parametros())

    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_TIMEOUT


def test_aa_dns_falhou_no_gate_previo(monkeypatch: pytest.MonkeyPatch) -> None:
    def _levanta_dns(host):
        raise rede_segura.HostNaoResolvidoError("dns falhou")

    monkeypatch.setattr(smtp_service_module, "validar_host_smtp_resolvivel", _levanta_dns)
    service = ConfiguracaoEmailSmtpService()

    resultado = service.testar(_parametros())

    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_DNS_FALHOU


def test_aa_dns_falhou_no_connect_em_si(monkeypatch: pytest.MonkeyPatch) -> None:
    def _factory_gaierror(host, port, timeout=None):
        raise socket.gaierror("dns falhou no connect")

    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=_factory_gaierror)
    resultado = service.testar(_parametros())

    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_DNS_FALHOU


def test_host_bloqueado_pelo_gate_previo(monkeypatch: pytest.MonkeyPatch) -> None:
    def _levanta_bloqueado(host):
        raise rede_segura.HostBloqueadoError("host bloqueado")

    monkeypatch.setattr(smtp_service_module, "validar_host_smtp_resolvivel", _levanta_bloqueado)
    service = ConfiguracaoEmailSmtpService()

    resultado = service.testar(_parametros(smtp_host="127.0.0.1"))

    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_HOST_BLOQUEADO
    assert "127.0.0.1" not in resultado.mensagem  # nunca expõe o endereço na resposta


def test_ab_conexao_recusada(monkeypatch: pytest.MonkeyPatch) -> None:
    def _factory_recusada(host, port, timeout=None):
        raise ConnectionRefusedError("connection refused")

    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=_factory_recusada)
    resultado = service.testar(_parametros())

    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_CONEXAO_RECUSADA


def test_ac_tls_invalido_starttls_nao_suportado(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = FakeSmtpCliente(falha_starttls=smtplib.SMTPNotSupportedError("STARTTLS not supported"))
    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=lambda host, port, timeout=None: cliente)

    resultado = service.testar(_parametros(usar_tls=True))

    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_TLS_INVALIDO


def test_ac_tls_invalido_erro_ssl(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = FakeSmtpCliente(falha_starttls=ssl.SSLError("certificate verify failed"))
    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=lambda host, port, timeout=None: cliente)

    resultado = service.testar(_parametros(usar_tls=True))

    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_TLS_INVALIDO


# --------------------------------------------------------------------------------------
# AD: configuração incompleta
# --------------------------------------------------------------------------------------


def test_ad_sem_host_e_configuracao_incompleta(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_sem_ssrf_gate(monkeypatch)
    resultado = service.testar(_parametros(smtp_host=None))
    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_CONFIGURACAO_INCOMPLETA


def test_ad_sem_porta_e_configuracao_incompleta(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_sem_ssrf_gate(monkeypatch)
    resultado = service.testar(_parametros(smtp_port=None))
    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_CONFIGURACAO_INCOMPLETA


def test_ad_usuario_sem_senha_e_configuracao_incompleta(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_sem_ssrf_gate(monkeypatch)
    resultado = service.testar(_parametros(smtp_usuario="user@exemplo.com", smtp_senha=None))
    assert resultado.sucesso is False
    assert resultado.motivo == MOTIVO_CONFIGURACAO_INCOMPLETA


# --------------------------------------------------------------------------------------
# AE: nenhum e-mail é enviado — garantido pelo próprio FakeSmtpCliente acima (sendmail/
# send_message levantam AssertionError se chamados). Reforça com verificação explícita nas
# chamadas registradas em todos os cenários de sucesso já cobertos (V, W, X).
# --------------------------------------------------------------------------------------


def test_ae_nenhuma_chamada_de_envio_em_nenhum_cenario_de_sucesso(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = FakeSmtpCliente()
    service = _service_sem_ssrf_gate(monkeypatch, smtp_factory=lambda host, port, timeout=None: cliente)

    service.testar(_parametros(usar_tls=True, smtp_usuario="user@exemplo.com", smtp_senha="segredo"))

    assert not any("sendmail" in chamada or "send_message" in chamada for chamada in cliente.chamadas)
