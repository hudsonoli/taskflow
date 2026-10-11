"""Recuperação de senha self-service — `POST /auth/password-reset/request` e `/confirm`
(`AuthService.solicitar_redefinicao_senha` / `confirmar_redefinicao_senha`).

O e-mail NUNCA é enviado de verdade: o `ConfiguracaoEmailService` do `auth_service` é trocado por
`EmailFalso`, que registra o que receberia (de onde o teste extrai o token do link). O tempo é
congelado (`Relogio`) nos testes de expiração/cooldown para o limite ser exato, sem sleep.

O que a suíte precisa provar (revisão de segurança): o token em texto puro só existe no e-mail
(nunca no banco, no evento nem no log); resposta pública idêntica para qualquer pedido de formato
válido; uso único; expiração no instante exato; tenant; e que nenhum caminho cria credencial.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import re
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from app.api.routes import auth as auth_routes
from app.core.security import generate_password_reset_token, hash_password_reset_token, verify_password
from app.domain.event_types import EVENT_TYPES, DomainEventType
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.repositories.usuario_credencial_repository import UsuarioCredencialRepository
from app.services import auth_service as auth_service_module
from app.services.configuracao_email_service import EmailEnvioFalhouError, EmailNaoConfiguradoError
from tests.fixtures.usuarios import SENHA_CONHECIDA

MENSAGEM_PUBLICA = "Se existir uma conta habilitada para este e-mail, você receberá as instruções para redefinir a senha."
MENSAGEM_TOKEN_INVALIDO = "Este link é inválido ou expirou. Solicite uma nova redefinição de senha."
NOVA_SENHA = "OutraSenhaBoa456!"
URL_PUBLICA = "https://app.exemplo.com"


class EmailFalso:
    """Substitui `ConfiguracaoEmailService` no `AuthService`: registra o que seria enviado."""

    def __init__(self, falha: Exception | None = None) -> None:
        self.enviados: list[dict] = []
        self.tentativas: list[dict] = []  # TODAS as chamadas, inclusive as que falharam
        self.falha = falha

    def enviar_email_transacional(self, db, **kwargs):
        self.tentativas.append(kwargs)
        if self.falha is not None:
            raise self.falha
        self.enviados.append(kwargs)


class Relogio:
    """Congela `datetime.now()` do módulo do AuthService (só ele): o teste move o tempo à mão."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, inicio: datetime) -> None:
        self.agora = inicio
        relogio = self

        class Fixo(datetime):
            @classmethod
            def now(cls, tz=None):
                return relogio.agora if tz is None else relogio.agora.astimezone(tz)

        monkeypatch.setattr(auth_service_module, "datetime", Fixo)

    def avancar(self, **kwargs) -> None:
        self.agora = self.agora + timedelta(**kwargs)


@pytest.fixture()
def email(monkeypatch: pytest.MonkeyPatch) -> EmailFalso:
    falso = EmailFalso()
    monkeypatch.setattr(auth_routes.auth_service, "configuracao_email_service", falso)
    return falso


@pytest.fixture(autouse=True)
def _url_publica(monkeypatch: pytest.MonkeyPatch) -> None:
    configuracao = replace(auth_routes.auth_service.settings, app_public_url=URL_PUBLICA)
    monkeypatch.setattr(auth_routes.auth_service, "settings", configuracao)


def _pedir(client: TestClient, empresa: Empresa, endereco: str):
    return client.post("/auth/password-reset/request", json={"empresaCodigo": empresa.codigo_interno, "email": endereco})


def _confirmar(client: TestClient, empresa: Empresa, token: str, nova: str = NOVA_SENHA, confirmacao: str | None = None):
    return client.post(
        "/auth/password-reset/confirm",
        json={
            "empresaCodigo": empresa.codigo_interno,
            "token": token,
            "novaSenha": nova,
            "confirmacaoSenha": nova if confirmacao is None else confirmacao,
        },
    )


def _login(client: TestClient, empresa: Empresa, usuario: Usuario, senha: str):
    return client.post(
        "/auth/login", json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": senha}
    )


def _token_do_email(email: EmailFalso) -> str:
    achado = re.search(r"#token=([A-Za-z0-9_\-]+)", email.enviados[-1]["texto"])
    assert achado, "o e-mail deveria trazer o link com #token="
    return achado.group(1)


def _credencial(db: Session, usuario: Usuario) -> UsuarioCredencial:
    credencial = db.scalars(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == usuario.id)).one()
    db.refresh(credencial)
    return credencial


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------------------
# Request — conta elegível
# --------------------------------------------------------------------------------------


def test_conta_elegivel_recebe_o_e_mail_com_link_em_fragmento_e_resposta_generica(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    resposta = _pedir(client, empresa, usuario_operador.email)
    assert resposta.status_code == 200 and resposta.json() == {"message": MENSAGEM_PUBLICA}

    (enviado,) = email.enviados
    assert enviado["destinatario"] == usuario_operador.email and enviado["empresa_id"] == empresa.id
    assert enviado["assunto"] == "Redefinição de senha — TaskFlow"
    texto = enviado["texto"]
    token = _token_do_email(email)
    assert f"{URL_PUBLICA}/e/{empresa.slug}/redefinir-senha#token={token}" in texto  # fragmento, não query string
    assert "?token" not in texto and "&token" not in texto
    assert "30 minutos" in texto and "ignore este e-mail" in texto.lower()
    assert SENHA_CONHECIDA not in texto


def test_so_o_sha256_do_token_e_persistido(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    antes = _agora()
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    credencial = _credencial(db_session, usuario_operador)

    assert credencial.reset_senha_token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert len(credencial.reset_senha_token_hash) == 64 and credencial.reset_senha_token_hash != token
    assert timedelta(minutes=29, seconds=55) <= credencial.reset_senha_expira_em - antes <= timedelta(minutes=30, seconds=5)
    assert credencial.reset_senha_solicitado_em is not None

    # O texto puro não está em NENHUMA coluna de NENHUMA linha de credencial (nem no evento).
    linhas = db_session.execute(text("select row_to_json(c)::text from usuario_credenciais c")).scalars().all()
    assert linhas and not any(token in linha for linha in linhas)
    eventos = db_session.execute(text("select payload::text from eventos")).scalars().all()
    assert not any(token in e or credencial.reset_senha_token_hash in e for e in eventos)


def test_endereco_e_normalizado_como_no_login(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    _pedir(client, empresa, f"  {usuario_operador.email.upper()} ")
    assert len(email.enviados) == 1


def test_url_publica_vem_da_configuracao_nunca_do_host_ou_origin_da_requisicao(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    client.post(
        "/auth/password-reset/request",
        json={"empresaCodigo": empresa.codigo_interno, "email": usuario_operador.email},
        headers={"Host": "atacante.example", "Origin": "https://atacante.example", "Referer": "https://atacante.example/x", "X-Forwarded-Host": "atacante.example"},
    )
    texto = email.enviados[0]["texto"]
    assert "atacante" not in texto and URL_PUBLICA in texto


def test_url_publica_com_barra_final_nao_duplica_barras(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth_routes.auth_service, "settings", replace(auth_routes.auth_service.settings, app_public_url="https://app.exemplo.com//"))
    _pedir(client, empresa, usuario_operador.email)
    assert f"https://app.exemplo.com/e/{empresa.slug}/redefinir-senha#token=" in email.enviados[0]["texto"]


@pytest.mark.parametrize("url", [None, "", "   ", "ftp://app.exemplo.com", "app.exemplo.com", "https://app.exemplo.com\nBcc: x@y.com", "https://a b.com"])
def test_sem_url_publica_valida_nada_e_enviado_nem_persistido(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso, monkeypatch: pytest.MonkeyPatch, url
) -> None:
    monkeypatch.setattr(auth_routes.auth_service, "settings", replace(auth_routes.auth_service.settings, app_public_url=url))
    resposta = _pedir(client, empresa, usuario_operador.email)
    assert resposta.status_code == 200 and resposta.json() == {"message": MENSAGEM_PUBLICA}
    assert email.enviados == []
    credencial = _credencial(db_session, usuario_operador)
    assert credencial.reset_senha_token_hash is None and credencial.reset_senha_solicitado_em is None


# --------------------------------------------------------------------------------------
# Request — contas NÃO elegíveis (mesma resposta, nenhum e-mail, nenhum token)
# --------------------------------------------------------------------------------------


def _cenarios_inelegiveis(db: Session, empresa: Empresa, outra_empresa: Empresa, usuario: Usuario):
    """Devolve (rotulo, empresa_do_pedido, email_do_pedido) para cada motivo de inelegibilidade."""
    agora = _agora()

    def _criar(**campos) -> Usuario:
        sufixo = uuid.uuid4().hex[:8]
        novo = Usuario(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"x-{sufixo}", nome=f"Pessoa {sufixo}",
            email=f"x-{sufixo}@teste.local", perfil_base="operador", acesso_sistema=True, status="ativo",
            created_at=agora, updated_at=agora,
        )
        for chave, valor in campos.items():
            setattr(novo, chave, valor)
        db.add(novo)
        db.flush()
        return novo

    def _com_credencial(novo: Usuario) -> Usuario:
        from app.core.security import hash_password

        db.add(UsuarioCredencial(
            id=str(uuid.uuid4()), usuario_id=novo.id, senha_hash=hash_password(SENHA_CONHECIDA), senha_definida_em=agora,
            tentativas_falhas=0, senha_deve_ser_alterada=False, created_at=agora, updated_at=agora,
        ))
        db.flush()
        return novo

    return [
        ("email_inexistente", empresa, "ninguem@teste.local"),
        ("usuario_inativo", empresa, _com_credencial(_criar(status="inativo")).email),
        ("usuario_arquivado", empresa, _com_credencial(_criar(status="arquivado")).email),
        ("usuario_bloqueado", empresa, _com_credencial(_criar(status="bloqueado")).email),
        ("sem_acesso_ao_sistema", empresa, _com_credencial(_criar(acesso_sistema=False)).email),
        ("conta_de_sistema", empresa, _com_credencial(_criar(is_system_account=True)).email),
        ("sem_credencial_local", empresa, _criar().email),
        ("empresa_errada", outra_empresa, usuario.email),
    ]


def test_inelegiveis_recebem_a_mesma_resposta_sem_e_mail_e_sem_token(
    client: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    for rotulo, empresa_do_pedido, endereco in _cenarios_inelegiveis(db_session, empresa, outra_empresa, usuario_operador):
        resposta = _pedir(client, empresa_do_pedido, endereco)
        assert (resposta.status_code, resposta.json()) == (200, {"message": MENSAGEM_PUBLICA}), rotulo
    assert email.enviados == []
    assert db_session.scalar(select(UsuarioCredencial).where(UsuarioCredencial.reset_senha_token_hash.is_not(None))) is None


def test_empresa_inexistente_ou_inativa_recebe_a_mesma_resposta(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    inexistente = client.post("/auth/password-reset/request", json={"empresaCodigo": "NAO-EXISTE", "email": usuario_operador.email})
    empresa.status = "inativa"
    db_session.flush()
    inativa = _pedir(client, empresa, usuario_operador.email)
    assert (inexistente.status_code, inexistente.json()) == (inativa.status_code, inativa.json()) == (200, {"message": MENSAGEM_PUBLICA})
    assert email.enviados == []


def test_o_pedido_nunca_cria_credencial_para_quem_nao_tem_senha_local(
    client: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    cenarios = _cenarios_inelegiveis(db_session, empresa, outra_empresa, usuario_operador)
    sem_credencial = next(email_ for rotulo, _, email_ in cenarios if rotulo == "sem_credencial_local")
    antes = db_session.scalar(text("select count(*) from usuario_credenciais"))
    _pedir(client, empresa, sem_credencial)
    assert db_session.scalar(text("select count(*) from usuario_credenciais")) == antes
    assert email.enviados == []


@pytest.mark.parametrize("corpo", [{}, {"email": "a@b.com"}, {"empresaCodigo": "X"}, {"empresaCodigo": "X", "email": ""}])
def test_corpo_malformado_e_422_de_formato(client: TestClient, corpo: dict) -> None:
    assert client.post("/auth/password-reset/request", json=corpo).status_code == 422


# --------------------------------------------------------------------------------------
# Anti-enumeration — comparação explícita
# --------------------------------------------------------------------------------------


def test_resposta_publica_identica_em_todos_os_cenarios(
    client: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario,
    usuario_gestor: Usuario, email: EmailFalso, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _impressao(resposta):
        return (resposta.status_code, resposta.json(), resposta.headers.get("content-type"), resposta.headers.get("content-length"))

    existente = _impressao(_pedir(client, empresa, usuario_operador.email))
    em_cooldown = _impressao(_pedir(client, empresa, usuario_operador.email))
    assert len(email.enviados) == 1  # o cooldown realmente não enviou

    monkeypatch.setattr(auth_routes.auth_service, "configuracao_email_service", EmailFalso(falha=EmailEnvioFalhouError("timeout", empresa.id)))
    falha_de_envio = _impressao(_pedir(client, empresa, usuario_gestor.email))

    outras = [_impressao(_pedir(client, e, a)) for _, e, a in _cenarios_inelegiveis(db_session, empresa, outra_empresa, usuario_operador)]
    todas = [existente, em_cooldown, falha_de_envio, *outras]
    assert len(set(map(repr, todas))) == 1, todas


# --------------------------------------------------------------------------------------
# Cooldown
# --------------------------------------------------------------------------------------


def test_cooldown_de_60s_nao_gera_token_nem_envia_e_depois_libera(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso, monkeypatch: pytest.MonkeyPatch
) -> None:
    relogio = Relogio(monkeypatch, datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc))
    _pedir(client, empresa, usuario_operador.email)
    primeiro = _credencial(db_session, usuario_operador).reset_senha_token_hash

    relogio.avancar(seconds=59, microseconds=999999)
    resposta = _pedir(client, empresa, usuario_operador.email)
    assert resposta.json() == {"message": MENSAGEM_PUBLICA}
    assert len(email.enviados) == 1 and _credencial(db_session, usuario_operador).reset_senha_token_hash == primeiro

    relogio.avancar(microseconds=1)  # exatamente 60 s depois do pedido anterior
    _pedir(client, empresa, usuario_operador.email)
    assert len(email.enviados) == 2
    segundo = _credencial(db_session, usuario_operador).reset_senha_token_hash
    assert segundo != primeiro


def test_novo_pedido_invalida_o_token_anterior(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso, monkeypatch: pytest.MonkeyPatch
) -> None:
    relogio = Relogio(monkeypatch, datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc))
    _pedir(client, empresa, usuario_operador.email)
    antigo = _token_do_email(email)
    relogio.avancar(seconds=61)
    _pedir(client, empresa, usuario_operador.email)
    novo = _token_do_email(email)

    assert antigo != novo
    assert _confirmar(client, empresa, antigo).status_code == 400
    assert _confirmar(client, empresa, novo).status_code == 204


# --------------------------------------------------------------------------------------
# Falha de e-mail — transação coerente
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "falha",
    [EmailEnvioFalhouError("timeout", "x"), EmailNaoConfiguradoError("configuracao_ausente", "x"), RuntimeError("bug inesperado no sender")],
)
def test_falha_no_envio_apaga_o_token_preserva_o_cooldown_e_responde_igual(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, monkeypatch: pytest.MonkeyPatch, falha: Exception
) -> None:
    falso = EmailFalso(falha=falha)
    monkeypatch.setattr(auth_routes.auth_service, "configuracao_email_service", falso)
    resposta = _pedir(client, empresa, usuario_operador.email)
    assert (resposta.status_code, resposta.json()) == (200, {"message": MENSAGEM_PUBLICA})

    credencial = _credencial(db_session, usuario_operador)
    assert credencial.reset_senha_token_hash is None and credencial.reset_senha_expira_em is None  # nenhum token "válido" sem e-mail
    assert credencial.reset_senha_solicitado_em is not None  # o cooldown vale também para a tentativa que falhou

    # Novo pedido imediato cai no cooldown: nem tenta enviar de novo.
    falso.falha = None
    _pedir(client, empresa, usuario_operador.email)
    assert falso.enviados == []


def test_sender_real_sem_smtp_configurado_tambem_responde_igual_e_nao_deixa_token(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    """Sem o `email` falso: o `ConfiguracaoEmailService` REAL levanta `EmailNaoConfiguradoError`
    (a Empresa não tem SMTP) — estado de produção hoje."""
    resposta = _pedir(client, empresa, usuario_operador.email)
    assert (resposta.status_code, resposta.json()) == (200, {"message": MENSAGEM_PUBLICA})
    assert _credencial(db_session, usuario_operador).reset_senha_token_hash is None


def test_nem_token_nem_link_nem_corpo_aparecem_no_log(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_gestor: Usuario,
    email: EmailFalso, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        _pedir(client, empresa, usuario_operador.email)
        token = _token_do_email(email)
        _confirmar(client, empresa, token)
        falho = EmailFalso(falha=EmailEnvioFalhouError("timeout", empresa.id))
        monkeypatch.setattr(auth_routes.auth_service, "configuracao_email_service", falho)
        _pedir(client, empresa, usuario_gestor.email)
    token_que_falhou = re.search(r"#token=([A-Za-z0-9_\-]+)", falho.tentativas[-1]["texto"]).group(1)
    registro = caplog.text
    assert token not in registro and token_que_falhou not in registro  # nem o do sucesso, nem o da falha
    assert "redefinir-senha" not in registro and NOVA_SENHA not in registro and SENHA_CONHECIDA not in registro
    assert usuario_gestor.email not in registro and usuario_operador.email not in registro
    assert "motivo=timeout" in registro and f"empresa_id={empresa.id}" in registro  # só contexto seguro


# --------------------------------------------------------------------------------------
# Token
# --------------------------------------------------------------------------------------


def test_token_tem_pelo_menos_32_bytes_de_entropia_e_nao_repete() -> None:
    tokens = {generate_password_reset_token() for _ in range(500)}
    assert len(tokens) == 500
    for token in list(tokens)[:20]:
        bruto = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        assert len(bruto) >= 32
        assert re.fullmatch(r"[A-Za-z0-9_\-]+", token)  # seguro num fragmento de URL


def test_hash_do_token_e_sha256_hex_deterministico() -> None:
    assert hash_password_reset_token("abc") == hashlib.sha256(b"abc").hexdigest()
    assert len(hash_password_reset_token("qualquer")) == 64


def test_lookup_do_token_usa_for_update(db_session: Session) -> None:
    comandos: list[str] = []

    def _capturar(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _capturar)
    try:
        UsuarioCredencialRepository().get_by_reset_token_hash(db_session, "0" * 64)
    finally:
        event.remove(engine, "before_cursor_execute", _capturar)
    assert any("FOR UPDATE" in c.upper() for c in comandos)  # confirmações simultâneas se serializam


def test_expiracao_e_exata_30_minutos_e_no_limite_ja_e_invalido(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso, monkeypatch: pytest.MonkeyPatch
) -> None:
    relogio = Relogio(monkeypatch, datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc))
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    assert _credencial(db_session, usuario_operador).reset_senha_expira_em == datetime(2026, 10, 5, 12, 30, tzinfo=timezone.utc)

    relogio.avancar(minutes=30)  # exatamente a expiração: inválido
    assert _confirmar(client, empresa, token).status_code == 400
    assert _login(client, empresa, usuario_operador, SENHA_CONHECIDA).status_code == 200  # senha NÃO mudou


def test_um_instante_antes_da_expiracao_ainda_vale(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso, monkeypatch: pytest.MonkeyPatch
) -> None:
    relogio = Relogio(monkeypatch, datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc))
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    relogio.avancar(minutes=29, seconds=59, microseconds=999999)
    assert _confirmar(client, empresa, token).status_code == 204


def test_token_expirado_nao_troca_a_senha_e_responde_a_mensagem_neutra(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso, monkeypatch: pytest.MonkeyPatch
) -> None:
    relogio = Relogio(monkeypatch, datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc))
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    relogio.avancar(hours=3)
    resposta = _confirmar(client, empresa, token)
    assert resposta.status_code == 400 and resposta.json() == {"detail": MENSAGEM_TOKEN_INVALIDO}


# --------------------------------------------------------------------------------------
# Confirm
# --------------------------------------------------------------------------------------


def test_confirm_valido_troca_a_senha_limpa_o_reset_e_nao_autentica(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    hash_antigo = _credencial(db_session, usuario_operador).senha_hash

    resposta = _confirmar(client, empresa, token)
    assert resposta.status_code == 204 and resposta.content == b""  # sem corpo, sem accessToken
    assert "set-cookie" not in resposta.headers and "authorization" not in resposta.headers

    credencial = _credencial(db_session, usuario_operador)
    assert credencial.senha_hash != hash_antigo and verify_password(NOVA_SENHA, credencial.senha_hash)
    assert credencial.reset_senha_token_hash is None and credencial.reset_senha_expira_em is None
    assert credencial.reset_senha_solicitado_em is None and credencial.senha_alterada_em is not None

    assert _login(client, empresa, usuario_operador, SENHA_CONHECIDA).status_code == 401  # a antiga deixa de valer
    assert _login(client, empresa, usuario_operador, NOVA_SENHA).status_code == 200  # a nova funciona


def test_token_so_vale_uma_vez(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    assert _confirmar(client, empresa, token).status_code == 204
    segunda = _confirmar(client, empresa, token, nova="MaisUmaSenha789!")
    assert segunda.status_code == 400 and segunda.json() == {"detail": MENSAGEM_TOKEN_INVALIDO}
    assert _login(client, empresa, usuario_operador, NOVA_SENHA).status_code == 200  # a segunda tentativa não mudou nada


@pytest.mark.parametrize("token", ["token-que-nao-existe", "A" * 43, "   ", "x" * 512])
def test_token_inexistente_ou_vazio_e_a_mesma_resposta_neutra(client: TestClient, empresa: Empresa, usuario_operador: Usuario, token: str) -> None:
    resposta = _confirmar(client, empresa, token)
    assert resposta.status_code == 400 and resposta.json() == {"detail": MENSAGEM_TOKEN_INVALIDO}


def test_token_de_outra_empresa_e_recusado_e_nao_e_consumido(
    client: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    assert _confirmar(client, outra_empresa, token).status_code == 400
    assert _credencial(db_session, usuario_operador).reset_senha_token_hash is not None  # continua valendo na empresa certa
    assert _confirmar(client, empresa, token).status_code == 204


def test_usuario_que_ficou_inativo_depois_do_pedido_nao_redefine(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    usuario_operador.status = "inativo"
    db_session.flush()
    assert _confirmar(client, empresa, token).status_code == 400
    usuario_operador.status = "ativo"
    usuario_operador.acesso_sistema = False
    db_session.flush()
    assert _confirmar(client, empresa, token).status_code == 400


def test_senha_curta_confirmacao_divergente_e_senha_igual_a_atual_sao_422_sem_consumir_o_token(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)

    curta = _confirmar(client, empresa, token, nova="curta1")
    assert curta.status_code == 422 and "8 caracteres" in curta.json()["detail"]
    divergente = _confirmar(client, empresa, token, nova=NOVA_SENHA, confirmacao="Diferente123!")
    assert divergente.status_code == 422 and "Confirmação" in divergente.json()["detail"]
    igual = _confirmar(client, empresa, token, nova=SENHA_CONHECIDA)
    assert igual.status_code == 422 and "diferente da senha atual" in igual.json()["detail"]

    assert _credencial(db_session, usuario_operador).reset_senha_token_hash is not None  # token intacto
    assert _login(client, empresa, usuario_operador, SENHA_CONHECIDA).status_code == 200  # senha intacta
    assert _confirmar(client, empresa, token).status_code == 204  # e dá para tentar de novo


def test_token_invalido_com_senha_curta_responde_a_neutra_nao_a_politica(
    client: TestClient, empresa: Empresa, usuario_operador: Usuario
) -> None:
    """A política só é avaliada com token válido — senão a resposta viraria um oráculo."""
    resposta = _confirmar(client, empresa, "token-invalido", nova="curta")
    assert resposta.status_code == 400 and resposta.json() == {"detail": MENSAGEM_TOKEN_INVALIDO}


def test_confirm_zera_tentativas_bloqueio_e_senha_temporaria(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    credencial = _credencial(db_session, usuario_operador)
    credencial.tentativas_falhas = 5
    credencial.bloqueado_ate = _agora() + timedelta(minutes=10)
    credencial.senha_deve_ser_alterada = True
    db_session.flush()
    assert _login(client, empresa, usuario_operador, SENHA_CONHECIDA).status_code == 401  # bloqueado

    _pedir(client, empresa, usuario_operador.email)
    assert _confirmar(client, empresa, _token_do_email(email)).status_code == 204
    credencial = _credencial(db_session, usuario_operador)
    assert (credencial.tentativas_falhas, credencial.bloqueado_ate, credencial.senha_deve_ser_alterada) == (0, None, False)
    resposta = _login(client, empresa, usuario_operador, NOVA_SENHA)
    assert resposta.status_code == 200 and resposta.json()["mustChangePassword"] is False


def test_sucesso_registra_evento_sem_token_e_o_pedido_nao_registra_nada(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    assert DomainEventType.AUTH_PASSWORD_RESET_COMPLETED.value in EVENT_TYPES
    _pedir(client, empresa, usuario_operador.email)
    assert db_session.scalars(select(Evento).where(Evento.tipo.like("auth.password_reset%"))).all() == []  # pedido: nenhum evento

    token = _token_do_email(email)
    _confirmar(client, empresa, token)
    (evento,) = db_session.scalars(select(Evento).where(Evento.tipo == "auth.password_reset_completed")).all()
    assert evento.entidade_id == usuario_operador.id and evento.empresa_id == empresa.id
    assert evento.payload["resultado"] == "sucesso"
    texto = str(evento.payload) + str(evento.metadata_)
    assert token not in texto and hash_password_reset_token(token) not in texto and "email" not in evento.payload


# --------------------------------------------------------------------------------------
# Outros caminhos de senha invalidam o reset pendente
# --------------------------------------------------------------------------------------


def test_reset_administrativo_invalida_token_pendente(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    assert _credencial(db_session, usuario_operador).reset_senha_token_hash is not None

    auth_routes.auth_service.definir_senha_usuario(
        db_session, empresa_codigo=empresa.codigo_interno, email=usuario_operador.email, senha="SenhaDoAdmin789!"
    )
    credencial = _credencial(db_session, usuario_operador)
    assert credencial.reset_senha_token_hash is None and credencial.reset_senha_expira_em is None
    assert credencial.reset_senha_solicitado_em is None

    assert _confirmar(client, empresa, token).status_code == 400  # o link antigo não funciona mais
    assert _login(client, empresa, usuario_operador, "SenhaDoAdmin789!").status_code == 200


def test_troca_de_senha_logada_tambem_invalida_token_pendente(
    client: TestClient, client_operador: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso
) -> None:
    _pedir(client, empresa, usuario_operador.email)
    token = _token_do_email(email)
    resposta = client_operador.post(
        "/auth/alterar-senha",
        json={"senhaAtual": SENHA_CONHECIDA, "novaSenha": "TrocaLogada123!", "confirmacaoSenha": "TrocaLogada123!"},
    )
    assert resposta.status_code == 204
    assert _credencial(db_session, usuario_operador).reset_senha_token_hash is None
    assert _confirmar(client, empresa, token).status_code == 400


# --------------------------------------------------------------------------------------
# Superfície
# --------------------------------------------------------------------------------------


def test_rotas_sao_publicas_e_nao_criam_sessao(client: TestClient, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso) -> None:
    pedido = _pedir(client, empresa, usuario_operador.email)
    assert pedido.status_code == 200 and "set-cookie" not in pedido.headers
    assert _confirmar(client, empresa, _token_do_email(email)).status_code == 204
    caminhos = set(client.app.openapi()["paths"])
    assert {"/auth/password-reset/request", "/auth/password-reset/confirm"} <= caminhos
