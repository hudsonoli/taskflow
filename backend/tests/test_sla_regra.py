"""Testes do módulo SLA (Fase 2G.6B) — cadastro real, sem resolução/cálculo automático ainda
(ver app/models/sla_regra.py e relatório da Fase 2G.6A). Mesmo padrão de test_tipo_tarefa.py/
test_modelo_campanha.py.

Sem `GET /slas/diretorio` nesta fase (decisão da 2G.6B, item 15 — SLA nunca é escolhido
manualmente por outro formulário, o motor resolverá automaticamente na 2G.6C)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.sla_regra import SlaRegra
from tests.helpers.assertions import assert_conflito_arquivado, assert_erro_simples


def _payload(nome: str | None = None, **extra) -> dict:
    base = {
        "nome": nome or f"SLA {uuid.uuid4().hex[:8]}",
        "prazoPrimeiraRespostaQuantidade": 4,
        "prazoPrimeiraRespostaUnidade": "horas",
        "prazoResolucaoQuantidade": 48,
        "prazoResolucaoUnidade": "horas",
    }
    base.update(extra)
    return base


def _criar(client: TestClient, nome: str | None = None, **extra) -> dict:
    resposta = client.post("/slas", json=_payload(nome, **extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _departamento(db: Session, empresa: Empresa, *, status: str = "ativo") -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"dep-{sufixo}", codigo_referencia=f"D26{sufixo[:6]}",
        ano_referencia=26, sequencial_referencia=int(sufixo[:5], 16) % 900000, nome=f"Departamento {sufixo}",
        nome_normalizado=f"departamento {sufixo}", cor_identificacao="blue", status=status,
        created_at=agora, updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _cliente(db: Session, empresa: Empresa, *, status: str = "ativo") -> Cliente:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    cliente = Cliente(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"cli-{sufixo}", codigo_referencia=f"C26{sufixo[:6]}",
        ano_referencia=26, sequencial_referencia=int(sufixo[:5], 16) % 900000, nome=f"Cliente {sufixo}",
        nome_normalizado=f"cliente {sufixo}", tipo_documento="cnpj", cor_identificacao="blue", status=status,
        created_at=agora, updated_at=agora,
    )
    db.add(cliente)
    db.flush()
    return cliente


# --------------------------------------------------------------------------------------
# CRUD / RBAC (item 29)
# --------------------------------------------------------------------------------------


def test_admin_cria(client_admin: TestClient) -> None:
    resposta = client_admin.post("/slas", json=_payload(f"SLA Padrão {uuid.uuid4().hex[:8]}"))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "ativo"
    assert corpo["prioridadeRegra"] == 100  # default
    assert corpo["prioridadeAlvo"] is None
    assert corpo["departamentoId"] is None
    assert corpo["clienteId"] is None
    assert corpo["considerarApenasExpediente"] is True
    assert corpo["empresaId"]


def test_gestor_cria(client_gestor: TestClient) -> None:
    resposta = client_gestor.post("/slas", json=_payload())
    assert resposta.status_code == 201, resposta.text


def test_operador_nao_cria(client_operador: TestClient) -> None:
    resposta = client_operador.post("/slas", json=_payload())
    assert resposta.status_code == 403, resposta.text


def test_operador_nao_lista(client_operador: TestClient) -> None:
    resposta = client_operador.get("/slas")
    assert resposta.status_code == 403, resposta.text


def test_operador_nao_le_por_id(client_operador: TestClient, client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_operador.get(f"/slas/{criado['id']}")
    assert resposta.status_code == 403, resposta.text


def test_operador_nao_edita(client_operador: TestClient, client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_operador.patch(f"/slas/{criado['id']}", json={"nome": "x"})
    assert resposta.status_code == 403, resposta.text


def test_operador_nao_arquiva(client_operador: TestClient, client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_operador.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert resposta.status_code == 403, resposta.text


def test_criar_com_criterios_completos(client_admin: TestClient, empresa: Empresa, db_session: Session) -> None:
    departamento = _departamento(db_session, empresa)
    cliente = _cliente(db_session, empresa)
    criado = _criar(
        client_admin,
        "SLA Completo",
        prioridadeAlvo="alta",
        departamentoId=departamento.id,
        clienteId=cliente.id,
        prioridadeRegra=10,
        considerarApenasExpediente=False,
    )
    assert criado["prioridadeAlvo"] == "alta"
    assert criado["departamentoId"] == departamento.id
    assert criado["clienteId"] == cliente.id
    assert criado["prioridadeRegra"] == 10
    assert criado["considerarApenasExpediente"] is False


def test_listar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    listagem = client_admin.get("/slas")
    assert listagem.status_code == 200, listagem.text
    ids = [item["id"] for item in listagem.json()]
    assert criado["id"] in ids


def test_obter_por_id(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.get(f"/slas/{criado['id']}")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["id"] == criado["id"]


def test_editar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(
        f"/slas/{criado['id']}",
        json={"nome": "Nome Editado", "prazoResolucaoQuantidade": 72, "prazoResolucaoUnidade": "dias_uteis"},
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Nome Editado"
    assert corpo["prazoResolucaoQuantidade"] == 72
    assert corpo["prazoResolucaoUnidade"] == "dias_uteis"


def test_arquivar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "não usado mais"})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "arquivado"
    assert corpo["motivoArquivamento"] == "não usado mais"
    assert corpo["arquivadoAt"] is not None


def test_restaurar(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.post(f"/slas/{criado['id']}/restaurar")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "ativo"


def test_tenant_listagem_scoped(client_admin: TestClient, outra_empresa: Empresa, db_session: Session) -> None:
    meu = _criar(client_admin)

    agora = datetime.now(timezone.utc)
    de_outra = SlaRegra(
        id=str(uuid.uuid4()), empresa_id=outra_empresa.id, nome="SLA de outra empresa",
        nome_normalizado="sla de outra empresa", prioridade_regra=100,
        prazo_primeira_resposta_quantidade=4, prazo_primeira_resposta_unidade="horas",
        prazo_resolucao_quantidade=48, prazo_resolucao_unidade="horas",
        considerar_apenas_expediente=True, status="ativo", created_at=agora, updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()

    listagem = client_admin.get("/slas")
    assert listagem.status_code == 200, listagem.text
    ids = [item["id"] for item in listagem.json()]
    assert meu["id"] in ids
    assert de_outra.id not in ids


def test_cross_tenant_404_nao_403(client_admin: TestClient, outra_empresa: Empresa, db_session: Session) -> None:
    agora = datetime.now(timezone.utc)
    de_outra = SlaRegra(
        id=str(uuid.uuid4()), empresa_id=outra_empresa.id, nome="SLA de outra empresa 2",
        nome_normalizado="sla de outra empresa 2", prioridade_regra=100,
        prazo_primeira_resposta_quantidade=4, prazo_primeira_resposta_unidade="horas",
        prazo_resolucao_quantidade=48, prazo_resolucao_unidade="horas",
        considerar_apenas_expediente=True, status="ativo", created_at=agora, updated_at=agora,
    )
    db_session.add(de_outra)
    db_session.flush()

    resposta = client_admin.get(f"/slas/{de_outra.id}")
    assert resposta.status_code == 404, resposta.text


def test_nao_aceita_empresa_id_no_payload(client_admin: TestClient, outra_empresa: Empresa) -> None:
    resposta = client_admin.post("/slas", json=_payload(empresaId=str(outra_empresa.id)))
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Validação (item 30)
# --------------------------------------------------------------------------------------


def test_prioridade_alvo_valida(client_admin: TestClient) -> None:
    for prioridade in ("baixa", "media", "alta"):
        criado = _criar(client_admin, prioridadeAlvo=prioridade)
        assert criado["prioridadeAlvo"] == prioridade


def test_prioridade_alvo_invalida_422(client_admin: TestClient) -> None:
    resposta = client_admin.post("/slas", json=_payload(prioridadeAlvo="urgente"))
    assert resposta.status_code == 422, resposta.text


def test_prioridade_alvo_nula_significa_todas(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    assert criado["prioridadeAlvo"] is None


def test_prioridade_regra_menor_que_1_rejeitada(client_admin: TestClient) -> None:
    resposta = client_admin.post("/slas", json=_payload(prioridadeRegra=0))
    assert resposta.status_code == 422, resposta.text


def test_prioridade_regra_igual_a_1_aceita(client_admin: TestClient) -> None:
    criado = _criar(client_admin, prioridadeRegra=1)
    assert criado["prioridadeRegra"] == 1


def test_quantidade_primeira_resposta_zero_rejeitada(client_admin: TestClient) -> None:
    resposta = client_admin.post("/slas", json=_payload(prazoPrimeiraRespostaQuantidade=0))
    assert resposta.status_code == 422, resposta.text


def test_quantidade_resolucao_negativa_rejeitada(client_admin: TestClient) -> None:
    resposta = client_admin.post("/slas", json=_payload(prazoResolucaoQuantidade=-1))
    assert resposta.status_code == 422, resposta.text


def test_unidade_invalida_rejeitada(client_admin: TestClient) -> None:
    resposta = client_admin.post("/slas", json=_payload(prazoPrimeiraRespostaUnidade="semanas"))
    assert resposta.status_code == 422, resposta.text


def test_todas_unidades_v1_aceitas(client_admin: TestClient) -> None:
    for unidade in ("minutos", "horas", "dias_corridos", "dias_uteis"):
        criado = _criar(client_admin, prazoPrimeiraRespostaUnidade=unidade, prazoResolucaoUnidade=unidade)
        assert criado["prazoPrimeiraRespostaUnidade"] == unidade
        assert criado["prazoResolucaoUnidade"] == unidade


def test_status_invalido_rejeitado_no_update(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"status": "excluido"})
    assert resposta.status_code == 422, resposta.text


def test_status_arquivado_rejeitado_via_patch(client_admin: TestClient) -> None:
    """`arquivado` só pela rota dedicada — mesmo padrão de TipoTarefaUpdate."""
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"status": "arquivado"})
    assert resposta.status_code == 422, resposta.text


def test_cliente_cross_tenant_rejeitado(client_admin: TestClient, outra_empresa: Empresa, db_session: Session) -> None:
    cliente_alheio = _cliente(db_session, outra_empresa)
    resposta = client_admin.post("/slas", json=_payload(clienteId=cliente_alheio.id))
    assert resposta.status_code == 422, resposta.text


def test_departamento_cross_tenant_rejeitado(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    departamento_alheio = _departamento(db_session, outra_empresa)
    resposta = client_admin.post("/slas", json=_payload(departamentoId=departamento_alheio.id))
    assert resposta.status_code == 422, resposta.text


def test_departamento_arquivado_em_novo_vinculo_rejeitado(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    departamento_arquivado = _departamento(db_session, empresa, status="arquivado")
    resposta = client_admin.post("/slas", json=_payload(departamentoId=departamento_arquivado.id))
    assert resposta.status_code == 422, resposta.text


def test_cliente_arquivado_em_novo_vinculo_rejeitado(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    cliente_arquivado = _cliente(db_session, empresa, status="arquivado")
    resposta = client_admin.post("/slas", json=_payload(clienteId=cliente_arquivado.id))
    assert resposta.status_code == 422, resposta.text


def test_departamento_inativo_em_novo_vinculo_aceito(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    """Só `arquivado` bloqueia vínculo novo — `inativo` é aceito (mesmo padrão de
    ProjetoService/ProjetoModeloCampanhaService para Departamento)."""
    departamento_inativo = _departamento(db_session, empresa, status="inativo")
    criado = _criar(client_admin, departamentoId=departamento_inativo.id)
    assert criado["departamentoId"] == departamento_inativo.id


def test_ator_nunca_vem_do_payload(client_admin: TestClient) -> None:
    resposta = client_admin.post("/slas", json=_payload(arquivadoPorUsuarioId=str(uuid.uuid4())))
    assert resposta.status_code == 422, resposta.text


def test_nome_duplicado_mesma_empresa_rejeitado(client_admin: TestClient) -> None:
    nome = f"Duplicado {uuid.uuid4().hex[:8]}"
    primeiro = client_admin.post("/slas", json=_payload(nome))
    assert primeiro.status_code == 201, primeiro.text

    segundo = client_admin.post("/slas", json=_payload(f"  {nome.upper()}  "))
    assert_erro_simples(segundo, 409)


def test_nome_duplicado_de_arquivado_409_oferece_restaurar(client_admin: TestClient) -> None:
    nome = f"Duplicado Arquivado {uuid.uuid4().hex[:8]}"
    criado = _criar(client_admin, nome)
    arquivar = client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "teste"})
    assert arquivar.status_code == 200, arquivar.text

    tentativa = client_admin.post("/slas", json=_payload(nome))
    detail = assert_conflito_arquivado(tentativa, code="SLA_REGRA_ARQUIVADA_EXISTENTE")
    assert detail["slaRegraArquivadaId"] == criado["id"]


# --------------------------------------------------------------------------------------
# Lifecycle (item 31)
# --------------------------------------------------------------------------------------


def test_ativo_para_inativo(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"status": "inativo"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "inativo"


def test_inativo_para_ativo(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.patch(f"/slas/{criado['id']}", json={"status": "inativo"})
    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"status": "ativo"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "ativo"


def test_ativo_para_arquivado_e_depois_restaurado(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    arquivar = client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert arquivar.json()["status"] == "arquivado"

    restaurar = client_admin.post(f"/slas/{criado['id']}/restaurar")
    assert restaurar.json()["status"] == "ativo"


def test_inativo_para_arquivado_e_depois_restaurado_volta_ativo(client_admin: TestClient) -> None:
    """Restaura sempre para `ativo`, mesmo vindo de `inativo` antes de arquivar — mesmo
    comportamento de TipoTarefa/WorkflowModelo/Departamento (não volta pro status anterior)."""
    criado = _criar(client_admin)
    client_admin.patch(f"/slas/{criado['id']}", json={"status": "inativo"})
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    restaurar = client_admin.post(f"/slas/{criado['id']}/restaurar")
    assert restaurar.status_code == 200, restaurar.text
    assert restaurar.json()["status"] == "ativo"


def test_arquivar_ja_arquivado_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    segunda = client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "y"})
    assert_erro_simples(segunda, 409)


def test_restaurar_nao_arquivado_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.post(f"/slas/{criado['id']}/restaurar")
    assert_erro_simples(resposta, 409)


def test_editar_status_de_arquivado_via_patch_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"status": "ativo"})
    assert_erro_simples(resposta, 409)


def test_editar_outro_campo_de_arquivado_permitido(client_admin: TestClient) -> None:
    """Arquivar não congela o registro inteiro — só bloqueia mudar `status` fora da rota
    dedicada (mesmo padrão de TipoTarefaService/ModeloCampanhaService)."""
    criado = _criar(client_admin)
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"descricao": "Nova descrição"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["descricao"] == "Nova descrição"
    assert resposta.json()["status"] == "arquivado"


def test_listagem_padrao_exclui_arquivado(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    listagem = client_admin.get("/slas")
    ids = [item["id"] for item in listagem.json()]
    assert criado["id"] not in ids


def test_listagem_com_filtro_status_arquivado_mostra(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    listagem = client_admin.get("/slas", params={"status": "arquivado"})
    ids = [item["id"] for item in listagem.json()]
    assert criado["id"] in ids


def test_arquivado_continua_legivel_por_id(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    resposta = client_admin.get(f"/slas/{criado['id']}")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "arquivado"


def test_busca_por_nome(client_admin: TestClient) -> None:
    unico = f"Ubuntu{uuid.uuid4().hex[:8]}"
    criado = _criar(client_admin, f"SLA {unico}")

    listagem = client_admin.get("/slas", params={"search": unico})
    assert listagem.status_code == 200, listagem.text
    ids = [item["id"] for item in listagem.json()]
    assert criado["id"] in ids


# --------------------------------------------------------------------------------------
# Preservação de referência (item 32)
# --------------------------------------------------------------------------------------


def test_editar_outro_campo_com_referencia_ja_arquivada_nao_exige_troca(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    departamento = _departamento(db_session, empresa)
    criado = _criar(client_admin, departamentoId=departamento.id)

    # Departamento é arquivado DEPOIS de já vinculado à regra.
    departamento.status = "arquivado"
    db_session.flush()

    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"descricao": "Ajuste sem trocar departamento"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["departamentoId"] == departamento.id
    assert resposta.json()["descricao"] == "Ajuste sem trocar departamento"


def test_trocar_para_referencia_invalida_rejeitado(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    departamento_valido = _departamento(db_session, empresa)
    departamento_arquivado = _departamento(db_session, empresa, status="arquivado")
    criado = _criar(client_admin, departamentoId=departamento_valido.id)

    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"departamentoId": departamento_arquivado.id})
    assert resposta.status_code == 422, resposta.text


def test_trocar_para_referencia_valida_aceito(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    departamento_1 = _departamento(db_session, empresa)
    departamento_2 = _departamento(db_session, empresa)
    criado = _criar(client_admin, departamentoId=departamento_1.id)

    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"departamentoId": departamento_2.id})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["departamentoId"] == departamento_2.id


def test_manter_mesma_referencia_nao_revalida(
    client_admin: TestClient, empresa: Empresa, db_session: Session
) -> None:
    departamento = _departamento(db_session, empresa)
    criado = _criar(client_admin, departamentoId=departamento.id)
    departamento.status = "arquivado"
    db_session.flush()

    # Reenviar o MESMO departamentoId (já arquivado) não deve ser tratado como troca.
    resposta = client_admin.patch(f"/slas/{criado['id']}", json={"departamentoId": departamento.id})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["departamentoId"] == departamento.id


# --------------------------------------------------------------------------------------
# Eventos
# --------------------------------------------------------------------------------------


def test_eventos_publicados(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)
    client_admin.patch(f"/slas/{criado['id']}", json={"nome": "Renomeado"})
    client_admin.post(f"/slas/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    client_admin.post(f"/slas/{criado['id']}/restaurar")

    eventos = (
        db_session.query(Evento)
        .filter(Evento.entidade_tipo == "sla_regra", Evento.entidade_id == criado["id"])
        .order_by(Evento.occurred_at.asc())
        .all()
    )
    tipos = [evento.tipo for evento in eventos]
    assert tipos == [
        "sla_regra.criada",
        "sla_regra.alterada",
        "sla_regra.arquivada",
        "sla_regra.restaurada",
    ]
    for evento in eventos:
        assert "senha" not in evento.payload
