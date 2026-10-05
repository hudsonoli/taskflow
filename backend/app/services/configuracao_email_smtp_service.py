"""Transporte SMTP do domínio Email — teste de conexão (Fase 2G.7B1) e envio transacional.

## Duas operações, uma só infraestrutura

- `testar` (POST /configuracoes/email/testar) testa SOMENTE conectividade: DNS/connect,
  negociação TLS/SSL conforme a configuração salva, EHLO, e AUTH se usuário+senha estiverem
  configurados. **NUNCA envia e-mail** — não há nenhuma chamada a `sendmail`/`send_message` no
  caminho de `testar` (ver Fase 2G.7A, item 20, e kickoff 2G.7B1, item 22).
- `enviar` (envio transacional) é a única operação que entrega uma mensagem. Reutiliza
  EXATAMENTE as mesmas etapas de `testar` — validação de parâmetros, gate de rede segura
  (`validar_host_smtp_resolvivel`), abertura de sessão (connect → ehlo → [starttls → ehlo] →
  [login]) e classificação de falhas — compartilhadas por `_validar_parametros`,
  `_abrir_sessao` e `_classificar_falha`. Não existe segundo caminho de conexão: o envio não
  pode ser um alvo SSRF diferente do testador.

Timeout curto e explícito (nunca o default/infinito de `smtplib`) — ver Fase 2G.7A, item 19.

Nunca desabilita verificação de certificado: sempre `ssl.create_default_context()`, nunca
`CERT_NONE`/`check_hostname=False` (kickoff 2G.7B1, item 23).

Falha de SMTP é resultado ESPERADO — nunca uma exceção crua sobe até quem chama; todo motivo
de falha é um dos valores `MOTIVO_*` abaixo, com mensagem fixa (nunca ecoa a resposta do
servidor, host, usuário ou senha).

Este módulo não conhece `Session`, repository nem Fernet: recebe parâmetros já resolvidos
(senha em texto claro só neste instante) e devolve um resultado.
"""

from __future__ import annotations

import smtplib
import socket
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
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
# Só no envio: o servidor aceitou a sessão, mas recusou o destinatário / o remetente / os dados.
MOTIVO_DESTINATARIO_RECUSADO = "destinatario_recusado"
MOTIVO_ENVIO_RECUSADO = "envio_recusado"

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
    MOTIVO_DESTINATARIO_RECUSADO: "O servidor SMTP recusou o destinatário.",
    MOTIVO_ENVIO_RECUSADO: "O servidor SMTP recusou o envio da mensagem.",
}

_MENSAGEM_ENVIO_SUCESSO = "Mensagem entregue ao servidor SMTP."


@dataclass(frozen=True)
class ParametrosTesteSmtp:
    """Sempre a configuração JÁ SALVA — nunca um draft arbitrário do request (ver Fase 2G.7A,
    item 18). `smtp_senha` chega aqui já em texto claro: SÓ `ConfiguracaoEmailService`
    descriptografa, este módulo não conhece Fernet nem a chave mestra. Usado também pelo envio."""

    smtp_host: str | None
    smtp_port: int | None
    smtp_usuario: str | None
    # `repr=False`: a senha em texto claro nunca aparece num repr/log acidental do dataclass.
    smtp_senha: str | None = field(repr=False)
    usar_tls: bool
    usar_ssl: bool


@dataclass(frozen=True)
class ResultadoTesteSmtp:
    sucesso: bool
    motivo: str
    mensagem: str


@dataclass(frozen=True)
class ResultadoEnvioSmtp:
    sucesso: bool
    motivo: str
    mensagem: str


class ConfiguracaoEmailSmtpService:
    """Isolado do resto do domínio de propósito: não conhece `ConfiguracaoEmail` (model), não
    conhece `Session`/repository — recebe parâmetros já resolvidos e devolve um resultado,
    nunca levanta exceção pra fora (exceto uma exceção que não seja de nenhuma categoria
    conhecida — bug de programação, não falha de SMTP)."""

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

    # ----------------------------------------------------------------------------------
    # Teste de conexão — NUNCA envia
    # ----------------------------------------------------------------------------------

    def testar(self, parametros: ParametrosTesteSmtp) -> ResultadoTesteSmtp:
        motivo = self._validar_parametros(parametros)
        if motivo is not None:
            return self._resultado(False, motivo)

        cliente: smtplib.SMTP | None = None
        try:
            cliente = self._abrir_sessao(parametros)
            # NUNCA cliente.sendmail(...)/send_message(...) aqui — `testar` só testa conectividade.
            return self._resultado(True, MOTIVO_SUCESSO)
        except Exception as exc:
            motivo = self._classificar_falha(exc)
            if motivo is None:
                raise
            return self._resultado(False, motivo)
        finally:
            self._encerrar(cliente)

    # ----------------------------------------------------------------------------------
    # Envio transacional — única operação que entrega mensagem
    # ----------------------------------------------------------------------------------

    def enviar(
        self,
        parametros: ParametrosTesteSmtp,
        mensagem: EmailMessage,
        *,
        remetente: str,
        destinatario: str,
    ) -> ResultadoEnvioSmtp:
        """Entrega UMA mensagem a UM destinatário pela mesma sessão do testador. O envelope
        (`MAIL FROM`/`RCPT TO`) é passado explicitamente — nunca derivado dos cabeçalhos —, então
        só os dois endereços já validados por quem chama participam da entrega."""
        motivo = self._validar_parametros(parametros)
        if motivo is not None:
            return self._resultado_envio(False, motivo)

        cliente: smtplib.SMTP | None = None
        try:
            cliente = self._abrir_sessao(parametros)
            cliente.send_message(mensagem, from_addr=remetente, to_addrs=[destinatario])
            return ResultadoEnvioSmtp(sucesso=True, motivo=MOTIVO_SUCESSO, mensagem=_MENSAGEM_ENVIO_SUCESSO)
        except Exception as exc:
            motivo = self._classificar_falha(exc)
            if motivo is None:
                raise
            return self._resultado_envio(False, motivo)
        finally:
            self._encerrar(cliente)

    # ----------------------------------------------------------------------------------
    # Etapas compartilhadas por `testar` e `enviar`
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _validar_parametros(parametros: ParametrosTesteSmtp) -> str | None:
        """Gate prévio: configuração completa e destino de rede permitido. Devolve o motivo de
        recusa, ou `None` se pode conectar."""
        if not parametros.smtp_host or not parametros.smtp_port:
            return MOTIVO_CONFIGURACAO_INCOMPLETA
        if parametros.smtp_usuario and not parametros.smtp_senha:
            return MOTIVO_CONFIGURACAO_INCOMPLETA

        try:
            validar_host_smtp_resolvivel(parametros.smtp_host)
        except HostNaoResolvidoError:
            return MOTIVO_DNS_FALHOU
        except HostBloqueadoError:
            return MOTIVO_HOST_BLOQUEADO
        return None

    def _abrir_sessao(self, parametros: ParametrosTesteSmtp) -> smtplib.SMTP:
        """connect → ehlo → [starttls → ehlo] → [login]. Em qualquer falha no meio, a conexão já
        aberta é encerrada aqui antes de a exceção subir."""
        cliente = self._conectar(parametros)
        try:
            cliente.ehlo()
            if parametros.usar_tls:
                cliente.starttls(context=ssl.create_default_context())
                cliente.ehlo()
            if parametros.smtp_usuario and parametros.smtp_senha:
                cliente.login(parametros.smtp_usuario, parametros.smtp_senha)
        except BaseException:
            self._encerrar(cliente)
            raise
        return cliente

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
    def _classificar_falha(exc: Exception) -> str | None:
        """Exceção de transporte -> motivo finito. `None` = não é nenhuma categoria conhecida
        (quem chama deve re-levantar)."""
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            return MOTIVO_AUTENTICACAO_INVALIDA
        if isinstance(exc, smtplib.SMTPNotSupportedError):
            return MOTIVO_TLS_INVALIDO
        if isinstance(exc, ssl.SSLError):
            return MOTIVO_TLS_INVALIDO
        if isinstance(exc, ConnectionRefusedError):
            return MOTIVO_CONEXAO_RECUSADA
        if isinstance(exc, TimeoutError):
            # `socket.timeout` é alias de `TimeoutError` desde o Python 3.10 — um único
            # isinstance cobre os dois nomes.
            return MOTIVO_TIMEOUT
        if isinstance(exc, socket.gaierror):
            # Também pode ocorrer aqui (não só em validar_host_smtp_resolvivel) se a segunda
            # resolução de DNS feita pelo smtplib divergir da primeira — ver risco residual
            # documentado em app/core/rede_segura.py.
            return MOTIVO_DNS_FALHOU
        if isinstance(exc, smtplib.SMTPRecipientsRefused):
            return MOTIVO_DESTINATARIO_RECUSADO
        if isinstance(exc, (smtplib.SMTPSenderRefused, smtplib.SMTPDataError)):
            return MOTIVO_ENVIO_RECUSADO
        if isinstance(exc, smtplib.SMTPException):
            return MOTIVO_ERRO_SMTP
        if isinstance(exc, OSError):
            return MOTIVO_ERRO_DESCONHECIDO
        return None

    @staticmethod
    def _encerrar(cliente: smtplib.SMTP | None) -> None:
        if cliente is None:
            return
        try:
            cliente.quit()
        except Exception:
            try:
                cliente.close()
            except Exception:
                pass

    @staticmethod
    def _resultado(sucesso: bool, motivo: str) -> ResultadoTesteSmtp:
        return ResultadoTesteSmtp(sucesso=sucesso, motivo=motivo, mensagem=_MENSAGENS[motivo])

    @staticmethod
    def _resultado_envio(sucesso: bool, motivo: str) -> ResultadoEnvioSmtp:
        return ResultadoEnvioSmtp(sucesso=sucesso, motivo=motivo, mensagem=_MENSAGENS[motivo])
