"""Fase 3 — Administração da Plataforma: definir Gestor escolhendo um Usuário EXISTENTE da própria empresa.

`GET /plataforma/empresas/{id}/candidatos-gestor` e `POST /plataforma/empresas/{id}/usuarios/{uid}/promover-gestor`.
O que a suíte prova: só candidatos elegíveis da PRÓPRIA empresa; promoção preserva id, credencial, exceções de permissão e
histórico (sem gerar senha); cross-tenant nunca promove; autoridade é da PLATAFORMA (Gestor tenant continua sem criar/promover
Gestor); o fluxo de "novo Gestor" da Fase 1B segue igual; auditoria registrada sem segredo.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.models.usuario_permissao import UsuarioPermissao
from tests.fixtures.usuarios import SENHA_CONHECIDA, _criar_usuario_com_credencial
from tests.test_plataforma import (  # noqa: F401  (fixtures reutilizadas)
    PLAT,
    _criar_empresa,
    _tenant_client,
    administrador,
    client_plataforma,
    usuario_plataforma,
)


def _usuario(db: Session, empresa_id: str, nome: str, *, perfil: str = "operador", status: str = "ativo", acesso: bool = True,
             sistema: bool = False) -> Usuario:
    agora = datetime.now(timezone.utc)
    usuario = Usuario(
        id=str(uuid.uuid4()), empresa_id=empresa_id, codigo_interno=f"U-{uuid.uuid4().hex[:8]}".upper(), nome=nome,
        email=f"{nome.lower().replace(' ', '.')}.{uuid.uuid4().hex[:6]}@alvo.test", perfil_base=perfil, acesso_sistema=acesso,
        status=status, is_system_account=sistema, created_at=agora, updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _com_credencial(db: Session, usuario: Usuario) -> UsuarioCredencial:
    agora = datetime.now(timezone.utc)
    credencial = UsuarioCredencial(
        id=str(uuid.uuid4()), usuario_id=usuario.id, senha_hash=hash_password(SENHA_CONHECIDA), senha_definida_em=agora,
        senha_deve_ser_alterada=False, created_at=agora, updated_at=agora,
    )
    db.add(credencial)
    db.flush()
    return credencial


@pytest.fixture()
def alvo(client_plataforma: TestClient) -> dict:
    return _criar_empresa(client_plataforma)


def _promover(client: TestClient, empresa_id: str, usuario_id: str):
    return client.post(f"{PLAT}/empresas/{empresa_id}/usuarios/{usuario_id}/promover-gestor")


# --------------------------------------------------------------------------------------
# Candidatos
# --------------------------------------------------------------------------------------


def test_candidatos_sao_so_usuarios_ativos_com_acesso_da_propria_empresa(
    client_plataforma: TestClient, db_session: Session, alvo: dict, empresa: Empresa
) -> None:
    ok = _usuario(db_session, alvo["id"], "Candidato Valido")
    _usuario(db_session, alvo["id"], "Inativo", status="inativo")
    _usuario(db_session, alvo["id"], "Bloqueado", status="bloqueado")
    _usuario(db_session, alvo["id"], "Arquivado", status="arquivado")
    _usuario(db_session, alvo["id"], "Sem Acesso", acesso=False)
    _usuario(db_session, alvo["id"], "Admin Legado", perfil="admin")
    _usuario(db_session, alvo["id"], "Ja Gestor", perfil="gestor")
    _usuario(db_session, alvo["id"], "Conta Sistema", perfil="admin", sistema=True)
    _usuario(db_session, empresa.id, "De Outra Empresa")  # `empresa` é outra empresa

    resposta = client_plataforma.get(f"{PLAT}/empresas/{alvo['id']}/candidatos-gestor")
    assert resposta.status_code == 200
    candidatos = resposta.json()
    assert [c["id"] for c in candidatos] == [ok.id]
    assert set(candidatos[0]) == {"id", "nome", "email", "perfilBase", "status", "acessoSistema", "createdAt"}
    assert candidatos[0]["perfilBase"] == "operador"  # a UI traduz para "Usuário"; a API segue o nome técnico


def test_candidatos_de_empresa_inexistente_e_404_e_sem_autoridade_e_negado(
    client_plataforma: TestClient, client_gestor: TestClient, alvo: dict
) -> None:
    assert client_plataforma.get(f"{PLAT}/empresas/{uuid.uuid4()}/candidatos-gestor").status_code == 404
    assert client_gestor.get(f"{PLAT}/empresas/{alvo['id']}/candidatos-gestor").status_code in (401, 403)
    assert TestClient(client_gestor.app).get(f"{PLAT}/empresas/{alvo['id']}/candidatos-gestor").status_code == 401


# --------------------------------------------------------------------------------------
# Promoção
# --------------------------------------------------------------------------------------


def test_promover_preserva_id_credencial_excecoes_e_historico_sem_gerar_senha(
    client_plataforma: TestClient, db_session: Session, alvo: dict, usuario_plataforma: Usuario
) -> None:
    pessoa = _usuario(db_session, alvo["id"], "Pessoa Promovida")
    credencial = _com_credencial(db_session, pessoa)
    agora = datetime.now(timezone.utc)
    db_session.add(UsuarioPermissao(
        id=str(uuid.uuid4()), empresa_id=alvo["id"], usuario_id=pessoa.id, permissao="usuarios.criar", efeito="negar",
        motivo="exceção individual", concedido_por_usuario_id=None, created_at=agora, updated_at=agora,
    ))
    db_session.flush()
    hash_antes, definida_antes, deve_antes, criado_antes = credencial.senha_hash, credencial.senha_definida_em, credencial.senha_deve_ser_alterada, pessoa.created_at

    resposta = _promover(client_plataforma, alvo["id"], pessoa.id)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["id"] == pessoa.id and corpo["perfilBase"] == "gestor"
    assert "senha" not in resposta.text.lower()  # nenhuma senha (temporária ou não) na resposta

    db_session.refresh(pessoa)
    db_session.refresh(credencial)
    assert pessoa.perfil_base == "gestor" and pessoa.empresa_id == alvo["id"] and pessoa.created_at == criado_antes
    assert pessoa.status == "ativo" and pessoa.acesso_sistema is True and pessoa.is_system_account is False
    # credencial intacta: mesma senha, nenhuma troca forçada, nenhuma credencial nova
    assert (credencial.senha_hash, credencial.senha_definida_em, credencial.senha_deve_ser_alterada) == (hash_antes, definida_antes, deve_antes)
    assert len(db_session.scalars(select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == pessoa.id)).all()) == 1
    # exceção individual de permissão preservada
    sobrou = db_session.scalars(select(UsuarioPermissao).where(UsuarioPermissao.usuario_id == pessoa.id)).all()
    assert [(p.permissao, p.efeito) for p in sobrou] == [("usuarios.criar", "negar")]
    # a empresa agora conta o Gestor
    assert client_plataforma.get(f"{PLAT}/empresas/{alvo['id']}").json()["gestoresAtivos"] == 1
    # e ele deixa de ser candidato
    assert pessoa.id not in [c["id"] for c in client_plataforma.get(f"{PLAT}/empresas/{alvo['id']}/candidatos-gestor").json()]


def test_promovido_entra_com_a_mesma_senha_e_passa_a_ter_autoridade_de_gestor(
    app, client_plataforma: TestClient, db_session: Session, alvo: dict
) -> None:
    pessoa = _usuario(db_session, alvo["id"], "Vai Virar Gestor")
    _com_credencial(db_session, pessoa)
    _promover(client_plataforma, alvo["id"], pessoa.id)

    login = TestClient(app).post(
        "/auth/login", json={"empresaCodigo": alvo["codigoInterno"], "email": pessoa.email, "senha": SENHA_CONHECIDA}
    )
    assert login.status_code == 200 and login.json().get("mustChangePassword") is False
    tenant = _tenant_client(app, pessoa)
    criado = tenant.post("/usuarios", json={"empresaId": alvo["id"], "nome": "Novo Usuario", "email": "novo@alvo.test", "perfilBase": "operador", "acessoSistema": True})
    assert criado.status_code == 201, criado.text  # autoridade de Gestor da própria empresa


def test_promocao_gera_eventos_de_auditoria_sem_segredo(
    client_plataforma: TestClient, db_session: Session, alvo: dict, usuario_plataforma: Usuario
) -> None:
    pessoa = _usuario(db_session, alvo["id"], "Auditada")
    _promover(client_plataforma, alvo["id"], pessoa.id)
    eventos = db_session.scalars(select(Evento).where(Evento.empresa_id == alvo["id"])).all()
    tipos = [e.tipo for e in eventos]
    assert "empresa.gestor_promovido" in tipos and "usuario.alterado" in tipos
    promovido = next(e for e in eventos if e.tipo == "empresa.gestor_promovido")
    assert promovido.usuario_id == usuario_plataforma.id  # o ator é o administrador da plataforma
    assert promovido.payload["usuarioId"] == pessoa.id and promovido.payload["perfilAnterior"] == "operador"
    alterado = next(e for e in eventos if e.tipo == "usuario.alterado" and e.entidade_id == pessoa.id)
    assert alterado.payload["camposAlterados"] == ["perfilBase"]
    assert not any(t in str([e.payload for e in eventos]).lower() for t in ("senha", "password", "hash", "token"))


def test_multiplos_gestores_e_novo_gestor_continuam_possiveis(client_plataforma: TestClient, db_session: Session, alvo: dict) -> None:
    a, b = _usuario(db_session, alvo["id"], "Primeiro"), _usuario(db_session, alvo["id"], "Segundo")
    assert _promover(client_plataforma, alvo["id"], a.id).status_code == 200
    assert _promover(client_plataforma, alvo["id"], b.id).status_code == 200
    novo = client_plataforma.post(f"{PLAT}/empresas/{alvo['id']}/gestores", json={"nome": "Terceiro Novo", "email": "terceiro@alvo.test"})
    assert novo.status_code == 201 and novo.json()["usuario"]["perfilBase"] == "gestor"
    assert novo.json()["deveAlterarSenha"] is True and len(novo.json()["senhaTemporaria"]) >= 12
    assert client_plataforma.get(f"{PLAT}/empresas/{alvo['id']}").json()["gestoresAtivos"] == 3


# --------------------------------------------------------------------------------------
# Recusas
# --------------------------------------------------------------------------------------


def test_cross_tenant_nunca_promove(client_plataforma: TestClient, db_session: Session, alvo: dict, empresa: Empresa) -> None:
    de_a = _usuario(db_session, empresa.id, "Pertence A")  # usuário da empresa A (fixture)
    outra = _criar_empresa(client_plataforma)  # empresa B
    resposta = _promover(client_plataforma, outra["id"], de_a.id)  # usuário de A com o empresa_id de B
    assert resposta.status_code == 404
    db_session.refresh(de_a)
    assert de_a.perfil_base == "operador"
    # nem pelo caminho certo da outra empresa sem ser da empresa dela
    assert _promover(client_plataforma, alvo["id"], de_a.id).status_code == 404
    db_session.refresh(de_a)
    assert de_a.perfil_base == "operador"
    assert not db_session.scalars(select(Evento).where(Evento.tipo == "empresa.gestor_promovido")).all()


@pytest.mark.parametrize(
    "kwargs, esperado",
    [
        ({"perfil": "gestor"}, 409),  # já é Gestor
        ({"perfil": "admin"}, 409),  # admin legado não é promovido por aqui
        ({"status": "inativo"}, 409),
        ({"status": "bloqueado"}, 409),
        ({"acesso": False}, 409),
        ({"status": "arquivado"}, 404),  # arquivado = não existe para a plataforma
        ({"perfil": "admin", "sistema": True}, 404),  # conta de sistema: nunca selecionável, nem revela que existe
    ],
)
def test_usuarios_inelegiveis_nao_sao_promovidos(
    client_plataforma: TestClient, db_session: Session, alvo: dict, kwargs: dict, esperado: int
) -> None:
    pessoa = _usuario(db_session, alvo["id"], "Inelegivel", **kwargs)
    antes = (pessoa.perfil_base, pessoa.status, pessoa.acesso_sistema)
    assert _promover(client_plataforma, alvo["id"], pessoa.id).status_code == esperado
    db_session.refresh(pessoa)
    assert (pessoa.perfil_base, pessoa.status, pessoa.acesso_sistema) == antes
    assert not db_session.scalars(select(Evento).where(Evento.tipo == "empresa.gestor_promovido")).all()


def test_ja_gestor_nao_duplica_efeitos(client_plataforma: TestClient, db_session: Session, alvo: dict) -> None:
    pessoa = _usuario(db_session, alvo["id"], "Gestor Existente", perfil="gestor")
    eventos_antes = len(db_session.scalars(select(Evento).where(Evento.empresa_id == alvo["id"])).all())
    assert _promover(client_plataforma, alvo["id"], pessoa.id).status_code == 409
    assert len(db_session.scalars(select(Evento).where(Evento.empresa_id == alvo["id"])).all()) == eventos_antes


def test_usuario_ou_empresa_inexistentes_sao_404(client_plataforma: TestClient, alvo: dict) -> None:
    assert _promover(client_plataforma, alvo["id"], str(uuid.uuid4())).status_code == 404
    assert _promover(client_plataforma, str(uuid.uuid4()), str(uuid.uuid4())).status_code == 404


# --------------------------------------------------------------------------------------
# Autoridade: só a PLATAFORMA promove / cria Gestor
# --------------------------------------------------------------------------------------


def test_gestor_tenant_nao_promove_nem_cria_gestor_e_o_token_tenant_nao_entra_na_plataforma(
    app, db_session: Session, alvo: dict, client_gestor: TestClient, client_admin: TestClient, empresa: Empresa
) -> None:
    alvo_tenant = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="alvo")
    # Fase 1A segue valendo: Gestor tenant administra Usuários, mas não promove nem cria Gestor
    assert client_gestor.patch(f"/usuarios/{alvo_tenant.id}", json={"perfilBase": "gestor"}).status_code == 403
    assert client_gestor.post(
        "/usuarios", json={"empresaId": empresa.id, "nome": "Novo Gestor", "email": "ng@x.test", "perfilBase": "gestor", "acessoSistema": True}
    ).status_code == 403
    # e nenhum token tenant (nem Gestor, nem admin legado) entra nas rotas novas de plataforma
    for cliente in (client_gestor, client_admin):
        assert _promover(cliente, empresa.id, alvo_tenant.id).status_code in (401, 403)
        assert cliente.get(f"{PLAT}/empresas/{empresa.id}/candidatos-gestor").status_code in (401, 403)
    db_session.refresh(alvo_tenant)
    assert alvo_tenant.perfil_base == "operador"


def test_novo_gestor_nunca_vira_admin_e_nao_vaza_senha_para_evento(
    client_plataforma: TestClient, db_session: Session, alvo: dict
) -> None:
    for extra in ({"perfilBase": "admin"}, {"perfilBase": "gestor"}):
        assert client_plataforma.post(
            f"{PLAT}/empresas/{alvo['id']}/gestores", json={"nome": "X", "email": "x@alvo.test", **extra}
        ).status_code == 422
    corpo = client_plataforma.post(f"{PLAT}/empresas/{alvo['id']}/gestores", json={"nome": "Sigiloso", "email": "sig@alvo.test"}).json()
    senha = corpo["senhaTemporaria"]
    eventos = db_session.scalars(select(Evento).where(Evento.empresa_id == alvo["id"])).all()
    assert senha not in str([e.payload for e in eventos])


# --------------------------------------------------------------------------------------
# Gestor É o usuário (perfil_base="gestor"); a empresa pode ter vários
# --------------------------------------------------------------------------------------


def test_varios_gestores_sao_listados_e_adicionar_outro_nao_altera_os_demais(
    client_plataforma: TestClient, db_session: Session, alvo: dict
) -> None:
    a, b, c = (_usuario(db_session, alvo["id"], nome) for nome in ("Gestor A", "Gestor B", "Gestor C"))
    comum = _usuario(db_session, alvo["id"], "Usuario Comum")
    _usuario(db_session, alvo["id"], "Admin Legado", perfil="admin")
    _usuario(db_session, alvo["id"], "Conta Sistema", perfil="admin", sistema=True)
    for pessoa in (a, b, c):
        assert _promover(client_plataforma, alvo["id"], pessoa.id).status_code == 200

    def gestores() -> dict[str, str]:
        usuarios = client_plataforma.get(f"{PLAT}/empresas/{alvo['id']}/usuarios", params={"limit": 200}).json()
        return {u["id"]: u["nome"] for u in usuarios if u["perfilBase"] == "gestor"}

    assert gestores() == {a.id: "Gestor A", b.id: "Gestor B", c.id: "Gestor C"}
    assert client_plataforma.get(f"{PLAT}/empresas/{alvo['id']}").json()["gestoresAtivos"] == 3

    # adicionar o Gestor D (promovendo outro usuário) não remove nem altera A/B/C
    assert _promover(client_plataforma, alvo["id"], comum.id).status_code == 200
    assert gestores() == {a.id: "Gestor A", b.id: "Gestor B", c.id: "Gestor C", comum.id: "Usuario Comum"}
    assert client_plataforma.get(f"{PLAT}/empresas/{alvo['id']}").json()["gestoresAtivos"] == 4
    # a lista nunca traz a conta de sistema, e o admin legado não é contado como Gestor
    nomes = [u["nome"] for u in client_plataforma.get(f"{PLAT}/empresas/{alvo['id']}/usuarios", params={"limit": 200}).json()]
    assert "Conta Sistema" not in nomes and "Admin Legado" in nomes


def test_gestor_e_o_proprio_usuario_sem_cadastro_paralelo_nem_limite_no_banco(db_session: Session) -> None:
    from sqlalchemy import inspect

    inspetor = inspect(db_session.get_bind())
    tabelas = set(inspetor.get_table_names())
    assert not {"gestores", "gestor", "empresa_gestor", "empresas_gestores"} & tabelas  # não existe entidade separada
    assert "gestor_id" not in {c["name"] for c in inspetor.get_columns("empresas")}
    # nenhum índice/constraint ÚNICO envolve perfil_base: nada limita a empresa a um Gestor
    unicos = [i for i in inspetor.get_indexes("usuarios") if i.get("unique")] + inspetor.get_unique_constraints("usuarios")
    assert not any("perfil_base" in (u.get("column_names") or []) for u in unicos)
