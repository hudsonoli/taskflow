"""Fase 10B.1 — primeiro acesso por SENHA TEMPORÁRIA (sem convite, sem SMTP) e troca obrigatória imposta pelo SERVIDOR.

Fluxo: a Gestão cria Empresa + Gestor (senha temporária gerada no backend, só o hash persiste, exibida UMA vez) → o Gestor entra em /e/<slug>/login com ela → o servidor
bloqueia toda a aplicação (403 SENHA_TROCA_OBRIGATORIA) até a troca em /auth/definir-senha-inicial (SÓ nova senha + confirmação, sem senha atual) → a temporária morre e a
nova vale. Regeneração (só Administrador da Plataforma) enquanto o primeiro acesso está pendente. Provas de segurança: a senha nunca aparece em banco, evento, log ou GET.
"""

from __future__ import annotations

import json
import logging
import re
import uuid

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user, get_current_user_password_ready, get_current_user_password_ready_sem_expediente
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from tests.test_plataforma import PLAT, _client, administrador, client_plataforma, usuario_plataforma  # noqa: F401  (fixtures)

ONBOARDING = f"{PLAT}/empresas/onboarding"
NOVA = "SenhaPessoalNova123!"
ROTAS_LIVRES_DO_GATE = {"/auth/me", "/auth/alterar-senha", "/auth/definir-senha-inicial"}


def _payload() -> dict:
    s = uuid.uuid4().hex[:8]
    return {
        "empresa": {"nome": f"Empresa PA {s}", "nomeFantasia": f"PA {s}", "codigoInterno": f"pa-{s}", "slug": f"pa-{s}"},
        "gestor": {"nome": "Gestora Primeiro Acesso", "email": f"gestora-{s}@pa.test"},
    }


def _criar(client_plataforma: TestClient) -> dict:
    resposta = client_plataforma.post(ONBOARDING, json=_payload())
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _login(app, corpo: dict, senha: str, db: Session):
    email = db.get(Usuario, corpo["gestor"]["id"]).email
    return _client(app, None).post("/auth/login", json={"empresaSlug": corpo["empresa"]["slug"], "email": email, "senha": senha})


def _tenant(app, token: str) -> TestClient:
    return _client(app, token)


@pytest.fixture()
def pendente(app, client_plataforma: TestClient, db_session: Session):
    """Empresa nova + Gestor com a temporária: devolve (corpo da criação, cliente tenant já autenticado com a temporária)."""
    corpo = _criar(client_plataforma)
    login = _login(app, corpo, corpo["senhaTemporaria"], db_session)
    assert login.status_code == 200, login.text
    return corpo, _tenant(app, login.json()["accessToken"])


# ======================================================================================
# onboarding: criação, senha temporária, atomicidade, sem SMTP/convite
# ======================================================================================


def test_onboarding_devolve_a_senha_temporaria_uma_vez_e_ela_autentica(app, client_plataforma: TestClient, db_session: Session) -> None:
    corpo = _criar(client_plataforma)
    assert set(corpo) == {"empresa", "gestor", "senhaTemporaria", "deveAlterarSenha", "urlAcesso"}
    senha = corpo["senhaTemporaria"]
    assert len(senha) == 14 and re.search(r"[A-Z]", senha) and re.search(r"[a-z]", senha) and re.search(r"\d", senha)
    assert not set(senha) & set("0O1lI")  # sem caracteres ambíguos
    assert corpo["deveAlterarSenha"] is True and corpo["gestor"]["primeiroAcessoPendente"] is True
    assert corpo["urlAcesso"].endswith(f"/e/{corpo['empresa']['slug']}/login") and "token" not in corpo["urlAcesso"]
    login = _login(app, corpo, senha, db_session)
    assert login.status_code == 200 and login.json()["mustChangePassword"] is True
    assert _login(app, corpo, senha + "x", db_session).status_code == 401  # temporária errada


def test_cada_onboarding_gera_uma_senha_diferente_e_nao_derivada_de_dados_da_empresa(client_plataforma: TestClient) -> None:
    corpos = [_criar(client_plataforma) for _ in range(8)]
    senhas = {c["senhaTemporaria"] for c in corpos}
    assert len(senhas) == 8
    for c in corpos:
        minuscula = c["senhaTemporaria"].lower()
        for dado in (c["empresa"]["slug"], c["empresa"]["codigoInterno"].lower(), c["gestor"]["nome"].lower(), c["gestor"]["email"].split("@")[0]):
            assert dado not in minuscula


def test_gestor_e_empresa_corretos_credencial_com_hash_e_troca_obrigatoria(client_plataforma: TestClient, db_session: Session) -> None:
    corpo = _criar(client_plataforma)
    usuario = db_session.get(Usuario, corpo["gestor"]["id"])
    assert usuario.empresa_id == corpo["empresa"]["id"] and usuario.perfil_base == "gestor" and usuario.acesso_sistema is True
    credencial = db_session.scalar(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == usuario.id))
    assert credencial.senha_deve_ser_alterada is True
    assert credencial.senha_hash != corpo["senhaTemporaria"] and corpo["senhaTemporaria"] not in credencial.senha_hash
    # sem nenhum resquício de convite/token de recuperação
    assert credencial.reset_senha_token_hash is None and credencial.reset_senha_expira_em is None and credencial.reset_senha_solicitado_em is None


def test_onboarding_nao_usa_smtp_nem_convite(client_plataforma: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_password_reset import EmailFalso
    from app.api.routes import plataforma as rotas

    falso = EmailFalso()
    monkeypatch.setattr(rotas.plataforma_service.auth_service, "configuracao_email_service", falso)
    corpo = _criar(client_plataforma)
    assert falso.tentativas == [] and falso.enviados == []  # nenhuma tentativa de envio (nem convite, nem senha)
    texto = json.dumps(corpo)
    for proibido in ("convite", "linkAcesso", "#token", "\"token", "expiraEm", "\"motivo\""):
        assert proibido not in texto
    assert not hasattr(rotas.plataforma_service.auth_service, "enviar_convite")
    assert not hasattr(rotas.plataforma_service.auth_service, "preparar_convite")
    caminhos = {r.path for r in rotas.router.routes if isinstance(r, APIRoute)}
    assert not any("convite" in c for c in caminhos)  # o endpoint de reenvio de convite deixou de existir
    assert f"{PLAT}/empresas/{{empresa_id}}/usuarios/{{usuario_id}}/senha-temporaria" in caminhos


def test_falha_no_meio_do_onboarding_desfaz_empresa_gestor_e_credencial(client_plataforma: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routes import plataforma as rotas
    from app.models.empresa import Empresa

    db_session.commit()
    antes = (db_session.scalar(text("select count(*) from empresas")), db_session.scalar(text("select count(*) from usuarios")), db_session.scalar(text("select count(*) from usuario_credenciais")))

    def quebrar(*a, **k):
        raise RuntimeError("falha simulada ao gravar a credencial")

    monkeypatch.setattr(rotas.plataforma_service.auth_service, "aplicar_senha_temporaria", quebrar)
    dados = _payload()
    with pytest.raises(RuntimeError):
        rotas.plataforma_service.criar_empresa_com_gestor(
            db_session, rotas.PlataformaEmpresaOnboardingCreate.model_validate(dados), ator=db_session.scalars(select(Usuario)).first()
        )
    depois = (db_session.scalar(text("select count(*) from empresas")), db_session.scalar(text("select count(*) from usuarios")), db_session.scalar(text("select count(*) from usuario_credenciais")))
    assert depois == antes  # tudo ou nada
    assert db_session.scalar(select(Empresa).where(Empresa.slug == dados["empresa"]["slug"])) is None


# ======================================================================================
# bloqueio SERVER-SIDE enquanto a troca inicial está pendente
# ======================================================================================


def _rotas_efetivas(app):
    """Rotas reais do app (path com prefixo, métodos, dependant já com as dependências dos routers). FastAPI 0.139: `app.routes` guarda `_IncludedRouter`, não `APIRoute`."""
    for rota in app.routes:
        if hasattr(rota, "effective_route_contexts"):
            yield from rota.effective_route_contexts()
        elif isinstance(rota, APIRoute):
            yield rota


def test_toda_rota_tenant_autenticada_passa_pelo_gate_da_troca_obrigatoria(app) -> None:
    """Prova ESTRUTURAL: qualquer rota que dependa do usuário tenant também depende de `get_current_user_password_ready` — exceto /auth/me, /auth/alterar-senha e a troca
    inicial. Uma rota nova sem o gate quebra aqui (o redirect do React nunca é a barreira)."""

    def chamadas(dependant):
        yield dependant.call
        for sub in dependant.dependencies:
            yield from chamadas(sub)

    sem_gate: list[str] = []
    total = 0
    for contexto in _rotas_efetivas(app):
        total += 1
        usadas = set(chamadas(contexto.dependant))
        # `..._sem_expediente` APLICA o mesmo gate da troca obrigatória (só dispensa o de expediente: polling `/expediente/estado` e a porta da plataforma).
        tem_gate = get_current_user_password_ready in usadas or get_current_user_password_ready_sem_expediente in usadas
        if get_current_user in usadas and not tem_gate and contexto.path not in ROTAS_LIVRES_DO_GATE:
            sem_gate.append(f"{sorted(contexto.methods)[0]} {contexto.path}")
    # Guarda contra teste vazio: no FastAPI >= 0.139 os routers incluídos aparecem como `_IncludedRouter` em `app.routes` (nenhum APIRoute direto).
    assert total > 100, f"apenas {total} rotas verificadas — a varredura das rotas efetivas quebrou"
    assert sem_gate == [], f"rotas autenticadas fora do gate da troca obrigatória: {sem_gate}"


@pytest.mark.parametrize("caminho", ["/demandas", "/usuarios", "/clientes", "/notificacoes/resumo", "/arquivos/resumo-lote", "/projetos/diretorio", "/workflow-modelos", "/configuracoes/personalizacao"])
def test_rotas_normais_ficam_bloqueadas_ate_a_troca(pendente, caminho: str) -> None:
    _, tenant = pendente
    resposta = tenant.get(caminho)
    assert resposta.status_code in (403, 404, 405) and not (resposta.status_code == 200), (caminho, resposta.status_code)
    if resposta.status_code == 403:
        assert resposta.json()["detail"]["code"] == "SENHA_TROCA_OBRIGATORIA"


def test_empresas_legado_tambem_exige_a_troca_obrigatoria(pendente) -> None:
    """/empresas usa `require_admin`/`require_admin_or_gestor` (que dependem do `get_current_user` cru): o gate vem do router. Leitura e escrita legadas bloqueiam com o código."""
    corpo, tenant = pendente
    empresa_id = corpo["empresa"]["id"]
    chamadas = [
        tenant.get("/empresas"),
        tenant.get(f"/empresas/{empresa_id}"),
        tenant.patch(f"/empresas/{empresa_id}", json={}),
        tenant.post("/empresas", json={}),
        tenant.post(f"/empresas/{empresa_id}/inativar"),
        tenant.post(f"/empresas/{empresa_id}/reativar"),
    ]
    for resposta in chamadas:
        assert resposta.status_code == 403, (resposta.request.method, resposta.request.url.path, resposta.status_code)
        assert resposta.json()["detail"]["code"] == "SENHA_TROCA_OBRIGATORIA", resposta.request.url.path


def test_usuarios_e_demandas_devolvem_o_codigo_de_troca_obrigatoria(pendente) -> None:
    _, tenant = pendente
    for caminho in ("/usuarios", "/demandas"):
        resposta = tenant.get(caminho)
        assert resposta.status_code == 403 and resposta.json()["detail"]["code"] == "SENHA_TROCA_OBRIGATORIA", caminho


def test_me_e_a_troca_inicial_continuam_acessiveis_para_sair_do_bloqueio(pendente) -> None:
    corpo, tenant = pendente
    me = tenant.get("/auth/me")
    assert me.status_code == 200 and me.json()["mustChangePassword"] is True and me.json()["empresaSlug"] == corpo["empresa"]["slug"]


# ======================================================================================
# troca inicial: só nova senha + confirmação
# ======================================================================================


def test_troca_inicial_sem_senha_atual_libera_a_aplicacao_e_mata_a_temporaria(app, pendente, db_session: Session) -> None:
    corpo, tenant = pendente
    temporaria = corpo["senhaTemporaria"]
    resposta = tenant.post("/auth/definir-senha-inicial", json={"novaSenha": NOVA, "confirmacaoSenha": NOVA})
    assert resposta.status_code == 204, resposta.text

    credencial = db_session.scalar(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == corpo["gestor"]["id"]))
    db_session.refresh(credencial)
    assert credencial.senha_deve_ser_alterada is False and credencial.senha_alterada_em is not None
    assert NOVA not in credencial.senha_hash
    # a MESMA sessão (token antigo) reflete o estado atual: gate liberado e /me atualizado (sem Redis, sem estado local)
    assert tenant.get("/auth/me").json()["mustChangePassword"] is False
    assert tenant.get("/notificacoes/resumo").status_code == 200  # a aplicação voltou a responder com a MESMA sessão
    # a temporária deixou de funcionar; a pessoal funciona (sem nova obrigação)
    assert _login(app, corpo, temporaria, db_session).status_code == 401
    novo = _login(app, corpo, NOVA, db_session)
    assert novo.status_code == 200 and novo.json()["mustChangePassword"] is False


def test_o_contrato_da_troca_inicial_e_estrito(pendente) -> None:
    _, tenant = pendente
    caminho = "/auth/definir-senha-inicial"
    assert tenant.post(caminho, json={"novaSenha": NOVA, "confirmacaoSenha": NOVA, "senhaAtual": "qualquer"}).status_code == 422  # campo extra rejeitado
    assert tenant.post(caminho, json={"novaSenha": NOVA}).status_code == 422
    assert tenant.post(caminho, json={"novaSenha": NOVA, "confirmacaoSenha": NOVA + "x"}).status_code == 422  # confirmação diferente
    assert tenant.post(caminho, json={"novaSenha": "curta1", "confirmacaoSenha": "curta1"}).status_code == 422  # política (mínimo 8)
    assert tenant.get("/auth/me").json()["mustChangePassword"] is True  # nada mudou nas recusas


def test_nao_aceita_reutilizar_a_senha_temporaria(pendente) -> None:
    corpo, tenant = pendente
    resposta = tenant.post("/auth/definir-senha-inicial", json={"novaSenha": corpo["senhaTemporaria"], "confirmacaoSenha": corpo["senhaTemporaria"]})
    assert resposta.status_code == 422 and "temporária" in resposta.json()["detail"]
    assert tenant.get("/auth/me").json()["mustChangePassword"] is True


def test_troca_inicial_exige_autenticacao_e_so_vale_enquanto_pendente(app, pendente, client_operador: TestClient) -> None:
    corpo, tenant = pendente
    assert _client(app, None).post("/auth/definir-senha-inicial", json={"novaSenha": NOVA, "confirmacaoSenha": NOVA}).status_code == 401
    # usuário SEM troca pendente (operador comum) não usa este caminho como "alterar senha" sem a atual
    assert client_operador.post("/auth/definir-senha-inicial", json={"novaSenha": NOVA, "confirmacaoSenha": NOVA}).status_code == 409
    assert tenant.post("/auth/definir-senha-inicial", json={"novaSenha": NOVA, "confirmacaoSenha": NOVA}).status_code == 204
    assert tenant.post("/auth/definir-senha-inicial", json={"novaSenha": NOVA + "2", "confirmacaoSenha": NOVA + "2"}).status_code == 409  # já concluída


def test_a_troca_inicial_registra_evento_sem_senha(pendente, db_session: Session) -> None:
    corpo, tenant = pendente
    assert tenant.post("/auth/definir-senha-inicial", json={"novaSenha": NOVA, "confirmacaoSenha": NOVA}).status_code == 204
    db_session.expire_all()
    eventos = db_session.scalars(select(Evento).where(Evento.empresa_id == corpo["empresa"]["id"])).all()
    assert any(e.tipo == "auth.senha_alterada" for e in eventos)
    for segredo in (NOVA, corpo["senhaTemporaria"]):
        assert segredo not in json.dumps([e.payload for e in eventos], default=str)


def test_usuarios_existentes_nao_sao_marcados_para_troca(client_gestor: TestClient, client_operador: TestClient) -> None:
    for cliente in (client_gestor, client_operador):
        assert cliente.get("/auth/me").json()["mustChangePassword"] is False


# ======================================================================================
# regeneração da senha temporária (primeiro acesso ainda pendente)
# ======================================================================================


def _regenerar(client: TestClient, corpo: dict):
    return client.post(f"{PLAT}/empresas/{corpo['empresa']['id']}/usuarios/{corpo['gestor']['id']}/senha-temporaria")


def test_administrador_gera_nova_temporaria_a_anterior_morre_e_a_troca_continua_obrigatoria(app, client_plataforma: TestClient, db_session: Session) -> None:
    corpo = _criar(client_plataforma)
    antiga = corpo["senhaTemporaria"]
    resposta = _regenerar(client_plataforma, corpo)
    assert resposta.status_code == 200, resposta.text
    nova = resposta.json()
    assert nova["senhaTemporaria"] != antiga and nova["deveAlterarSenha"] is True and nova["usuario"]["primeiroAcessoPendente"] is True
    assert set(nova) == {"usuario", "senhaTemporaria", "deveAlterarSenha"}
    assert _login(app, corpo, antiga, db_session).status_code == 401  # a anterior foi invalidada na hora
    login = _login(app, corpo, nova["senhaTemporaria"], db_session)
    assert login.status_code == 200 and login.json()["mustChangePassword"] is True  # continua obrigado a trocar
    assert _tenant(app, login.json()["accessToken"]).get("/notificacoes/resumo").status_code == 403


def test_regeneracao_e_auditada_com_o_ator_real_e_sem_senha(client_plataforma: TestClient, db_session: Session, usuario_plataforma: Usuario) -> None:  # noqa: F811
    corpo = _criar(client_plataforma)
    nova = _regenerar(client_plataforma, corpo).json()["senhaTemporaria"]
    db_session.expire_all()
    eventos = db_session.scalars(select(Evento).where(Evento.empresa_id == corpo["empresa"]["id"])).all()
    gerado = [e for e in eventos if e.tipo == "empresa.senha_temporaria_gerada"]
    assert len(gerado) == 1 and gerado[0].usuario_id == usuario_plataforma.id
    for segredo in (nova, corpo["senhaTemporaria"]):
        assert segredo not in json.dumps([e.payload for e in eventos], default=str)
        assert segredo not in json.dumps([e.metadata_ for e in eventos], default=str)


def test_so_o_administrador_da_plataforma_regenera(app, client_plataforma: TestClient, client_gestor: TestClient, client_operador: TestClient, pendente) -> None:
    corpo, tenant_pendente = pendente
    for cliente in (client_gestor, client_operador, tenant_pendente, _client(app, None)):
        assert _regenerar(cliente, corpo).status_code in (401, 403)


def test_regeneracao_cross_tenant_e_impossivel(client_plataforma: TestClient) -> None:
    a, b = _criar(client_plataforma), _criar(client_plataforma)
    cruzado = client_plataforma.post(f"{PLAT}/empresas/{b['empresa']['id']}/usuarios/{a['gestor']['id']}/senha-temporaria")
    assert cruzado.status_code == 404
    assert client_plataforma.post(f"{PLAT}/empresas/{uuid.uuid4()}/usuarios/{a['gestor']['id']}/senha-temporaria").status_code == 404


def test_usuario_que_ja_concluiu_o_primeiro_acesso_nao_recebe_nova_temporaria(app, client_plataforma: TestClient, db_session: Session) -> None:
    corpo = _criar(client_plataforma)
    login = _login(app, corpo, corpo["senhaTemporaria"], db_session)
    assert _tenant(app, login.json()["accessToken"]).post("/auth/definir-senha-inicial", json={"novaSenha": NOVA, "confirmacaoSenha": NOVA}).status_code == 204
    resposta = _regenerar(client_plataforma, corpo)
    assert resposta.status_code == 409 and "Esqueci minha senha" in resposta.json()["detail"]
    assert _login(app, corpo, NOVA, db_session).status_code == 200  # a senha pessoal segue intacta
    listados = client_plataforma.get(f"{PLAT}/empresas/{corpo['empresa']['id']}/usuarios").json()
    assert [u["primeiroAcessoPendente"] for u in listados if u["id"] == corpo["gestor"]["id"]] == [False]


def test_usuarios_comuns_nao_recebem_temporaria_pela_gestao(client_plataforma: TestClient, db_session: Session) -> None:
    corpo = _criar(client_plataforma)
    comum = _criar(client_plataforma)  # outra empresa — usuário SEM relação com esta
    assert client_plataforma.post(f"{PLAT}/empresas/{corpo['empresa']['id']}/usuarios/{comum['gestor']['id']}/senha-temporaria").status_code == 404


# ======================================================================================
# a senha nunca vaza: DB, eventos, logs, GETs posteriores
# ======================================================================================


def test_a_senha_temporaria_so_existe_na_resposta_inicial(client_plataforma: TestClient, db_session: Session, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    corpo = _criar(client_plataforma)
    senha = corpo["senhaTemporaria"]
    empresa_id, gestor_id = corpo["empresa"]["id"], corpo["gestor"]["id"]

    # banco: nenhuma coluna das tabelas envolvidas guarda a senha em claro
    for tabela, filtro in (("usuario_credenciais", f"usuario_id = '{gestor_id}'"), ("usuarios", f"id = '{gestor_id}'"), ("empresas", f"id = '{empresa_id}'")):
        linhas = db_session.execute(text(f"select * from {tabela} where {filtro}")).mappings().all()
        assert linhas and senha not in json.dumps([dict(l) for l in linhas], default=str), tabela
    # eventos (payload e metadata) e logs
    eventos = db_session.scalars(select(Evento).where(Evento.empresa_id == empresa_id)).all()
    assert eventos and senha not in json.dumps([[e.payload, e.metadata_] for e in eventos], default=str)
    assert senha not in caplog.text
    # GETs posteriores (empresa, lista, detalhe) e a listagem global
    for url in (f"{PLAT}/empresas/{empresa_id}", f"{PLAT}/empresas/{empresa_id}/usuarios", f"{PLAT}/empresas", f"{PLAT}/dashboard", f"{PLAT}/empresas/{empresa_id}/candidatos-gestor"):
        resposta = client_plataforma.get(url)
        assert resposta.status_code == 200 and senha not in resposta.text, url
    assert not resposta.url.__str__().count(senha)
