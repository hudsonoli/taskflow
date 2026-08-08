"""Testes do módulo Grupo de Cliente — cobertura de negócio (não infra, ver
test_infra_smoke.py). Regras completas em docs/padrao-arquivamento.md +
GrupoClienteService."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.services.grupo_cliente_service import GrupoClienteService
from tests.helpers.assertions import assert_conflito_arquivado, assert_erro_simples


def _payload(nome: str, cor: str = "blue") -> dict:
    return {"nome": nome, "corIdentificacao": cor}


def test_criar_grupo_com_nome_novo(client_admin: TestClient) -> None:
    resposta = client_admin.post("/grupos-cliente", json=_payload(f"Grupo Novo {uuid.uuid4().hex[:8]}"))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["nome"].startswith("Grupo Novo")
    assert corpo["status"] == "ativo"
    assert corpo["codigoInterno"]
    # empresaId sempre vem do usuário autenticado, nunca do payload (payload nem tem o campo).
    assert corpo["empresaId"]


def test_editar_grupo(client_admin: TestClient) -> None:
    criado = client_admin.post("/grupos-cliente", json=_payload(f"Editar {uuid.uuid4().hex[:8]}")).json()
    resposta = client_admin.patch(f"/grupos-cliente/{criado['id']}", json={"nome": "Nome Editado"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["nome"] == "Nome Editado"


def test_nome_duplicado_de_ativo_409_simples(client_admin: TestClient) -> None:
    nome = f"Duplicado Ativo {uuid.uuid4().hex[:8]}"
    primeiro = client_admin.post("/grupos-cliente", json=_payload(nome))
    assert primeiro.status_code == 201, primeiro.text

    segundo = client_admin.post("/grupos-cliente", json=_payload(nome.upper()))
    assert_erro_simples(segundo, 409)
    assert isinstance(segundo.json()["detail"], str)


def test_nome_duplicado_de_arquivado_409_padronizado_oferece_restaurar(client_admin: TestClient) -> None:
    nome = f"Duplicado Arquivado {uuid.uuid4().hex[:8]}"
    criado = client_admin.post("/grupos-cliente", json=_payload(nome)).json()
    arquivar = client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={"motivoArquivamento": "teste"})
    assert arquivar.status_code == 200, arquivar.text

    tentativa = client_admin.post("/grupos-cliente", json=_payload(nome))
    detail = assert_conflito_arquivado(tentativa, code="GRUPO_CLIENTE_ARQUIVADO_EXISTENTE")
    assert detail["grupoClienteArquivadoId"] == criado["id"]


def test_arquivar_sem_motivo_422(client_admin: TestClient) -> None:
    criado = client_admin.post("/grupos-cliente", json=_payload(f"Sem Motivo {uuid.uuid4().hex[:8]}")).json()
    resposta = client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={})
    assert resposta.status_code == 422, resposta.text


def test_arquivar_valido(client_admin: TestClient) -> None:
    criado = client_admin.post("/grupos-cliente", json=_payload(f"Arquivar Valido {uuid.uuid4().hex[:8]}")).json()
    resposta = client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={"motivoArquivamento": "não usado mais"})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "arquivado"
    assert corpo["motivoArquivamento"] == "não usado mais"
    assert corpo["arquivadoAt"] is not None


def test_arquivar_ja_arquivado_409(client_admin: TestClient) -> None:
    criado = client_admin.post("/grupos-cliente", json=_payload(f"Ja Arquivado {uuid.uuid4().hex[:8]}")).json()
    client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    segunda = client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={"motivoArquivamento": "y"})
    assert_erro_simples(segunda, 409)


def test_restaurar(client_admin: TestClient) -> None:
    criado = client_admin.post("/grupos-cliente", json=_payload(f"Restaurar {uuid.uuid4().hex[:8]}")).json()
    client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.post(f"/grupos-cliente/{criado['id']}/restaurar")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "ativo"


def test_listagem_padrao_exclui_arquivado(client_admin: TestClient) -> None:
    nome = f"Lista Padrao {uuid.uuid4().hex[:8]}"
    criado = client_admin.post("/grupos-cliente", json=_payload(nome)).json()
    client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    listagem = client_admin.get("/grupos-cliente")
    assert listagem.status_code == 200, listagem.text
    ids = [g["id"] for g in listagem.json()]
    assert criado["id"] not in ids


def test_listagem_com_filtro_status_arquivado(client_admin: TestClient) -> None:
    nome = f"Lista Filtro {uuid.uuid4().hex[:8]}"
    criado = client_admin.post("/grupos-cliente", json=_payload(nome)).json()
    client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    listagem = client_admin.get("/grupos-cliente", params={"status": "arquivado"})
    assert listagem.status_code == 200, listagem.text
    ids = [g["id"] for g in listagem.json()]
    assert criado["id"] in ids


def test_diretorio_inclui_arquivado_com_status_e_nome_corretos(client_admin: TestClient) -> None:
    nome = f"Diretorio Arquivado {uuid.uuid4().hex[:8]}"
    criado = client_admin.post("/grupos-cliente", json=_payload(nome)).json()
    client_admin.post(f"/grupos-cliente/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    diretorio = client_admin.get("/grupos-cliente/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    encontrado = next(item for item in diretorio.json() if item["id"] == criado["id"])
    assert encontrado["status"] == "arquivado"
    assert encontrado["nome"] == nome
    assert encontrado["codigoInterno"] == criado["codigoInterno"]


def test_isolamento_por_empresa_404(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    from datetime import datetime, timezone

    from app.models.grupo_cliente import GrupoCliente

    agora = datetime.now(timezone.utc)
    grupo_outra_empresa = GrupoCliente(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"grupo-outra-empresa-{uuid.uuid4().hex[:8]}",
        nome="Grupo de Outra Empresa",
        nome_normalizado="grupo de outra empresa",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(grupo_outra_empresa)
    db_session.flush()

    resposta = client_admin.get(f"/grupos-cliente/{grupo_outra_empresa.id}")
    assert resposta.status_code == 404, resposta.text


def test_operador_403_ao_criar_gestor_pode(client_operador: TestClient, client_gestor: TestClient) -> None:
    negado = client_operador.post("/grupos-cliente", json=_payload(f"Operador {uuid.uuid4().hex[:8]}"))
    assert negado.status_code == 403, negado.text

    permitido = client_gestor.post("/grupos-cliente", json=_payload(f"Gestor {uuid.uuid4().hex[:8]}"))
    assert permitido.status_code == 201, permitido.text


def test_codigo_interno_imutavel_no_patch(client_admin: TestClient) -> None:
    criado = client_admin.post("/grupos-cliente", json=_payload(f"Imutavel {uuid.uuid4().hex[:8]}")).json()
    resposta = client_admin.patch(f"/grupos-cliente/{criado['id']}", json={"codigoInterno": "tentativa-de-troca"})
    # GrupoClienteUpdate não tem esse campo — é ignorado silenciosamente (schema não aceita
    # o alias), não gera 422 nem altera o valor.
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["codigoInterno"] == criado["codigoInterno"]


def test_seed_idempotente_via_codigo_legado(db_session: Session, empresa: Empresa) -> None:
    service = GrupoClienteService()
    codigo = f"grupo-legado-{uuid.uuid4().hex[:8]}"
    primeiro = service.create_grupo_cliente_com_codigo_legado(
        db_session,
        nome="Grupo Legado",
        cor_identificacao="zinc",
        empresa_id=empresa.id,
        codigo_interno=codigo,
    )
    segundo = service.create_grupo_cliente_com_codigo_legado(
        db_session,
        nome="Grupo Legado",
        cor_identificacao="zinc",
        empresa_id=empresa.id,
        codigo_interno=codigo,
    )
    assert primeiro.id == segundo.id


def test_concorrencia_nome_duplicado_vira_conflito_nao_erro_bruto(db_session: Session, empresa: Empresa) -> None:
    """Simula a corrida tratada por IntegrityError em _criar: inserir direto via
    repository (bypassando os checks do service) e então tentar criar via service com o
    mesmo nome deve resultar em conflito tratado, não IntegrityError vazando."""
    from datetime import datetime, timezone

    from app.models.grupo_cliente import GrupoCliente
    from app.services.grupo_cliente_service import GrupoClienteArquivadoConflictError, GrupoClienteConflictError
    from app.schemas.grupo_cliente import GrupoClienteCreate

    nome = f"Corrida {uuid.uuid4().hex[:8]}"
    agora = datetime.now(timezone.utc)
    existente = GrupoCliente(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"grupo-corrida-{uuid.uuid4().hex[:8]}",
        nome=nome,
        nome_normalizado=nome.strip().lower(),
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(existente)
    db_session.flush()

    service = GrupoClienteService()
    try:
        service.create_grupo_cliente(
            db_session,
            GrupoClienteCreate(nome=nome, corIdentificacao="green"),
            empresa_id=empresa.id,
            actor_usuario_id=None,
        )
        raise AssertionError("deveria ter levantado conflito")
    except (GrupoClienteConflictError, GrupoClienteArquivadoConflictError):
        pass
