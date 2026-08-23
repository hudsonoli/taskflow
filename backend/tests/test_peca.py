"""Testes do módulo Peça (Fase 2G.4) — catálogo, não execução (sem vínculo Demanda↔Peça
nesta fase). Mesmo padrão de test_tipo_tarefa.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.categoria_peca import CategoriaPeca
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.peca import Peca
from tests.helpers.assertions import assert_erro_simples


def _payload(nome: str, **extra) -> dict:
    return {"nome": nome, **extra}


def _criar(client: TestClient, nome: str | None = None, **extra) -> dict:
    resposta = client.post("/pecas", json=_payload(nome or f"Peça {uuid.uuid4().hex[:8]}", **extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_categoria(client: TestClient, nome: str | None = None) -> dict:
    resposta = client.post("/categorias-peca", json={"nome": nome or f"Categoria {uuid.uuid4().hex[:8]}"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _categoria_de_outra_empresa(db_session: Session, outra_empresa: Empresa) -> CategoriaPeca:
    agora = datetime.now(timezone.utc)
    categoria = CategoriaPeca(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        nome="Categoria de outra empresa",
        nome_normalizado="categoria de outra empresa",
        ordem=0,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(categoria)
    db_session.flush()
    return categoria


# --------------------------------------------------------------------------------------
# CRUD básico / RBAC
# --------------------------------------------------------------------------------------


def test_admin_cria(client_admin: TestClient) -> None:
    resposta = client_admin.post("/pecas", json=_payload(f"Post feed {uuid.uuid4().hex[:8]}"))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "ativo"
    assert corpo["empresaId"]
    assert corpo["categoriaId"] is None
    assert corpo["categoriaNome"] is None
    assert corpo["briefingPadrao"] == ""
    assert corpo["sindicatoAtivo"] is False


def test_gestor_cria(client_gestor: TestClient) -> None:
    resposta = client_gestor.post("/pecas", json=_payload(f"Stories {uuid.uuid4().hex[:8]}"))
    assert resposta.status_code == 201, resposta.text


def test_operador_nao_cria(client_operador: TestClient) -> None:
    resposta = client_operador.post("/pecas", json=_payload(f"Operador {uuid.uuid4().hex[:8]}"))
    assert resposta.status_code == 403, resposta.text


def test_operador_nao_le_lista(client_operador: TestClient) -> None:
    resposta = client_operador.get("/pecas")
    assert resposta.status_code == 403, resposta.text


def test_operador_nao_le_diretorio(client_operador: TestClient) -> None:
    resposta = client_operador.get("/pecas/diretorio")
    assert resposta.status_code == 403, resposta.text


def test_editar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(
        f"/pecas/{criado['id']}",
        json={"nome": "Nome Editado", "briefingPadrao": "Novo briefing", "tempoEstimadoMinutos": 90},
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Nome Editado"
    assert corpo["briefingPadrao"] == "Novo briefing"
    assert corpo["tempoEstimadoMinutos"] == 90


def test_inativar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/pecas/{criado['id']}", json={"status": "inativo"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "inativo"


def test_arquivar_e_restaurar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    arquivar = client_admin.post(f"/pecas/{criado['id']}/arquivar", json={"motivoArquivamento": "descontinuada"})
    assert arquivar.status_code == 200, arquivar.text
    corpo = arquivar.json()
    assert corpo["status"] == "arquivado"
    assert corpo["motivoArquivamento"] == "descontinuada"

    restaurar = client_admin.post(f"/pecas/{criado['id']}/restaurar")
    assert restaurar.status_code == 200, restaurar.text
    assert restaurar.json()["status"] == "ativo"


def test_arquivar_ja_arquivado_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/pecas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    segunda = client_admin.post(f"/pecas/{criado['id']}/arquivar", json={"motivoArquivamento": "y"})
    assert_erro_simples(segunda, 409)


def test_editar_arquivada_exige_restaurar_primeiro(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/pecas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.patch(f"/pecas/{criado['id']}", json={"status": "ativo"})
    assert_erro_simples(resposta, 409)


# --------------------------------------------------------------------------------------
# Nome não é único — duplicatas legítimas do catálogo importado
# --------------------------------------------------------------------------------------


def test_nome_duplicado_e_permitido(client_admin: TestClient) -> None:
    nome = f"Nome repetido {uuid.uuid4().hex[:8]}"
    primeira = _criar(client_admin, nome)
    segunda = _criar(client_admin, nome)
    assert primeira["id"] != segunda["id"]
    assert primeira["nome"] == segunda["nome"] == nome


# --------------------------------------------------------------------------------------
# Escopo / cross-tenant
# --------------------------------------------------------------------------------------


def test_listagem_scoped_por_empresa(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    minha = _criar(client_admin)

    agora = datetime.now(timezone.utc)
    de_outra = Peca(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        categoria_id=None,
        nome="Peça de outra empresa",
        codigo_legado=None,
        briefing_padrao="",
        sindicato_ativo=False,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()

    listagem = client_admin.get("/pecas")
    assert listagem.status_code == 200, listagem.text
    ids = [item["id"] for item in listagem.json()]
    assert minha["id"] in ids
    assert de_outra.id not in ids


def test_get_cross_tenant_404_nao_403(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    agora = datetime.now(timezone.utc)
    de_outra = Peca(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        categoria_id=None,
        nome="Peça de outra empresa 2",
        codigo_legado=None,
        briefing_padrao="",
        sindicato_ativo=False,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()

    resposta = client_admin.get(f"/pecas/{de_outra.id}")
    assert resposta.status_code == 404, resposta.text


# --------------------------------------------------------------------------------------
# Categoria
# --------------------------------------------------------------------------------------


def test_criar_com_categoria_da_mesma_empresa(client_admin: TestClient) -> None:
    categoria = _criar_categoria(client_admin)
    criado = _criar(client_admin, categoriaId=categoria["id"])
    assert criado["categoriaId"] == categoria["id"]
    assert criado["categoriaNome"] == categoria["nome"]


def test_criar_com_categoria_de_outra_empresa_rejeitado(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    categoria_alheia = _categoria_de_outra_empresa(db_session, outra_empresa)
    resposta = client_admin.post("/pecas", json=_payload("Peça", categoriaId=categoria_alheia.id))
    assert_erro_simples(resposta, 422)


def test_criar_com_categoria_arquivada_rejeitado(client_admin: TestClient) -> None:
    categoria = _criar_categoria(client_admin)
    client_admin.post(f"/categorias-peca/{categoria['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.post("/pecas", json=_payload("Peça", categoriaId=categoria["id"]))
    assert_erro_simples(resposta, 422)


def test_editar_categoria_preserva_referencia_historica_arquivada(client_admin: TestClient) -> None:
    """Peça já vinculada a uma Categoria que foi arquivada depois continua íntegra — só um
    NOVO vínculo a uma Categoria arquivada é recusado (ver PecaService._ensure_categoria_valida)."""
    categoria = _criar_categoria(client_admin)
    criado = _criar(client_admin, categoriaId=categoria["id"])
    client_admin.post(f"/categorias-peca/{categoria['id']}/arquivar", json={"motivoArquivamento": "x"})

    # Editar outro campo sem tocar em categoriaId — não deve recusar.
    resposta = client_admin.patch(f"/pecas/{criado['id']}", json={"nome": "Renomeada"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["categoriaId"] == categoria["id"]
    assert resposta.json()["categoriaNome"] == categoria["nome"]


# --------------------------------------------------------------------------------------
# Diretório
# --------------------------------------------------------------------------------------


def test_arquivada_nao_aparece_no_diretorio(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/pecas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    diretorio = client_admin.get("/pecas/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    ids = [item["id"] for item in diretorio.json()]
    assert criado["id"] not in ids


def test_inativa_nao_aparece_no_diretorio(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.patch(f"/pecas/{criado['id']}", json={"status": "inativo"})

    diretorio = client_admin.get("/pecas/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    ids = [item["id"] for item in diretorio.json()]
    assert criado["id"] not in ids


def test_diretorio_so_tem_id_e_nome(client_admin: TestClient) -> None:
    criado = _criar(client_admin, "Diretorio enxuto")
    diretorio = client_admin.get("/pecas/diretorio")
    encontrado = next(item for item in diretorio.json() if item["id"] == criado["id"])
    assert set(encontrado.keys()) == {"id", "nome"}


# --------------------------------------------------------------------------------------
# Valores monetários e tempo
# --------------------------------------------------------------------------------------


def test_valores_centavos_preservados(client_admin: TestClient) -> None:
    criado = _criar(
        client_admin,
        valorTabelaCentavos=125090,
        sindicatoAtivo=True,
        valorSindicatoCriacaoCentavos=50000,
        valorSindicatoAdaptacaoCentavos=20000,
        valorSindicatoFinalizacaoCentavos=10000,
        tempoEstimadoMinutos=90,
        tempoMedioMinutos=120,
    )
    assert criado["valorTabelaCentavos"] == 125090
    assert criado["sindicatoAtivo"] is True
    assert criado["valorSindicatoCriacaoCentavos"] == 50000
    assert criado["valorSindicatoAdaptacaoCentavos"] == 20000
    assert criado["valorSindicatoFinalizacaoCentavos"] == 10000
    assert criado["tempoEstimadoMinutos"] == 90
    assert criado["tempoMedioMinutos"] == 120
    # Nunca preenchido pela API — só por sessão de trabalho real, que não existe nesta fase.
    assert criado["tempoCalculadoExecucaoMinutos"] is None

    relida = client_admin.get(f"/pecas/{criado['id']}")
    assert relida.status_code == 200, relida.text
    assert relida.json()["valorTabelaCentavos"] == 125090


# --------------------------------------------------------------------------------------
# Auditoria
# --------------------------------------------------------------------------------------


def test_eventos_publicados(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)
    client_admin.patch(f"/pecas/{criado['id']}", json={"nome": "Renomeada"})
    client_admin.post(f"/pecas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    client_admin.post(f"/pecas/{criado['id']}/restaurar")

    eventos = (
        db_session.query(Evento)
        .filter(Evento.entidade_tipo == "peca", Evento.entidade_id == criado["id"])
        .order_by(Evento.occurred_at.asc())
        .all()
    )
    tipos = [evento.tipo for evento in eventos]
    assert tipos == ["peca.criada", "peca.alterada", "peca.arquivada", "peca.restaurada"]
    # Payload enxuto — nenhum valor financeiro nem dado sensível no evento.
    for evento in eventos:
        assert "valorTabelaCentavos" not in evento.payload
        assert "senha" not in evento.payload
