"""WorkflowModelo — modelos de workflow (etapas de execução de tarefas).

Ver app/services/workflow_modelo_service.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.helpers.assertions import assert_conflito_arquivado, assert_erro_simples


def _nome_unico(prefixo: str) -> str:
    return f"{prefixo} {uuid.uuid4().hex[:8]}"


def _etapa(
    nome: str = "Etapa 1",
    tipo: str = "execucao",
    quantidade: int = 1,
    unidade: str = "dias_corridos",
    responsavel_ids: list[str] | None = None,
    departamento_ids: list[str] | None = None,
) -> dict:
    return {
        "nome": nome,
        "tipo": tipo,
        "quantidadeAntesDeadline": quantidade,
        "unidadePrazo": unidade,
        "usuarioResponsavelIds": responsavel_ids or [],
        "departamentoResponsavelIds": departamento_ids or [],
    }


_SENTINEL = object()


def _payload(nome: str | None = None, etapas=_SENTINEL, **extra) -> dict:
    return {
        "nome": nome if nome is not None else _nome_unico("Workflow"),
        "etapas": [_etapa()] if etapas is _SENTINEL else etapas,
        **extra,
    }


def _criar_usuario_na_empresa(db: Session, empresa: Empresa, status: str = "ativo") -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"resp-{sufixo}",
        nome=f"Responsável {sufixo}",
        email=f"resp-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _criar_departamento_na_empresa(db: Session, empresa: Empresa, status: str = "ativo"):
    from app.models.departamento import Departamento

    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Departamento {sufixo}",
        nome_normalizado=f"departamento {sufixo}",
        cor_identificacao="blue",
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


# --------------------------------------------------------------------------------------
# Criação, código de referência e etapas
# --------------------------------------------------------------------------------------

def test_criar_workflow_modelo(client_admin: TestClient) -> None:
    resposta = client_admin.post("/workflow-modelos", json=_payload("Criação Teste"))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Criação Teste"
    assert corpo["status"] == "ativo"
    assert corpo["empresaId"]
    assert corpo["codigoInterno"]
    assert len(corpo["etapas"]) == 1


def test_codigo_referencia_no_formato_esperado(client_admin: TestClient) -> None:
    corpo = client_admin.post("/workflow-modelos", json=_payload()).json()
    ano = datetime.now(timezone.utc).year
    assert corpo["codigoReferencia"] == f"W{ano % 100:02d}{corpo['sequencialReferencia']:06d}"
    assert corpo["anoReferencia"] == ano
    assert len(corpo["codigoReferencia"]) == 9


def test_sequencial_avanca_entre_criacoes(client_admin: TestClient) -> None:
    primeiro = client_admin.post("/workflow-modelos", json=_payload()).json()
    segundo = client_admin.post("/workflow-modelos", json=_payload()).json()
    assert segundo["sequencialReferencia"] == primeiro["sequencialReferencia"] + 1


def test_ordenacao_de_etapas_preserva_ordem_de_envio(client_admin: TestClient) -> None:
    etapas = [_etapa("Primeira"), _etapa("Segunda"), _etapa("Terceira")]
    corpo = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas)).json()
    nomes_por_ordem = [e["nome"] for e in sorted(corpo["etapas"], key=lambda e: e["ordem"])]
    assert nomes_por_ordem == ["Primeira", "Segunda", "Terceira"]
    assert [e["ordem"] for e in sorted(corpo["etapas"], key=lambda e: e["ordem"])] == [1, 2, 3]


def test_editar_nome_preserva_etapas(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload(etapas=[_etapa("Única")])).json()
    resposta = client_admin.patch(
        f"/workflow-modelos/{criado['id']}", json={"nome": _nome_unico("Editado")}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["nome"].startswith("Editado")
    assert [e["nome"] for e in corpo["etapas"]] == ["Única"]


def test_editar_substitui_etapas_por_completo(client_admin: TestClient) -> None:
    criado = client_admin.post(
        "/workflow-modelos", json=_payload(etapas=[_etapa("Velha A"), _etapa("Velha B")])
    ).json()
    resposta = client_admin.patch(
        f"/workflow-modelos/{criado['id']}", json={"etapas": [_etapa("Nova Única")]}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert [e["nome"] for e in corpo["etapas"]] == ["Nova Única"]

    # As etapas antigas não sobram órfãs na tabela.
    total = client_admin.get(f"/workflow-modelos/{criado['id']}").json()["etapas"]
    assert len(total) == 1


def test_patch_sem_etapas_no_payload_preserva_etapas_existentes(
    client_admin: TestClient, db_session: Session
) -> None:
    """PATCH que omite `etapas` do payload não pode mexer nas etapas existentes — nem
    apagar, nem substituir por cópias equivalentes. Só compara nome não provaria isso (uma
    troca por etapas com o mesmo nome passaria despercebida); aqui comparamos os IDs
    persistidos antes/depois e a contagem de linhas na tabela, para confirmar que o
    full-replace (`_substituir_etapas`) simplesmente não roda quando `etapas` não vem no
    payload — `exclude_unset=True` em `WorkflowModeloService.update_workflow_modelo`."""
    criado = client_admin.post(
        "/workflow-modelos", json=_payload(etapas=[_etapa("Etapa A"), _etapa("Etapa B")])
    ).json()
    ids_originais = {etapa["id"] for etapa in criado["etapas"]}
    assert len(ids_originais) == 2

    # PATCH só com `status` — `etapas` nem aparece no payload.
    resposta = client_admin.patch(f"/workflow-modelos/{criado['id']}", json={"status": "inativo"})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "inativo"

    ids_apos_patch = {etapa["id"] for etapa in corpo["etapas"]}
    assert ids_apos_patch == ids_originais, "PATCH sem `etapas` não pode substituir nem apagar etapas existentes"

    total_no_banco = db_session.execute(
        text("SELECT count(*) FROM workflow_modelo_etapas WHERE workflow_modelo_id = :w"),
        {"w": criado["id"]},
    ).scalar_one()
    assert total_no_banco == 2

    # Reconfirma via GET independente (não só a resposta do PATCH).
    reconsultado = client_admin.get(f"/workflow-modelos/{criado['id']}").json()
    assert {etapa["id"] for etapa in reconsultado["etapas"]} == ids_originais


# --------------------------------------------------------------------------------------
# Campos gerados, validação de payload
# --------------------------------------------------------------------------------------

def test_payload_com_campos_gerados_e_rejeitado(client_admin: TestClient, empresa: Empresa) -> None:
    proibidos = [
        {"empresaId": empresa.id},
        {"actorUsuarioId": str(uuid.uuid4())},
        {"codigoInterno": "workflow-hackeado"},
        {"codigoReferencia": "W26999999"},
        {"anoReferencia": 2030},
        {"sequencialReferencia": 999},
    ]
    for extra in proibidos:
        resposta = client_admin.post("/workflow-modelos", json=_payload(**extra))
        assert resposta.status_code == 422, f"{extra} deveria ser rejeitado: {resposta.text}"


def test_codigos_sao_imutaveis_no_patch(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    for extra in [
        {"codigoReferencia": "W26999999"},
        {"anoReferencia": 2030},
        {"sequencialReferencia": 999},
        {"codigoInterno": "workflow-outro"},
    ]:
        resposta = client_admin.patch(f"/workflow-modelos/{criado['id']}", json=extra)
        assert resposta.status_code == 422, f"{extra}: {resposta.text}"


def test_nome_vazio_e_rejeitado(client_admin: TestClient) -> None:
    resposta = client_admin.post("/workflow-modelos", json=_payload(nome=""))
    assert resposta.status_code == 422, resposta.text


def test_etapas_vazias_e_rejeitado(client_admin: TestClient) -> None:
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=[]))
    assert resposta.status_code == 422, resposta.text


def test_tipo_de_etapa_invalido_e_rejeitado(client_admin: TestClient) -> None:
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=[_etapa(tipo="invalido")]))
    assert resposta.status_code == 422, resposta.text


def test_unidade_prazo_invalida_e_rejeitada(client_admin: TestClient) -> None:
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=[_etapa(unidade="invalida")]))
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Duplicidade
# --------------------------------------------------------------------------------------

def test_nome_duplicado_ativo_409_simples(client_admin: TestClient) -> None:
    nome = _nome_unico("Duplicado")
    assert client_admin.post("/workflow-modelos", json=_payload(nome)).status_code == 201
    segundo = client_admin.post("/workflow-modelos", json=_payload(nome.upper()))
    assert_erro_simples(segundo, 409)
    assert isinstance(segundo.json()["detail"], str)


def test_nome_de_arquivado_409_padronizado(client_admin: TestClient) -> None:
    nome = _nome_unico("Arquivado")
    criado = client_admin.post("/workflow-modelos", json=_payload(nome)).json()
    client_admin.post(f"/workflow-modelos/{criado['id']}/arquivar", json={"motivoArquivamento": "teste"})

    tentativa = client_admin.post("/workflow-modelos", json=_payload(nome))
    detail = assert_conflito_arquivado(tentativa, code="WORKFLOW_MODELO_ARQUIVADO_EXISTENTE")
    assert detail["workflowModeloArquivadoId"] == criado["id"]


# --------------------------------------------------------------------------------------
# Ciclo de vida
# --------------------------------------------------------------------------------------

def test_arquivar_sem_motivo_422(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    assert client_admin.post(f"/workflow-modelos/{criado['id']}/arquivar", json={}).status_code == 422


def test_arquivar_valido_preserva_etapas(client_admin: TestClient, db_session: Session) -> None:
    criado = client_admin.post(
        "/workflow-modelos", json=_payload(etapas=[_etapa("A"), _etapa("B")])
    ).json()
    resposta = client_admin.post(
        f"/workflow-modelos/{criado['id']}/arquivar", json={"motivoArquivamento": "não usado mais"}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "arquivado"
    assert corpo["motivoArquivamento"] == "não usado mais"
    assert corpo["arquivadoAt"] is not None
    assert corpo["codigoReferencia"] == criado["codigoReferencia"]

    total = db_session.execute(
        text("SELECT count(*) FROM workflow_modelo_etapas WHERE workflow_modelo_id = :w"),
        {"w": criado["id"]},
    ).scalar_one()
    assert total == 2, "arquivar não pode apagar etapas"


def test_arquivar_ja_arquivado_409(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    client_admin.post(f"/workflow-modelos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    segunda = client_admin.post(f"/workflow-modelos/{criado['id']}/arquivar", json={"motivoArquivamento": "y"})
    assert_erro_simples(segunda, 409)


def test_restaurar(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    client_admin.post(f"/workflow-modelos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.post(f"/workflow-modelos/{criado['id']}/restaurar")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "ativo"
    assert corpo["codigoReferencia"] == criado["codigoReferencia"]


def test_restaurar_nao_arquivado_409(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    resposta = client_admin.post(f"/workflow-modelos/{criado['id']}/restaurar")
    assert_erro_simples(resposta, 409)


# --------------------------------------------------------------------------------------
# Listagem, filtro e busca
# --------------------------------------------------------------------------------------

def test_listagem_padrao_exclui_arquivado(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    client_admin.post(f"/workflow-modelos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    ids = [w["id"] for w in client_admin.get("/workflow-modelos").json()]
    assert criado["id"] not in ids


def test_filtro_status_arquivado(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    client_admin.post(f"/workflow-modelos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    ids = [w["id"] for w in client_admin.get("/workflow-modelos", params={"status": "arquivado"}).json()]
    assert criado["id"] in ids


def test_busca_por_codigo_referencia_case_insensitive(client_admin: TestClient) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    codigo = criado["codigoReferencia"]
    for termo in (codigo, codigo.lower()):
        encontrados = client_admin.get("/workflow-modelos", params={"search": termo}).json()
        assert any(w["id"] == criado["id"] for w in encontrados), f"não achou com {termo!r}"


def test_busca_por_nome(client_admin: TestClient) -> None:
    nome = _nome_unico("Buscavel")
    criado = client_admin.post("/workflow-modelos", json=_payload(nome)).json()
    encontrados = client_admin.get("/workflow-modelos", params={"search": nome}).json()
    assert any(w["id"] == criado["id"] for w in encontrados)


# --------------------------------------------------------------------------------------
# Responsável de etapa
# --------------------------------------------------------------------------------------

def test_responsavel_de_etapa_da_mesma_empresa_e_aceito(
    client_admin: TestClient, usuario_gestor: Usuario
) -> None:
    etapas = [_etapa(responsavel_ids=[usuario_gestor.id])]
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas))
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["etapas"][0]["usuarioResponsavelIds"] == [usuario_gestor.id]


def test_responsavel_de_etapa_cross_tenant_422(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    forasteiro = _criar_usuario_na_empresa(db_session, outra_empresa)
    etapas = [_etapa(responsavel_ids=[forasteiro.id])]
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas))
    assert resposta.status_code == 422, resposta.text


def test_responsavel_de_etapa_arquivado_nao_pode_ser_definido(
    client_admin: TestClient, usuario_operador: Usuario, db_session: Session
) -> None:
    usuario_operador.status = "arquivado"
    db_session.flush()
    etapas = [_etapa(responsavel_ids=[usuario_operador.id])]
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas))
    assert resposta.status_code == 422, resposta.text


def test_responsavel_de_etapa_continua_resolvendo_apos_inativacao(
    client_admin: TestClient, usuario_gestor: Usuario, db_session: Session
) -> None:
    """Vínculo histórico: definido enquanto o usuário estava ativo, permanece depois."""
    etapas = [_etapa(responsavel_ids=[usuario_gestor.id])]
    criado = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas)).json()

    usuario_gestor.status = "inativo"
    db_session.flush()

    atual = client_admin.get(f"/workflow-modelos/{criado['id']}").json()
    assert atual["etapas"][0]["usuarioResponsavelIds"] == [usuario_gestor.id]


# --------------------------------------------------------------------------------------
# Departamento responsável de etapa
# --------------------------------------------------------------------------------------

def test_departamento_responsavel_de_etapa_da_mesma_empresa_e_aceito(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _criar_departamento_na_empresa(db_session, empresa)
    etapas = [_etapa(departamento_ids=[departamento.id])]
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas))
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["etapas"][0]["departamentoResponsavelIds"] == [departamento.id]


def test_departamento_responsavel_de_etapa_cross_tenant_422(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    departamento_alheio = _criar_departamento_na_empresa(db_session, outra_empresa)
    etapas = [_etapa(departamento_ids=[departamento_alheio.id])]
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas))
    assert resposta.status_code == 422, resposta.text


def test_departamento_responsavel_de_etapa_arquivado_nao_pode_ser_definido(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _criar_departamento_na_empresa(db_session, empresa, status="arquivado")
    etapas = [_etapa(departamento_ids=[departamento.id])]
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas))
    assert resposta.status_code == 422, resposta.text


def test_departamento_responsavel_de_etapa_inativo_e_aceito(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Mesmo critério de Demanda: só arquivado bloqueia vínculo novo — inativo não."""
    departamento = _criar_departamento_na_empresa(db_session, empresa, status="inativo")
    etapas = [_etapa(departamento_ids=[departamento.id])]
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas))
    assert resposta.status_code == 201, resposta.text


def test_usuario_e_departamento_responsaveis_convivem_na_mesma_etapa(
    client_admin: TestClient, usuario_gestor: Usuario, db_session: Session, empresa: Empresa
) -> None:
    departamento = _criar_departamento_na_empresa(db_session, empresa)
    etapas = [_etapa(responsavel_ids=[usuario_gestor.id], departamento_ids=[departamento.id])]
    resposta = client_admin.post("/workflow-modelos", json=_payload(etapas=etapas))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()["etapas"][0]
    assert corpo["usuarioResponsavelIds"] == [usuario_gestor.id]
    assert corpo["departamentoResponsavelIds"] == [departamento.id]


def test_editar_substitui_departamentos_responsaveis_por_completo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    dep_a = _criar_departamento_na_empresa(db_session, empresa)
    dep_b = _criar_departamento_na_empresa(db_session, empresa)
    criado = client_admin.post(
        "/workflow-modelos", json=_payload(etapas=[_etapa(departamento_ids=[dep_a.id])])
    ).json()

    resposta = client_admin.patch(
        f"/workflow-modelos/{criado['id']}", json={"etapas": [_etapa(departamento_ids=[dep_b.id])]}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["etapas"][0]["departamentoResponsavelIds"] == [dep_b.id]


# --------------------------------------------------------------------------------------
# Isolamento por empresa e autorização
# --------------------------------------------------------------------------------------

def _workflow_modelo_de_outra_empresa(db_session: Session, outra_empresa: Empresa) -> str:
    from app.models.workflow_modelo import WorkflowModelo

    agora = datetime.now(timezone.utc)
    alheio = WorkflowModelo(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"workflow-alheio-{uuid.uuid4().hex[:8]}",
        codigo_referencia=f"W26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome="Workflow de Outra Empresa",
        nome_normalizado=f"workflow outra empresa {uuid.uuid4().hex[:6]}",
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
    alheio_id = _workflow_modelo_de_outra_empresa(db_session, outra_empresa)

    assert client_admin.get(f"/workflow-modelos/{alheio_id}").status_code == 404
    assert client_admin.patch(f"/workflow-modelos/{alheio_id}", json={"nome": "Tentativa"}).status_code == 404
    assert (
        client_admin.post(f"/workflow-modelos/{alheio_id}/arquivar", json={"motivoArquivamento": "x"}).status_code
        == 404
    )
    assert client_admin.post(f"/workflow-modelos/{alheio_id}/restaurar").status_code == 404

    assert all(w["id"] != alheio_id for w in client_admin.get("/workflow-modelos").json())


def test_operador_le_detalhe_completo_para_previa_na_selecao(
    client_operador: TestClient, client_admin: TestClient
) -> None:
    """GET /{id} é aberto (diferente de GET "" e do CRUD): quem pode criar Demanda precisa
    ver as etapas do workflow escolhido antes de aplicar — não só nome/id do diretório."""
    criado = client_admin.post("/workflow-modelos", json=_payload(etapas=[_etapa("Etapa")])).json()
    resposta = client_operador.get(f"/workflow-modelos/{criado['id']}")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["etapas"][0]["nome"] == "Etapa"


def test_operador_le_detalhe_completo_cross_tenant_404(
    client_operador: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    alheio_id = _workflow_modelo_de_outra_empresa(db_session, outra_empresa)
    assert client_operador.get(f"/workflow-modelos/{alheio_id}").status_code == 404


def test_sem_token_401(client: TestClient) -> None:
    assert client.get("/workflow-modelos").status_code == 401
    assert client.post("/workflow-modelos", json=_payload()).status_code == 401


def test_operador_403_gestor_pode(client_operador: TestClient, client_gestor: TestClient) -> None:
    assert client_operador.post("/workflow-modelos", json=_payload()).status_code == 403
    assert client_gestor.post("/workflow-modelos", json=_payload()).status_code == 201


def test_operador_403_nas_demais_rotas_de_escrita(
    client_operador: TestClient, client_admin: TestClient
) -> None:
    criado = client_admin.post("/workflow-modelos", json=_payload()).json()
    assert client_operador.get("/workflow-modelos").status_code == 403
    assert client_operador.patch(f"/workflow-modelos/{criado['id']}", json={"nome": "X"}).status_code == 403
    assert (
        client_operador.post(
            f"/workflow-modelos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"}
        ).status_code
        == 403
    )
    assert client_operador.post(f"/workflow-modelos/{criado['id']}/restaurar").status_code == 403


# --------------------------------------------------------------------------------------
# Contador e concorrência
# --------------------------------------------------------------------------------------

def test_falha_na_criacao_nao_queima_numero(db_session: Session, empresa: Empresa) -> None:
    """Nome duplicado aborta antes do commit — o contador não avança."""
    from app.schemas.workflow_modelo import WorkflowModeloCreate
    from app.services.workflow_modelo_service import WorkflowModeloConflictError, WorkflowModeloService

    service = WorkflowModeloService()
    nome = _nome_unico("RollbackContador")
    service.create_workflow_modelo(
        db_session,
        WorkflowModeloCreate(nome=nome, etapas=[_etapa()]),
        empresa_id=empresa.id,
        actor_usuario_id=None,
    )
    antes = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_referencia "
            "WHERE empresa_id = :e AND tipo_entidade = 'workflow_modelo'"
        ),
        {"e": empresa.id},
    ).scalar_one()

    try:
        service.create_workflow_modelo(
            db_session,
            WorkflowModeloCreate(nome=nome, etapas=[_etapa()]),
            empresa_id=empresa.id,
            actor_usuario_id=None,
        )
        raise AssertionError("deveria ter levantado conflito")
    except WorkflowModeloConflictError:
        pass

    depois = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_referencia "
            "WHERE empresa_id = :e AND tipo_entidade = 'workflow_modelo'"
        ),
        {"e": empresa.id},
    ).scalar_one()
    assert depois == antes, "criação falha não pode queimar número da sequência"


def test_concorrencia_nome_duplicado_vira_conflito_tratado(db_session: Session, empresa: Empresa) -> None:
    """Insere direto pelo repository (bypassando os checks) e então cria pelo service com o
    mesmo nome: o IntegrityError precisa virar conflito tratado, não vazar."""
    from app.models.workflow_modelo import WorkflowModelo
    from app.schemas.workflow_modelo import WorkflowModeloCreate
    from app.services.workflow_modelo_service import (
        WorkflowModeloArquivadoConflictError,
        WorkflowModeloConflictError,
        WorkflowModeloService,
    )

    nome = _nome_unico("Corrida")
    agora = datetime.now(timezone.utc)
    existente = WorkflowModelo(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"workflow-corrida-{uuid.uuid4().hex[:8]}",
        codigo_referencia=f"W26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=nome,
        nome_normalizado=nome.strip().lower(),
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(existente)
    db_session.flush()

    service = WorkflowModeloService()
    try:
        service.create_workflow_modelo(
            db_session,
            WorkflowModeloCreate(nome=nome, etapas=[_etapa()]),
            empresa_id=empresa.id,
            actor_usuario_id=None,
        )
        raise AssertionError("deveria ter levantado conflito")
    except (WorkflowModeloConflictError, WorkflowModeloArquivadoConflictError):
        pass
