"""Gate de privacidade antes do primeiro Gestor (Fase 1B): arquivos e comentários de CONTA DE SISTEMA.

Antes: `GET /arquivos` devolvia `usuarioNome` (nome real do remetente) e as listagens por demanda devolviam o id
(`enviadoPorUsuarioId` / `autorUsuarioId`); no frontend, o autor de comentário era resolvido pelo diretório de usuários
(que esconde a conta de sistema) e aparecia como "Usuário removido". Agora, para o tenant: autor = "Sistema", id
ausente, e o registro (arquivo, comentário, horários, conteúdo) segue intacto. A própria conta de sistema vê o seu.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.usuario import Usuario

from tests.fixtures.usuarios import _criar_usuario_com_credencial

NOME_REAL = "Proprietário Plataforma Secreto"


def _conta_de_sistema(db: Session, empresa: Empresa) -> Usuario:
    conta = _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="admin", email_prefixo="sistema-arq")
    conta.nome = NOME_REAL
    conta.is_system_account = True
    db.flush()
    return conta


def _client_de(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _demanda(client: TestClient) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Tarefa {uuid.uuid4().hex[:6]}"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _upload(client: TestClient, demanda_id: str, nome: str = "briefing.pdf") -> dict:
    resposta = client.post(
        f"/demandas/{demanda_id}/arquivos", files={"file": (nome, b"%PDF-1.4 conteudo", "application/pdf")}
    )
    assert resposta.status_code in (200, 201), resposta.text
    return resposta.json()


# --------------------------------------------------------------------------------------
# Arquivos
# --------------------------------------------------------------------------------------


def test_arquivo_enviado_pela_conta_de_sistema_aparece_como_sistema_na_central(
    app, db_session: Session, empresa: Empresa, client_gestor: TestClient
) -> None:
    sistema = _conta_de_sistema(db_session, empresa)
    cliente_sistema = _client_de(app, sistema)
    demanda = _demanda(cliente_sistema)
    arquivo = _upload(cliente_sistema, demanda["id"])

    bruto = client_gestor.get("/arquivos", params={"demandaId": demanda["id"]})
    assert bruto.status_code == 200, bruto.text
    item = next(i for i in bruto.json() if i["id"] == arquivo["id"])  # o arquivo continua existindo
    assert item["usuarioNome"] == "Sistema"
    assert item["enviadoPorUsuarioId"] is None
    assert item["enviadoPorSistema"] is True
    assert item["nome"] == "briefing.pdf"  # a informação do arquivo é preservada
    for segredo in (NOME_REAL, sistema.email, sistema.codigo_interno, sistema.id):
        assert segredo not in bruto.text


def test_listagem_por_demanda_nao_expoe_o_id_da_conta_de_sistema(
    app, db_session: Session, empresa: Empresa, client_gestor: TestClient
) -> None:
    sistema = _conta_de_sistema(db_session, empresa)
    cliente_sistema = _client_de(app, sistema)
    demanda = _demanda(cliente_sistema)
    arquivo = _upload(cliente_sistema, demanda["id"])
    lista = client_gestor.get(f"/demandas/{demanda['id']}/arquivos")
    assert lista.status_code == 200
    item = next(i for i in lista.json() if i["id"] == arquivo["id"])
    assert item["enviadoPorUsuarioId"] is None and item["enviadoPorSistema"] is True
    assert sistema.id not in lista.text


def test_arquivo_de_usuario_comum_preserva_o_nome(
    client_gestor: TestClient, client_admin: TestClient, usuario_admin: Usuario
) -> None:
    demanda = _demanda(client_admin)
    arquivo = _upload(client_admin, demanda["id"])
    item = next(i for i in client_gestor.get("/arquivos", params={"demandaId": demanda["id"]}).json() if i["id"] == arquivo["id"])
    assert item["usuarioNome"] == usuario_admin.nome
    assert item["enviadoPorUsuarioId"] == usuario_admin.id
    assert item["enviadoPorSistema"] is False


def test_a_propria_conta_de_sistema_ve_o_proprio_nome_no_arquivo(
    app, db_session: Session, empresa: Empresa
) -> None:
    sistema = _conta_de_sistema(db_session, empresa)
    cliente_sistema = _client_de(app, sistema)
    demanda = _demanda(cliente_sistema)
    arquivo = _upload(cliente_sistema, demanda["id"])
    item = next(i for i in cliente_sistema.get("/arquivos", params={"demandaId": demanda["id"]}).json() if i["id"] == arquivo["id"])
    assert item["usuarioNome"] == NOME_REAL and item["enviadoPorUsuarioId"] == sistema.id


# --------------------------------------------------------------------------------------
# Comentários
# --------------------------------------------------------------------------------------


def test_comentario_da_conta_de_sistema_aparece_como_sistema_para_o_tenant(
    app, db_session: Session, empresa: Empresa, client_gestor: TestClient
) -> None:
    sistema = _conta_de_sistema(db_session, empresa)
    cliente_sistema = _client_de(app, sistema)
    demanda = _demanda(cliente_sistema)
    criado = cliente_sistema.post(f"/demandas/{demanda['id']}/comentarios", json={"texto": "Nota interna do sistema"})
    assert criado.status_code == 201, criado.text

    lista = client_gestor.get(f"/demandas/{demanda['id']}/comentarios")
    assert lista.status_code == 200
    item = next(c for c in lista.json() if c["id"] == criado.json()["id"])
    assert item["texto"] == "Nota interna do sistema"  # o comentário continua, com conteúdo e horário
    assert item["createdAt"]
    assert item["autorUsuarioId"] is None and item["autorSistema"] is True
    assert sistema.id not in lista.text and NOME_REAL not in lista.text


def test_comentario_de_usuario_comum_preserva_o_autor(
    client_gestor: TestClient, client_admin: TestClient, usuario_admin: Usuario
) -> None:
    demanda = _demanda(client_admin)
    criado = client_admin.post(f"/demandas/{demanda['id']}/comentarios", json={"texto": "Olá"}).json()
    item = next(c for c in client_gestor.get(f"/demandas/{demanda['id']}/comentarios").json() if c["id"] == criado["id"])
    assert item["autorUsuarioId"] == usuario_admin.id and item["autorSistema"] is False


def test_a_propria_conta_de_sistema_continua_autora_dos_seus_comentarios(
    app, db_session: Session, empresa: Empresa
) -> None:
    sistema = _conta_de_sistema(db_session, empresa)
    cliente_sistema = _client_de(app, sistema)
    demanda = _demanda(cliente_sistema)
    criado = cliente_sistema.post(f"/demandas/{demanda['id']}/comentarios", json={"texto": "Meu"}).json()
    item = next(c for c in cliente_sistema.get(f"/demandas/{demanda['id']}/comentarios").json() if c["id"] == criado["id"])
    assert item["autorUsuarioId"] == sistema.id and item["autorSistema"] is False  # a UI ainda a reconhece como autora
