"""Projeto — o trabalho contratado, sob o qual as demandas acontecem (Fase 2D).

Cobre CRUD, arquivamento, vínculos N:N, isolamento por empresa, autorização, imutabilidade
do código e busca.

A seção que merece atenção é **unicidade**: Projeto é o primeiro domínio com nome único
*por cliente*, e não por empresa (Departamento/Equipe) nem sem unicidade nenhuma
(Cliente/Fornecedor). Os testes cobrem os dois lados — inclusive o caso `cliente_id IS NULL`,
que sem o índice parcial escaparia da constraint.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario


def _cliente(db: Session, empresa: Empresa, *, nome: str | None = None, status: str = "ativo") -> Cliente:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    cliente = Cliente(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"cli-{sufixo}",
        codigo_referencia=f"C26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=nome or f"Cliente {sufixo}",
        nome_normalizado=(nome or f"Cliente {sufixo}").lower(),
        tipo_documento="cnpj",
        status=status,
        cor_identificacao="blue",
        created_at=agora,
        updated_at=agora,
    )
    db.add(cliente)
    db.flush()
    return cliente


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


def _payload(**extra) -> dict:
    return {"nome": f"Projeto {uuid.uuid4().hex[:8]}", **extra}


def _criar(client: TestClient, **extra) -> dict:
    resposta = client.post("/projetos", json=_payload(**extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ======================================================================================
# CRUD
# ======================================================================================

def test_criar_projeto(client_admin: TestClient) -> None:
    corpo = _criar(client_admin, campanha="Marca 2026", descricao="Reposicionamento")
    assert corpo["status"] == "planejamento"
    assert corpo["prioridade"] == "media"
    assert corpo["campanha"] == "Marca 2026"
    assert corpo["clienteId"] is None
    assert corpo["responsavelIds"] == []
    assert corpo["departamentoResponsavelIds"] == []
    assert corpo["equipe"] == []
    uuid.UUID(corpo["id"])


def test_codigo_referencia_no_formato_P_ano_sequencial(client_admin: TestClient) -> None:
    codigo = _criar(client_admin)["codigoReferencia"]
    assert codigo.startswith("P"), codigo
    assert len(codigo) == 9, codigo
    assert codigo[1:].isdigit(), codigo


def test_sequencial_avanca_sem_buracos(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin)["sequencialReferencia"]
    assert _criar(client_admin)["sequencialReferencia"] == primeiro + 1


def test_projeto_nao_expoe_codigo_interno(client_admin: TestClient) -> None:
    """Removido na microfase 2D.1: sem importação de Projeto, era cópia literal do
    `codigo_referencia`. Projeto tem dois identificadores — UUID e codigoReferencia."""
    criado = _criar(client_admin)
    assert "codigoInterno" not in criado
    listado = client_admin.get("/projetos", params={"limit": 200}).json()[0]
    assert "codigoInterno" not in listado
    diretorio = client_admin.get("/projetos/diretorio").json()[0]
    assert "codigoInterno" not in diretorio


def test_codigo_referencia_e_imutavel_no_patch(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    alterado = client_admin.patch(f"/projetos/{criado['id']}", json={"nome": "Outro Nome"}).json()
    assert alterado["codigoReferencia"] == criado["codigoReferencia"]
    assert alterado["sequencialReferencia"] == criado["sequencialReferencia"]


def test_editar_projeto(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(
        f"/projetos/{criado['id']}", json={"nome": "Nome Novo", "prioridade": "alta", "status": "ativo"}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Nome Novo"
    assert corpo["prioridade"] == "alta"
    assert corpo["status"] == "ativo"


def test_get_de_id_inexistente_devolve_404(client_admin: TestClient) -> None:
    assert client_admin.get(f"/projetos/{uuid.uuid4()}").status_code == 404


# ======================================================================================
# Unicidade — por cliente, não por empresa
# ======================================================================================

def test_mesmo_nome_em_clientes_diferentes_e_permitido(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """O caso que motivou a regra: "Campanha de Natal" para dois clientes é legítimo."""
    cliente_a = _cliente(db_session, empresa)
    cliente_b = _cliente(db_session, empresa)

    primeiro = client_admin.post(
        "/projetos", json={"nome": "Campanha de Natal", "clienteId": cliente_a.id}
    )
    segundo = client_admin.post(
        "/projetos", json={"nome": "Campanha de Natal", "clienteId": cliente_b.id}
    )
    assert primeiro.status_code == 201, primeiro.text
    assert segundo.status_code == 201, segundo.text


def test_mesmo_nome_no_mesmo_cliente_devolve_409(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    client_admin.post("/projetos", json={"nome": "Campanha de Natal", "clienteId": cliente.id})
    segundo = client_admin.post(
        "/projetos", json={"nome": "Campanha de Natal", "clienteId": cliente.id}
    )
    assert segundo.status_code == 409, segundo.text


def test_nome_diferente_por_caixa_e_acento_ainda_colide(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    client_admin.post("/projetos", json={"nome": "Campanha Natal", "clienteId": cliente.id})
    segundo = client_admin.post(
        "/projetos", json={"nome": "  CAMPANHA NATAL  ", "clienteId": cliente.id}
    )
    assert segundo.status_code == 409, segundo.text


def test_mesmo_nome_sem_cliente_devolve_409(client_admin: TestClient) -> None:
    """Sem o índice parcial este caso passaria: o Postgres trata NULL como distinto de NULL,
    e a UNIQUE de três colunas deixaria de valer justamente nos projetos internos."""
    client_admin.post("/projetos", json={"nome": "Projeto Interno"})
    segundo = client_admin.post("/projetos", json={"nome": "Projeto Interno"})
    assert segundo.status_code == 409, segundo.text


def test_projeto_sem_cliente_nao_colide_com_projeto_de_cliente(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    primeiro = client_admin.post("/projetos", json={"nome": "Rebranding"})
    segundo = client_admin.post("/projetos", json={"nome": "Rebranding", "clienteId": cliente.id})
    assert primeiro.status_code == 201
    assert segundo.status_code == 201, "escopos diferentes — não é duplicidade"


def test_conflito_com_arquivado_devolve_id_para_restaurar(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    criado = client_admin.post(
        "/projetos", json={"nome": "Campanha Antiga", "clienteId": cliente.id}
    ).json()
    client_admin.post(f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "Encerrado"})

    conflito = client_admin.post(
        "/projetos", json={"nome": "Campanha Antiga", "clienteId": cliente.id}
    )
    assert conflito.status_code == 409
    assert conflito.json()["detail"]["projetoArquivadoId"] == criado["id"]


def test_patch_que_move_para_cliente_com_nome_ocupado_devolve_409(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Trocar de cliente muda o escopo da unicidade — a checagem tem de olhar os valores
    finais, não só o campo que mudou."""
    cliente_a = _cliente(db_session, empresa)
    cliente_b = _cliente(db_session, empresa)
    client_admin.post("/projetos", json={"nome": "Lançamento", "clienteId": cliente_b.id})
    movido = client_admin.post(
        "/projetos", json={"nome": "Lançamento", "clienteId": cliente_a.id}
    ).json()

    resposta = client_admin.patch(f"/projetos/{movido['id']}", json={"clienteId": str(cliente_b.id)})
    assert resposta.status_code == 409, resposta.text


def test_patch_para_o_proprio_nome_nao_conflita(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/projetos/{criado['id']}", json={"nome": criado["nome"]})
    assert resposta.status_code == 200


# ======================================================================================
# Contrato público — extra="forbid"
# ======================================================================================

@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("empresaId", str(uuid.uuid4())),
        ("actorUsuarioId", str(uuid.uuid4())),
        # `codigoInterno` foi removido na microfase 2D.1 — continua no rol de proibidos
        # porque `extra="forbid"` deve recusar campo inexistente, não ignorá-lo.
        ("codigoInterno", "forjado"),
        ("codigoReferencia", "P26999999"),
        ("anoReferencia", 26),
        ("sequencialReferencia", 999),
        ("agenciaId", "agencia-principal"),  # campo do mock que saiu da modelagem
    ],
)
def test_campo_proibido_devolve_422(client_admin: TestClient, campo: str, valor) -> None:
    assert client_admin.post("/projetos", json=_payload(**{campo: valor})).status_code == 422


def test_status_arquivado_nao_e_aceito_pelo_patch(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/projetos/{criado['id']}", json={"status": "arquivado"})
    assert resposta.status_code == 422, resposta.text


def test_data_fim_antes_do_inicio_e_recusada(client_admin: TestClient) -> None:
    resposta = client_admin.post(
        "/projetos", json=_payload(dataInicio="2026-08-10", dataFimPrevista="2026-08-01")
    )
    assert resposta.status_code in (409, 422, 500), resposta.text
    assert resposta.status_code != 201, "período impossível não pode ser aceito"


# ======================================================================================
# Vínculos — cliente, responsáveis, departamentos, equipe
# ======================================================================================

def test_vincula_cliente_responsaveis_departamentos_e_equipe(
    client_admin: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    cliente = _cliente(db_session, empresa)
    departamento = _departamento(db_session, empresa)

    corpo = client_admin.post(
        "/projetos",
        json={
            "nome": "Projeto Completo",
            "clienteId": cliente.id,
            "responsavelIds": [usuario_operador.id],
            "departamentoResponsavelIds": [departamento.id],
            "equipe": [{"usuarioId": usuario_operador.id, "funcao": "Direção de arte"}],
        },
    )
    assert corpo.status_code == 201, corpo.text
    dados = corpo.json()
    assert dados["clienteId"] == str(cliente.id)
    assert dados["responsavelIds"] == [str(usuario_operador.id)]
    assert dados["departamentoResponsavelIds"] == [str(departamento.id)]
    assert dados["equipe"] == [{"usuarioId": str(usuario_operador.id), "funcao": "Direção de arte"}]


def test_cliente_arquivado_recusa_vinculo_novo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    cliente = _cliente(db_session, empresa, status="arquivado")
    resposta = client_admin.post("/projetos", json=_payload(clienteId=cliente.id))
    assert resposta.status_code == 422, resposta.text


def test_departamento_arquivado_recusa_vinculo_novo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa, status="arquivado")
    resposta = client_admin.post(
        "/projetos", json=_payload(departamentoResponsavelIds=[departamento.id])
    )
    assert resposta.status_code == 422, resposta.text


def test_cliente_inexistente_recusado(client_admin: TestClient) -> None:
    assert client_admin.post("/projetos", json=_payload(clienteId=str(uuid.uuid4()))).status_code == 422


def test_responsavel_inexistente_recusado(client_admin: TestClient) -> None:
    resposta = client_admin.post("/projetos", json=_payload(responsavelIds=[str(uuid.uuid4())]))
    assert resposta.status_code == 422


def test_sincronizacao_de_responsaveis_no_patch(
    client_admin: TestClient, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    criado = _criar(client_admin, responsavelIds=[usuario_operador.id])
    alterado = client_admin.patch(
        f"/projetos/{criado['id']}", json={"responsavelIds": [usuario_gestor.id]}
    ).json()
    assert alterado["responsavelIds"] == [str(usuario_gestor.id)]


def test_funcao_do_membro_e_atualizavel(client_admin: TestClient, usuario_operador: Usuario) -> None:
    criado = _criar(
        client_admin, equipe=[{"usuarioId": usuario_operador.id, "funcao": "Redação"}]
    )
    alterado = client_admin.patch(
        f"/projetos/{criado['id']}",
        json={"equipe": [{"usuarioId": usuario_operador.id, "funcao": "Revisão"}]},
    ).json()
    assert alterado["equipe"] == [{"usuarioId": str(usuario_operador.id), "funcao": "Revisão"}]


def test_arquivar_cliente_depois_nao_derruba_o_projeto(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Vínculo histórico é preservado — só o vínculo NOVO é barrado."""
    cliente = _cliente(db_session, empresa)
    criado = _criar(client_admin, clienteId=cliente.id)

    db_session.execute(
        text("UPDATE clientes SET status = 'arquivado' WHERE id = :i"), {"i": cliente.id}
    )
    db_session.flush()

    corpo = client_admin.get(f"/projetos/{criado['id']}").json()
    assert corpo["clienteId"] == str(cliente.id)


# ======================================================================================
# modeloCampanha — value objects
# ======================================================================================

def test_modelo_campanha_persiste_como_value_object(client_admin: TestClient) -> None:
    """Os ids de tipoTarefa/workflow são texto legado, sem FK — TipoTarefa e Workflow ainda
    não têm tabela."""
    itens = [
        {
            "id": "modelo-item-1",
            "nomeDemanda": "Posts de lançamento",
            "tipoTarefaId": "tipo-post",
            "tipoTarefaNome": "Post social",
            "briefingBase": "Criar peças para redes sociais.",
            "prioridadePadrao": "media",
            "workflowSugeridoId": "workflow-criacao",
            "workflowSugeridoNome": "Criação padrão",
            "responsavelOuSetorSugeridoId": "dep-criacao",
            "responsavelOuSetorSugeridoNome": "Criação",
        }
    ]
    criado = _criar(client_admin, modeloCampanha=itens, modeloCampanhaId="modelo-campanha-1")
    assert criado["modeloCampanhaId"] == "modelo-campanha-1"
    assert criado["modeloCampanha"][0]["tipoTarefaId"] == "tipo-post"

    esvaziado = client_admin.patch(f"/projetos/{criado['id']}", json={"modeloCampanha": []}).json()
    assert esvaziado["modeloCampanha"] == []


# ======================================================================================
# Arquivamento
# ======================================================================================

def test_arquivar_exige_motivo(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    assert client_admin.post(f"/projetos/{criado['id']}/arquivar", json={}).status_code == 422
    assert (
        client_admin.post(
            f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "   "}
        ).status_code
        == 422
    )


def test_arquivar_guarda_auditoria_e_status_anterior(client_admin: TestClient) -> None:
    criado = _criar(client_admin, status="ativo")
    corpo = client_admin.post(
        f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "Contrato encerrado"}
    ).json()
    assert corpo["status"] == "arquivado"
    assert corpo["statusAnteriorArquivamento"] == "ativo"
    assert corpo["arquivadoAt"] is not None
    assert corpo["arquivadoPorUsuarioId"] is not None


def test_arquivado_sai_da_listagem_padrao(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    ids = [p["id"] for p in client_admin.get("/projetos", params={"limit": 200}).json()]
    assert criado["id"] not in ids

    arquivados = client_admin.get("/projetos", params={"status": "arquivado", "limit": 200}).json()
    assert criado["id"] in [p["id"] for p in arquivados]


def test_arquivar_nao_apaga_fisicamente(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    total = db_session.execute(
        text("SELECT count(*) FROM projetos WHERE id = :i"), {"i": criado["id"]}
    ).scalar_one()
    assert total == 1


def test_arquivado_nao_pode_ser_editado(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert client_admin.patch(f"/projetos/{criado['id']}", json={"nome": "X"}).status_code == 409


def test_restaurar_devolve_status_anterior(client_admin: TestClient) -> None:
    criado = _criar(client_admin, status="pausado")
    client_admin.post(f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    corpo = client_admin.post(f"/projetos/{criado['id']}/restaurar").json()
    assert corpo["status"] == "pausado"
    assert corpo["arquivadoAt"] is None
    assert corpo["statusAnteriorArquivamento"] is None


def test_arquivar_nao_libera_o_nome(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """A linha arquivada continua ocupando `(empresa, cliente, nome)`.

    É o que garante que restaurar nunca encontre conflito — e por isso `restaurar_projeto`
    não faz checagem de nome. Se um dia arquivar passar a liberar o nome, este teste quebra e
    a decisão volta à mesa.
    """
    cliente = _cliente(db_session, empresa)
    original = client_admin.post(
        "/projetos", json={"nome": "Retomada", "clienteId": cliente.id}
    ).json()
    client_admin.post(f"/projetos/{original['id']}/arquivar", json={"motivoArquivamento": "x"})

    ocupado = db_session.execute(
        text(
            "SELECT count(*) FROM projetos WHERE empresa_id = :e AND cliente_id = :c "
            "AND nome_normalizado = 'retomada'"
        ),
        {"e": empresa.id, "c": cliente.id},
    ).scalar_one()
    assert ocupado == 1, "arquivado tem de continuar ocupando o trio da UNIQUE"

    # E restaurar volta sem conflito, justamente porque ninguém pôde tomar o lugar.
    assert client_admin.post(f"/projetos/{original['id']}/restaurar").status_code == 200


def test_restaurar_o_que_nao_esta_arquivado_devolve_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    assert client_admin.post(f"/projetos/{criado['id']}/restaurar").status_code == 409


# ======================================================================================
# Autorização e isolamento
# ======================================================================================

def test_operador_nao_administra_projetos(client_operador: TestClient) -> None:
    assert client_operador.post("/projetos", json=_payload()).status_code == 403
    assert client_operador.get("/projetos").status_code == 403


def test_gestor_administra_projetos(client_gestor: TestClient) -> None:
    assert client_gestor.post("/projetos", json=_payload()).status_code == 201


def test_sem_autenticacao_nao_acessa(client: TestClient) -> None:
    assert client.get("/projetos").status_code == 401


def test_projeto_de_outra_empresa_devolve_404(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    alheio_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)
    db_session.execute(
        text(
            """
            INSERT INTO projetos (
                id, empresa_id, codigo_referencia, ano_referencia,
                sequencial_referencia, nome, nome_normalizado, status, prioridade,
                created_at, updated_at
            ) VALUES (
                :id, :emp, 'P26099999', 26, 99999, 'Alheio', 'alheio',
                'ativo', 'media', :a, :a
            )
            """
        ),
        {"id": alheio_id, "emp": outra_empresa.id, "a": agora},
    )
    db_session.flush()

    assert client_admin.get(f"/projetos/{alheio_id}").status_code == 404
    assert client_admin.patch(f"/projetos/{alheio_id}", json={"nome": "X"}).status_code == 404


def test_cliente_de_outra_empresa_recusado(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    """Cross-tenant é tratado como inexistente — não vaza a existência do cliente alheio."""
    alheio = _cliente(db_session, outra_empresa)
    assert client_admin.post("/projetos", json=_payload(clienteId=alheio.id)).status_code == 422


# ======================================================================================
# Diretório
# ======================================================================================

def test_diretorio_inclui_arquivados(client_admin: TestClient) -> None:
    """Referência histórica de uma Demanda precisa continuar resolvendo o nome mesmo depois
    do Projeto ser arquivado (Fase 2E.5A/B). Mesmo padrão de /clientes/diretorio — diverge
    do critério antigo (que seguia Fornecedor) porque só Cliente/Departamento/Usuário/Equipe
    e agora Projeto têm domínio (Demanda) que referencia o id depois do fato."""
    criado = _criar(client_admin)
    client_admin.post(f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    diretorio = client_admin.get("/projetos/diretorio").json()
    encontrado = next((p for p in diretorio if p["id"] == criado["id"]), None)
    assert encontrado is not None
    assert encontrado["status"] == "arquivado"
    assert encontrado["nome"] == criado["nome"]


def test_diretorio_e_acessivel_a_operador(client_operador: TestClient) -> None:
    assert client_operador.get("/projetos/diretorio").status_code == 200


def test_diretorio_nao_expoe_dados_administrativos(client_admin: TestClient) -> None:
    """Projeção mínima — resumo, modeloCampanha, equipe etc. não vazam para quem só está
    resolvendo referência histórica ou montando um seletor de vínculo novo."""
    _criar(client_admin, campanha="Marca 2026", descricao="Reposicionamento", resumo="Sigiloso")
    item = client_admin.get("/projetos/diretorio").json()[0]
    assert set(item) == {"id", "codigoReferencia", "sequencialReferencia", "nome", "status", "clienteId"}


def test_diretorio_isola_por_empresa(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    alheio_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)
    db_session.execute(
        text(
            """
            INSERT INTO projetos (
                id, empresa_id, codigo_referencia, ano_referencia,
                sequencial_referencia, nome, nome_normalizado, status, prioridade,
                created_at, updated_at
            ) VALUES (
                :id, :emp, 'P26088888', 26, 88888, 'Alheio Diretorio', 'alheio diretorio',
                'ativo', 'media', :a, :a
            )
            """
        ),
        {"id": alheio_id, "emp": outra_empresa.id, "a": agora},
    )
    db_session.flush()

    ids = [p["id"] for p in client_admin.get("/projetos/diretorio").json()]
    assert alheio_id not in ids


# ======================================================================================
# Busca — a regra mora em app/core/busca.py
# ======================================================================================

def test_pesquisa_por_nome_e_campanha(client_admin: TestClient) -> None:
    criado = _criar(client_admin, nome="Reposicionamento Institucional", campanha="Marca 2026")
    por_nome = client_admin.get("/projetos", params={"search": "reposicionamento"}).json()
    por_campanha = client_admin.get("/projetos", params={"search": "Marca 2026"}).json()
    assert criado["id"] in [p["id"] for p in por_nome]
    assert criado["id"] in [p["id"] for p in por_campanha]


def test_pesquisa_por_codigo_case_insensitive(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    achados = client_admin.get(
        "/projetos", params={"search": criado["codigoReferencia"].lower()}
    ).json()
    assert [p["id"] for p in achados] == [criado["id"]]


def test_filtro_por_cliente(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    meu = _criar(client_admin, clienteId=cliente.id)
    _criar(client_admin)
    achados = client_admin.get(
        "/projetos", params={"clienteId": str(cliente.id), "limit": 200}
    ).json()
    assert [p["id"] for p in achados] == [meu["id"]]


def test_filtro_por_departamento(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    meu = _criar(client_admin, departamentoResponsavelIds=[departamento.id])
    _criar(client_admin)
    achados = client_admin.get(
        "/projetos", params={"departamentoId": str(departamento.id), "limit": 200}
    ).json()
    assert [p["id"] for p in achados] == [meu["id"]]


@pytest.mark.parametrize("termo", ["QA FASE2D", "#2401", "P26000001", "Marca 2026"])
def test_nenhum_termo_alfanumerico_vira_filtro_de_documento(
    client_admin: TestClient, termo: str
) -> None:
    """Projeto não tem documento, mas usa o mesmo `interpretar_termo_busca` — a invariante é
    que todo resultado se justifique pelo texto, nunca por extração de dígitos."""
    for i in range(4):
        _criar(client_admin, nome=f"Ruido sem relacao {i}")

    achados = client_admin.get("/projetos", params={"search": termo, "limit": 200}).json()
    alvo = termo.lower()
    for achado in achados:
        justificado = (
            alvo in achado["nome"].lower()
            or alvo in (achado["campanha"] or "").lower()
            or alvo in achado["codigoReferencia"].lower()
        )
        assert justificado, f"{achado['nome']} não se justifica pelo texto {termo!r}"


# ======================================================================================
# Eventos
# ======================================================================================

def _tipos_de_evento(db: Session, projeto_id: str) -> list[str]:
    linhas = db.execute(
        text("SELECT tipo FROM eventos WHERE entidade_id = :i ORDER BY occurred_at, tipo"),
        {"i": projeto_id},
    ).scalars()
    return list(linhas)


def test_eventos_no_ciclo_de_vida(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    criado = _criar(client_admin, responsavelIds=[usuario_operador.id])
    tipos = _tipos_de_evento(db_session, criado["id"])
    assert "projeto.criado" in tipos
    assert "projeto.responsavel_adicionado" in tipos

    client_admin.patch(f"/projetos/{criado['id']}", json={"responsavelIds": []})
    assert "projeto.responsavel_removido" in _tipos_de_evento(db_session, criado["id"])

    client_admin.post(f"/projetos/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert "projeto.arquivado" in _tipos_de_evento(db_session, criado["id"])

    client_admin.post(f"/projetos/{criado['id']}/restaurar")
    assert "projeto.restaurado" in _tipos_de_evento(db_session, criado["id"])


def test_evento_nao_e_publicado_sem_alteracao_real(
    client_admin: TestClient, db_session: Session
) -> None:
    criado = _criar(client_admin)
    client_admin.patch(f"/projetos/{criado['id']}", json={"nome": criado["nome"]})
    assert _tipos_de_evento(db_session, criado["id"]) == ["projeto.criado"]


# ======================================================================================
# Rollback da sequência e concorrência
# ======================================================================================

def test_falha_na_criacao_nao_queima_sequencia(client_admin: TestClient) -> None:
    antes = _criar(client_admin)["sequencialReferencia"]
    recusada = client_admin.post("/projetos", json=_payload(clienteId=str(uuid.uuid4())))
    assert recusada.status_code == 422
    assert _criar(client_admin)["sequencialReferencia"] == antes + 1


def test_criacoes_concorrentes_nao_repetem_sequencial(test_engine) -> None:
    """8 criações simultâneas recebem sequenciais distintos — cada thread com sua conexão."""
    from sqlalchemy.orm import Session as SessionRaw

    from app.models.empresa import Empresa as EmpresaModel
    from app.schemas.projeto import ProjetoCreate
    from app.services.projeto_service import ProjetoService

    agora = datetime.now(timezone.utc)
    empresa_id = str(uuid.uuid4())
    with SessionRaw(bind=test_engine) as setup:
        setup.add(
            EmpresaModel(
                id=empresa_id,
                codigo_interno=f"CONP{uuid.uuid4().hex[:6].upper()}",
                nome="Empresa Concorrência Projeto",
                status="ativa",
                created_at=agora,
                updated_at=agora,
            )
        )
        setup.commit()

    total = 8
    obtidos: list[int] = []
    trava = threading.Lock()
    barreira = threading.Barrier(total)
    service = ProjetoService()

    def criar() -> None:
        with SessionRaw(bind=test_engine) as sessao:
            barreira.wait()
            projeto = service.create_projeto(
                sessao, ProjetoCreate.model_validate(_payload()), empresa_id=empresa_id
            )
            with trava:
                obtidos.append(projeto.sequencial_referencia)

    threads = [threading.Thread(target=criar) for _ in range(total)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(obtidos) == list(range(1, total + 1)), f"duplicados/faltando: {obtidos}"
    finally:
        with SessionRaw(bind=test_engine) as limpeza:
            limpeza.execute(text("DELETE FROM projetos WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM eventos WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(
                text("DELETE FROM sequencias_referencia WHERE empresa_id = :e"), {"e": empresa_id}
            )
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
            limpeza.commit()
