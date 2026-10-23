"""P1_WORKFLOW_COLOR — cor (identidade visual) do modelo de workflow: HEX `#RRGGBB` opcional, normalizado em maiúsculas, `null` = sem cor personalizada.

Prova: create/update/read/diretório, normalização, rejeição de tudo que não é HEX canônico (nome CSS, `#FFF`, rgb(), injeção), compatibilidade com payload antigo, remoção, RBAC (a mesma autoridade de editar o
Workflow), tenant, evento de alteração pelo mecanismo existente, constraint do banco e que a cor NÃO entra no snapshot das Demandas.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.evento import Evento
from tests.test_workflow_modelo import _etapa, _payload, _workflow_modelo_de_outra_empresa

URL = "/workflow-modelos"


def _criar(client: TestClient, **extra) -> dict:
    resposta = client.post(URL, json=_payload(**extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_create_sem_cor_fica_null_e_payload_antigo_continua_valido(client_admin: TestClient) -> None:
    criado = _criar(client_admin)  # payload exatamente como os clientes antigos enviam: sem `cor`
    assert criado["cor"] is None
    assert client_admin.get(f"{URL}/{criado['id']}").json()["cor"] is None
    assert client_admin.patch(f"{URL}/{criado['id']}", json={"nome": criado["nome"] + " X"}).json()["cor"] is None  # PATCH antigo não mexe na cor


def test_create_com_cor_aceita_e_normaliza_para_maiusculas(client_admin: TestClient) -> None:
    assert _criar(client_admin, cor="#8B5CF6")["cor"] == "#8B5CF6"
    assert _criar(client_admin, cor="#8b5cf6")["cor"] == "#8B5CF6"
    assert _criar(client_admin, cor="  #f97316 ")["cor"] == "#F97316"
    assert _criar(client_admin, cor="\t#06b6d4\n")["cor"] == "#06B6D4"  # espaço em volta é aparado, o resto continua exigindo o formato
    assert _criar(client_admin, cor=None)["cor"] is None


@pytest.mark.parametrize("invalida", ["#FFF", "red", "123456", "#GGGGGG", "#12345", "#1234567", "rgb(1,2,3)", "hsl(0,0%,0%)", "bg-red-500", "", " ", "#8B5CF6;color:red", "<script>alert(1)</script>", "javascript:alert(1)", "url(x)", 123, True, ["#8B5CF6"]])
def test_cores_invalidas_sao_422_no_create_e_no_update(client_admin: TestClient, invalida) -> None:
    resposta = client_admin.post(URL, json=_payload(cor=invalida))
    assert resposta.status_code == 422, (invalida, resposta.text)
    criado = _criar(client_admin, cor="#06B6D4")
    resposta = client_admin.patch(f"{URL}/{criado['id']}", json={"cor": invalida})
    assert resposta.status_code == 422, (invalida, resposta.text)
    assert client_admin.get(f"{URL}/{criado['id']}").json()["cor"] == "#06B6D4"  # nada mudou


def test_update_define_troca_e_remove_a_cor(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    definida = client_admin.patch(f"{URL}/{criado['id']}", json={"cor": "#8b5cf6"})
    assert definida.status_code == 200 and definida.json()["cor"] == "#8B5CF6"
    trocada = client_admin.patch(f"{URL}/{criado['id']}", json={"cor": "#F97316"})
    assert trocada.json()["cor"] == "#F97316"
    removida = client_admin.patch(f"{URL}/{criado['id']}", json={"cor": None})
    assert removida.status_code == 200 and removida.json()["cor"] is None  # volta ao neutro: nunca vira uma cor fixa do sistema
    assert client_admin.get(f"{URL}/{criado['id']}").json()["cor"] is None


def test_omitir_cor_no_patch_nao_altera_e_status_e_etapas_seguem_independentes(client_admin: TestClient) -> None:
    criado = _criar(client_admin, cor="#06B6D4")
    assert client_admin.patch(f"{URL}/{criado['id']}", json={"status": "inativo"}).json()["cor"] == "#06B6D4"
    assert client_admin.patch(f"{URL}/{criado['id']}", json={"etapas": [_etapa("Nova")]}).json()["cor"] == "#06B6D4"


def test_leitura_lista_detalhe_e_diretorio_devolvem_a_cor(client_admin: TestClient, client_operador: TestClient) -> None:
    com = _criar(client_admin, cor="#06B6D4")
    sem = _criar(client_admin)
    lista = {w["id"]: w["cor"] for w in client_admin.get(URL).json()}
    assert lista[com["id"]] == "#06B6D4" and lista[sem["id"]] is None
    diretorio = {w["id"]: w["cor"] for w in client_operador.get(f"{URL}/diretorio").json()}  # quem só seleciona o workflow também vê a cor
    assert diretorio[com["id"]] == "#06B6D4" and diretorio[sem["id"]] is None
    assert client_operador.get(f"{URL}/{com['id']}").json()["cor"] == "#06B6D4"


def test_rbac_alterar_a_cor_exige_a_mesma_autoridade_de_editar_o_workflow(client_admin: TestClient, client_gestor: TestClient, client_operador: TestClient) -> None:
    criado = _criar(client_admin)
    assert client_operador.patch(f"{URL}/{criado['id']}", json={"cor": "#8B5CF6"}).status_code == 403
    assert client_operador.post(URL, json=_payload(cor="#8B5CF6")).status_code == 403
    assert client_gestor.patch(f"{URL}/{criado['id']}", json={"cor": "#8B5CF6"}).status_code == 200
    assert client_admin.get(f"{URL}/{criado['id']}").json()["cor"] == "#8B5CF6"


def test_tenant_workflow_de_outra_empresa_nao_e_alteravel_nem_aparece(client_admin: TestClient, outra_empresa: Empresa, db_session: Session) -> None:
    alheio = _workflow_modelo_de_outra_empresa(db_session, outra_empresa)
    assert client_admin.patch(f"{URL}/{alheio}", json={"cor": "#8B5CF6"}).status_code == 404
    assert alheio not in [w["id"] for w in client_admin.get(f"{URL}/diretorio").json()]


def test_alterar_a_cor_usa_o_evento_existente_e_no_op_nao_publica(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)

    def eventos() -> list[Evento]:
        db_session.expire_all()
        return list(db_session.scalars(select(Evento).where(Evento.entidade_id == criado["id"], Evento.tipo == "workflow_modelo.alterado")).all())

    client_admin.patch(f"{URL}/{criado['id']}", json={"cor": "#8B5CF6"})
    [evento] = eventos()
    assert evento.payload["camposAlterados"] == ["cor"]  # entra no mesmo mecanismo, sem sistema paralelo
    client_admin.patch(f"{URL}/{criado['id']}", json={"cor": "#8b5cf6"})  # mesmo valor depois de normalizar
    assert len(eventos()) == 1
    client_admin.patch(f"{URL}/{criado['id']}", json={"cor": None})
    assert len(eventos()) == 2


def test_cor_nao_entra_no_snapshot_da_demanda_e_mudar_a_cor_nao_toca_nas_etapas_materializadas(client_admin: TestClient, db_session: Session) -> None:
    modelo = _criar(client_admin, cor="#8B5CF6", etapas=[_etapa("Redação"), _etapa("Arte")])
    demanda = client_admin.post("/demandas", json={"nome": "Demanda com workflow", "workflowModeloId": modelo["id"]}).json()
    assert "cor" not in demanda and all("cor" not in etapa for etapa in demanda["workflowEtapas"])

    def etapas_hash() -> str:
        db_session.expire_all()
        return db_session.execute(text("SELECT md5(string_agg(row_to_json(e)::text, ',' ORDER BY id)) FROM demanda_workflow_etapas e WHERE demanda_id = :d"), {"d": demanda["id"]}).scalar()

    antes = etapas_hash()
    assert client_admin.patch(f"{URL}/{modelo['id']}", json={"cor": "#3B82F6"}).status_code == 200
    assert etapas_hash() == antes


def test_constraint_do_banco_recusa_cor_fora_do_formato_canonico(db_session: Session, client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    for invalida in ("#8b5cf6", "#FFF", "red", ""):
        with pytest.raises(IntegrityError):
            with db_session.begin_nested():
                db_session.execute(text("UPDATE workflow_modelos SET cor = :c WHERE id = :i"), {"c": invalida, "i": criado["id"]})
    db_session.execute(text("UPDATE workflow_modelos SET cor = '#8B5CF6' WHERE id = :i"), {"i": criado["id"]})
    db_session.execute(text("UPDATE workflow_modelos SET cor = NULL WHERE id = :i"), {"i": criado["id"]})
