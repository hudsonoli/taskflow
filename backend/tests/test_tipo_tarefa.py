"""Testes do módulo Tipo de Tarefa (Fase 2G.2) — cobertura de negócio (não infra, ver
test_infra_smoke.py). Mesmo padrão de test_grupo_cliente.py/test_workflow_modelo.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.tipo_tarefa import TipoTarefa
from tests.helpers.assertions import assert_conflito_arquivado, assert_erro_simples


def _payload(nome: str, **extra) -> dict:
    return {"nome": nome, **extra}


def _criar(client: TestClient, nome: str | None = None, **extra) -> dict:
    resposta = client.post("/tipos-tarefa", json=_payload(nome or f"Tipo {uuid.uuid4().hex[:8]}", **extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_admin_cria(client_admin: TestClient) -> None:
    resposta = client_admin.post("/tipos-tarefa", json=_payload(f"Post social {uuid.uuid4().hex[:8]}"))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "ativo"
    assert corpo["ordem"] == 0
    assert corpo["empresaId"]


def test_gestor_cria(client_gestor: TestClient) -> None:
    resposta = client_gestor.post("/tipos-tarefa", json=_payload(f"Landing page {uuid.uuid4().hex[:8]}"))
    assert resposta.status_code == 201, resposta.text


def test_operador_nao_cria(client_operador: TestClient) -> None:
    resposta = client_operador.post("/tipos-tarefa", json=_payload(f"Operador {uuid.uuid4().hex[:8]}"))
    assert resposta.status_code == 403, resposta.text


def test_operador_nao_le_diretorio(client_operador: TestClient) -> None:
    """Diferente de /workflow-modelos/diretorio: aqui o único consumidor é área
    administrativa, então o diretório também é admin/gestor nesta fase."""
    resposta = client_operador.get("/tipos-tarefa/diretorio")
    assert resposta.status_code == 403, resposta.text


def test_criar_com_descricao_e_ordem(client_admin: TestClient) -> None:
    criado = _criar(client_admin, "Com descricao", descricao="Texto livre", ordem=3)
    assert criado["descricao"] == "Texto livre"
    assert criado["ordem"] == 3


def test_listagem_scoped_por_empresa(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    meu = _criar(client_admin)

    agora = datetime.now(timezone.utc)
    de_outra = TipoTarefa(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        nome="Tipo de outra empresa",
        nome_normalizado="tipo de outra empresa",
        ordem=0,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()

    listagem = client_admin.get("/tipos-tarefa")
    assert listagem.status_code == 200, listagem.text
    ids = [item["id"] for item in listagem.json()]
    assert meu["id"] in ids
    assert de_outra.id not in ids


def test_get_cross_tenant_404_nao_403(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    agora = datetime.now(timezone.utc)
    de_outra = TipoTarefa(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        nome="Tipo de outra empresa 2",
        nome_normalizado="tipo de outra empresa 2",
        ordem=0,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()

    resposta = client_admin.get(f"/tipos-tarefa/{de_outra.id}")
    assert resposta.status_code == 404, resposta.text


def test_mesmo_nome_normalizado_mesma_empresa_rejeita(client_admin: TestClient) -> None:
    nome = f"Duplicado {uuid.uuid4().hex[:8]}"
    primeiro = client_admin.post("/tipos-tarefa", json=_payload(nome))
    assert primeiro.status_code == 201, primeiro.text

    segundo = client_admin.post("/tipos-tarefa", json=_payload(f"  {nome.upper()}  "))
    assert_erro_simples(segundo, 409)
    assert isinstance(segundo.json()["detail"], str)


def test_mesmo_nome_em_empresa_diferente_permitido(
    client_admin: TestClient, empresa: Empresa, outra_empresa: Empresa, db_session: Session
) -> None:
    nome = f"Mesmo nome {uuid.uuid4().hex[:8]}"
    criado = _criar(client_admin, nome)
    assert criado["nome"] == nome

    agora = datetime.now(timezone.utc)
    de_outra = TipoTarefa(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        nome=nome,
        nome_normalizado=nome.strip().lower(),
        ordem=0,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()  # não levanta IntegrityError — unique é (empresa_id, nome_normalizado)


def test_nome_duplicado_de_arquivado_409_padronizado_oferece_restaurar(client_admin: TestClient) -> None:
    nome = f"Duplicado Arquivado {uuid.uuid4().hex[:8]}"
    criado = _criar(client_admin, nome)
    arquivar = client_admin.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "teste"})
    assert arquivar.status_code == 200, arquivar.text

    tentativa = client_admin.post("/tipos-tarefa", json=_payload(nome))
    detail = assert_conflito_arquivado(tentativa, code="TIPO_TAREFA_ARQUIVADO_EXISTENTE")
    assert detail["tipoTarefaArquivadoId"] == criado["id"]


def test_update(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(
        f"/tipos-tarefa/{criado['id']}", json={"nome": "Nome Editado", "descricao": "Nova descricao", "ordem": 5}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Nome Editado"
    assert corpo["descricao"] == "Nova descricao"
    assert corpo["ordem"] == 5


def test_update_para_inativo(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/tipos-tarefa/{criado['id']}", json={"status": "inativo"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "inativo"


def test_arquivar_valido(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "não usado mais"})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "arquivado"
    assert corpo["motivoArquivamento"] == "não usado mais"
    assert corpo["arquivadoAt"] is not None


def test_arquivar_ja_arquivado_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    segunda = client_admin.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "y"})
    assert_erro_simples(segunda, 409)


def test_restaurar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.post(f"/tipos-tarefa/{criado['id']}/restaurar")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "ativo"


def test_listagem_padrao_exclui_arquivado(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    listagem = client_admin.get("/tipos-tarefa")
    assert listagem.status_code == 200, listagem.text
    ids = [item["id"] for item in listagem.json()]
    assert criado["id"] not in ids


def test_arquivado_nao_aparece_no_diretorio(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    diretorio = client_admin.get("/tipos-tarefa/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    ids = [item["id"] for item in diretorio.json()]
    assert criado["id"] not in ids


def test_inativo_nao_aparece_no_diretorio(client_admin: TestClient) -> None:
    """Diretório é só `ativo` (mesmo padrão de /workflow-modelos/diretorio, Fase 2G.1) — sem
    resolução histórica; `inativo` também fica de fora, não só `arquivado`."""
    criado = _criar(client_admin)
    client_admin.patch(f"/tipos-tarefa/{criado['id']}", json={"status": "inativo"})

    diretorio = client_admin.get("/tipos-tarefa/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    ids = [item["id"] for item in diretorio.json()]
    assert criado["id"] not in ids


def test_diretorio_so_tem_id_e_nome(client_admin: TestClient) -> None:
    criado = _criar(client_admin, "Diretorio enxuto")
    diretorio = client_admin.get("/tipos-tarefa/diretorio")
    encontrado = next(item for item in diretorio.json() if item["id"] == criado["id"])
    assert set(encontrado.keys()) == {"id", "nome"}
    assert encontrado["nome"] == "Diretorio enxuto"


def test_eventos_publicados(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)
    client_admin.patch(f"/tipos-tarefa/{criado['id']}", json={"nome": "Renomeado"})
    client_admin.post(f"/tipos-tarefa/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    client_admin.post(f"/tipos-tarefa/{criado['id']}/restaurar")

    eventos = (
        db_session.query(Evento)
        .filter(Evento.entidade_tipo == "tipo_tarefa", Evento.entidade_id == criado["id"])
        .order_by(Evento.occurred_at.asc())
        .all()
    )
    tipos = [evento.tipo for evento in eventos]
    assert tipos == [
        "tipo_tarefa.criado",
        "tipo_tarefa.alterado",
        "tipo_tarefa.arquivado",
        "tipo_tarefa.restaurado",
    ]
    # Nenhum payload carrega dado sensível — mesma checagem de espírito do publisher real.
    for evento in eventos:
        assert "senha" not in evento.payload
