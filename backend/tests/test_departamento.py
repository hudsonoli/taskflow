"""Departamento — Fase 2A. Ver app/services/departamento_service.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.helpers.assertions import assert_conflito_arquivado, assert_erro_simples


def _payload(nome: str, cor: str = "blue", **extra) -> dict:
    return {"nome": nome, "corIdentificacao": cor, **extra}


def _nome_unico(prefixo: str) -> str:
    return f"{prefixo} {uuid.uuid4().hex[:8]}"


def _criar(client: TestClient, nome: str | None = None, **extra):
    return client.post("/departamentos", json=_payload(nome or _nome_unico("Depto"), **extra))


# --------------------------------------------------------------------------------------
# Criação e código de referência
# --------------------------------------------------------------------------------------

def test_criar_departamento(client_admin: TestClient) -> None:
    resposta = _criar(client_admin, "Criação Teste")
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Criação Teste"
    assert corpo["status"] == "ativo"
    assert corpo["empresaId"]
    assert corpo["codigoInterno"]


def test_codigo_referencia_no_formato_esperado(client_admin: TestClient) -> None:
    corpo = _criar(client_admin).json()
    ano = datetime.now(timezone.utc).year
    assert corpo["codigoReferencia"] == f"D{ano % 100:02d}{corpo['sequencialReferencia']:06d}"
    assert corpo["anoReferencia"] == ano
    assert len(corpo["codigoReferencia"]) == 9


def test_sequencial_avanca_entre_criacoes(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin).json()
    segundo = _criar(client_admin).json()
    assert segundo["sequencialReferencia"] == primeiro["sequencialReferencia"] + 1


def test_editar_departamento(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    resposta = client_admin.patch(f"/departamentos/{criado['id']}", json={"nome": _nome_unico("Editado")})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["nome"].startswith("Editado")


# --------------------------------------------------------------------------------------
# Campos gerados não são aceitos no payload
# --------------------------------------------------------------------------------------

def test_payload_com_campos_gerados_e_rejeitado(client_admin: TestClient, empresa: Empresa) -> None:
    proibidos = [
        {"empresaId": empresa.id},
        {"actorUsuarioId": str(uuid.uuid4())},
        {"codigoInterno": "dep-hackeado"},
        {"codigoReferencia": "D26999999"},
        {"anoReferencia": 2030},
        {"sequencialReferencia": 999},
    ]
    for extra in proibidos:
        resposta = client_admin.post("/departamentos", json=_payload(_nome_unico("X"), **extra))
        assert resposta.status_code == 422, f"{extra} deveria ser rejeitado: {resposta.text}"


def test_codigos_sao_imutaveis_no_patch(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    for extra in [
        {"codigoReferencia": "D26999999"},
        {"anoReferencia": 2030},
        {"sequencialReferencia": 999},
        {"codigoInterno": "dep-outro"},
    ]:
        resposta = client_admin.patch(f"/departamentos/{criado['id']}", json=extra)
        assert resposta.status_code == 422, f"{extra}: {resposta.text}"

    atual = client_admin.get(f"/departamentos/{criado['id']}").json()
    assert atual["codigoReferencia"] == criado["codigoReferencia"]
    assert atual["anoReferencia"] == criado["anoReferencia"]
    assert atual["sequencialReferencia"] == criado["sequencialReferencia"]
    assert atual["codigoInterno"] == criado["codigoInterno"]


# --------------------------------------------------------------------------------------
# Duplicidade
# --------------------------------------------------------------------------------------

def test_nome_duplicado_ativo_409_simples(client_admin: TestClient) -> None:
    nome = _nome_unico("Duplicado")
    assert _criar(client_admin, nome).status_code == 201
    segundo = client_admin.post("/departamentos", json=_payload(nome.upper()))
    assert_erro_simples(segundo, 409)
    assert isinstance(segundo.json()["detail"], str)


def test_nome_de_arquivado_409_padronizado(client_admin: TestClient) -> None:
    nome = _nome_unico("Arquivado")
    criado = _criar(client_admin, nome).json()
    client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "teste"})

    tentativa = client_admin.post("/departamentos", json=_payload(nome))
    detail = assert_conflito_arquivado(tentativa, code="DEPARTAMENTO_ARQUIVADO_EXISTENTE")
    assert detail["departamentoArquivadoId"] == criado["id"]


# --------------------------------------------------------------------------------------
# Ciclo de vida
# --------------------------------------------------------------------------------------

def test_arquivar_sem_motivo_422(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    assert client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={}).status_code == 422


def test_arquivar_valido(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    resposta = client_admin.post(
        f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "não usado mais"}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "arquivado"
    assert corpo["motivoArquivamento"] == "não usado mais"
    assert corpo["arquivadoAt"] is not None
    # O código emitido não muda ao arquivar.
    assert corpo["codigoReferencia"] == criado["codigoReferencia"]


def test_arquivar_ja_arquivado_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    segunda = client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "y"})
    assert_erro_simples(segunda, 409)


def test_restaurar(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.post(f"/departamentos/{criado['id']}/restaurar")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "ativo"
    assert corpo["codigoReferencia"] == criado["codigoReferencia"]


# --------------------------------------------------------------------------------------
# Listagem, filtro, diretório e busca
# --------------------------------------------------------------------------------------

def test_listagem_padrao_exclui_arquivado(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    ids = [d["id"] for d in client_admin.get("/departamentos").json()]
    assert criado["id"] not in ids


def test_filtro_status_arquivado(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    ids = [d["id"] for d in client_admin.get("/departamentos", params={"status": "arquivado"}).json()]
    assert criado["id"] in ids


def test_diretorio_inclui_arquivado(client_admin: TestClient) -> None:
    nome = _nome_unico("Diretorio")
    criado = _criar(client_admin, nome).json()
    client_admin.post(f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    diretorio = client_admin.get("/departamentos/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    item = next(d for d in diretorio.json() if d["id"] == criado["id"])
    assert item["status"] == "arquivado"
    assert item["nome"] == nome
    assert item["codigoReferencia"] == criado["codigoReferencia"]


def test_busca_por_codigo_referencia_case_insensitive(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    codigo = criado["codigoReferencia"]

    for termo in (codigo, codigo.lower()):
        encontrados = client_admin.get("/departamentos", params={"search": termo}).json()
        assert any(d["id"] == criado["id"] for d in encontrados), f"não achou com {termo!r}"


def test_busca_por_codigo_interno(client_admin: TestClient) -> None:
    criado = _criar(client_admin).json()
    encontrados = client_admin.get("/departamentos", params={"search": criado["codigoInterno"]}).json()
    assert any(d["id"] == criado["id"] for d in encontrados)


# --------------------------------------------------------------------------------------
# Responsável
# --------------------------------------------------------------------------------------

def test_responsavel_da_mesma_empresa_e_aceito(client_admin: TestClient, usuario_gestor: Usuario) -> None:
    resposta = client_admin.post(
        "/departamentos", json=_payload(_nome_unico("ComResp"), responsavelUsuarioId=usuario_gestor.id)
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["responsavelUsuarioId"] == usuario_gestor.id


def test_responsavel_de_outra_empresa_422(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    agora = datetime.now(timezone.utc)
    forasteiro = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"forasteiro-{uuid.uuid4().hex[:8]}",
        nome="Usuário de Outra Empresa",
        email=f"forasteiro-{uuid.uuid4().hex[:8]}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(forasteiro)
    db_session.flush()

    resposta = client_admin.post(
        "/departamentos", json=_payload(_nome_unico("CrossTenant"), responsavelUsuarioId=forasteiro.id)
    )
    assert resposta.status_code == 422, resposta.text


def test_responsavel_arquivado_nao_pode_ser_definido(
    client_admin: TestClient, usuario_operador: Usuario, db_session: Session
) -> None:
    usuario_operador.status = "arquivado"
    db_session.flush()

    resposta = client_admin.post(
        "/departamentos", json=_payload(_nome_unico("RespArquivado"), responsavelUsuarioId=usuario_operador.id)
    )
    assert resposta.status_code == 422, resposta.text


def test_responsavel_continua_resolvendo_apos_inativacao(
    client_admin: TestClient, usuario_gestor: Usuario, db_session: Session
) -> None:
    """Vínculo histórico: definido enquanto o usuário estava ativo, permanece depois."""
    criado = client_admin.post(
        "/departamentos", json=_payload(_nome_unico("Historico"), responsavelUsuarioId=usuario_gestor.id)
    ).json()

    usuario_gestor.status = "inativo"
    db_session.flush()

    atual = client_admin.get(f"/departamentos/{criado['id']}").json()
    assert atual["responsavelUsuarioId"] == usuario_gestor.id


# --------------------------------------------------------------------------------------
# Isolamento por empresa (todas as rotas) e autorização
# --------------------------------------------------------------------------------------

def _departamento_de_outra_empresa(db_session: Session, outra_empresa: Empresa) -> str:
    from app.models.departamento import Departamento

    agora = datetime.now(timezone.utc)
    alheio = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"dep-alheio-{uuid.uuid4().hex[:8]}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome="Departamento de Outra Empresa",
        nome_normalizado=f"departamento de outra empresa {uuid.uuid4().hex[:6]}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(alheio)
    db_session.flush()
    return alheio.id


def test_isolamento_por_empresa_em_todas_as_rotas(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    alheio_id = _departamento_de_outra_empresa(db_session, outra_empresa)

    assert client_admin.get(f"/departamentos/{alheio_id}").status_code == 404
    assert client_admin.patch(f"/departamentos/{alheio_id}", json={"nome": "Tentativa"}).status_code == 404
    assert (
        client_admin.post(f"/departamentos/{alheio_id}/arquivar", json={"motivoArquivamento": "x"}).status_code
        == 404
    )
    assert client_admin.post(f"/departamentos/{alheio_id}/restaurar").status_code == 404

    # Listagem e diretório não podem sequer mencionar o recurso alheio.
    assert all(d["id"] != alheio_id for d in client_admin.get("/departamentos").json())
    assert all(d["id"] != alheio_id for d in client_admin.get("/departamentos/diretorio").json())


def test_operador_403_gestor_pode(client_operador: TestClient, client_gestor: TestClient) -> None:
    assert client_operador.post("/departamentos", json=_payload(_nome_unico("Operador"))).status_code == 403
    assert client_gestor.post("/departamentos", json=_payload(_nome_unico("Gestor"))).status_code == 201


def test_operador_403_nas_demais_rotas_de_escrita(
    client_operador: TestClient, client_admin: TestClient
) -> None:
    criado = _criar(client_admin).json()
    assert client_operador.patch(f"/departamentos/{criado['id']}", json={"nome": "X"}).status_code == 403
    assert (
        client_operador.post(
            f"/departamentos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"}
        ).status_code
        == 403
    )
    assert client_operador.post(f"/departamentos/{criado['id']}/restaurar").status_code == 403


def test_operador_acessa_diretorio(client_operador: TestClient) -> None:
    """O diretório alimenta seletores operacionais — liberado a qualquer autenticado."""
    assert client_operador.get("/departamentos/diretorio").status_code == 200


# --------------------------------------------------------------------------------------
# Seed e contador
# --------------------------------------------------------------------------------------

def test_seed_idempotente_nao_consome_sequencia(db_session: Session, empresa: Empresa) -> None:
    from sqlalchemy import text

    from app.services.departamento_service import DepartamentoService

    service = DepartamentoService()
    codigo = f"dep-legado-{uuid.uuid4().hex[:8]}"

    primeiro = service.create_departamento_com_codigo_legado(
        db_session, nome=_nome_unico("Legado"), cor_identificacao="zinc",
        empresa_id=empresa.id, codigo_interno=codigo,
    )
    contador_apos_criar = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_referencia "
            "WHERE empresa_id = :e AND tipo_entidade = 'departamento'"
        ),
        {"e": empresa.id},
    ).scalar_one()

    segundo = service.create_departamento_com_codigo_legado(
        db_session, nome=_nome_unico("Legado"), cor_identificacao="zinc",
        empresa_id=empresa.id, codigo_interno=codigo,
    )
    contador_apos_repetir = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_referencia "
            "WHERE empresa_id = :e AND tipo_entidade = 'departamento'"
        ),
        {"e": empresa.id},
    ).scalar_one()

    assert primeiro.id == segundo.id
    assert primeiro.codigo_referencia == segundo.codigo_referencia
    assert contador_apos_repetir == contador_apos_criar, "a repetição não pode avançar o contador"


def test_falha_na_criacao_nao_queima_numero(db_session: Session, empresa: Empresa) -> None:
    """Nome duplicado aborta antes do commit — o contador não avança."""
    from sqlalchemy import text

    from app.schemas.departamento import DepartamentoCreate
    from app.services.departamento_service import DepartamentoConflictError, DepartamentoService

    service = DepartamentoService()
    nome = _nome_unico("RollbackContador")
    service.create_departamento(
        db_session, DepartamentoCreate(nome=nome, corIdentificacao="blue"),
        empresa_id=empresa.id, actor_usuario_id=None,
    )
    antes = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_referencia "
            "WHERE empresa_id = :e AND tipo_entidade = 'departamento'"
        ),
        {"e": empresa.id},
    ).scalar_one()

    try:
        service.create_departamento(
            db_session, DepartamentoCreate(nome=nome, corIdentificacao="blue"),
            empresa_id=empresa.id, actor_usuario_id=None,
        )
        raise AssertionError("deveria ter levantado conflito")
    except DepartamentoConflictError:
        pass

    depois = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_referencia "
            "WHERE empresa_id = :e AND tipo_entidade = 'departamento'"
        ),
        {"e": empresa.id},
    ).scalar_one()
    assert depois == antes, "criação falha não pode queimar número da sequência"


def test_concorrencia_nome_duplicado_vira_conflito_tratado(db_session: Session, empresa: Empresa) -> None:
    """Insere direto pelo repository (bypassando os checks) e então cria pelo service com o
    mesmo nome: o IntegrityError precisa virar conflito tratado, não vazar."""
    from app.models.departamento import Departamento
    from app.schemas.departamento import DepartamentoCreate
    from app.services.departamento_service import (
        DepartamentoArquivadoConflictError,
        DepartamentoConflictError,
        DepartamentoService,
    )

    nome = _nome_unico("Corrida")
    agora = datetime.now(timezone.utc)
    existente = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-corrida-{uuid.uuid4().hex[:8]}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=nome,
        nome_normalizado=nome.strip().lower(),
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(existente)
    db_session.flush()

    service = DepartamentoService()
    try:
        service.create_departamento(
            db_session, DepartamentoCreate(nome=nome, corIdentificacao="green"),
            empresa_id=empresa.id, actor_usuario_id=None,
        )
        raise AssertionError("deveria ter levantado conflito")
    except (DepartamentoConflictError, DepartamentoArquivadoConflictError):
        pass
