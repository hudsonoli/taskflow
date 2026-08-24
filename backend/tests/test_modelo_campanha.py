"""Testes do módulo Modelo de Campanha (Fase 2G.5A) — biblioteca reutilizável, sem nenhum
vínculo com Projeto ainda (isso é 2G.5C). Mesmo padrão de test_peca.py/test_tipo_tarefa.py,
com a complexidade adicional de 5 tipos de referência por item (Peça/TipoTarefa/Workflow/
Usuário/Departamento) e preservação de vínculo histórico."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.modelo_campanha import ModeloCampanha
from app.models.peca import Peca
from app.models.tipo_tarefa import TipoTarefa
from app.models.workflow_modelo import WorkflowModelo
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.helpers.assertions import assert_conflito_arquivado, assert_erro_simples


# --------------------------------------------------------------------------------------
# Fábricas de entidades referenciadas — direto no model, sem passar pela API (mais rápido,
# e permite fabricar estados como "inativo"/"arquivado" sem precisar de outro endpoint)
# --------------------------------------------------------------------------------------


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


def _usuario(db: Session, empresa: Empresa, *, status: str = "ativo"):
    usuario = _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="operador", email_prefixo="mc")
    usuario.status = status
    db.flush()
    return usuario


def _payload(nome: str | None = None, **extra) -> dict:
    return {"nome": nome or f"Modelo {uuid.uuid4().hex[:8]}", **extra}


def _criar(client: TestClient, nome: str | None = None, **extra) -> dict:
    resposta = client.post("/modelos-campanha", json=_payload(nome, **extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _item(**overrides) -> dict:
    base = {"nome": f"Item {uuid.uuid4().hex[:8]}"}
    base.update(overrides)
    return base


# --------------------------------------------------------------------------------------
# CRUD básico / RBAC
# --------------------------------------------------------------------------------------


def test_admin_cria(client_admin: TestClient) -> None:
    resposta = client_admin.post("/modelos-campanha", json=_payload())
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "ativo"
    assert corpo["itens"] == []
    assert corpo["empresaId"]


def test_gestor_cria(client_gestor: TestClient) -> None:
    resposta = client_gestor.post("/modelos-campanha", json=_payload())
    assert resposta.status_code == 201, resposta.text


def test_operador_nao_cria(client_operador: TestClient) -> None:
    resposta = client_operador.post("/modelos-campanha", json=_payload())
    assert resposta.status_code == 403, resposta.text


def test_operador_nao_le_lista(client_operador: TestClient) -> None:
    assert client_operador.get("/modelos-campanha").status_code == 403


def test_operador_nao_le_diretorio(client_operador: TestClient) -> None:
    assert client_operador.get("/modelos-campanha/diretorio").status_code == 403


def test_mesmo_nome_normalizado_mesma_empresa_rejeita(client_admin: TestClient) -> None:
    nome = f"Duplicado {uuid.uuid4().hex[:8]}"
    primeiro = client_admin.post("/modelos-campanha", json=_payload(nome))
    assert primeiro.status_code == 201, primeiro.text

    segundo = client_admin.post("/modelos-campanha", json=_payload(f"  {nome.upper()}  "))
    assert_erro_simples(segundo, 409)


def test_mesmo_nome_em_empresa_diferente_permitido(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    nome = f"Mesmo nome {uuid.uuid4().hex[:8]}"
    criado = _criar(client_admin, nome)
    assert criado["nome"] == nome

    agora = datetime.now(timezone.utc)
    de_outra = ModeloCampanha(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        nome=nome,
        nome_normalizado=nome.strip().lower(),
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()  # não levanta IntegrityError — unique é (empresa_id, nome_normalizado)


def test_editar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/modelos-campanha/{criado['id']}", json={"nome": "Renomeado", "descricao": "Nova"})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Renomeado"
    assert corpo["descricao"] == "Nova"


def test_inativar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/modelos-campanha/{criado['id']}", json={"status": "inativo"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "inativo"


def test_lifecycle_ativo_arquivar_restaurar_volta_ativo(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)
    arquivar = client_admin.post(f"/modelos-campanha/{criado['id']}/arquivar", json={"motivoArquivamento": "descontinuado"})
    assert arquivar.status_code == 200, arquivar.text
    assert arquivar.json()["status"] == "arquivado"
    assert arquivar.json()["motivoArquivamento"] == "descontinuado"

    # Auditoria: grava o status de origem (aqui "ativo"), mas isso NUNCA decide o destino do
    # restore — só é lido diretamente no banco, a API não expõe esse campo (ver item 1 da
    # revisão da Fase 2G.5A).
    linha = db_session.get(ModeloCampanha, criado["id"])
    assert linha.status_anterior_arquivamento == "ativo"

    restaurar = client_admin.post(f"/modelos-campanha/{criado['id']}/restaurar")
    assert restaurar.status_code == 200, restaurar.text
    assert restaurar.json()["status"] == "ativo"


def test_lifecycle_inativo_arquivar_restaurar_volta_ativo_mesmo_assim(
    client_admin: TestClient, db_session: Session
) -> None:
    """ModeloCampanha segue o mesmo padrão de TipoTarefa/Peça/WorkflowModelo/Departamento:
    restaurar SEMPRE devolve `ativo`, mesmo que o registro estivesse `inativo` antes de ser
    arquivado — `status_anterior_arquivamento` é só auditoria, nunca fonte de decisão do
    destino. Diverge deliberadamente de Cliente/Fornecedor/Projeto/Demanda (que reconstroem o
    status anterior) — ver relatório da revisão."""
    criado = _criar(client_admin)
    client_admin.patch(f"/modelos-campanha/{criado['id']}", json={"status": "inativo"})

    arquivar = client_admin.post(f"/modelos-campanha/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert arquivar.status_code == 200, arquivar.text

    linha = db_session.get(ModeloCampanha, criado["id"])
    assert linha.status_anterior_arquivamento == "inativo"

    restaurar = client_admin.post(f"/modelos-campanha/{criado['id']}/restaurar")
    assert restaurar.status_code == 200, restaurar.text
    assert restaurar.json()["status"] == "ativo"  # NÃO volta pra "inativo"


def test_nome_duplicado_de_arquivado_409_padronizado_oferece_restaurar(client_admin: TestClient) -> None:
    nome = f"Duplicado Arquivado {uuid.uuid4().hex[:8]}"
    criado = _criar(client_admin, nome)
    client_admin.post(f"/modelos-campanha/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    tentativa = client_admin.post("/modelos-campanha", json=_payload(nome))
    detail = assert_conflito_arquivado(tentativa, code="MODELO_CAMPANHA_ARQUIVADO_EXISTENTE")
    assert detail["modeloCampanhaArquivadoId"] == criado["id"]


def test_diretorio_so_ativo(client_admin: TestClient) -> None:
    ativo = _criar(client_admin)
    inativo = _criar(client_admin)
    client_admin.patch(f"/modelos-campanha/{inativo['id']}", json={"status": "inativo"})
    arquivado = _criar(client_admin)
    client_admin.post(f"/modelos-campanha/{arquivado['id']}/arquivar", json={"motivoArquivamento": "x"})

    diretorio = client_admin.get("/modelos-campanha/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    ids = {item["id"] for item in diretorio.json()}
    assert ativo["id"] in ids
    assert inativo["id"] not in ids
    assert arquivado["id"] not in ids


def test_diretorio_so_tem_id_e_nome(client_admin: TestClient) -> None:
    criado = _criar(client_admin, "Diretorio enxuto")
    diretorio = client_admin.get("/modelos-campanha/diretorio")
    encontrado = next(item for item in diretorio.json() if item["id"] == criado["id"])
    assert set(encontrado.keys()) == {"id", "nome"}


def test_get_cross_tenant_404_nao_403(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    agora = datetime.now(timezone.utc)
    de_outra = ModeloCampanha(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        nome="Modelo de outra empresa",
        nome_normalizado="modelo de outra empresa",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()

    resposta = client_admin.get(f"/modelos-campanha/{de_outra.id}")
    assert resposta.status_code == 404, resposta.text


# --------------------------------------------------------------------------------------
# Itens — criação, ordem, campos simples
# --------------------------------------------------------------------------------------


def test_criar_com_varios_itens(client_admin: TestClient) -> None:
    criado = _criar(
        client_admin,
        itens=[_item(nome="Item A"), _item(nome="Item B", briefingPadrao="Briefing B", prioridadePadrao="alta")],
    )
    assert len(criado["itens"]) == 2
    assert [item["nome"] for item in criado["itens"]] == ["Item A", "Item B"]
    assert criado["itens"][1]["briefingPadrao"] == "Briefing B"
    assert criado["itens"][1]["prioridadePadrao"] == "alta"
    # prioridade default
    assert criado["itens"][0]["prioridadePadrao"] == "media"


def test_ordem_reconstruida_pelo_servidor_ignora_qualquer_valor_do_cliente(client_admin: TestClient) -> None:
    criado = _criar(client_admin, itens=[_item(nome="Primeiro"), _item(nome="Segundo"), _item(nome="Terceiro")])
    ordens = [item["ordem"] for item in criado["itens"]]
    assert ordens == [1, 2, 3]


def test_reordenar_no_update(client_admin: TestClient) -> None:
    criado = _criar(client_admin, itens=[_item(nome="A"), _item(nome="B")])
    item_a_id = criado["itens"][0]["id"]
    item_b_id = criado["itens"][1]["id"]

    resposta = client_admin.patch(
        f"/modelos-campanha/{criado['id']}",
        json={"itens": [{"id": item_b_id, "nome": "B"}, {"id": item_a_id, "nome": "A"}]},
    )
    assert resposta.status_code == 200, resposta.text
    itens = resposta.json()["itens"]
    assert [item["nome"] for item in itens] == ["B", "A"]
    assert [item["ordem"] for item in itens] == [1, 2]
    # Identidade: reordenar não troca o id dos itens que já existiam — mesmo com DELETE+INSERT
    # por baixo, o id enviado pelo cliente (que bate com o item existente) é reaproveitado.
    assert [item["id"] for item in itens] == [item_b_id, item_a_id]


def test_editar_item_existente_preserva_id(client_admin: TestClient) -> None:
    criado = _criar(client_admin, itens=[_item(nome="Original", briefingPadrao="Antigo")])
    item_id = criado["itens"][0]["id"]

    resposta = client_admin.patch(
        f"/modelos-campanha/{criado['id']}",
        json={"itens": [{"id": item_id, "nome": "Renomeado", "briefingPadrao": "Novo"}]},
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["id"] == item_id
    assert item["nome"] == "Renomeado"
    assert item["briefingPadrao"] == "Novo"


def test_adicionar_item_gera_id_novo_diferente_dos_existentes(client_admin: TestClient) -> None:
    criado = _criar(client_admin, itens=[_item(nome="Original")])
    item_original_id = criado["itens"][0]["id"]

    resposta = client_admin.patch(
        f"/modelos-campanha/{criado['id']}",
        json={"itens": [{"id": item_original_id, "nome": "Original"}, {"nome": "Novo"}]},
    )
    assert resposta.status_code == 200, resposta.text
    itens = resposta.json()["itens"]
    assert itens[0]["id"] == item_original_id
    novo_id = itens[1]["id"]
    assert novo_id != item_original_id
    uuid.UUID(novo_id)  # é um UUID válido, gerado pelo servidor


def test_remover_item_no_update(client_admin: TestClient) -> None:
    criado = _criar(client_admin, itens=[_item(nome="Fica"), _item(nome="Sai")])
    item_fica_id = criado["itens"][0]["id"]
    resposta = client_admin.patch(
        f"/modelos-campanha/{criado['id']}", json={"itens": [{"id": item_fica_id, "nome": "Fica"}]}
    )
    assert resposta.status_code == 200, resposta.text
    itens = resposta.json()["itens"]
    assert len(itens) == 1
    assert itens[0]["nome"] == "Fica"
    assert itens[0]["id"] == item_fica_id  # o item que sobrou manteve seu id original


def test_incluir_item_no_update(client_admin: TestClient) -> None:
    criado = _criar(client_admin, itens=[_item(nome="Original")])
    resposta = client_admin.patch(
        f"/modelos-campanha/{criado['id']}", json={"itens": [{"nome": "Original"}, {"nome": "Novo"}]}
    )
    assert resposta.status_code == 200, resposta.text
    assert len(resposta.json()["itens"]) == 2


def test_id_de_item_de_outro_modelo_nao_e_reaproveitado(client_admin: TestClient) -> None:
    """Um `id` sintaticamente válido, mas que pertence a um item de OUTRO Modelo, nunca pode
    ser usado como a PK da nova linha — senão colide com a linha real que já existe. O
    service deve tratar como item novo e gerar um id próprio, silenciosamente."""
    outro_modelo = _criar(client_admin, itens=[_item(nome="Item de outro Modelo")])
    id_alheio = outro_modelo["itens"][0]["id"]

    meu_modelo = _criar(client_admin, itens=[_item(nome="Meu item")])
    resposta = client_admin.patch(
        f"/modelos-campanha/{meu_modelo['id']}",
        json={"itens": [{"id": id_alheio, "nome": "Item disfarçado"}]},
    )
    assert resposta.status_code == 200, resposta.text
    item = resposta.json()["itens"][0]
    assert item["id"] != id_alheio  # o id alheio foi descartado, não reaproveitado
    assert item["nome"] == "Item disfarçado"

    # E o item original do outro Modelo continua intacto, sem ter sido afetado.
    outro_relido = client_admin.get(f"/modelos-campanha/{outro_modelo['id']}")
    assert outro_relido.json()["itens"][0]["id"] == id_alheio
    assert outro_relido.json()["itens"][0]["nome"] == "Item de outro Modelo"


def test_id_inexistente_tratado_como_item_novo(client_admin: TestClient) -> None:
    """Um `id` bem-formado mas que nunca existiu em nenhum Modelo também não pode ser
    reaproveitado como PK — mesmo tratamento do id de outro Modelo: vira item novo."""
    id_inventado = str(uuid.uuid4())
    criado = _criar(client_admin, itens=[{"id": id_inventado, "nome": "Primeiro item"}])
    assert criado["itens"][0]["id"] != id_inventado


# --------------------------------------------------------------------------------------
# Referências — Peça / Tipo de Tarefa / Workflow válidos
# --------------------------------------------------------------------------------------


def test_item_com_peca_valida(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    peca = _peca(db_session, empresa)
    criado = _criar(client_admin, itens=[_item(pecaId=peca.id)])
    assert criado["itens"][0]["pecaId"] == peca.id
    assert criado["itens"][0]["pecaNome"] == peca.nome


def test_item_com_tipo_tarefa_valido(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    tipo = _tipo_tarefa(db_session, empresa)
    criado = _criar(client_admin, itens=[_item(tipoTarefaId=tipo.id)])
    assert criado["itens"][0]["tipoTarefaId"] == tipo.id
    assert criado["itens"][0]["tipoTarefaNome"] == tipo.nome


def test_item_com_workflow_valido(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    workflow = _workflow_modelo(db_session, empresa)
    criado = _criar(client_admin, itens=[_item(workflowModeloId=workflow.id)])
    assert criado["itens"][0]["workflowModeloId"] == workflow.id
    assert criado["itens"][0]["workflowModeloNome"] == workflow.nome


def test_item_com_responsavel_usuario(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    usuario = _usuario(db_session, empresa)
    criado = _criar(client_admin, itens=[_item(responsavelUsuarioId=usuario.id)])
    assert criado["itens"][0]["responsavelUsuarioId"] == usuario.id
    assert criado["itens"][0]["responsavelUsuarioNome"] == usuario.nome


def test_item_com_responsavel_departamento(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    departamento = _departamento(db_session, empresa)
    criado = _criar(client_admin, itens=[_item(responsavelDepartamentoId=departamento.id)])
    assert criado["itens"][0]["responsavelDepartamentoId"] == departamento.id
    assert criado["itens"][0]["responsavelDepartamentoNome"] == departamento.nome


def test_item_sem_nenhum_responsavel_permitido(client_admin: TestClient) -> None:
    criado = _criar(client_admin, itens=[_item()])
    assert criado["itens"][0]["responsavelUsuarioId"] is None
    assert criado["itens"][0]["responsavelDepartamentoId"] is None


def test_item_usuario_e_departamento_simultaneos_rejeitado(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    usuario = _usuario(db_session, empresa)
    departamento = _departamento(db_session, empresa)
    resposta = client_admin.post(
        "/modelos-campanha",
        json=_payload(itens=[_item(responsavelUsuarioId=usuario.id, responsavelDepartamentoId=departamento.id)]),
    )
    assert_erro_simples(resposta, 422)


# --------------------------------------------------------------------------------------
# Referências — cross-tenant e status inválido em vínculo NOVO
# --------------------------------------------------------------------------------------


def test_peca_de_outra_empresa_rejeitada(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    peca_alheia = _peca(db_session, outra_empresa)
    resposta = client_admin.post("/modelos-campanha", json=_payload(itens=[_item(pecaId=peca_alheia.id)]))
    assert_erro_simples(resposta, 422)


def test_tipo_tarefa_de_outra_empresa_rejeitado(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    tipo_alheio = _tipo_tarefa(db_session, outra_empresa)
    resposta = client_admin.post("/modelos-campanha", json=_payload(itens=[_item(tipoTarefaId=tipo_alheio.id)]))
    assert_erro_simples(resposta, 422)


def test_workflow_de_outra_empresa_rejeitado(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    workflow_alheio = _workflow_modelo(db_session, outra_empresa)
    resposta = client_admin.post(
        "/modelos-campanha", json=_payload(itens=[_item(workflowModeloId=workflow_alheio.id)])
    )
    assert_erro_simples(resposta, 422)


def test_usuario_de_outra_empresa_rejeitado(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    usuario_alheio = _usuario(db_session, outra_empresa)
    resposta = client_admin.post(
        "/modelos-campanha", json=_payload(itens=[_item(responsavelUsuarioId=usuario_alheio.id)])
    )
    assert_erro_simples(resposta, 422)


def test_departamento_de_outra_empresa_rejeitado(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    departamento_alheio = _departamento(db_session, outra_empresa)
    resposta = client_admin.post(
        "/modelos-campanha", json=_payload(itens=[_item(responsavelDepartamentoId=departamento_alheio.id)])
    )
    assert_erro_simples(resposta, 422)


def test_peca_arquivada_rejeitada_em_vinculo_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    peca_arquivada = _peca(db_session, empresa, status="arquivado")
    resposta = client_admin.post("/modelos-campanha", json=_payload(itens=[_item(pecaId=peca_arquivada.id)]))
    assert_erro_simples(resposta, 422)


def test_peca_inativa_rejeitada_em_vinculo_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    peca_inativa = _peca(db_session, empresa, status="inativo")
    resposta = client_admin.post("/modelos-campanha", json=_payload(itens=[_item(pecaId=peca_inativa.id)]))
    assert_erro_simples(resposta, 422)


def test_tipo_tarefa_arquivado_rejeitado_em_vinculo_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    tipo_arquivado = _tipo_tarefa(db_session, empresa, status="arquivado")
    resposta = client_admin.post("/modelos-campanha", json=_payload(itens=[_item(tipoTarefaId=tipo_arquivado.id)]))
    assert_erro_simples(resposta, 422)


def test_workflow_arquivado_rejeitado_em_vinculo_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    workflow_arquivado = _workflow_modelo(db_session, empresa, status="arquivado")
    resposta = client_admin.post(
        "/modelos-campanha", json=_payload(itens=[_item(workflowModeloId=workflow_arquivado.id)])
    )
    assert_erro_simples(resposta, 422)


def test_usuario_inativo_rejeitado_em_vinculo_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    usuario_inativo = _usuario(db_session, empresa, status="inativo")
    resposta = client_admin.post(
        "/modelos-campanha", json=_payload(itens=[_item(responsavelUsuarioId=usuario_inativo.id)])
    )
    assert_erro_simples(resposta, 422)


def test_departamento_arquivado_rejeitado_em_vinculo_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    departamento_arquivado = _departamento(db_session, empresa, status="arquivado")
    resposta = client_admin.post(
        "/modelos-campanha", json=_payload(itens=[_item(responsavelDepartamentoId=departamento_arquivado.id)])
    )
    assert_erro_simples(resposta, 422)


def test_departamento_inativo_aceito_em_vinculo_novo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    """Departamento é o único caso em que `inativo` é aceito em vínculo NOVO — mesma
    divergência já existente e deliberada em ProjetoService/DemandaService
    (`_ensure_departamento_valido` só recusa `arquivado`)."""
    departamento_inativo = _departamento(db_session, empresa, status="inativo")
    criado = _criar(client_admin, itens=[_item(responsavelDepartamentoId=departamento_inativo.id)])
    assert criado["itens"][0]["responsavelDepartamentoId"] == departamento_inativo.id


# --------------------------------------------------------------------------------------
# Preservação de referência histórica
# --------------------------------------------------------------------------------------


def test_vinculo_historico_preservado_quando_item_nao_muda(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    peca = _peca(db_session, empresa)
    criado = _criar(client_admin, itens=[_item(nome="Fixo", pecaId=peca.id)])
    item_id = criado["itens"][0]["id"]

    # Arquiva a Peça DEPOIS que o item já a referencia.
    peca.status = "arquivado"
    db_session.flush()

    # Edita outro campo do item, mandando o MESMO pecaId de volta — não deve rejeitar.
    resposta = client_admin.patch(
        f"/modelos-campanha/{criado['id']}",
        json={"itens": [{"id": item_id, "nome": "Fixo Renomeado", "pecaId": peca.id}]},
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["itens"][0]["pecaId"] == peca.id
    assert resposta.json()["itens"][0]["nome"] == "Fixo Renomeado"


def test_troca_para_entidade_arquivada_rejeitada(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    peca_ativa = _peca(db_session, empresa)
    peca_arquivada = _peca(db_session, empresa, status="arquivado")
    criado = _criar(client_admin, itens=[_item(nome="Item", pecaId=peca_ativa.id)])
    item_id = criado["itens"][0]["id"]

    # Tenta TROCAR pra uma Peça arquivada — precisa rejeitar (é vínculo novo pra essa Peça).
    resposta = client_admin.patch(
        f"/modelos-campanha/{criado['id']}",
        json={"itens": [{"id": item_id, "nome": "Item", "pecaId": peca_arquivada.id}]},
    )
    assert_erro_simples(resposta, 422)


def test_item_sem_id_e_tratado_como_novo_mesmo_com_referencia_igual_a_outro_item(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    """Um item sem `id` (ou com `id` que não bate com nenhum item atual) é sempre NOVO — a
    referência é validada, mesmo que o valor coincida com o de outro item que já existia."""
    peca_arquivada = _peca(db_session, empresa, status="arquivado")
    resposta = client_admin.post(
        "/modelos-campanha", json=_payload(itens=[_item(nome="Item novo", pecaId=peca_arquivada.id)])
    )
    assert_erro_simples(resposta, 422)


# --------------------------------------------------------------------------------------
# Update — atomicidade
# --------------------------------------------------------------------------------------


def test_update_com_item_invalido_faz_rollback_completo(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    criado = _criar(client_admin, itens=[_item(nome="Original")])

    peca_arquivada = _peca(db_session, empresa, status="arquivado")
    resposta = client_admin.patch(
        f"/modelos-campanha/{criado['id']}",
        json={"nome": "Não deveria persistir", "itens": [{"nome": "Novo item", "pecaId": peca_arquivada.id}]},
    )
    assert_erro_simples(resposta, 422)

    # Nada mudou — nem o nome, nem os itens.
    relido = client_admin.get(f"/modelos-campanha/{criado['id']}")
    assert relido.json()["nome"] == criado["nome"]
    assert [item["nome"] for item in relido.json()["itens"]] == ["Original"]


# --------------------------------------------------------------------------------------
# Auditoria
# --------------------------------------------------------------------------------------


def test_eventos_publicados(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin, itens=[_item(nome="Item")])
    client_admin.patch(f"/modelos-campanha/{criado['id']}", json={"nome": "Renomeado"})
    client_admin.post(f"/modelos-campanha/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    client_admin.post(f"/modelos-campanha/{criado['id']}/restaurar")

    eventos = (
        db_session.query(Evento)
        .filter(Evento.entidade_tipo == "modelo_campanha", Evento.entidade_id == criado["id"])
        .order_by(Evento.occurred_at.asc())
        .all()
    )
    tipos = [evento.tipo for evento in eventos]
    assert tipos == [
        "modelo_campanha.criado",
        "modelo_campanha.alterado",
        "modelo_campanha.arquivado",
        "modelo_campanha.restaurado",
    ]
    # Payload enxuto — nunca serializa os itens.
    for evento in eventos:
        assert "itens" not in evento.payload
        assert "senha" not in evento.payload
