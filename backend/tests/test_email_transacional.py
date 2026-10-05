"""Envio transacional por SMTP — `ConfiguracaoEmailService.enviar_email_transacional` e
`ConfiguracaoEmailSmtpService.enviar`, sobre a configuração SMTP JÁ existente (Fase 2G.7).

Nenhum teste abre socket: o smtplib é substituído por `FakeSmtp` via as factories injetáveis, e o
gate de rede segura é liberado (o caso de host bloqueado usa o gate REAL, com 127.0.0.1). A senha
SMTP de teste é um valor reconhecível (`SENHA_SMTP`), procurado em todo erro/repr/chamada que não
deveria carregá-la.
"""

from __future__ import annotations

import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email import message_from_bytes, policy

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.configuracao_email import ConfiguracaoEmail
from app.models.empresa import Empresa
from app.services import configuracao_email_smtp_service as smtp_module
from app.services.configuracao_email_crypto_service import ConfiguracaoEmailCryptoService
from app.services.configuracao_email_service import (
    ConfiguracaoEmailService,
    EmailConteudoInvalidoError,
    EmailEnvioFalhouError,
    EmailNaoConfiguradoError,
    EmailTransacionalError,
)
from app.services.configuracao_email_smtp_service import ConfiguracaoEmailSmtpService, ParametrosTesteSmtp

SENHA_SMTP = "s3nh4-smtp-MUITO-secreta"
CHAVE = Fernet.generate_key().decode()
TEXTO = "Olá!\nSegue o link de teste."


class FakeSmtp:
    """Simula `smtplib.SMTP`/`SMTP_SSL` e registra a sequência de chamadas."""

    def __init__(
        self,
        host: str = "",
        porta: int = 0,
        *,
        falha_starttls: Exception | None = None,
        falha_login: Exception | None = None,
        falha_envio: Exception | None = None,
    ) -> None:
        self.host, self.porta = host, porta
        self.chamadas: list[str] = []
        self.mensagens: list[tuple] = []
        self._falha_starttls, self._falha_login, self._falha_envio = falha_starttls, falha_login, falha_envio

    def ehlo(self):
        self.chamadas.append("ehlo")

    def starttls(self, context=None):
        self.chamadas.append("starttls")
        assert isinstance(context, ssl.SSLContext) and context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        if self._falha_starttls:
            raise self._falha_starttls

    def login(self, usuario, senha):
        self.chamadas.append("login")
        self.credenciais = (usuario, senha)
        if self._falha_login:
            raise self._falha_login

    def send_message(self, msg, from_addr=None, to_addrs=None):
        self.chamadas.append("send_message")
        if self._falha_envio:
            raise self._falha_envio
        self.mensagens.append((msg, from_addr, to_addrs))

    def quit(self):
        self.chamadas.append("quit")

    def close(self):
        self.chamadas.append("close")


class Fabrica:
    """Factory injetável: cria um FakeSmtp por conexão e guarda todos (host/porta/ssl)."""

    def __init__(self, *, ssl_implicito: bool = False, falha_conexao: Exception | None = None, **kwargs) -> None:
        self.clientes: list[FakeSmtp] = []
        self.ssl_implicito = ssl_implicito
        self._falha_conexao = falha_conexao
        self._kwargs = kwargs

    def __call__(self, host, porta, timeout=None, context=None):
        if self._falha_conexao:
            raise self._falha_conexao
        assert timeout is not None and timeout > 0  # nunca sem timeout
        if self.ssl_implicito:
            assert isinstance(context, ssl.SSLContext) and context.verify_mode == ssl.CERT_REQUIRED
        cliente = FakeSmtp(host, porta, **self._kwargs)
        self.clientes.append(cliente)
        return cliente


@pytest.fixture(autouse=True)
def _gate_de_rede_liberado(monkeypatch: pytest.MonkeyPatch) -> None:
    """O gate SSRF tem testes próprios (test_rede_segura.py); aqui só o caso de host bloqueado o reativa."""
    monkeypatch.setattr(smtp_module, "validar_host_smtp_resolvivel", lambda host: None)


def _crypto() -> ConfiguracaoEmailCryptoService:
    return ConfiguracaoEmailCryptoService(chave=CHAVE)


def _config(db: Session, empresa: Empresa, **overrides) -> ConfiguracaoEmail:
    agora = datetime.now(timezone.utc)
    base = dict(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        smtp_host="smtp.exemplo.com",
        smtp_port=587,
        smtp_usuario="usuario@exemplo.com",
        smtp_senha_criptografada=_crypto().criptografar(SENHA_SMTP),
        remetente_email="no-reply@exemplo.com",
        remetente_nome="Equipe TaskFloww",
        usar_tls=True,
        usar_ssl=False,
        ativo=True,
        created_at=agora,
        updated_at=agora,
    )
    base.update(overrides)
    config = ConfiguracaoEmail(**base)
    db.add(config)
    db.flush()
    return config


def _servico(fabrica: Fabrica, fabrica_ssl: Fabrica | None = None, crypto: ConfiguracaoEmailCryptoService | None = None):
    smtp = ConfiguracaoEmailSmtpService(smtp_factory=fabrica, smtp_ssl_factory=fabrica_ssl or Fabrica(ssl_implicito=True))
    return ConfiguracaoEmailService(crypto=crypto or _crypto(), smtp_service=smtp)


def _enviar(servico: ConfiguracaoEmailService, db: Session, empresa: Empresa, **kwargs):
    dados = dict(empresa_id=empresa.id, destinatario="pessoa@cliente.com", assunto="Redefinição de senha", texto=TEXTO)
    dados.update(kwargs)
    return servico.enviar_email_transacional(db, **dados)


def _sem_segredo(erro: BaseException) -> None:
    for texto in (str(erro), repr(erro), repr(erro.args)):
        assert SENHA_SMTP not in texto
        assert "smtp.exemplo.com" not in texto and "usuario@exemplo.com" not in texto


# --------------------------------------------------------------------------------------
# Sucesso
# --------------------------------------------------------------------------------------


def test_envia_com_remetente_da_configuracao_e_destinatario_assunto_e_texto(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa, usar_tls=False, smtp_usuario=None, smtp_senha_criptografada=None)
    fabrica = Fabrica()
    _enviar(_servico(fabrica), db_session, empresa)

    (cliente,) = fabrica.clientes
    (msg, from_addr, to_addrs), = cliente.mensagens
    assert cliente.chamadas == ["ehlo", "send_message", "quit"]  # sem TLS e sem AUTH: nem starttls nem login
    assert from_addr == "no-reply@exemplo.com" and to_addrs == ["pessoa@cliente.com"]  # envelope explícito
    assert (cliente.host, cliente.porta) == ("smtp.exemplo.com", 587)
    assert msg["From"].addresses[0].display_name == "Equipe TaskFloww"
    assert msg["From"].addresses[0].addr_spec == "no-reply@exemplo.com"
    assert msg["To"].addresses[0].addr_spec == "pessoa@cliente.com"
    assert msg["Subject"] == "Redefinição de senha"
    assert msg.get_content_type() == "text/plain"
    assert msg.get_content().strip() == TEXTO.replace("\n", "\n").strip()
    assert msg["Date"] and msg["Message-ID"].endswith("@exemplo.com>")


def test_html_opcional_mantem_o_texto_puro_como_fallback(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa, usar_tls=False, smtp_usuario=None, smtp_senha_criptografada=None)
    fabrica = Fabrica()
    _enviar(_servico(fabrica), db_session, empresa, html="<p>Olá! <a href='https://x.com/r'>Link</a></p>")

    (msg, _, _), = fabrica.clientes[0].mensagens
    assert msg.get_content_type() == "multipart/alternative"
    assert msg.get_body(("plain",)).get_content().strip() == TEXTO
    assert "<a href=" in msg.get_body(("html",)).get_content()
    # A mensagem serializada é MIME válida e relê com o mesmo conteúdo.
    relida = message_from_bytes(msg.as_bytes(), policy=policy.default)
    assert relida.get_body(("plain",)).get_content().strip() == TEXTO


def test_starttls_sequencia_correta_com_auth(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa)  # TLS + usuário/senha
    fabrica = Fabrica()
    _enviar(_servico(fabrica), db_session, empresa)

    (cliente,) = fabrica.clientes
    assert cliente.chamadas == ["ehlo", "starttls", "ehlo", "login", "send_message", "quit"]
    assert cliente.credenciais == ("usuario@exemplo.com", SENHA_SMTP)  # a senha decifrada chega ao login


def test_ssl_implicito_usa_a_factory_ssl_e_nao_faz_starttls(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa, usar_tls=False, usar_ssl=True, smtp_port=465)
    plano, implicito = Fabrica(), Fabrica(ssl_implicito=True)
    _enviar(_servico(plano, implicito), db_session, empresa)

    assert plano.clientes == []
    (cliente,) = implicito.clientes
    assert cliente.chamadas == ["ehlo", "login", "send_message", "quit"]
    assert cliente.porta == 465


def test_sem_tls_e_sem_ssl_continua_permitido_como_no_teste_de_conexao(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa, usar_tls=False, usar_ssl=False)
    fabrica = Fabrica()
    _enviar(_servico(fabrica), db_session, empresa)
    assert fabrica.clientes[0].chamadas == ["ehlo", "login", "send_message", "quit"]


def test_assunto_e_nome_do_remetente_com_acentos_sao_codificados(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa, remetente_nome="Equipe Atenção", usar_tls=False, smtp_usuario=None, smtp_senha_criptografada=None)
    fabrica = Fabrica()
    _enviar(_servico(fabrica), db_session, empresa, assunto="Redefinição — ação necessária")
    (msg, _, _), = fabrica.clientes[0].mensagens
    bruto = msg.as_bytes()
    assert bruto.split(b"\n\n", 1)[0].isascii()  # cabeçalhos só em ASCII (RFC 2047), nunca bytes crus
    relida = message_from_bytes(bruto, policy=policy.default)
    assert relida["Subject"] == "Redefinição — ação necessária"
    assert relida["From"].addresses[0].display_name == "Equipe Atenção"


def test_envio_so_le_o_banco_sem_escrita_nem_commit(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa)
    db_session.flush()
    comandos: list[str] = []

    def _capturar(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement.strip().split(None, 1)[0].upper())

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _capturar)
    try:
        _enviar(_servico(Fabrica()), db_session, empresa)
    finally:
        event.remove(engine, "before_cursor_execute", _capturar)
    assert comandos and set(comandos) == {"SELECT"}
    assert not db_session.new and not db_session.dirty and not db_session.deleted


# --------------------------------------------------------------------------------------
# Configuração ausente / inativa / incompleta / senha ilegível
# --------------------------------------------------------------------------------------


def test_sem_configuracao_levanta_erro_tipado_e_nao_conecta(db_session: Session, empresa: Empresa) -> None:
    fabrica = Fabrica()
    with pytest.raises(EmailNaoConfiguradoError) as erro:
        _enviar(_servico(fabrica), db_session, empresa)
    assert erro.value.motivo == "configuracao_ausente" and erro.value.empresa_id == empresa.id
    assert fabrica.clientes == []


def test_configuracao_inativa_nao_envia(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa, ativo=False)
    fabrica = Fabrica()
    with pytest.raises(EmailNaoConfiguradoError) as erro:
        _enviar(_servico(fabrica), db_session, empresa)
    assert erro.value.motivo == "configuracao_inativa"
    assert fabrica.clientes == []
    _sem_segredo(erro.value)


@pytest.mark.parametrize("campo,valor", [("remetente_email", None), ("remetente_email", "sem-arroba"), ("remetente_nome", "Eq\nBcc: x@y.com")])
def test_remetente_ausente_ou_invalido_nao_envia(db_session: Session, empresa: Empresa, campo: str, valor) -> None:
    _config(db_session, empresa, **{campo: valor})
    fabrica = Fabrica()
    with pytest.raises(EmailNaoConfiguradoError) as erro:
        _enviar(_servico(fabrica), db_session, empresa)
    assert erro.value.motivo == "remetente_invalido"
    assert fabrica.clientes == []


def test_configuracao_incompleta_sem_host(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa, smtp_host=None)
    fabrica = Fabrica()
    with pytest.raises(EmailNaoConfiguradoError) as erro:
        _enviar(_servico(fabrica), db_session, empresa)
    assert erro.value.motivo == "configuracao_incompleta"
    assert fabrica.clientes == []


def test_senha_impossivel_de_descriptografar_nao_vaza_nada(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa)
    fabrica = Fabrica()
    servico_com_outra_chave = _servico(fabrica, crypto=ConfiguracaoEmailCryptoService(chave=Fernet.generate_key().decode()))
    with pytest.raises(EmailNaoConfiguradoError) as erro:
        _enviar(servico_com_outra_chave, db_session, empresa)
    assert erro.value.motivo == "senha_smtp_ilegivel"
    assert erro.value.__cause__ is None and erro.value.__suppress_context__  # `from None`: sem cadeia
    assert fabrica.clientes == []
    _sem_segredo(erro.value)


# --------------------------------------------------------------------------------------
# Rede segura / transporte
# --------------------------------------------------------------------------------------


def test_host_bloqueado_pelo_gate_real_nao_conecta(db_session: Session, empresa: Empresa, monkeypatch: pytest.MonkeyPatch) -> None:
    """O MESMO gate do teste de conexão: 127.0.0.1 (loopback) é recusado antes de qualquer connect."""
    from app.core.rede_segura import validar_host_smtp_resolvivel

    monkeypatch.setattr(smtp_module, "validar_host_smtp_resolvivel", validar_host_smtp_resolvivel)
    _config(db_session, empresa, smtp_host="127.0.0.1")
    fabrica = Fabrica()
    with pytest.raises(EmailEnvioFalhouError) as erro:
        _enviar(_servico(fabrica), db_session, empresa)
    assert erro.value.motivo == "host_bloqueado"
    assert fabrica.clientes == []
    _sem_segredo(erro.value)


@pytest.mark.parametrize(
    "fabrica_kwargs,motivo",
    [
        (dict(falha_login=smtplib.SMTPAuthenticationError(535, b"Credenciais invalidas: s3nh4-smtp-MUITO-secreta")), "autenticacao_invalida"),
        (dict(falha_starttls=smtplib.SMTPNotSupportedError("STARTTLS extension not supported")), "tls_invalido"),
        (dict(falha_envio=smtplib.SMTPRecipientsRefused({"pessoa@cliente.com": (550, b"no such user")})), "destinatario_recusado"),
        (dict(falha_envio=smtplib.SMTPSenderRefused(553, b"sender rejected", "no-reply@exemplo.com")), "envio_recusado"),
        (dict(falha_envio=smtplib.SMTPDataError(554, b"message rejected")), "envio_recusado"),
        (dict(falha_envio=smtplib.SMTPServerDisconnected("conexao perdida")), "erro_smtp"),
        (dict(falha_conexao=TimeoutError()), "timeout"),
        (dict(falha_conexao=ConnectionRefusedError()), "conexao_recusada"),
        (dict(falha_conexao=ssl.SSLError("handshake")), "tls_invalido"),
    ],
)
def test_falhas_de_transporte_viram_categoria_sem_vazar_segredo(
    db_session: Session, empresa: Empresa, fabrica_kwargs: dict, motivo: str
) -> None:
    _config(db_session, empresa)
    fabrica = Fabrica(**fabrica_kwargs)
    with pytest.raises(EmailEnvioFalhouError) as erro:
        _enviar(_servico(fabrica), db_session, empresa)
    assert erro.value.motivo == motivo and erro.value.empresa_id == empresa.id
    _sem_segredo(erro.value)
    assert "pessoa@cliente.com" not in str(erro.value)  # nem o destinatário
    for cliente in fabrica.clientes:  # a conexão aberta é sempre encerrada
        assert cliente.chamadas[-1] in ("quit", "close")
        assert not cliente.mensagens


def test_excecao_de_programacao_nao_e_engolida(db_session: Session, empresa: Empresa) -> None:
    _config(db_session, empresa)
    with pytest.raises(KeyError):
        _enviar(_servico(Fabrica(falha_envio=KeyError("bug"))), db_session, empresa)


# --------------------------------------------------------------------------------------
# Tenant
# --------------------------------------------------------------------------------------


def test_empresa_sem_configuracao_nunca_usa_a_de_outra_empresa(db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    _config(db_session, empresa)  # só a empresa A configurou
    fabrica = Fabrica()
    with pytest.raises(EmailNaoConfiguradoError) as erro:
        _enviar(_servico(fabrica), db_session, outra_empresa)
    assert erro.value.motivo == "configuracao_ausente"
    assert fabrica.clientes == []


def test_cada_empresa_usa_o_proprio_host_remetente_e_credencial(db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    _config(db_session, empresa, smtp_host="smtp.a.com", remetente_email="a@a.com", remetente_nome="A", smtp_usuario="ua")
    _config(
        db_session, outra_empresa, smtp_host="smtp.b.com", remetente_email="b@b.com", remetente_nome="B", smtp_usuario="ub",
        smtp_senha_criptografada=_crypto().criptografar("senha-da-b"),
    )
    fabrica = Fabrica()
    servico = _servico(fabrica)
    _enviar(servico, db_session, empresa)
    _enviar(servico, db_session, outra_empresa)

    a, b = fabrica.clientes
    assert (a.host, a.credenciais, a.mensagens[0][1]) == ("smtp.a.com", ("ua", SENHA_SMTP), "a@a.com")
    assert (b.host, b.credenciais, b.mensagens[0][1]) == ("smtp.b.com", ("ub", "senha-da-b"), "b@b.com")


# --------------------------------------------------------------------------------------
# Conteúdo inválido / injeção de cabeçalho — recusado ANTES de qualquer I/O
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "destinatario",
    [
        "pessoa@cliente.com\nBcc: atacante@x.com",
        "pessoa@cliente.com\r\nBcc: atacante@x.com",
        "pessoa@cliente.com\n",  # `$` do regex aceitaria o "\n" final — recusado à parte
        "pessoa@cliente.com\r",
        "Bcc: a@x.com\npessoa@cliente.com",
        "sem-arroba",
        "dois@@cliente.com",
        "com espaco@cliente.com",
        "",
        "a@" + "b" * 260 + ".com",
    ],
)
def test_destinatario_invalido_ou_com_quebra_de_linha_falha_antes_de_enviar(db_session: Session, empresa: Empresa, destinatario: str) -> None:
    _config(db_session, empresa)
    fabrica = Fabrica()
    with pytest.raises(EmailConteudoInvalidoError):
        _enviar(_servico(fabrica), db_session, empresa, destinatario=destinatario)
    assert fabrica.clientes == []


@pytest.mark.parametrize("assunto", ["Oi\nBcc: atacante@x.com", "Oi\r\nX-Hack: 1", "Oi\r", "", "   ", "x" * 300])
def test_assunto_invalido_ou_com_quebra_de_linha_falha_antes_de_enviar(db_session: Session, empresa: Empresa, assunto: str) -> None:
    _config(db_session, empresa)
    fabrica = Fabrica()
    with pytest.raises(EmailConteudoInvalidoError):
        _enviar(_servico(fabrica), db_session, empresa, assunto=assunto)
    assert fabrica.clientes == []


@pytest.mark.parametrize("campo,valor", [("texto", ""), ("texto", "  \n "), ("html", "")])
def test_corpo_vazio_falha_antes_de_enviar(db_session: Session, empresa: Empresa, campo: str, valor: str) -> None:
    _config(db_session, empresa)
    fabrica = Fabrica()
    with pytest.raises(EmailConteudoInvalidoError):
        _enviar(_servico(fabrica), db_session, empresa, **{campo: valor})
    assert fabrica.clientes == []


def test_conteudo_invalido_nem_consulta_a_configuracao(db_session: Session, empresa: Empresa) -> None:
    """Conteúdo ruim é recusado antes de qualquer SELECT — nem sinaliza se a Empresa tem SMTP."""
    comandos: list[str] = []

    def _capturar(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _capturar)
    try:
        with pytest.raises(EmailConteudoInvalidoError):
            _enviar(_servico(Fabrica()), db_session, empresa, destinatario="a@b.com\nBcc: x@y.com")
    finally:
        event.remove(engine, "before_cursor_execute", _capturar)
    assert comandos == []


# --------------------------------------------------------------------------------------
# Segredos e superfície
# --------------------------------------------------------------------------------------


def test_repr_dos_parametros_smtp_nao_mostra_a_senha() -> None:
    parametros = ParametrosTesteSmtp(
        smtp_host="h", smtp_port=25, smtp_usuario="u", smtp_senha=SENHA_SMTP, usar_tls=False, usar_ssl=False
    )
    assert SENHA_SMTP not in repr(parametros) and SENHA_SMTP not in str(parametros)


def test_erros_tem_hierarquia_unica_para_o_consumidor_capturar() -> None:
    assert issubclass(EmailNaoConfiguradoError, EmailTransacionalError)
    assert issubclass(EmailEnvioFalhouError, EmailTransacionalError)


def test_nao_existe_endpoint_http_de_envio(app) -> None:
    """O envio é função interna: nenhuma rota pública de envio de e-mail."""
    caminhos = set(app.openapi()["paths"])
    assert not any("enviar" in caminho or "send" in caminho for caminho in caminhos)
    assert "/configuracoes/email/testar" in caminhos  # o teste de conexão continua sendo só teste
