"""Testes operacionais do snapshot de Modelo de Campanha em Projeto (Fase 2G.5C2) — aplicar,
reaplicar, ler e editar via API real. Complementa test_projeto_modelo_campanha.py (que cobre
só schema/model)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.modelo_campanha import ModeloCampanha, ModeloCampanhaItem
from app.models.peca import Peca
from app.models.projeto import Projeto
from app.models.projeto_modelo_campanha import ProjetoModeloCampanha, ProjetoModeloCampanhaItem
from app.models.tipo_tarefa import TipoTarefa
from app.models.workflow_modelo import WorkflowModelo
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.helpers.assertions import assert_erro_simples


# --------------------------------------------------------------------------------------
# Fábricas diretas no model — mesmo padrão de test_projeto_modelo_campanha.py e
# test_modelo_campanha.py
# --------------------------------------------------------------------------------------


def _projeto(db: Session, empresa: Empresa) -> Projeto:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    projeto = Projeto(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_referencia=f"P26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Projeto {sufixo}",
        nome_normalizado=f"projeto {sufixo}",
        status="planejamento",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db.add(projeto)
    db.flush()
    return projeto


def _modelo_campanha(db: Session, empresa: Empresa, *, status: str = "ativo") -> ModeloCampanha:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    modelo = ModeloCampanha(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        nome=f"Modelo {sufixo}",
        nome_normalizado=f"modelo {sufixo}",
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(modelo)
    db.flush()
    return modelo


def _modelo_item(db: Session, modelo: ModeloCampanha, *, ordem: int, **overrides) -> ModeloCampanhaItem:
    agora = datetime.now(timezone.utc)
    defaults = dict(
        id=str(uuid.uuid4()),
        modelo_campanha_id=modelo.id,
        ordem=ordem,
        nome=f"Item Modelo {ordem}",
        briefing_padrao=None,
        prioridade_padrao="media",
        peca_id=None,
        tipo_tarefa_id=None,
        workflow_modelo_id=None,
        responsavel_usuario_id=None,
        responsavel_departamento_id=None,
        created_at=agora,
        updated_at=agora,
    )
    defaults.update(overrides)
    item = ModeloCampanhaItem(**defaults)
    db.add(item)
    db.flush()
    return item


def _peca(db: Session, empresa: Empresa, *, status: str = "ativo") -> Peca:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    peca = Peca(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        categoria_id=None,
        nome=f"Peça {sufixo}",
        codigo_legado=None,
        briefing_padrao="",
        sindicato_ativo=False,
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(peca)
    db.flush()
    return peca


def _tipo_tarefa(db: Session, empresa: Empresa, *, status: str = "ativo") -> TipoTarefa:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    tipo = TipoTarefa(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        nome=f"Tipo {sufixo}",
        nome_normalizado=f"tipo {sufixo}",
        ordem=0,
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(tipo)
    db.flush()
    return tipo


def _workflow_modelo(db: Session, empresa: Empresa, *, status: str = "ativo") -> WorkflowModelo:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    workflow = WorkflowModelo(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"wf-{sufixo}",
        codigo_referencia=f"W26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Workflow {sufixo}",
        nome_normalizado=f"workflow {sufixo}",
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(workflow)
    db.flush()
    return workflow


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


def _usuario(db: Session, empresa: Empresa, *, status: str = "ativo"):
    usuario = _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="operador", email_prefixo="pmcs")
    usuario.status = status
    db.flush()
    return usuario


def _aplicar(client: TestClient, projeto_id: str, modelo_id: str):
    return client.post(f"/projetos/{projeto_id}/modelo-campanha/aplicar", json={"modeloCampanhaId": modelo_id})


def _get_snapshot(client: TestClient, projeto_id: str):
    return client.get(f"/projetos/{projeto_id}/modelo-campanha")


def _patch_snapshot(client: TestClient, projeto_id: str, itens: list[dict]):
    return client.patch(f"/projetos/{projeto_id}/modelo-campanha", json={"itens": itens})


# --------------------------------------------------------------------------------------
# Aplicar
# --------------------------------------------------------------------------------------


def test_admin_aplica_modelo(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Post de lançamento")

    resposta = _aplicar(client_admin, projeto.id, modelo.id)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["modeloCampanhaOrigemId"] == modelo.id
    assert corpo["modeloCampanhaNomeSnapshot"] == modelo.nome
    assert corpo["aplicadoAt"] is not None
    assert len(corpo["itens"]) == 1
    assert corpo["itens"][0]["nome"] == "Post de lançamento"
    assert corpo["itens"][0]["ordem"] == 1


def test_gestor_aplica_modelo(client_gestor: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)

    resposta = _aplicar(client_gestor, projeto.id, modelo.id)
    assert resposta.status_code == 200, resposta.text


def test_operador_nao_aplica(client_operador: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)

    resposta = _aplicar(client_operador, projeto.id, modelo.id)
    assert resposta.status_code == 403


def test_aplicar_projeto_cross_tenant_404(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    projeto_alheio = _projeto(db_session, outra_empresa)
    modelo = _modelo_campanha(db_session, outra_empresa)

    resposta = _aplicar(client_admin, projeto_alheio.id, modelo.id)
    assert resposta.status_code == 404


def test_aplicar_modelo_cross_tenant_rejeitado(
    client_admin: TestClient, empresa: Empresa, outra_empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo_alheio = _modelo_campanha(db_session, outra_empresa)

    resposta = _aplicar(client_admin, projeto.id, modelo_alheio.id)
    assert_erro_simples(resposta, 422)


def test_aplicar_modelo_inativo_rejeitado(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa, status="inativo")

    resposta = _aplicar(client_admin, projeto.id, modelo.id)
    assert_erro_simples(resposta, 422)


def test_aplicar_modelo_arquivado_rejeitado(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa, status="arquivado")

    resposta = _aplicar(client_admin, projeto.id, modelo.id)
    assert_erro_simples(resposta, 422)


def test_aplicar_modelo_com_itens_completos_materializa_snapshot(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    peca = _peca(db_session, empresa)
    tipo = _tipo_tarefa(db_session, empresa)
    workflow = _workflow_modelo(db_session, empresa)
    usuario = _usuario(db_session, empresa)
    departamento = _departamento(db_session, empresa)

    item_biblioteca = _modelo_item(
        db_session,
        modelo,
        ordem=1,
        nome="Item completo",
        briefing_padrao="Briefing X",
        prioridade_padrao="alta",
        peca_id=peca.id,
        tipo_tarefa_id=tipo.id,
        workflow_modelo_id=workflow.id,
        responsavel_usuario_id=usuario.id,
    )
    _modelo_item(db_session, modelo, ordem=2, nome="Item com depto", responsavel_departamento_id=departamento.id)

    resposta = _aplicar(client_admin, projeto.id, modelo.id)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    itens = corpo["itens"]
    assert len(itens) == 2

    item_1 = itens[0]
    assert item_1["nome"] == "Item completo"
    assert item_1["briefingPadrao"] == "Briefing X"
    assert item_1["prioridadePadrao"] == "alta"
    assert item_1["pecaId"] == peca.id
    assert item_1["pecaNomeSnapshot"] == peca.nome
    assert item_1["tipoTarefaId"] == tipo.id
    assert item_1["tipoTarefaNomeSnapshot"] == tipo.nome
    assert item_1["workflowModeloId"] == workflow.id
    assert item_1["workflowModeloNomeSnapshot"] == workflow.nome
    assert item_1["responsavelUsuarioId"] == usuario.id
    assert item_1["responsavelUsuarioNomeSnapshot"] == usuario.nome
    # Ids do snapshot NUNCA reaproveitam os ids dos itens da biblioteca.
    assert item_1["id"] != item_biblioteca.id

    item_2 = itens[1]
    assert item_2["responsavelDepartamentoId"] == departamento.id
    assert item_2["responsavelDepartamentoNomeSnapshot"] == departamento.nome


def test_aplicar_cabecalho_persistido_no_banco(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)

    resposta = _aplicar(client_admin, projeto.id, modelo.id)
    assert resposta.status_code == 200, resposta.text

    db_session.expire_all()
    cabecalho = (
        db_session.query(ProjetoModeloCampanha).filter(ProjetoModeloCampanha.projeto_id == projeto.id).one()
    )
    assert cabecalho.modelo_campanha_origem_id == modelo.id
    assert cabecalho.aplicado_por_usuario_id is not None


def test_aplicar_publica_evento(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)

    resposta = _aplicar(client_admin, projeto.id, modelo.id)
    assert resposta.status_code == 200, resposta.text

    eventos = (
        db_session.query(Evento)
        .filter(Evento.entidade_tipo == "projeto", Evento.entidade_id == projeto.id)
        .all()
    )
    assert len(eventos) == 1
    assert eventos[0].tipo == "projeto.modelo_campanha_aplicado"
    assert eventos[0].payload["modelo_campanha_origem_id"] == modelo.id
    assert eventos[0].payload["modelo_campanha_origem_anterior_id"] is None
    assert "itens" not in eventos[0].payload


# --------------------------------------------------------------------------------------
# Reaplicar
# --------------------------------------------------------------------------------------


def test_reaplicar_mantem_id_do_cabecalho_e_substitui_conteudo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo_1 = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo_1, ordem=1, nome="Item do modelo 1")
    modelo_2 = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo_2, ordem=1, nome="Item do modelo 2")
    _modelo_item(db_session, modelo_2, ordem=2, nome="Outro item do modelo 2")

    primeira = _aplicar(client_admin, projeto.id, modelo_1.id)
    assert primeira.status_code == 200, primeira.text
    cabecalho_id = primeira.json()["id"]
    item_antigo_id = primeira.json()["itens"][0]["id"]

    segunda = _aplicar(client_admin, projeto.id, modelo_2.id)
    assert segunda.status_code == 200, segunda.text
    corpo = segunda.json()

    assert corpo["id"] == cabecalho_id  # mesmo cabeçalho, nunca recriado
    assert corpo["modeloCampanhaOrigemId"] == modelo_2.id
    assert corpo["modeloCampanhaNomeSnapshot"] == modelo_2.nome
    assert len(corpo["itens"]) == 2
    assert corpo["itens"][0]["nome"] == "Item do modelo 2"
    assert all(item["id"] != item_antigo_id for item in corpo["itens"])  # itens antigos substituídos


def test_reaplicar_atualiza_aplicado_at_e_aplicado_por(
    client_admin: TestClient, client_gestor: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo_1 = _modelo_campanha(db_session, empresa)
    modelo_2 = _modelo_campanha(db_session, empresa)

    primeira = _aplicar(client_admin, projeto.id, modelo_1.id)
    aplicado_por_1 = primeira.json()["aplicadoPorUsuarioId"]

    segunda = _aplicar(client_gestor, projeto.id, modelo_2.id)
    aplicado_por_2 = segunda.json()["aplicadoPorUsuarioId"]

    assert aplicado_por_1 != aplicado_por_2


def test_reaplicar_evento_registra_origem_anterior(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo_1 = _modelo_campanha(db_session, empresa)
    modelo_2 = _modelo_campanha(db_session, empresa)

    _aplicar(client_admin, projeto.id, modelo_1.id)
    _aplicar(client_admin, projeto.id, modelo_2.id)

    eventos = (
        db_session.query(Evento)
        .filter(Evento.entidade_tipo == "projeto", Evento.entidade_id == projeto.id)
        .order_by(Evento.occurred_at.asc())
        .all()
    )
    assert len(eventos) == 2
    assert eventos[0].payload["modelo_campanha_origem_anterior_id"] is None
    assert eventos[1].payload["modelo_campanha_origem_id"] == modelo_2.id
    assert eventos[1].payload["modelo_campanha_origem_anterior_id"] == modelo_1.id


# --------------------------------------------------------------------------------------
# Leitura
# --------------------------------------------------------------------------------------


def test_get_snapshot_projeto_sem_snapshot_retorna_200_null(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    resposta = _get_snapshot(client_admin, projeto.id)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() is None


def test_get_snapshot_projeto_com_snapshot(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item")
    _aplicar(client_admin, projeto.id, modelo.id)

    resposta = _get_snapshot(client_admin, projeto.id)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["modeloCampanhaOrigemId"] == modelo.id
    assert len(corpo["itens"]) == 1


def test_get_snapshot_cross_tenant_404(client_admin: TestClient, outra_empresa: Empresa, db_session: Session) -> None:
    projeto_alheio = _projeto(db_session, outra_empresa)
    resposta = _get_snapshot(client_admin, projeto_alheio.id)
    assert resposta.status_code == 404


def test_get_snapshot_operador_bloqueado(client_operador: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    resposta = _get_snapshot(client_operador, projeto.id)
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Edição
# --------------------------------------------------------------------------------------


def test_patch_sem_snapshot_retorna_409(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    resposta = _patch_snapshot(client_admin, projeto.id, [{"nome": "Item novo"}])
    assert_erro_simples(resposta, 409)


def test_patch_edita_nome_briefing_prioridade(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Original")
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    resposta = _patch_snapshot(
        client_admin,
        projeto.id,
        [{"id": item_id, "nome": "Editado", "briefingPadrao": "Novo briefing", "prioridadePadrao": "alta"}],
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["id"] == item_id
    assert item["nome"] == "Editado"
    assert item["briefingPadrao"] == "Novo briefing"
    assert item["prioridadePadrao"] == "alta"


def test_patch_reordena_preservando_ids(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="A")
    _modelo_item(db_session, modelo, ordem=2, nome="B")
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    id_a, id_b = aplicar.json()["itens"][0]["id"], aplicar.json()["itens"][1]["id"]

    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": id_b, "nome": "B"}, {"id": id_a, "nome": "A"}]
    )
    assert resposta.status_code == 200, resposta.text
    itens = resposta.json()["itens"]
    assert [item["id"] for item in itens] == [id_b, id_a]
    assert [item["ordem"] for item in itens] == [1, 2]


def test_patch_remove_item(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Fica")
    _modelo_item(db_session, modelo, ordem=2, nome="Sai")
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    id_fica = aplicar.json()["itens"][0]["id"]

    resposta = _patch_snapshot(client_admin, projeto.id, [{"id": id_fica, "nome": "Fica"}])
    assert resposta.status_code == 200, resposta.text
    itens = resposta.json()["itens"]
    assert len(itens) == 1
    assert itens[0]["id"] == id_fica


def test_patch_inclui_item_novo_com_id_gerado_pelo_servidor(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Original")
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    id_original = aplicar.json()["itens"][0]["id"]

    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": id_original, "nome": "Original"}, {"nome": "Novo"}]
    )
    assert resposta.status_code == 200, resposta.text
    itens = resposta.json()["itens"]
    assert len(itens) == 2
    novo_id = itens[1]["id"]
    assert novo_id != id_original
    uuid.UUID(novo_id)


def test_patch_id_de_outro_projeto_nao_reaproveitado(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto_a = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item de A")
    aplicar_a = _aplicar(client_admin, projeto_a.id, modelo.id)
    id_alheio = aplicar_a.json()["itens"][0]["id"]

    projeto_b = _projeto(db_session, empresa)
    _aplicar(client_admin, projeto_b.id, modelo.id)

    resposta = _patch_snapshot(client_admin, projeto_b.id, [{"id": id_alheio, "nome": "Disfarçado"}])
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["itens"][0]["id"] != id_alheio

    # O item do Projeto A continua intacto.
    relido_a = _get_snapshot(client_admin, projeto_a.id)
    assert relido_a.json()["itens"][0]["id"] == id_alheio
    assert relido_a.json()["itens"][0]["nome"] == "Item de A"


def test_patch_id_inexistente_tratado_como_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _aplicar(client_admin, projeto.id, modelo.id)

    id_inventado = str(uuid.uuid4())
    resposta = _patch_snapshot(client_admin, projeto.id, [{"id": id_inventado, "nome": "Item"}])
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["itens"][0]["id"] != id_inventado


def test_patch_responsavel_usuario_e_departamento_simultaneos_rejeitado(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _aplicar(client_admin, projeto.id, modelo.id)
    usuario = _usuario(db_session, empresa)
    departamento = _departamento(db_session, empresa)

    resposta = _patch_snapshot(
        client_admin,
        projeto.id,
        [{"nome": "Item", "responsavelUsuarioId": usuario.id, "responsavelDepartamentoId": departamento.id}],
    )
    assert_erro_simples(resposta, 422)


def test_patch_rollback_completo_se_item_invalido(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Original")
    _aplicar(client_admin, projeto.id, modelo.id)

    peca_arquivada = _peca(db_session, empresa, status="arquivado")
    resposta = _patch_snapshot(
        client_admin,
        projeto.id,
        [{"nome": "Novo item", "pecaId": peca_arquivada.id}],
    )
    assert_erro_simples(resposta, 422)

    relido = _get_snapshot(client_admin, projeto.id)
    assert [item["nome"] for item in relido.json()["itens"]] == ["Original"]


# --------------------------------------------------------------------------------------
# Referência histórica — Peça
# --------------------------------------------------------------------------------------


def test_peca_historico_preservado_quando_item_nao_muda(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    peca = _peca(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", peca_id=peca.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    peca.status = "arquivado"
    db_session.flush()

    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Renomeado", "pecaId": peca.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["pecaId"] == peca.id
    assert item["pecaNomeSnapshot"] == peca.nome
    assert item["nome"] == "Renomeado"


def test_peca_troca_para_arquivada_rejeitada(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    peca_ativa = _peca(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", peca_id=peca_ativa.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    peca_arquivada = _peca(db_session, empresa, status="arquivado")
    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Item", "pecaId": peca_arquivada.id}]
    )
    assert_erro_simples(resposta, 422)


def test_peca_troca_para_nova_valida_atualiza_nome(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    peca_original = _peca(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", peca_id=peca_original.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    peca_nova = _peca(db_session, empresa)
    resposta = _patch_snapshot(client_admin, projeto.id, [{"id": item_id, "nome": "Item", "pecaId": peca_nova.id}])
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["pecaId"] == peca_nova.id
    assert item["pecaNomeSnapshot"] == peca_nova.nome


def test_peca_nome_historico_nao_recalculado_apos_renomear(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    """Prova arquitetural do item 36: aplicar com "Nome A", renomear a Peça pra "Nome B",
    o GET do snapshot continua devolvendo "Nome A"."""
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    peca = _peca(db_session, empresa)
    peca.nome = "Nome A"
    db_session.flush()
    _modelo_item(db_session, modelo, ordem=1, nome="Item", peca_id=peca.id)
    _aplicar(client_admin, projeto.id, modelo.id)

    peca.nome = "Nome B"
    db_session.flush()

    resposta = _get_snapshot(client_admin, projeto.id)
    assert resposta.json()["itens"][0]["pecaNomeSnapshot"] == "Nome A"


# --------------------------------------------------------------------------------------
# Referência histórica — Tipo de Tarefa
# --------------------------------------------------------------------------------------


def test_tipo_tarefa_historico_preservado_quando_item_nao_muda(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    tipo = _tipo_tarefa(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", tipo_tarefa_id=tipo.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    tipo.status = "arquivado"
    db_session.flush()

    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Renomeado", "tipoTarefaId": tipo.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["tipoTarefaId"] == tipo.id
    assert item["tipoTarefaNomeSnapshot"] == tipo.nome


def test_tipo_tarefa_troca_para_arquivada_rejeitada(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    tipo_ativo = _tipo_tarefa(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", tipo_tarefa_id=tipo_ativo.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    tipo_arquivado = _tipo_tarefa(db_session, empresa, status="arquivado")
    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Item", "tipoTarefaId": tipo_arquivado.id}]
    )
    assert_erro_simples(resposta, 422)


def test_tipo_tarefa_troca_para_nova_valida_atualiza_nome(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    tipo_original = _tipo_tarefa(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", tipo_tarefa_id=tipo_original.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    tipo_novo = _tipo_tarefa(db_session, empresa)
    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Item", "tipoTarefaId": tipo_novo.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["tipoTarefaId"] == tipo_novo.id
    assert item["tipoTarefaNomeSnapshot"] == tipo_novo.nome


# --------------------------------------------------------------------------------------
# Referência histórica — Workflow
# --------------------------------------------------------------------------------------


def test_workflow_historico_preservado_quando_item_nao_muda(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    workflow = _workflow_modelo(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", workflow_modelo_id=workflow.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    workflow.status = "arquivado"
    db_session.flush()

    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Renomeado", "workflowModeloId": workflow.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["workflowModeloId"] == workflow.id
    assert item["workflowModeloNomeSnapshot"] == workflow.nome


def test_workflow_troca_para_arquivado_rejeitada(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    workflow_ativo = _workflow_modelo(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", workflow_modelo_id=workflow_ativo.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    workflow_arquivado = _workflow_modelo(db_session, empresa, status="arquivado")
    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Item", "workflowModeloId": workflow_arquivado.id}]
    )
    assert_erro_simples(resposta, 422)


def test_workflow_troca_para_novo_valido_atualiza_nome(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    workflow_original = _workflow_modelo(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", workflow_modelo_id=workflow_original.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    workflow_novo = _workflow_modelo(db_session, empresa)
    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Item", "workflowModeloId": workflow_novo.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["workflowModeloId"] == workflow_novo.id
    assert item["workflowModeloNomeSnapshot"] == workflow_novo.nome


def test_workflow_nome_historico_nao_recalculado_apos_renomear(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    """Segunda prova arquitetural do item 36 (a primeira foi com Peça)."""
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    workflow = _workflow_modelo(db_session, empresa)
    workflow.nome = "Workflow A"
    db_session.flush()
    _modelo_item(db_session, modelo, ordem=1, nome="Item", workflow_modelo_id=workflow.id)
    _aplicar(client_admin, projeto.id, modelo.id)

    workflow.nome = "Workflow B"
    db_session.flush()

    resposta = _get_snapshot(client_admin, projeto.id)
    assert resposta.json()["itens"][0]["workflowModeloNomeSnapshot"] == "Workflow A"


# --------------------------------------------------------------------------------------
# Referência histórica — Usuário
# --------------------------------------------------------------------------------------


def test_usuario_historico_preservado_quando_item_nao_muda(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    usuario = _usuario(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", responsavel_usuario_id=usuario.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    usuario.status = "inativo"
    db_session.flush()

    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Renomeado", "responsavelUsuarioId": usuario.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["responsavelUsuarioId"] == usuario.id
    assert item["responsavelUsuarioNomeSnapshot"] == usuario.nome


def test_usuario_troca_para_inativo_rejeitada(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    usuario_ativo = _usuario(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", responsavel_usuario_id=usuario_ativo.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    usuario_inativo = _usuario(db_session, empresa, status="inativo")
    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Item", "responsavelUsuarioId": usuario_inativo.id}]
    )
    assert_erro_simples(resposta, 422)


def test_usuario_troca_para_novo_valido_atualiza_nome(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    usuario_original = _usuario(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", responsavel_usuario_id=usuario_original.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    usuario_novo = _usuario(db_session, empresa)
    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Item", "responsavelUsuarioId": usuario_novo.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["responsavelUsuarioId"] == usuario_novo.id
    assert item["responsavelUsuarioNomeSnapshot"] == usuario_novo.nome


# --------------------------------------------------------------------------------------
# Referência histórica — Departamento
# --------------------------------------------------------------------------------------


def test_departamento_historico_preservado_quando_item_nao_muda(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    departamento = _departamento(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", responsavel_departamento_id=departamento.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    departamento.status = "arquivado"
    db_session.flush()

    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Renomeado", "responsavelDepartamentoId": departamento.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["responsavelDepartamentoId"] == departamento.id
    assert item["responsavelDepartamentoNomeSnapshot"] == departamento.nome


def test_departamento_troca_para_arquivado_rejeitada(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    departamento_ativo = _departamento(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", responsavel_departamento_id=departamento_ativo.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    departamento_arquivado = _departamento(db_session, empresa, status="arquivado")
    resposta = _patch_snapshot(
        client_admin,
        projeto.id,
        [{"id": item_id, "nome": "Item", "responsavelDepartamentoId": departamento_arquivado.id}],
    )
    assert_erro_simples(resposta, 422)


def test_departamento_inativo_aceito_em_vinculo_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    """Departamento é o único caso em que `inativo` é aceito em vínculo NOVO — mesma
    divergência já adotada em ProjetoService/DemandaService/ModeloCampanhaService."""
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _aplicar(client_admin, projeto.id, modelo.id)
    departamento_inativo = _departamento(db_session, empresa, status="inativo")

    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"nome": "Item", "responsavelDepartamentoId": departamento_inativo.id}]
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["itens"][0]["responsavelDepartamentoId"] == departamento_inativo.id


def test_departamento_troca_para_novo_valido_atualiza_nome(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    departamento_original = _departamento(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item", responsavel_departamento_id=departamento_original.id)
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]

    departamento_novo = _departamento(db_session, empresa)
    resposta = _patch_snapshot(
        client_admin, projeto.id, [{"id": item_id, "nome": "Item", "responsavelDepartamentoId": departamento_novo.id}]
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["responsavelDepartamentoId"] == departamento_novo.id
    assert item["responsavelDepartamentoNomeSnapshot"] == departamento_novo.nome


# --------------------------------------------------------------------------------------
# Atomicidade
# --------------------------------------------------------------------------------------


def test_aplicar_com_item_do_modelo_invalido_faz_rollback_total(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    """Modelo com um item referenciando Peça hoje arquivada (a biblioteca permitia no
    momento em que o item foi criado, mas a Peça foi arquivada depois) — aplicar deve
    rejeitar por inteiro, sem criar cabeçalho nem itens parciais."""
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Item válido")
    peca_arquivada = _peca(db_session, empresa, status="arquivado")
    _modelo_item(db_session, modelo, ordem=2, nome="Item inválido", peca_id=peca_arquivada.id)

    resposta = _aplicar(client_admin, projeto.id, modelo.id)
    assert_erro_simples(resposta, 422)

    db_session.expire_all()
    cabecalho = (
        db_session.query(ProjetoModeloCampanha).filter(ProjetoModeloCampanha.projeto_id == projeto.id).first()
    )
    assert cabecalho is None


def test_reaplicar_invalido_preserva_snapshot_anterior(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo_1 = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo_1, ordem=1, nome="Item original")
    _aplicar(client_admin, projeto.id, modelo_1.id)

    modelo_2 = _modelo_campanha(db_session, empresa)
    peca_arquivada = _peca(db_session, empresa, status="arquivado")
    _modelo_item(db_session, modelo_2, ordem=1, nome="Item quebrado", peca_id=peca_arquivada.id)

    resposta = _aplicar(client_admin, projeto.id, modelo_2.id)
    assert_erro_simples(resposta, 422)

    relido = _get_snapshot(client_admin, projeto.id)
    assert relido.json()["modeloCampanhaOrigemId"] == modelo_1.id
    assert relido.json()["itens"][0]["nome"] == "Item original"


def test_patch_invalido_preserva_snapshot_anterior(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    _modelo_item(db_session, modelo, ordem=1, nome="Original")
    aplicar = _aplicar(client_admin, projeto.id, modelo.id)
    item_id = aplicar.json()["itens"][0]["id"]
    cabecalho_atualizado_em = aplicar.json()["updatedAt"]

    usuario = _usuario(db_session, empresa)
    departamento = _departamento(db_session, empresa)
    resposta = _patch_snapshot(
        client_admin,
        projeto.id,
        [
            {"id": item_id, "nome": "Deveria falhar"},
            {"nome": "Item ruim", "responsavelUsuarioId": usuario.id, "responsavelDepartamentoId": departamento.id},
        ],
    )
    assert resposta.status_code == 422, resposta.text

    relido = _get_snapshot(client_admin, projeto.id)
    assert relido.json()["itens"] == aplicar.json()["itens"]
    assert relido.json()["updatedAt"] == cabecalho_atualizado_em
