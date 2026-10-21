"""Hotfix P1 — onboarding de usuário criado na empresa + observabilidade da recuperação de senha.

Incidente: o usuário criado em `POST /usuarios` não ganhava credencial nem senha temporária, e "Esqueci minha senha" (que só atende quem JÁ tem credencial) ignorava a conta em
silêncio — os dois sintomas tinham a mesma causa. Desenho do produto: primeiro acesso por SENHA TEMPORÁRIA exibida uma vez (sem convite, sem e-mail no onboarding).

Nenhum e-mail real: o `ConfiguracaoEmailService` do `auth_service` é trocado por um falso. A senha temporária nunca pode aparecer em log, evento, GET posterior ou coluna do banco.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.routes import auth as auth_routes
from app.core.security import create_access_token, verify_password
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.services.configuracao_email_service import EmailEnvioFalhouError
from tests.fixtures.usuarios import _criar_usuario_com_credencial

MENSAGEM_PUBLICA = "Se existir uma conta habilitada para este e-mail, você receberá as instruções para redefinir a senha."


class EmailFalso:
    def __init__(self, falha: Exception | None = None) -> None:
        self.enviados: list[dict] = []
        self.falha = falha

    def enviar_email_transacional(self, db, **kwargs):
        if self.falha is not None:
            raise self.falha
        self.enviados.append(kwargs)


@pytest.fixture()
def email(monkeypatch: pytest.MonkeyPatch) -> EmailFalso:
    falso = EmailFalso()
    monkeypatch.setattr(auth_routes.auth_service, "configuracao_email_service", falso)
    monkeypatch.setattr(
        auth_routes.auth_service, "settings", replace(auth_routes.auth_service.settings, app_public_url="https://app.exemplo.com")
    )
    return falso


def _payload(empresa: Empresa, **extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    corpo = {"empresaId": empresa.id, "nome": f"Pessoa {sufixo}", "email": f"pessoa-{sufixo}@teste.taskfloww.local", "perfilBase": "operador"}
    corpo.update(extra)
    return corpo


def _sem_credencial(db: Session, empresa: Empresa, **campos) -> Usuario:
    """Usuário como o hotfix encontrou em produção: criado pela API antiga, sem linha em `usuario_credenciais`."""
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"sc-{sufixo}", nome=f"Sem credencial {sufixo}",
        email=f"sc-{sufixo}@teste.taskfloww.local", perfil_base="operador", acesso_sistema=True, status="ativo", created_at=agora, updated_at=agora,
    )
    for chave, valor in campos.items():
        setattr(usuario, chave, valor)
    db.add(usuario)
    db.flush()
    return usuario


def _credencial(db: Session, usuario_id: str) -> UsuarioCredencial | None:
    return db.scalars(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == usuario_id)).first()


def _login(client: TestClient, empresa: Empresa, endereco: str, senha: str):
    return client.post("/auth/login", json={"empresaCodigo": empresa.codigo_interno, "email": endereco, "senha": senha})


def _pedir(client: TestClient, empresa: Empresa, endereco: str):
    return client.post("/auth/password-reset/request", json={"empresaCodigo": empresa.codigo_interno, "email": endereco})


def _client_de(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    cliente.headers["Authorization"] = "Bearer " + create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    return cliente


# --------------------------------------------------------------------------------------
# Criação: credencial + senha temporária devolvida UMA vez
# --------------------------------------------------------------------------------------


def test_criar_usuario_emite_senha_temporaria_so_na_resposta_e_persiste_apenas_o_hash(
    client_gestor: TestClient, db_session: Session, empresa: Empresa, caplog: pytest.LogCaptureFixture
) -> None:
    corpo = _payload(empresa)
    with caplog.at_level(logging.DEBUG):
        resposta = client_gestor.post("/usuarios", json=corpo)
    assert resposta.status_code == 201, resposta.text
    dados = resposta.json()
    senha = dados["senhaTemporaria"]
    assert isinstance(senha, str) and len(senha) == 14 and dados["deveAlterarSenha"] is True
    assert any(c.isupper() for c in senha) and any(c.islower() for c in senha) and any(c.isdigit() for c in senha)

    credencial = _credencial(db_session, dados["id"])
    assert credencial is not None and credencial.senha_deve_ser_alterada is True
    assert credencial.senha_hash != senha and verify_password(senha, credencial.senha_hash)

    # A senha em claro não está em NENHUMA coluna da credencial, nem em log, nem em evento.
    valores = " ".join(str(v) for v in (credencial.senha_hash, credencial.reset_senha_token_hash, credencial.reset_senha_expira_em))
    assert senha not in valores
    assert senha not in caplog.text
    eventos = db_session.scalars(select(Evento).where(Evento.entidade_id == dados["id"])).all()
    assert {e.tipo for e in eventos} >= {"usuario.criado", "usuario.senha_temporaria_gerada"}
    assert all(senha not in str(e.payload) + str(e.metadata_) for e in eventos)

    # Nenhum endpoint posterior a devolve.
    for caminho in (f"/usuarios/{dados['id']}", f"/usuarios?empresaId={empresa.id}&limit=200"):
        assert senha not in client_gestor.get(caminho).text
    assert "senhaTemporaria" not in client_gestor.get(f"/usuarios/{dados['id']}").json()


def test_senha_temporaria_loga_e_obriga_a_troca_no_primeiro_acesso(
    client_gestor: TestClient, client: TestClient, empresa: Empresa
) -> None:
    dados = client_gestor.post("/usuarios", json=_payload(empresa)).json()
    entrada = _login(client, empresa, dados["email"], dados["senhaTemporaria"])
    assert entrada.status_code == 200, entrada.text
    assert entrada.json()["mustChangePassword"] is True
    assert _login(client, empresa, dados["email"], "SenhaErrada123!").status_code == 401


def test_usuario_sem_acesso_ao_sistema_nao_recebe_credencial(client_gestor: TestClient, db_session: Session, empresa: Empresa) -> None:
    resposta = client_gestor.post("/usuarios", json=_payload(empresa, acessoSistema=False))
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["senhaTemporaria"] is None and resposta.json()["deveAlterarSenha"] is False
    assert _credencial(db_session, resposta.json()["id"]) is None


def test_criacao_recusada_nao_devolve_senha(client_gestor: TestClient, empresa: Empresa, usuario_operador: Usuario) -> None:
    """E-mail já cadastrado: 409 sem `senhaTemporaria`. (O rollback do serviço descarta fixtures não commitadas, então a contagem de credenciais não é observável aqui.)"""
    duplicado = client_gestor.post("/usuarios", json=_payload(empresa, email=usuario_operador.email))
    assert duplicado.status_code == 409 and "senhaTemporaria" not in duplicado.text


def test_listagem_sinaliza_primeiro_acesso_pendente_sem_expor_segredo(
    client_gestor: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    novo = client_gestor.post("/usuarios", json=_payload(empresa)).json()
    legado = _sem_credencial(db_session, empresa)
    sem_acesso = _sem_credencial(db_session, empresa, acesso_sistema=False)
    lista = client_gestor.get("/usuarios", params={"empresaId": empresa.id, "limit": 200})
    assert lista.status_code == 200
    por_id = {u["id"]: u for u in lista.json()}
    assert por_id[novo["id"]]["primeiroAcessoPendente"] is True  # troca obrigatória ainda ligada
    assert por_id[legado.id]["primeiroAcessoPendente"] is True  # sem credencial (o caso do incidente)
    assert por_id[usuario_operador.id]["primeiroAcessoPendente"] is False  # já definiu a própria senha
    assert por_id[sem_acesso.id]["primeiroAcessoPendente"] is False  # sem acesso ao sistema: nada a entregar
    assert novo["senhaTemporaria"] not in lista.text


# --------------------------------------------------------------------------------------
# Regeneração (saída para quem já ficou sem credencial)
# --------------------------------------------------------------------------------------


def test_gerar_senha_para_usuario_sem_credencial_destrava_o_acesso(
    client_gestor: TestClient, client: TestClient, db_session: Session, empresa: Empresa, caplog: pytest.LogCaptureFixture
) -> None:
    alvo = _sem_credencial(db_session, empresa)
    with caplog.at_level(logging.DEBUG):
        resposta = client_gestor.post(f"/usuarios/{alvo.id}/senha-temporaria")
    assert resposta.status_code == 200, resposta.text
    senha = resposta.json()["senhaTemporaria"]
    assert resposta.json()["usuarioId"] == alvo.id and resposta.json()["deveAlterarSenha"] is True
    assert senha not in caplog.text
    assert _credencial(db_session, alvo.id).senha_deve_ser_alterada is True
    assert _login(client, empresa, alvo.email, senha).json()["mustChangePassword"] is True
    (evento,) = db_session.scalars(select(Evento).where(Evento.tipo == "usuario.senha_temporaria_gerada", Evento.entidade_id == alvo.id)).all()
    assert senha not in str(evento.payload) + str(evento.metadata_)


def test_gerar_de_novo_enquanto_pendente_invalida_a_senha_anterior(
    client_gestor: TestClient, client: TestClient, db_session: Session, empresa: Empresa
) -> None:
    alvo = _sem_credencial(db_session, empresa)
    primeira = client_gestor.post(f"/usuarios/{alvo.id}/senha-temporaria").json()["senhaTemporaria"]
    segunda = client_gestor.post(f"/usuarios/{alvo.id}/senha-temporaria").json()["senhaTemporaria"]
    assert primeira != segunda
    assert _login(client, empresa, alvo.email, primeira).status_code == 401
    assert _login(client, empresa, alvo.email, segunda).status_code == 200


def test_quem_ja_definiu_a_propria_senha_recebe_409_e_nada_muda(
    client_gestor: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    antes = _credencial(db_session, usuario_operador.id).senha_hash
    resposta = client_gestor.post(f"/usuarios/{usuario_operador.id}/senha-temporaria")
    assert resposta.status_code == 409 and "Esqueci minha senha" in resposta.json()["detail"]
    assert _credencial(db_session, usuario_operador.id).senha_hash == antes


@pytest.mark.parametrize("campos", [{"status": "inativo"}, {"status": "bloqueado"}, {"acesso_sistema": False}])
def test_usuario_inelegivel_recebe_409(client_gestor: TestClient, db_session: Session, empresa: Empresa, campos: dict) -> None:
    alvo = _sem_credencial(db_session, empresa, **campos)
    assert client_gestor.post(f"/usuarios/{alvo.id}/senha-temporaria").status_code == 409
    assert _credencial(db_session, alvo.id) is None


def test_conta_de_sistema_e_arquivado_sao_recusados(client_gestor: TestClient, db_session: Session, empresa: Empresa) -> None:
    sistema = _sem_credencial(db_session, empresa, is_system_account=True)
    arquivado = _sem_credencial(db_session, empresa, status="arquivado")
    assert client_gestor.post(f"/usuarios/{sistema.id}/senha-temporaria").status_code in (403, 404)  # a API trata a conta de sistema como inexistente
    assert client_gestor.post(f"/usuarios/{arquivado.id}/senha-temporaria").status_code == 409
    assert _credencial(db_session, sistema.id) is None and _credencial(db_session, arquivado.id) is None


def test_autorizacao_da_regeneracao(
    app, client_gestor: TestClient, client_operador: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_gestor: Usuario
) -> None:
    alvo = _sem_credencial(db_session, empresa)
    assert client_operador.post(f"/usuarios/{alvo.id}/senha-temporaria").status_code == 403  # sem usuarios.editar
    assert TestClient(app).post(f"/usuarios/{alvo.id}/senha-temporaria").status_code in (401, 403)  # sem sessão
    assert client_gestor.post(f"/usuarios/{usuario_gestor.id}/senha-temporaria").status_code == 403  # nunca sobre si mesmo
    outro_gestor = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="gestor", email_prefixo="gestor2")
    assert client_gestor.post(f"/usuarios/{outro_gestor.id}/senha-temporaria").status_code == 403  # Gestor não administra Gestor
    de_fora = _sem_credencial(db_session, outra_empresa)
    assert client_gestor.post(f"/usuarios/{de_fora.id}/senha-temporaria").status_code == 404  # outra empresa = "não existe"
    assert client_gestor.post(f"/usuarios/{uuid.uuid4()}/senha-temporaria").status_code == 404
    assert _credencial(db_session, alvo.id) is None and _credencial(db_session, de_fora.id) is None


# --------------------------------------------------------------------------------------
# Recuperação de senha: resposta neutra INTACTA, mas o operador enxerga o motivo
# --------------------------------------------------------------------------------------


def test_recuperacao_de_conta_sem_credencial_e_neutra_nao_envia_e_registra_o_motivo(
    client: TestClient, db_session: Session, empresa: Empresa, email: EmailFalso, caplog: pytest.LogCaptureFixture
) -> None:
    alvo = _sem_credencial(db_session, empresa)
    with caplog.at_level(logging.INFO):
        resposta = _pedir(client, empresa, alvo.email)
    assert (resposta.status_code, resposta.json()) == (200, {"message": MENSAGEM_PUBLICA})
    assert email.enviados == []
    assert _credencial(db_session, alvo.id) is None  # a recuperação continua sem criar credencial
    assert "event=password_reset.skipped reason=no_credential" in caplog.text
    assert f"usuario_id={alvo.id}" in caplog.text and f"empresa_id={empresa.id}" in caplog.text
    assert alvo.email not in caplog.text  # nunca o e-mail


def test_e_mail_inexistente_continua_neutro_e_sem_rastro_de_enderecos(
    client: TestClient, empresa: Empresa, email: EmailFalso, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        resposta = _pedir(client, empresa, "ninguem@teste.local")
    assert (resposta.status_code, resposta.json()) == (200, {"message": MENSAGEM_PUBLICA})
    assert email.enviados == [] and "ninguem@teste.local" not in caplog.text and "password_reset.skipped" not in caplog.text


def test_recuperacao_valida_envia_exatamente_um_e_registra_aceite_sem_segredos(
    client: TestClient, empresa: Empresa, usuario_operador: Usuario, email: EmailFalso, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        resposta = _pedir(client, empresa, usuario_operador.email)
    assert (resposta.status_code, resposta.json()) == (200, {"message": MENSAGEM_PUBLICA})
    assert len(email.enviados) == 1
    token = email.enviados[0]["texto"].split("#token=")[1].split()[0]
    assert "event=email.password_reset.accepted provider=smtp" in caplog.text
    assert token not in caplog.text and usuario_operador.email not in caplog.text and "redefinir-senha" not in caplog.text


def test_falha_no_envio_e_registrada_com_contexto_sanitizado_e_a_resposta_segue_neutra(
    client: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    falho = EmailFalso(falha=EmailEnvioFalhouError("timeout", empresa.id))
    monkeypatch.setattr(auth_routes.auth_service, "configuracao_email_service", falho)
    monkeypatch.setattr(
        auth_routes.auth_service, "settings", replace(auth_routes.auth_service.settings, app_public_url="https://app.exemplo.com")
    )
    with caplog.at_level(logging.DEBUG):
        resposta = _pedir(client, empresa, usuario_operador.email)
    assert (resposta.status_code, resposta.json()) == (200, {"message": MENSAGEM_PUBLICA})
    linha = next(r.getMessage() for r in caplog.records if "email.password_reset.failed" in r.getMessage())
    assert "provider=smtp" in linha and "motivo=timeout" in linha and "exception_type=EmailEnvioFalhouError" in linha
    assert f"empresa_id={empresa.id}" in linha and f"usuario_id={usuario_operador.id}" in linha
    assert usuario_operador.email not in caplog.text and "#token=" not in caplog.text
    assert "password_reset.accepted" not in caplog.text
    assert _credencial(db_session, usuario_operador.id).reset_senha_token_hash is None  # nenhum token "válido" sem e-mail


def test_destravado_pelo_admin_o_usuario_passa_a_ter_recuperacao_normal(
    client_gestor: TestClient, client: TestClient, db_session: Session, empresa: Empresa, email: EmailFalso
) -> None:
    """Fim do incidente: depois da senha temporária o usuário tem credencial e o "Esqueci minha senha" passa a enviar o e-mail."""
    alvo = _sem_credencial(db_session, empresa)
    _pedir(client, empresa, alvo.email)
    assert email.enviados == []
    client_gestor.post(f"/usuarios/{alvo.id}/senha-temporaria")
    _pedir(client, empresa, alvo.email)
    assert len(email.enviados) == 1
