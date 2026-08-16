"""Integração Workflow ↔ Demanda (Fase 2E.2) — materialização de etapas na criação.

Ver DemandaService._materializar_workflow / _ensure_workflow_modelo_valido.

`WorkflowModelo` é o template; `demanda_workflow_etapas` é o snapshot aplicado no momento da
criação — os testes provam especificamente que editar/arquivar o template DEPOIS não altera
uma Demanda já criada, que é o requisito central desta fase.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario


def _nome_unico(prefixo: str) -> str:
    return f"{prefixo} {uuid.uuid4().hex[:8]}"


def _departamento(db: Session, empresa: Empresa, *, status: str = "ativo") -> Departamento:
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


def _etapa(nome: str = "Etapa 1", responsavel_ids: list[str] | None = None, departamento_ids: list[str] | None = None) -> dict:
    return {
        "nome": nome,
        "tipo": "execucao",
        "quantidadeAntesDeadline": 1,
        "unidadePrazo": "dias_corridos",
        "usuarioResponsavelIds": responsavel_ids or [],
        "departamentoResponsavelIds": departamento_ids or [],
    }


def _criar_workflow_modelo(client: TestClient, *, etapas: list[dict], nome: str | None = None) -> dict:
    resposta = client.post("/workflow-modelos", json={"nome": nome or _nome_unico("Workflow"), "etapas": etapas})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_demanda(client: TestClient, **extra) -> dict:
    payload = {"nome": _nome_unico("Demanda"), **extra}
    return client.post("/demandas", json=payload)


# --------------------------------------------------------------------------------------
# Sem workflow — compatibilidade
# --------------------------------------------------------------------------------------

def test_criar_demanda_sem_workflow_continua_funcionando(client_admin: TestClient) -> None:
    resposta = _criar_demanda(client_admin)
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["workflowModeloId"] is None
    assert corpo["workflowEtapas"] == []
    assert corpo["etapaAtualId"] is None


# --------------------------------------------------------------------------------------
# Materialização — caminho feliz
# --------------------------------------------------------------------------------------

def test_criar_demanda_com_workflow_materializa_etapas_e_responsaveis(
    client_admin: TestClient, usuario_gestor: Usuario, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    etapas = [
        _etapa("Primeira", responsavel_ids=[usuario_gestor.id], departamento_ids=[departamento.id]),
        _etapa("Segunda"),
        _etapa("Terceira"),
    ]
    modelo = _criar_workflow_modelo(client_admin, etapas=etapas)

    resposta = _criar_demanda(client_admin, workflowModeloId=modelo["id"])
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()

    assert corpo["workflowModeloId"] == modelo["id"]
    assert len(corpo["workflowEtapas"]) == 3
    nomes_por_ordem = [e["nome"] for e in sorted(corpo["workflowEtapas"], key=lambda e: e["ordem"])]
    assert nomes_por_ordem == ["Primeira", "Segunda", "Terceira"]

    primeira = next(e for e in corpo["workflowEtapas"] if e["nome"] == "Primeira")
    assert primeira["usuarioResponsavelIds"] == [usuario_gestor.id]
    assert primeira["departamentoResponsavelIds"] == [departamento.id]
    assert primeira["status"] == "pendente"

    # Etapa atual = menor ordem com status != concluida → a primeira.
    assert corpo["etapaAtualId"] == primeira["id"]


def test_etapas_materializadas_tem_ids_proprios_distintos_do_template(
    client_admin: TestClient,
) -> None:
    modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa("Única")])
    resposta = _criar_demanda(client_admin, workflowModeloId=modelo["id"])
    corpo = resposta.json()
    etapa_demanda_id = corpo["workflowEtapas"][0]["id"]
    etapa_template_id = modelo["etapas"][0]["id"]
    assert etapa_demanda_id != etapa_template_id


def test_etapa_atual_todas_concluidas_e_null(
    client_admin: TestClient, db_session: Session
) -> None:
    modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa("A"), _etapa("B")])
    criada = _criar_demanda(client_admin, workflowModeloId=modelo["id"]).json()

    db_session.execute(
        text("UPDATE demanda_workflow_etapas SET status = 'concluida' WHERE demanda_id = :d"),
        {"d": criada["id"]},
    )
    db_session.flush()

    atual = client_admin.get(f"/demandas/{criada['id']}").json()
    assert atual["etapaAtualId"] is None


def test_etapa_atual_pula_concluidas(client_admin: TestClient, db_session: Session) -> None:
    modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa("A"), _etapa("B"), _etapa("C")])
    criada = _criar_demanda(client_admin, workflowModeloId=modelo["id"]).json()
    primeira_id = next(e["id"] for e in criada["workflowEtapas"] if e["nome"] == "A")

    db_session.execute(
        text("UPDATE demanda_workflow_etapas SET status = 'concluida' WHERE id = :e"),
        {"e": primeira_id},
    )
    db_session.flush()

    atual = client_admin.get(f"/demandas/{criada['id']}").json()
    segunda_id = next(e["id"] for e in criada["workflowEtapas"] if e["nome"] == "B")
    assert atual["etapaAtualId"] == segunda_id


# --------------------------------------------------------------------------------------
# WorkflowModelo inválido para aplicação
# --------------------------------------------------------------------------------------

def test_workflow_inativo_e_rejeitado(client_admin: TestClient) -> None:
    modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa()])
    client_admin.patch(f"/workflow-modelos/{modelo['id']}", json={"status": "inativo"})

    resposta = _criar_demanda(client_admin, workflowModeloId=modelo["id"])
    assert resposta.status_code == 422, resposta.text


def test_workflow_arquivado_e_rejeitado(client_admin: TestClient) -> None:
    modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa()])
    client_admin.post(f"/workflow-modelos/{modelo['id']}/arquivar", json={"motivoArquivamento": "x"})

    resposta = _criar_demanda(client_admin, workflowModeloId=modelo["id"])
    assert resposta.status_code == 422, resposta.text


def test_workflow_de_outra_empresa_e_rejeitado(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    from app.models.workflow_modelo import WorkflowModelo

    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    alheio = WorkflowModelo(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"workflow-{sufixo}",
        codigo_referencia=f"W26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Workflow Alheio {sufixo}",
        nome_normalizado=f"workflow alheio {sufixo}",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(alheio)
    db_session.flush()

    resposta = _criar_demanda(client_admin, workflowModeloId=alheio.id)
    assert resposta.status_code == 422, resposta.text


def test_workflow_inexistente_e_rejeitado(client_admin: TestClient) -> None:
    resposta = _criar_demanda(client_admin, workflowModeloId=str(uuid.uuid4()))
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Responsável do template inválido no momento da aplicação (não na edição do template)
# --------------------------------------------------------------------------------------

def test_responsavel_usuario_do_template_arquivado_apos_edicao_rejeita_aplicacao(
    client_admin: TestClient, usuario_operador: Usuario, db_session: Session
) -> None:
    modelo = _criar_workflow_modelo(
        client_admin, etapas=[_etapa("Com responsável", responsavel_ids=[usuario_operador.id])]
    )
    # O responsável era válido quando o template foi salvo; fica inválido depois.
    usuario_operador.status = "arquivado"
    db_session.flush()

    antes = db_session.execute(text("SELECT count(*) FROM demandas")).scalar_one()
    etapas_antes = db_session.execute(text("SELECT count(*) FROM demanda_workflow_etapas")).scalar_one()

    resposta = _criar_demanda(client_admin, workflowModeloId=modelo["id"])
    assert resposta.status_code == 422, resposta.text

    # Nem a Demanda nem a etapa sobrevivem — mesma transação, rollback único.
    depois = db_session.execute(text("SELECT count(*) FROM demandas")).scalar_one()
    etapas_depois = db_session.execute(text("SELECT count(*) FROM demanda_workflow_etapas")).scalar_one()
    assert depois == antes, "demanda não pode sobreviver quando a materialização falha"
    assert etapas_depois == etapas_antes, "etapa não pode sobreviver órfã quando a materialização falha"


def test_responsavel_departamento_do_template_arquivado_apos_edicao_rejeita_aplicacao(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    modelo = _criar_workflow_modelo(
        client_admin, etapas=[_etapa("Com departamento", departamento_ids=[departamento.id])]
    )
    departamento.status = "arquivado"
    db_session.flush()

    resposta = _criar_demanda(client_admin, workflowModeloId=modelo["id"])
    assert resposta.status_code == 422, resposta.text


def test_responsavel_de_etapa_cross_tenant_no_momento_da_criacao(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    """Edge case improvável (o template só aceitava responsável da própria empresa ao ser
    salvo) mas cobrimos a mesma defesa que create_demanda já aplica a responsável direto:
    revalidar no momento da aplicação, não confiar cegamente no que o template guardava."""
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    forasteiro = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"forasteiro-{sufixo}",
        nome="Forasteiro",
        email=f"forasteiro-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(forasteiro)
    db_session.flush()

    modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa("Etapa")])
    # Injeta o responsável cross-tenant direto no template, contornando a validação de
    # criação do WorkflowModelo (que já bloquearia isso) — simula o cenário real: alguém
    # trocou de empresa depois que o vínculo foi criado. Fora do escopo deste teste
    # provocar isso via API; mexe direto na tabela do template.
    etapa_id = modelo["etapas"][0]["id"]
    db_session.execute(
        text(
            "INSERT INTO workflow_modelo_etapa_responsaveis (workflow_modelo_etapa_id, usuario_id, created_at) "
            "VALUES (:e, :u, :now)"
        ),
        {"e": etapa_id, "u": forasteiro.id, "now": agora},
    )
    db_session.flush()

    resposta = _criar_demanda(client_admin, workflowModeloId=modelo["id"])
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Snapshot: editar/arquivar o template depois não muda a Demanda já criada
# --------------------------------------------------------------------------------------

def test_editar_workflow_depois_nao_altera_demanda_existente(
    client_admin: TestClient, usuario_gestor: Usuario, usuario_operador: Usuario
) -> None:
    modelo = _criar_workflow_modelo(
        client_admin, etapas=[_etapa("Original", responsavel_ids=[usuario_gestor.id])]
    )
    criada = _criar_demanda(client_admin, workflowModeloId=modelo["id"]).json()
    etapa_original_id = criada["workflowEtapas"][0]["id"]

    # Edita o template por completo: nome do modelo, nome da etapa e responsável.
    client_admin.patch(
        f"/workflow-modelos/{modelo['id']}",
        json={
            "nome": "Nome Totalmente Novo",
            "etapas": [_etapa("Etapa Renomeada", responsavel_ids=[usuario_operador.id])],
        },
    )

    atual = client_admin.get(f"/demandas/{criada['id']}").json()
    assert len(atual["workflowEtapas"]) == 1
    assert atual["workflowEtapas"][0]["id"] == etapa_original_id
    assert atual["workflowEtapas"][0]["nome"] == "Original"
    assert atual["workflowEtapas"][0]["usuarioResponsavelIds"] == [usuario_gestor.id]


def test_arquivar_workflow_depois_nao_afeta_demanda_existente(client_admin: TestClient) -> None:
    modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa("Etapa")])
    criada = _criar_demanda(client_admin, workflowModeloId=modelo["id"]).json()

    resposta = client_admin.post(f"/workflow-modelos/{modelo['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert resposta.status_code == 200, resposta.text

    atual = client_admin.get(f"/demandas/{criada['id']}").json()
    assert atual["status"] != "arquivada"
    assert len(atual["workflowEtapas"]) == 1
    assert atual["workflowModeloId"] == modelo["id"]


# --------------------------------------------------------------------------------------
# GET /workflow-modelos/diretorio
# --------------------------------------------------------------------------------------

def test_diretorio_so_lista_ativo(client_admin: TestClient) -> None:
    ativo = _criar_workflow_modelo(client_admin, etapas=[_etapa()])
    inativo_modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa()])
    client_admin.patch(f"/workflow-modelos/{inativo_modelo['id']}", json={"status": "inativo"})
    arquivado_modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa()])
    client_admin.post(f"/workflow-modelos/{arquivado_modelo['id']}/arquivar", json={"motivoArquivamento": "x"})

    diretorio = client_admin.get("/workflow-modelos/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    ids = [item["id"] for item in diretorio.json()]
    assert ativo["id"] in ids
    assert inativo_modelo["id"] not in ids
    assert arquivado_modelo["id"] not in ids


def test_diretorio_nao_expoe_etapas(client_admin: TestClient) -> None:
    modelo = _criar_workflow_modelo(client_admin, etapas=[_etapa()])
    diretorio = client_admin.get("/workflow-modelos/diretorio").json()
    item = next(w for w in diretorio if w["id"] == modelo["id"])
    assert "etapas" not in item


def test_operador_acessa_diretorio_para_selecionar_workflow(client_operador: TestClient) -> None:
    """Selecionar workflow ao criar tarefa não é administrar Workflow — mesmo tier de leitura
    de Demanda, aberto a qualquer autenticado."""
    resposta = client_operador.get("/workflow-modelos/diretorio")
    assert resposta.status_code == 200, resposta.text


def test_diretorio_isola_por_empresa(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    from app.models.workflow_modelo import WorkflowModelo

    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    alheio = WorkflowModelo(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"workflow-{sufixo}",
        codigo_referencia=f"W26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Workflow Alheio {sufixo}",
        nome_normalizado=f"workflow alheio {sufixo}",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(alheio)
    db_session.flush()

    diretorio = client_admin.get("/workflow-modelos/diretorio").json()
    assert all(item["id"] != alheio.id for item in diretorio)


def test_operador_continua_sem_acesso_a_administracao_de_workflow(client_operador: TestClient) -> None:
    assert client_operador.post("/workflow-modelos", json={"nome": "X", "etapas": [_etapa()]}).status_code == 403
    assert client_operador.get("/workflow-modelos").status_code == 403
