"""Configuração de disparo SMTP — singleton por Empresa (Fase 2G.7B1).

Cobre: GET read-only (nunca escreve), criação/atualização do singleton via PATCH,
concorrência do primeiro PATCH, cross-tenant, RBAC, semântica de três estados de
`smtpSenha`, nunca serializar o segredo, comportamento com chave de criptografia
ausente/inválida e com ciphertext corrompido. Testes de SMTP real (mockado) e de
SSRF ficam em test_configuracao_email_smtp.py — este arquivo não abre nenhuma conexão de
rede real.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config as config_module
from app.core.security import create_access_token
from app.models.configuracao_email import ConfiguracaoEmail
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.repositories.configuracao_email_repository import ConfiguracaoEmailRepository
from app.schemas.configuracao_email import ConfiguracaoEmailUpdate
from app.services.configuracao_email_crypto_service import ConfiguracaoEmailCryptoService
from app.services.configuracao_email_service import ConfiguracaoEmailService
from tests.fixtures.usuarios import _criar_usuario_com_credencial

# --------------------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _resetar_cache_settings():
    """`get_settings()` é `@lru_cache` — qualquer teste que mude
    `EMAIL_CONFIG_ENCRYPTION_KEY` via monkeypatch precisa limpar o cache pra Settings
    refletir o ambiente atual (mesmo padrão de test_config_segredos.py). Autouse pra
    garantir que nenhum teste deste arquivo deixe o cache sujo pro próximo, mesmo que o
    teste falhe no meio."""
    yield
    config_module.get_settings.cache_clear()


@pytest.fixture()
def chave_criptografia_valida(monkeypatch: pytest.MonkeyPatch) -> str:
    chave = Fernet.generate_key().decode()
    monkeypatch.setenv("EMAIL_CONFIG_ENCRYPTION_KEY", chave)
    config_module.get_settings.cache_clear()
    return chave


@pytest.fixture()
def sem_chave_criptografia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMAIL_CONFIG_ENCRYPTION_KEY", raising=False)
    config_module.get_settings.cache_clear()


def _cliente_para_outra_empresa(
    app, db_session: Session, outra_empresa: Empresa, perfil_base: str = "admin"
) -> TestClient:
    """Mesmo padrão de test_regra_expediente.py::_cliente_para_outra_empresa."""
    usuario = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base=perfil_base, email_prefixo=perfil_base
    )
    db_session.flush()
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=perfil_base)
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _registro(db_session: Session, empresa_id: str) -> ConfiguracaoEmail:
    return db_session.scalars(
        select(ConfiguracaoEmail).where(ConfiguracaoEmail.empresa_id == empresa_id)
    ).one()


# --------------------------------------------------------------------------------------
# A-B: GET read-only
# --------------------------------------------------------------------------------------


def test_a_get_sem_registro_devolve_default(client_admin: TestClient) -> None:
    resposta = client_admin.get("/configuracoes/email")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["id"] is None
    assert corpo["smtpHost"] is None
    assert corpo["smtpPort"] is None
    assert corpo["smtpUsuario"] is None
    assert corpo["smtpSenhaConfigurada"] is False
    assert corpo["remetenteEmail"] is None
    assert corpo["remetenteNome"] is None
    assert corpo["usarTls"] is True
    assert corpo["usarSsl"] is False
    assert corpo["ativo"] is False
    assert corpo["createdAt"] is None
    assert corpo["updatedAt"] is None


def test_b_get_nao_cria_linha_no_banco(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    client_admin.get("/configuracoes/email")
    client_admin.get("/configuracoes/email")  # duas vezes — nenhuma cria
    existe = db_session.scalars(
        select(ConfiguracaoEmail).where(ConfiguracaoEmail.empresa_id == empresa.id)
    ).first()
    assert existe is None


# --------------------------------------------------------------------------------------
# C-E: singleton via PATCH
# --------------------------------------------------------------------------------------


def test_c_primeiro_patch_cria_singleton(client_admin: TestClient) -> None:
    resposta = client_admin.patch("/configuracoes/email", json={"smtpHost": "smtp.exemplo.com"})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["id"] is not None
    assert corpo["smtpHost"] == "smtp.exemplo.com"
    assert corpo["createdAt"] is not None
    assert corpo["updatedAt"] is not None


def test_d_patch_posterior_atualiza_mesma_linha(client_admin: TestClient) -> None:
    primeiro = client_admin.patch("/configuracoes/email", json={"smtpHost": "a.exemplo.com"}).json()
    segundo = client_admin.patch("/configuracoes/email", json={"smtpHost": "b.exemplo.com"}).json()
    assert primeiro["id"] == segundo["id"]
    assert segundo["smtpHost"] == "b.exemplo.com"
    assert segundo["createdAt"] == primeiro["createdAt"]  # não recriou


def test_e_unique_empresa_id_sequencial_nao_duplica(db_session: Session, empresa: Empresa) -> None:
    service = ConfiguracaoEmailService()
    primeira = service.atualizar(
        db_session, ConfiguracaoEmailUpdate(smtpHost="a.exemplo.com"), empresa_id=empresa.id, actor_usuario_id=None
    )
    segunda = service.atualizar(
        db_session, ConfiguracaoEmailUpdate(smtpHost="b.exemplo.com"), empresa_id=empresa.id, actor_usuario_id=None
    )
    assert primeira.id == segunda.id


def test_e_concorrencia_real_no_primeiro_patch_nao_duplica(
    test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simula a corrida de verdade: a PRIMEIRA vez que `get_by_empresa` é chamado dentro de
    `atualizar` devolve `None` (como se de fato não existisse ainda) mas, como efeito
    colateral, outra "transação" (uma conexão de banco genuinamente separada, com commit
    real) insere a linha ANTES do `flush` desta — forçando `_criar_com_retry` a cair no
    ramo de `IntegrityError` de verdade, não só a idempotência sequencial de test_e acima.

    Deliberadamente NÃO usa a fixture `db_session`: ela mantém uma transação aberta (via
    SAVEPOINT) durante todo o teste, e `service.atualizar` chamaria `commit()` dentro dela —
    um `commit()` que só libera o savepoint, sem soltar o lock de linha na transação real
    até o teardown do fixture. Uma conexão separada tentando limpar/verificar essa mesma
    linha (como este teste precisa fazer) travaria esperando esse lock nunca solto durante
    a execução do teste — deadlock. Por isso: sessão própria, ligada à `test_engine`, com
    commit de verdade — mesma técnica-espírito de
    test_k_concorrencia_apenas_uma_transacao_fixa_resolucao em test_demanda_resolucao_sla.py,
    adaptada para usar a Session ORM (que `ConfiguracaoEmailService.atualizar` exige)."""
    empresa_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)
    conexao_setup = test_engine.connect()
    conexao_setup.execute(
        Empresa.__table__.insert().values(
            id=empresa_id,
            nome="Empresa Concorrencia ConfiguracaoEmail",
            documento=None,
            codigo_interno=f"CONCR-EMAIL-{uuid.uuid4().hex[:8]}".upper(),
            status="ativa",
            created_at=agora,
            updated_at=agora,
        )
    )
    conexao_setup.commit()
    conexao_setup.close()

    original_get_by_empresa = ConfiguracaoEmailRepository.get_by_empresa
    estado = {"corrida_simulada": False}

    def get_by_empresa_com_corrida(self, db, empresa_id_chamado):
        resultado = original_get_by_empresa(self, db, empresa_id_chamado)
        if resultado is None and not estado["corrida_simulada"]:
            estado["corrida_simulada"] = True
            conexao = test_engine.connect()
            momento = datetime.now(timezone.utc)
            conexao.execute(
                ConfiguracaoEmail.__table__.insert().values(
                    id=str(uuid.uuid4()),
                    empresa_id=empresa_id_chamado,
                    smtp_host="vencedora-da-corrida.exemplo.com",
                    usar_tls=True,
                    usar_ssl=False,
                    ativo=False,
                    created_at=momento,
                    updated_at=momento,
                )
            )
            conexao.commit()
            conexao.close()
        return resultado

    monkeypatch.setattr(ConfiguracaoEmailRepository, "get_by_empresa", get_by_empresa_com_corrida)

    sessao_propria = Session(bind=test_engine)
    try:
        service = ConfiguracaoEmailService()
        resultado = service.atualizar(
            sessao_propria,
            ConfiguracaoEmailUpdate(smtpHost="minha-tentativa.exemplo.com"),
            empresa_id=empresa_id,
            actor_usuario_id=None,
        )

        assert estado["corrida_simulada"] is True  # confirma que o cenário foi exercitado de verdade

        total = sessao_propria.execute(
            select(ConfiguracaoEmail.id, ConfiguracaoEmail.smtp_host).where(
                ConfiguracaoEmail.empresa_id == empresa_id
            )
        ).all()

        assert len(total) == 1  # nunca duplicou
        assert total[0].id == str(resultado.id)
        # A requisição perdedora não perde a intenção: seu valor venceu por último (é quem
        # aplicou o UPDATE por cima da linha que a "vencedora" só acabou de inserir).
        assert total[0].smtp_host == "minha-tentativa.exemplo.com"
    finally:
        sessao_propria.close()
        conexao_limpeza = test_engine.connect()
        conexao_limpeza.execute(
            ConfiguracaoEmail.__table__.delete().where(ConfiguracaoEmail.empresa_id == empresa_id)
        )
        conexao_limpeza.execute(Empresa.__table__.delete().where(Empresa.id == empresa_id))
        conexao_limpeza.commit()
        conexao_limpeza.close()


# --------------------------------------------------------------------------------------
# F: cross-tenant
# --------------------------------------------------------------------------------------


def test_f_outra_empresa_tem_configuracao_independente(
    app, client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    minha = client_admin.patch("/configuracoes/email", json={"smtpHost": "minha.exemplo.com"}).json()

    cliente_outra = _cliente_para_outra_empresa(app, db_session, outra_empresa)
    da_outra = cliente_outra.get("/configuracoes/email").json()

    assert da_outra["id"] is None  # nunca viu/criou a config da outra Empresa
    assert da_outra["smtpHost"] is None

    da_outra_apos_patch = cliente_outra.patch(
        "/configuracoes/email", json={"smtpHost": "outra.exemplo.com"}
    ).json()
    assert da_outra_apos_patch["id"] != minha["id"]

    minha_relida = client_admin.get("/configuracoes/email").json()
    assert minha_relida["smtpHost"] == "minha.exemplo.com"  # PATCH da outra não vazou


# --------------------------------------------------------------------------------------
# G: RBAC
# --------------------------------------------------------------------------------------


def test_g_admin_le_e_edita(client_admin: TestClient) -> None:
    assert client_admin.get("/configuracoes/email").status_code == 200
    assert client_admin.patch("/configuracoes/email", json={"ativo": True}).status_code == 200


def test_g_gestor_le_e_edita(client_gestor: TestClient) -> None:
    assert client_gestor.get("/configuracoes/email").status_code == 200
    assert client_gestor.patch("/configuracoes/email", json={"ativo": True}).status_code == 200


def test_g_operador_403_em_tudo(client_operador: TestClient) -> None:
    assert client_operador.get("/configuracoes/email").status_code == 403
    assert client_operador.patch("/configuracoes/email", json={"ativo": True}).status_code == 403
    assert client_operador.post("/configuracoes/email/testar").status_code == 403


# --------------------------------------------------------------------------------------
# H-N: segredo
# --------------------------------------------------------------------------------------


def test_h_senha_armazenada_nao_e_plaintext(
    client_admin: TestClient, db_session: Session, empresa: Empresa, chave_criptografia_valida: str
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpSenha": "senha-super-secreta-123"})
    registro = _registro(db_session, empresa.id)
    assert registro.smtp_senha_criptografada is not None
    assert registro.smtp_senha_criptografada != "senha-super-secreta-123"
    assert "senha-super-secreta-123" not in registro.smtp_senha_criptografada


def test_i_get_nunca_retorna_smtp_senha(
    client_admin: TestClient, chave_criptografia_valida: str
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpSenha": "segredo-abc"})
    corpo = client_admin.get("/configuracoes/email").json()
    assert "smtpSenha" not in corpo
    assert corpo["smtpSenhaConfigurada"] is True


def test_j_get_nunca_retorna_ciphertext(
    client_admin: TestClient, chave_criptografia_valida: str
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpSenha": "segredo-abc"})
    corpo = client_admin.get("/configuracoes/email").json()
    assert "smtpSenhaCriptografada" not in corpo


def test_k_patch_omitindo_smtp_senha_preserva_ciphertext(
    client_admin: TestClient, db_session: Session, empresa: Empresa, chave_criptografia_valida: str
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpSenha": "segredo-original"})
    ciphertext_antes = _registro(db_session, empresa.id).smtp_senha_criptografada

    resposta = client_admin.patch("/configuracoes/email", json={"smtpHost": "novo-host.exemplo.com"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["smtpSenhaConfigurada"] is True

    ciphertext_depois = _registro(db_session, empresa.id).smtp_senha_criptografada
    assert ciphertext_depois == ciphertext_antes


def test_l_patch_smtp_senha_null_remove_ciphertext(
    client_admin: TestClient, db_session: Session, empresa: Empresa, chave_criptografia_valida: str
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpSenha": "para-remover"})
    assert _registro(db_session, empresa.id).smtp_senha_criptografada is not None

    resposta = client_admin.patch("/configuracoes/email", json={"smtpSenha": None})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["smtpSenhaConfigurada"] is False
    assert _registro(db_session, empresa.id).smtp_senha_criptografada is None


def test_m_patch_nova_string_troca_ciphertext(
    client_admin: TestClient, db_session: Session, empresa: Empresa, chave_criptografia_valida: str
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpSenha": "primeira-senha"})
    ciphertext_1 = _registro(db_session, empresa.id).smtp_senha_criptografada

    client_admin.patch("/configuracoes/email", json={"smtpSenha": "segunda-senha"})
    ciphertext_2 = _registro(db_session, empresa.id).smtp_senha_criptografada

    assert ciphertext_1 != ciphertext_2
    assert ConfiguracaoEmailCryptoService(chave=chave_criptografia_valida).descriptografar(
        ciphertext_2
    ) == "segunda-senha"


def test_n_smtp_senha_vazia_e_422(client_admin: TestClient, chave_criptografia_valida: str) -> None:
    resposta = client_admin.patch("/configuracoes/email", json={"smtpSenha": ""})
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# O: write protection
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"id": str(uuid.uuid4()), "smtpHost": "x.exemplo.com"},
        {"empresaId": str(uuid.uuid4())},
        {"createdAt": "2020-01-01T00:00:00Z"},
        {"updatedAt": "2020-01-01T00:00:00Z"},
        {"smtpSenhaConfigurada": True},
        {"smtpSenhaCriptografada": "qualquer-coisa"},
    ],
)
def test_o_campos_protegidos_rejeitados_com_422(client_admin: TestClient, payload: dict) -> None:
    resposta = client_admin.patch("/configuracoes/email", json=payload)
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# P-U: chave de criptografia / ciphertext inválido
# --------------------------------------------------------------------------------------


def test_p_get_sem_chave_funciona_mesmo_com_senha_configurada(
    client_admin: TestClient, chave_criptografia_valida: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpSenha": "segredo-qualquer"})

    monkeypatch.delenv("EMAIL_CONFIG_ENCRYPTION_KEY", raising=False)
    config_module.get_settings.cache_clear()

    resposta = client_admin.get("/configuracoes/email")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["smtpSenhaConfigurada"] is True  # nunca tentou descriptografar


def test_p_patch_sem_alterar_senha_funciona_sem_chave(
    client_admin: TestClient, sem_chave_criptografia: None
) -> None:
    resposta = client_admin.patch("/configuracoes/email", json={"smtpHost": "sem-chave.exemplo.com"})
    assert resposta.status_code == 200, resposta.text


def test_q_definir_senha_sem_chave_falha_controlado(
    client_admin: TestClient, sem_chave_criptografia: None
) -> None:
    resposta = client_admin.patch("/configuracoes/email", json={"smtpSenha": "nova-senha"})
    assert resposta.status_code == 500, resposta.text
    assert "criptografia" in resposta.json()["detail"].lower()
    assert "nova-senha" not in resposta.text


def test_r_ciphertext_invalido_nao_quebra_get(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpHost": "a.exemplo.com"})
    registro = _registro(db_session, empresa.id)
    registro.smtp_senha_criptografada = "isto-nao-e-um-token-fernet-valido"
    db_session.flush()

    resposta = client_admin.get("/configuracoes/email")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["smtpSenhaConfigurada"] is True


def test_s_patch_nao_relacionado_preserva_ciphertext_invalido(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpHost": "a.exemplo.com"})
    registro = _registro(db_session, empresa.id)
    registro.smtp_senha_criptografada = "ciphertext-corrompido"
    db_session.flush()

    resposta = client_admin.patch("/configuracoes/email", json={"smtpHost": "b.exemplo.com"})
    assert resposta.status_code == 200, resposta.text

    assert _registro(db_session, empresa.id).smtp_senha_criptografada == "ciphertext-corrompido"


def test_t_patch_nova_senha_valida_substitui_ciphertext_invalido(
    client_admin: TestClient, db_session: Session, empresa: Empresa, chave_criptografia_valida: str
) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpHost": "a.exemplo.com"})
    registro = _registro(db_session, empresa.id)
    registro.smtp_senha_criptografada = "ciphertext-corrompido"
    db_session.flush()

    resposta = client_admin.patch("/configuracoes/email", json={"smtpSenha": "senha-nova-valida"})
    assert resposta.status_code == 200, resposta.text

    ciphertext_novo = _registro(db_session, empresa.id).smtp_senha_criptografada
    assert ciphertext_novo != "ciphertext-corrompido"
    assert ConfiguracaoEmailCryptoService(chave=chave_criptografia_valida).descriptografar(
        ciphertext_novo
    ) == "senha-nova-valida"


def test_u_testar_conexao_com_ciphertext_invalido_resultado_controlado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    client_admin.patch(
        "/configuracoes/email",
        json={"smtpHost": "smtp.exemplo.com", "smtpPort": 587, "smtpUsuario": "user@exemplo.com"},
    )
    registro = _registro(db_session, empresa.id)
    registro.smtp_senha_criptografada = "ciphertext-corrompido"
    db_session.flush()

    resposta = client_admin.post("/configuracoes/email/testar")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["sucesso"] is False
    assert "senha" not in corpo["motivo"]


# --------------------------------------------------------------------------------------
# TLS/SSL mutuamente exclusivos
# --------------------------------------------------------------------------------------


def test_tls_e_ssl_juntos_no_mesmo_payload_e_422(client_admin: TestClient) -> None:
    resposta = client_admin.patch(
        "/configuracoes/email", json={"usarTls": True, "usarSsl": True}
    )
    assert resposta.status_code == 422, resposta.text


def test_tls_e_ssl_conflitantes_em_patches_separados_e_422(client_admin: TestClient) -> None:
    client_admin.patch("/configuracoes/email", json={"usarTls": True, "usarSsl": False})
    resposta = client_admin.patch("/configuracoes/email", json={"usarSsl": True})
    assert resposta.status_code == 422, resposta.text


def test_usar_ssl_true_com_tls_false_explicito_funciona(client_admin: TestClient) -> None:
    resposta = client_admin.patch(
        "/configuracoes/email", json={"usarTls": False, "usarSsl": True}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["usarSsl"] is True
    assert resposta.json()["usarTls"] is False


# --------------------------------------------------------------------------------------
# Validações adicionais
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("porta", [0, -1, 65536, 100000])
def test_smtp_port_fora_do_intervalo_e_422(client_admin: TestClient, porta: int) -> None:
    resposta = client_admin.patch("/configuracoes/email", json={"smtpPort": porta})
    assert resposta.status_code == 422, resposta.text


def test_remetente_email_formato_invalido_e_422(client_admin: TestClient) -> None:
    resposta = client_admin.patch("/configuracoes/email", json={"remetenteEmail": "nao-e-um-email"})
    assert resposta.status_code == 422, resposta.text


def test_remetente_email_valido_e_aceito(client_admin: TestClient) -> None:
    resposta = client_admin.patch(
        "/configuracoes/email", json={"remetenteEmail": "disparo@exemplo.com.br"}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["remetenteEmail"] == "disparo@exemplo.com.br"


def test_smtp_host_string_vazia_normaliza_para_none(client_admin: TestClient) -> None:
    client_admin.patch("/configuracoes/email", json={"smtpHost": "a.exemplo.com"})
    resposta = client_admin.patch("/configuracoes/email", json={"smtpHost": ""})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["smtpHost"] is None


# --------------------------------------------------------------------------------------
# 36: Serialização — segredo nunca aparece em nenhuma resposta/evento
# --------------------------------------------------------------------------------------


def test_serializacao_segredo_nunca_aparece_em_nenhuma_resposta_ou_evento(
    client_admin: TestClient, db_session: Session, empresa: Empresa, chave_criptografia_valida: str
) -> None:
    marcador = "MARCADOR-UNICO-9f8e7d6c5b4a-NUNCA-DEVE-VAZAR"

    resposta_patch = client_admin.patch(
        "/configuracoes/email",
        json={"smtpHost": "smtp.exemplo.com", "smtpUsuario": "user@exemplo.com", "smtpSenha": marcador},
    )
    assert resposta_patch.status_code == 200, resposta_patch.text
    assert marcador not in resposta_patch.text

    resposta_get = client_admin.get("/configuracoes/email")
    assert marcador not in resposta_get.text

    resposta_testar = client_admin.post("/configuracoes/email/testar")
    assert marcador not in resposta_testar.text

    registro = _registro(db_session, empresa.id)
    ciphertext = registro.smtp_senha_criptografada
    assert ciphertext is not None
    assert marcador not in ciphertext
    assert ciphertext not in resposta_patch.text
    assert ciphertext not in resposta_get.text

    eventos = db_session.scalars(
        select(Evento).where(Evento.tipo == "configuracao_email.alterada")
    ).all()
    assert len(eventos) >= 1
    for evento in eventos:
        payload_serializado = json.dumps(evento.payload)
        assert marcador not in payload_serializado
        assert ciphertext not in payload_serializado
        assert "smtpUsuario" not in evento.payload  # preferência conservadora do kickoff, item 16
        assert "smtpSenha" not in evento.payload  # só senhaAlterada/senhaRemovida (booleanos), nunca o campo em si
