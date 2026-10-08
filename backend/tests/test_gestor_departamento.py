"""Fase 5 — o Gestor continua Gestor ao trocar de departamento.

AUTORIDADE (perfil_base + permissões/overrides) é uma coisa; CONTEXTO OPERACIONAL (departamento atual) é outra. O backend
já lê o usuário do banco a cada requisição (nenhum claim de departamento/perfil vale no JWT), então a troca de departamento
nunca retira capacidade — estes testes TRAVAM isso, em TI → Criação, para Gestor e para o Usuário de controle, e provam
que o contexto (`/usuarios/me`, `departamentos_como_head`) acompanha o departamento ATUAL sem mover dados históricos.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.escopo import departamentos_como_head
from app.core.security import create_access_token
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_usuario_departamento import _departamento

# Capacidades administrativas-base que o Gestor tem por perfil (catálogo real: app/core/permissoes.py).
CAPACIDADES_GESTOR = {
    "usuarios.visualizar", "usuarios.criar", "usuarios.editar", "usuarios.suspender", "permissoes.gerenciar",
    "clientes.visualizar", "clientes.criar", "clientes.editar",
    "fornecedores.visualizar", "fornecedores.criar", "fornecedores.editar",
    "grupos_cliente.visualizar", "grupos_cliente.criar", "grupos_cliente.editar",
}


@pytest.fixture()
def ti(db_session: Session, empresa: Empresa) -> Departamento:
    return _departamento(db_session, empresa, "TI")


@pytest.fixture()
def criacao(db_session: Session, empresa: Empresa) -> Departamento:
    return _departamento(db_session, empresa, "Criação")


def _mover(client_admin: TestClient, usuario: Usuario, departamento: Departamento) -> None:
    resposta = client_admin.patch(f"/usuarios/{usuario.id}", json={"departamentoId": departamento.id})
    assert resposta.status_code == 200, resposta.text


def _me(cliente: TestClient) -> dict:
    resposta = cliente.get("/usuarios/me")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _acoes_administrativas(cliente: TestClient, empresa: Empresa, alvo: Usuario) -> dict[str, int]:
    """Uma chamada real por capacidade-base: cliente, fornecedor, grupo de clientes e edição/criação de usuários."""
    sufixo = uuid.uuid4().hex[:6]
    return {
        "grupo": cliente.post("/grupos-cliente", json={"nome": f"Grupo {sufixo}", "corIdentificacao": "blue"}).status_code,
        "cliente": cliente.post("/clientes", json={"nome": f"Cliente {sufixo}", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}).status_code,
        "fornecedor": cliente.post("/fornecedores", json={"nome": f"Forn {sufixo}", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}).status_code,
        "listar_usuarios": cliente.get("/usuarios", params={"empresaId": empresa.id}).status_code,
        "editar_usuario": cliente.patch(f"/usuarios/{alvo.id}", json={"nome": f"Nome {sufixo}"}).status_code,
        "criar_usuario": cliente.post(
            "/usuarios", json={"empresaId": empresa.id, "nome": f"Novo {sufixo}", "email": f"n{sufixo}@alvo.test", "perfilBase": "operador", "acessoSistema": True}
        ).status_code,
        "suspender_usuario": cliente.post(f"/usuarios/{alvo.id}/inativar", json={}).status_code,
    }


# --------------------------------------------------------------------------------------
# Gestor TI → Criação: a autoridade não muda; o contexto sim
# --------------------------------------------------------------------------------------


def test_gestor_troca_ti_por_criacao_sem_perder_nenhuma_capacidade(
    client_admin: TestClient, client_gestor: TestClient, db_session: Session, empresa: Empresa, usuario_gestor: Usuario, ti: Departamento, criacao: Departamento
) -> None:
    alvo = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="alvo")
    _mover(client_admin, usuario_gestor, ti)
    antes = _me(client_gestor)
    assert antes["perfilBase"] == "gestor" and antes["departamentoId"] == ti.id
    assert CAPACIDADES_GESTOR <= set(antes["permissoes"])
    assert set(_acoes_administrativas(client_gestor, empresa, alvo).values()) <= {200, 201}

    _mover(client_admin, usuario_gestor, criacao)  # SÓ o departamento muda — mesma sessão/token
    depois = _me(client_gestor)
    assert depois["perfilBase"] == "gestor" and depois["status"] == "ativo" and depois["acessoSistema"] is True
    assert depois["departamentoId"] == criacao.id  # contexto atual = Criação
    assert sorted(depois["permissoes"]) == sorted(antes["permissoes"])  # as MESMAS capacidades
    assert CAPACIDADES_GESTOR <= set(depois["permissoes"])
    outro = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="outro")
    resultado = _acoes_administrativas(client_gestor, empresa, outro)
    assert set(resultado.values()) <= {200, 201}, resultado  # clientes, fornecedores, grupos e usuários seguem permitidos


def test_historico_do_departamento_antigo_nao_e_movido(
    client_admin: TestClient, db_session: Session, empresa: Empresa, usuario_gestor: Usuario, ti: Departamento, criacao: Departamento
) -> None:
    colega = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="colega")
    _mover(client_admin, usuario_gestor, ti)
    _mover(client_admin, colega, ti)
    ti.responsavel_usuario_id = usuario_gestor.id  # dono formal do TI: vínculo histórico/cadastral
    db_session.flush()
    _mover(client_admin, usuario_gestor, criacao)
    db_session.refresh(ti)
    db_session.refresh(colega)
    assert colega.departamento_id == ti.id  # quem ficou no TI continua no TI
    assert ti.responsavel_usuario_id == usuario_gestor.id  # o cadastro do TI não foi reescrito
    assert ti.nome == "TI" and ti.status == "ativo"


def test_contexto_de_head_acompanha_o_departamento_atual(
    client_admin: TestClient, db_session: Session, usuario_gestor: Usuario, ti: Departamento, criacao: Departamento
) -> None:
    usuario_gestor.lider_departamento = True
    db_session.flush()
    _mover(client_admin, usuario_gestor, ti)
    db_session.refresh(usuario_gestor)
    assert departamentos_como_head(db_session, usuario_gestor) == [ti.id]
    _mover(client_admin, usuario_gestor, criacao)
    db_session.refresh(usuario_gestor)
    assert departamentos_como_head(db_session, usuario_gestor) == [criacao.id]  # "Meu Departamento" passa a ser Criação


def test_head_formal_do_antigo_departamento_continua_head_dele_e_do_atual(
    client_admin: TestClient, db_session: Session, usuario_gestor: Usuario, ti: Departamento, criacao: Departamento
) -> None:
    """Dono formal do TI + líder do departamento atual: AMBOS são Head. O frontend escolhe o ATUAL como "Meu Departamento"."""
    usuario_gestor.lider_departamento = True
    ti.responsavel_usuario_id = usuario_gestor.id
    db_session.flush()
    _mover(client_admin, usuario_gestor, criacao)
    db_session.refresh(usuario_gestor)
    heads = departamentos_como_head(db_session, usuario_gestor)
    assert heads[0] == ti.id and criacao.id in heads and set(heads) == {ti.id, criacao.id}


# --------------------------------------------------------------------------------------
# Sessão ativa: o backend nunca "congela" perfil nem departamento no token
# --------------------------------------------------------------------------------------


def test_promocao_e_troca_de_departamento_valem_na_sessao_ativa_sem_novo_login(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa, ti: Departamento, criacao: Departamento
) -> None:
    pessoa = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="promovida")
    sessao = TestClient(app)
    sessao.headers["Authorization"] = "Bearer " + create_access_token(sub=pessoa.id, empresa_id=empresa.id, perfil_base="operador")
    assert sessao.post("/grupos-cliente", json={"nome": "Antes", "corIdentificacao": "blue"}).status_code == 403  # ainda Usuário

    assert client_admin.patch(f"/usuarios/{pessoa.id}", json={"perfilBase": "gestor", "departamentoId": ti.id}).status_code == 200
    # MESMO token (emitido quando era operador): o backend já enxerga Gestor, sem logout/login
    assert sessao.post("/grupos-cliente", json={"nome": "Depois", "corIdentificacao": "blue"}).status_code == 201
    assert _me(sessao)["departamentoId"] == ti.id
    _mover(client_admin, pessoa, criacao)
    me = _me(sessao)
    assert me["perfilBase"] == "gestor" and me["departamentoId"] == criacao.id


def test_jwt_nao_carrega_departamento_nem_decide_o_perfil() -> None:
    from app.core.security import REQUIRED_ACCESS_TOKEN_CLAIMS

    assert not any("departamento" in c for c in REQUIRED_ACCESS_TOKEN_CLAIMS)
    assert REQUIRED_ACCESS_TOKEN_CLAIMS == {"sub", "empresa_id", "perfil_base", "iat", "exp", "tipo"}


# --------------------------------------------------------------------------------------
# Overrides e limites do Gestor
# --------------------------------------------------------------------------------------


def test_override_negar_individual_continua_valendo_depois_de_trocar_de_departamento(
    client_admin: TestClient, client_gestor: TestClient, usuario_gestor: Usuario, ti: Departamento, criacao: Departamento
) -> None:
    resposta = client_admin.put(f"/usuarios/{usuario_gestor.id}/permissoes/clientes.criar", json={"efeito": "negar", "motivo": "teste"})
    assert resposta.status_code == 200, resposta.text
    _mover(client_admin, usuario_gestor, ti)
    nega = {"nome": "X", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}
    assert client_gestor.post("/clientes", json=nega).status_code == 403
    _mover(client_admin, usuario_gestor, criacao)
    assert client_gestor.post("/clientes", json=nega).status_code == 403  # a exceção explícita NÃO foi destruída nem ignorada
    assert "clientes.criar" not in _me(client_gestor)["permissoes"]
    assert client_gestor.post("/fornecedores", json={"nome": "F", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}).status_code == 201


def test_limites_do_gestor_nao_mudam_com_o_departamento(
    client_admin: TestClient, client_gestor: TestClient, db_session: Session, empresa: Empresa, usuario_gestor: Usuario, ti: Departamento, criacao: Departamento
) -> None:
    outro_gestor = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="gestor", email_prefixo="outrog")
    admin_legado = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="admin", email_prefixo="adm")
    comum = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="comum")
    for departamento in (ti, criacao):
        _mover(client_admin, usuario_gestor, departamento)
        corpo = {"empresaId": empresa.id, "nome": "Gestor Novo", "email": f"g{uuid.uuid4().hex[:5]}@x.test", "perfilBase": "gestor", "acessoSistema": True}
        assert client_gestor.post("/usuarios", json=corpo).status_code == 403  # não cria Gestor
        assert client_gestor.patch(f"/usuarios/{comum.id}", json={"perfilBase": "gestor"}).status_code == 403  # não promove
        assert client_gestor.patch(f"/usuarios/{outro_gestor.id}", json={"nome": "Mexendo"}).status_code == 403  # não administra Gestor
        assert client_gestor.patch(f"/usuarios/{admin_legado.id}", json={"nome": "Mexendo"}).status_code == 403  # nem admin legado
        assert client_gestor.get("/plataforma/me").status_code in (401, 403)  # nem a Administração da Plataforma
        assert client_gestor.get("/plataforma/dashboard").status_code in (401, 403)


# --------------------------------------------------------------------------------------
# Controle: Usuário (operador) muda de contexto mas NÃO ganha autoridade
# --------------------------------------------------------------------------------------


def test_usuario_normal_muda_de_contexto_sem_ganhar_autoridade_de_gestor(
    client_admin: TestClient, client_operador: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, ti: Departamento, criacao: Departamento
) -> None:
    _mover(client_admin, usuario_operador, ti)
    antes = _me(client_operador)
    _mover(client_admin, usuario_operador, criacao)
    depois = _me(client_operador)
    assert depois["departamentoId"] == criacao.id  # contexto atualizou
    assert depois["perfilBase"] == "operador" and sorted(depois["permissoes"]) == sorted(antes["permissoes"])
    assert not CAPACIDADES_GESTOR & set(depois["permissoes"])  # nenhuma capacidade administrativa
    assert client_operador.post("/grupos-cliente", json={"nome": "Nao", "corIdentificacao": "blue"}).status_code == 403
    assert client_operador.post("/clientes", json={"nome": "Nao", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}).status_code == 403
    assert client_operador.get("/usuarios", params={"empresaId": empresa.id}).status_code == 403


def test_isolamento_entre_empresas_nao_muda_com_departamento(
    client_admin: TestClient, client_gestor: TestClient, db_session: Session, usuario_gestor: Usuario, ti: Departamento
) -> None:
    _mover(client_admin, usuario_gestor, ti)
    agora_outra = _outra_empresa(db_session)
    assert client_gestor.get("/usuarios", params={"empresaId": agora_outra.id}).status_code == 403


def _outra_empresa(db: Session) -> Empresa:
    from datetime import datetime, timezone

    agora = datetime.now(timezone.utc)
    outra = Empresa(id=str(uuid.uuid4()), nome="Outra", codigo_interno=f"OUTRA-{uuid.uuid4().hex[:6]}".upper(), status="ativa", created_at=agora, updated_at=agora)
    db.add(outra)
    db.flush()
    return outra
