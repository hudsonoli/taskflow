"""Teste de conexão SMTP (Fase 2G.7B1) — POST /configuracoes/email/testar.

V1 testa SOMENTE conectividade: DNS/connect, negociação TLS/SSL conforme a configuração
salva, EHLO, e AUTH se usuário+senha estiverem configurados. **NUNCA envia e-mail** — não há
nenhuma chamada a `sendmail`/`send_message` neste módulo nem em nenhum outro lugar do domínio
Email (ver Fase 2G.7A, item 20, e kickoff 2G.7B1, item 22).

Timeout curto e explícito (nunca o default/infinito de `smtplib`) — ver Fase 2G.7A, item 19.

Nunca desabilita verificação de certificado: sempre `ssl.create_default_context()`, nunca
`CERT_NONE`/`check_hostname=False` (kickoff 2G.7B1, item 23).

Falha de SMTP é resultado ESPERADO desta ação — nunca uma exceção crua sobe até a rota; todo
motivo de falha é um dos valores finitos em `MOTIVOS` (kickoff, item 24/25).
"""

from __future__ import annotations

import smtplib
import socket
import ssl
from dataclasses import dataclass
from typing import Callable

from app.core.rede_segura import HostBloqueadoError, HostNaoResolvidoError, validar_host_smtp_resolvivel

TIMEOUT_SEGUNDOS_PADRAO = 8

MOTIVO_SUCESSO = "sucesso"
MOTIVO_CONFIGURACAO_INCOMPLETA = "configuracao_incompleta"
MOTIVO_DNS_FALHOU = "dns_falhou"
MOTIVO_HOST_BLOQUEADO = "host_bloqueado"
MOTIVO_TIMEOUT = "timeout"
MOTIVO_AUTENTICACAO_INVALIDA = "autenticacao_invalida"
MOTIVO_TLS_INVALIDO = "tls_invalido"
MOTIVO_CONEXAO_RECUSADA = "conexao_recusada"
MOTIVO_ERRO_SMTP = "erro_smtp"
MOTIVO_ERRO_DESCONHECIDO = "erro_desconhecido"

_MENSAGENS: dict[str, str] = {
    MOTIVO_SUCESSO: "Conexão SMTP estabelecida com sucesso.",
    MOTIVO_CONFIGURACAO_INCOMPLETA: (
        "Configuração incompleta — servidor/porta SMTP não definidos, ou usuário definido sem senha."
    ),
    MOTIVO_DNS_FALHOU: "Não foi possível resolver o servidor SMTP configurado.",
    MOTIVO_HOST_BLOQUEADO: "O servidor SMTP configurado aponta para um endereço não permitido.",
    MOTIVO_TIMEOUT: "A conexão com o servidor SMTP expirou.",
    MOTIVO_AUTENTICACAO_INVALIDA: "O servidor SMTP recusou as credenciais configuradas.",
    MOTIVO_TLS_INVALIDO: "Falha na negociação TLS/SSL com o servidor SMTP.",
    MOTIVO_CONEXAO_RECUSADA: "O servidor SMTP recusou a conexão.",
    MOTIVO_ERRO_SMTP: "O servidor SMTP respondeu com um erro.",
    MOTIVO_ERRO_DESCONHECIDO: "Não foi possível testar a conexão com o servidor SMTP.",
}


@dataclass(frozen=True)
class ParametrosTesteSmtp:
    """Sempre a configuração JÁ SALVA — nunca um draft arbitrário do request (ver Fase 2G.7A,
    item 18). `smtp_senha` chega aqui já em texto claro: SÓ `ConfiguracaoEmailService`
    descriptografa, este módulo não conhece Fernet nem a chave mestra."""

    smtp_host: str | None
    smtp_port: int | None
    smtp_usuario: str | None
    smtp_senha: str | None
    usar_tls: bool
    usar_ssl: bool


@dataclass(frozen=True)
class ResultadoTesteSmtp:
    sucesso: bool
    motivo: str
    mensagem: str


class ConfiguracaoEmailSmtpService:
    """Isolado do resto do domínio de propósito: não conhece `ConfiguracaoEmail` (model), não
    conhece `Session`/repository — recebe parâmetros já resolvidos e devolve um resultado,
    nunca levanta exceção pra fora."""

    def __init__(
        self,
        *,
        timeout: int = TIMEOUT_SEGUNDOS_PADRAO,
        smtp_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP,
        smtp_ssl_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP_SSL,
    ) -> None:
        # Factories injetáveis SÓ para teste (mockar smtplib sem depender de rede real) — em
        # uso real, os defaults acima (as próprias classes de smtplib) bastam.
        self._timeout = timeout
        self._smtp_factory = smtp_factory
        self._smtp_ssl_factory = smtp_ssl_factory

    def testar(self, parametros: ParametrosTesteSmtp) -> ResultadoTesteSmtp:
        if not parametros.smtp_host or not parametros.smtp_port:
            return self._resultado(False, MOTIVO_CONFIGURACAO_INCOMPLETA)
        if parametros.smtp_usuario and not parametros.smtp_senha:
            return self._resultado(False, MOTIVO_CONFIGURACAO_INCOMPLETA)

        try:
            validar_host_smtp_resolvivel(parametros.smtp_host)
        except HostNaoResolvidoError:
            return self._resultado(False, MOTIVO_DNS_FALHOU)
        except HostBloqueadoError:
            return self._resultado(False, MOTIVO_HOST_BLOQUEADO)

        cliente: smtplib.SMTP | None = None
        try:
            cliente = self._conectar(parametros)
            cliente.ehlo()
            if parametros.usar_tls:
                cliente.starttls(context=ssl.create_default_context())
                cliente.ehlo()
            if parametros.smtp_usuario and parametros.smtp_senha:
                cliente.login(parametros.smtp_usuario, parametros.smtp_senha)
            # NUNCA cliente.sendmail(...)/send_message(...) aqui — V1 só testa conectividade.
            return self._resultado(True, MOTIVO_SUCESSO)
        except smtplib.SMTPAuthenticationError:
            return self._resultado(False, MOTIVO_AUTENTICACAO_INVALIDA)
        except smtplib.SMTPNotSupportedError:
            return self._resultado(False, MOTIVO_TLS_INVALIDO)
        except ssl.SSLError:
            return self._resultado(False, MOTIVO_TLS_INVALIDO)
        except ConnectionRefusedError:
            return self._resultado(False, MOTIVO_CONEXAO_RECUSADA)
        except TimeoutError:
            # `socket.timeout` é alias de `TimeoutError` desde o Python 3.10 — um único
            # except cobre os dois nomes.
            return self._resultado(False, MOTIVO_TIMEOUT)
        except socket.gaierror:
            # Também pode ocorrer aqui (não só em validar_host_smtp_resolvivel) se a segunda
            # resolução de DNS feita pelo smtplib divergir da primeira — ver risco residual
            # documentado em app/core/rede_segura.py.
            return self._resultado(False, MOTIVO_DNS_FALHOU)
        except smtplib.SMTPException:
            return self._resultado(False, MOTIVO_ERRO_SMTP)
        except OSError:
            return self._resultado(False, MOTIVO_ERRO_DESCONHECIDO)
        finally:
            if cliente is not None:
                try:
                    cliente.quit()
                except Exception:
                    try:
                        cliente.close()
                    except Exception:
                        pass

    def _conectar(self, parametros: ParametrosTesteSmtp) -> smtplib.SMTP:
        if parametros.usar_ssl:
            return self._smtp_ssl_factory(
                parametros.smtp_host,
                parametros.smtp_port,
                timeout=self._timeout,
                context=ssl.create_default_context(),
            )
        return self._smtp_factory(parametros.smtp_host, parametros.smtp_port, timeout=self._timeout)

    @staticmethod
    def _resultado(sucesso: bool, motivo: str) -> ResultadoTesteSmtp:
        return ResultadoTesteSmtp(sucesso=sucesso, motivo=motivo, mensagem=_MENSAGENS[motivo])
