"""Histórico de Demanda (Fase 2E.4) — leitura escopada da timeline, sem tabela própria.

Reaproveita `eventos`, já existente desde a fundação da auditoria — a prova central deste
domínio é que NENHUM evento novo precisa de código de leitura dedicado: publicar com
`entidade_tipo="demanda"`/`entidade_id=demanda.id` já basta para aparecer aqui.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.empresa import Empresa


def _nome_unico(prefixo: str) -> str:
    return f"{prefixo} {uuid.uuid4().hex[:8]}"


def _etapa() -> dict:
    return {
        "nome": "Etapa 1",
        "tipo": "execucao",
        "quantidadeAntesDeadline": 1,
        "unidadePrazo": "dias_corridos",
        "usuarioResponsavelIds": [],
        "departamentoResponsavelIds": [],
    }


def _criar_workflow_modelo(client: TestClient) -> dict:
    resposta = client.post(
        "/workflow-modelos", json={"nome": _nome_unico("Workflow"), "etapas": [_etapa()]}
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": _nome_unico("Demanda"), **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _tipos(historico: list[dict]) -> list[str]:
    return [item["tipo"] for item in historico]


# --------------------------------------------------------------------------------------
# Conteúdo e escopo
# --------------------------------------------------------------------------------------

def test_historico_contem_eventos_da_propria_demanda(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.get(f"/demandas/{demanda['id']}/historico")
    assert resposta.status_code == 200
    tipos = _tipos(resposta.json())
    assert "demanda.criada" in tipos


def test_historico_nao_mistura_eventos_de_outra_demanda(client_admin: TestClient) -> None:
    demanda_a = _criar_demanda(client_admin)
    demanda_b = _criar_demanda(client_admin)

    client_admin.post(f"/demandas/{demanda_a['id']}/checklist", json={"texto": "Item de A"})

    historico_b = client_admin.get(f"/demandas/{demanda_b['id']}/historico").json()
    assert "demanda.checklist_item_criado" not in _tipos(historico_b)

    historico_a = client_admin.get(f"/demandas/{demanda_a['id']}/historico").json()
    assert "demanda.checklist_item_criado" in _tipos(historico_a)


def test_demanda_inexistente_devolve_404(client_admin: TestClient) -> None:
    assert client_admin.get(f"/demandas/{uuid.uuid4()}/historico").status_code == 404


def test_operador_sem_escopo_recebe_404(client_admin: TestClient, client_operador: TestClient) -> None:
    alheia = _criar_demanda(client_admin)
    assert client_operador.get(f"/demandas/{alheia['id']}/historico").status_code == 404


def test_operador_com_escopo_le_historico(
    client_admin: TestClient, client_operador: TestClient, usuario_operador
) -> None:
    minha = _criar_demanda(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    resposta = client_operador.get(f"/demandas/{minha['id']}/historico")
    assert resposta.status_code == 200


def test_operador_continua_sem_acesso_ao_eventos_global(client_operador: TestClient) -> None:
    """A rota nova nunca deve virar uma porta lateral para a auditoria administrativa."""
    assert client_operador.get("/eventos").status_code == 403


def test_demanda_de_outra_empresa_devolve_404(client_admin: TestClient, db_session: Session) -> None:
    agora = datetime.now(timezone.utc)
    outra = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa Historico",
        documento=None,
        codigo_interno=f"HIS-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(outra)
    db_session.flush()

    intrusa = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        codigo_referencia="T26005555",
        ano_referencia=26,
        sequencial_referencia=5555,
        numero_operacional=5555,
        nome="Demanda de outra empresa",
        status="rascunho",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(intrusa)
    db_session.flush()

    assert client_admin.get(f"/demandas/{intrusa.id}/historico").status_code == 404


# --------------------------------------------------------------------------------------
# Ordenação
# --------------------------------------------------------------------------------------

def test_ordenacao_mais_recente_primeiro(client_admin: TestClient) -> None:
    """Mesmo comportamento visual que RegistrarAjusteCard/EnvioClienteCard já tinham no
    mock (prepend do evento novo no topo) — ver instrução da fase, item 13."""
    demanda = _criar_demanda(client_admin)
    client_admin.post(f"/demandas/{demanda['id']}/checklist", json={"texto": "Item 1"})
    client_admin.post(f"/demandas/{demanda['id']}/checklist", json={"texto": "Item 2"})

    historico = client_admin.get(f"/demandas/{demanda['id']}/historico").json()
    ocorrencias = [item["occurredAt"] for item in historico]
    assert ocorrencias == sorted(ocorrencias, reverse=True)
    # O mais recente (segundo item de checklist criado) aparece antes da criação da Demanda.
    assert historico[0]["tipo"] == "demanda.checklist_item_criado"
    assert historico[-1]["tipo"] == "demanda.criada"


# --------------------------------------------------------------------------------------
# Cobertura de domínios que já publicam evento
# --------------------------------------------------------------------------------------

def test_checklist_e_arquivos_aparecem_na_mesma_timeline(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    client_admin.post(f"/demandas/{demanda['id']}/checklist", json={"texto": "Item"})
    client_admin.post(
        f"/demandas/{demanda['id']}/arquivos",
        files={"file": ("teste.pdf", b"%PDF-1.4 conteudo", "application/pdf")},
    )

    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert "demanda.checklist_item_criado" in tipos
    assert "demanda.arquivo_enviado" in tipos


def test_workflow_aplicado_aparece_na_timeline(client_admin: TestClient) -> None:
    modelo = _criar_workflow_modelo(client_admin)
    demanda = _criar_demanda(client_admin, workflowModeloId=modelo["id"])

    historico = client_admin.get(f"/demandas/{demanda['id']}/historico").json()
    evento_workflow = next((item for item in historico if item["tipo"] == "demanda.workflow_aplicado"), None)
    assert evento_workflow is not None
    assert evento_workflow["dados"]["workflowModeloId"] == modelo["id"]


def test_workflow_aplicado_nao_aparece_em_demanda_sem_workflow(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert "demanda.workflow_aplicado" not in tipos


def test_ajuste_registrado_aparece_na_timeline(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.post(f"/demandas/{demanda['id']}/ajustes", json={"tipo": "refacao"})
    assert resposta.status_code == 201, resposta.text

    tipos = _tipos(client_admin.get(f"/demandas/{demanda['id']}/historico").json())
    assert "demanda.refacao_registrada" in tipos


# --------------------------------------------------------------------------------------
# Forma da resposta — sem internals de auditoria
# --------------------------------------------------------------------------------------

def test_payload_nao_expoe_internals_do_evento(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    historico = client_admin.get(f"/demandas/{demanda['id']}/historico").json()
    assert len(historico) > 0
    for item in historico:
        assert set(item.keys()) == {"id", "tipo", "usuarioId", "occurredAt", "dados"}
        assert "correlationId" not in item
        assert "causationId" not in item
        assert "metadata" not in item
        assert "empresaId" not in item
        assert "entidadeTipo" not in item
        assert "entidadeId" not in item


def test_usuario_inexistente_no_evento_nao_quebra_leitura(
    client_admin: TestClient, db_session: Session
) -> None:
    """`Evento.usuario_id` não tem FK (ver app/models/evento.py) — a leitura nunca falha por
    causa de um usuário removido depois; resolver o nome de exibição é responsabilidade do
    frontend (ver instrução da fase, item 9)."""
    from app.models.evento import Evento

    demanda = _criar_demanda(client_admin)
    agora = datetime.now(timezone.utc)
    evento_orfao = Evento(
        id=str(uuid.uuid4()),
        empresa_id=demanda["empresaId"],
        tipo="demanda.alterada",
        entidade_tipo="demanda",
        entidade_id=demanda["id"],
        usuario_id=str(uuid.uuid4()),  # nunca existiu
        payload={"camposAlterados": ["nome"]},
        occurred_at=agora,
        created_at=agora,
    )
    db_session.add(evento_orfao)
    db_session.flush()

    resposta = client_admin.get(f"/demandas/{demanda['id']}/historico")
    assert resposta.status_code == 200
    encontrado = next(item for item in resposta.json() if item["id"] == evento_orfao.id)
    assert encontrado["usuarioId"] == evento_orfao.usuario_id
