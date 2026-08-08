"""Cliente — primeira entidade comercial real (Fase 2B).

Cobre o contrato inteiro: CRUD, arquivamento, N:N com GrupoCliente, isolamento por empresa,
autorização, imutabilidade do código de referência, pesquisa e eventos de domínio.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.grupo_cliente import GrupoCliente


def _grupo(db: Session, empresa: Empresa, *, nome: str | None = None, status: str = "ativo") -> GrupoCliente:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    grupo = GrupoCliente(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"grupo-{sufixo}",
        nome=nome or f"Grupo {sufixo}",
        nome_normalizado=f"grupo {sufixo}",
        cor_identificacao="blue",
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(grupo)
    db.flush()
    return grupo


def _payload(**extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    return {
        "nome": f"Cliente {sufixo}",
        "tipoDocumento": "cnpj",
        "corIdentificacao": "blue",
        **extra,
    }


def _criar(client: TestClient, **extra) -> dict:
    resposta = client.post("/clientes", json=_payload(**extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ======================================================================================
# CRUD
# ======================================================================================

def test_criar_cliente(client_admin: TestClient) -> None:
    corpo = _criar(client_admin, razaoSocial="Razão Ltda", segmento="Varejo")
    assert corpo["status"] == "ativo"
    assert corpo["razaoSocial"] == "Razão Ltda"
    assert corpo["grupoClienteIds"] == []
    uuid.UUID(corpo["id"])


def test_codigo_referencia_no_formato_C_ano_sequencial(client_admin: TestClient) -> None:
    corpo = _criar(client_admin)
    codigo = corpo["codigoReferencia"]
    assert codigo.startswith("C"), codigo
    assert len(codigo) == 9, codigo  # C + 2 (ano) + 6 (sequencial)
    assert codigo[1:].isdigit(), codigo
    assert corpo["sequencialReferencia"] == int(codigo[3:])


def test_sequencial_avanca_sem_buracos(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin)["sequencialReferencia"]
    segundo = _criar(client_admin)["sequencialReferencia"]
    assert segundo == primeiro + 1


def test_editar_cliente(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(
        f"/clientes/{criado['id']}", json={"nome": "Nome Novo", "segmento": "Saúde"}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["nome"] == "Nome Novo"
    assert resposta.json()["segmento"] == "Saúde"


def test_get_por_id(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.get(f"/clientes/{criado['id']}")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["id"] == criado["id"]


# ======================================================================================
# Arquivamento — nunca há delete físico
# ======================================================================================

def test_arquivar_exige_motivo(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    assert client_admin.post(f"/clientes/{criado['id']}/arquivar", json={}).status_code == 422


def test_arquivar_e_restaurar(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)

    arquivado = client_admin.post(
        f"/clientes/{criado['id']}/arquivar", json={"motivoArquivamento": "Encerrou contrato"}
    )
    assert arquivado.status_code == 200, arquivado.text
    assert arquivado.json()["status"] == "arquivado"
    assert arquivado.json()["motivoArquivamento"] == "Encerrou contrato"

    # Registro continua fisicamente no banco.
    assert db_session.execute(
        text("SELECT count(*) FROM clientes WHERE id = :i"), {"i": criado["id"]}
    ).scalar_one() == 1

    restaurado = client_admin.post(f"/clientes/{criado['id']}/restaurar")
    assert restaurado.status_code == 200, restaurado.text
    assert restaurado.json()["status"] == "ativo"
    assert restaurado.json()["motivoArquivamento"] is None


def test_arquivado_sai_da_listagem_padrao(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/clientes/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    ids = [c["id"] for c in client_admin.get("/clientes", params={"limit": 200}).json()]
    assert criado["id"] not in ids

    ids_arquivados = [
        c["id"] for c in client_admin.get("/clientes", params={"status": "arquivado", "limit": 200}).json()
    ]
    assert criado["id"] in ids_arquivados


def test_arquivado_nao_pode_ser_editado(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/clientes/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.patch(f"/clientes/{criado['id']}", json={"nome": "Outro"})
    assert resposta.status_code == 409, resposta.text


def test_restaurar_preserva_status_anterior(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.patch(f"/clientes/{criado['id']}", json={"status": "suspenso"})
    client_admin.post(f"/clientes/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    restaurado = client_admin.post(f"/clientes/{criado['id']}/restaurar")
    assert restaurado.json()["status"] == "suspenso"


def test_restaurar_so_vale_para_arquivado(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    assert client_admin.post(f"/clientes/{criado['id']}/restaurar").status_code == 409


# ======================================================================================
# Possível duplicidade — AVISO, nunca bloqueio
#
# Não há UNIQUE de nome nem de documento (ver app/models/cliente.py). A base real tem
# filiais homônimas com CNPJ distinto e empreendimentos distintos sob o mesmo CNPJ; ambos
# são cadastros legítimos. Deduplicação é trabalho futuro, com revisão humana.
# ======================================================================================

def test_mesmo_nome_e_permitido(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin, nome="BRETAS CENTRO")
    resposta = client_admin.post("/clientes", json=_payload(nome="BRETAS CENTRO"))
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["id"] != primeiro["id"]


def test_mesmo_documento_e_permitido(client_admin: TestClient) -> None:
    _criar(client_admin, documento="10.748.163/0001-00")
    resposta = client_admin.post("/clientes", json=_payload(documento="10.748.163/0001-00"))
    assert resposta.status_code == 201, resposta.text


def test_mesmo_nome_e_documento_e_permitido(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin, nome="CMO Varandas", documento="11.111.111/0001-11")
    resposta = client_admin.post(
        "/clientes", json=_payload(nome="CMO Varandas", documento="11.111.111/0001-11")
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["id"] != primeiro["id"]


def test_aviso_por_nome(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin, nome="Padaria Central")
    corpo = client_admin.post("/clientes", json=_payload(nome="Padaria Central")).json()

    avisos = corpo["possiveisDuplicidades"]
    assert len(avisos) == 1, avisos
    assert avisos[0]["id"] == primeiro["id"]
    assert avisos[0]["codigoReferencia"] == primeiro["codigoReferencia"]
    assert avisos[0]["motivo"] == "nome"


def test_aviso_por_documento(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin, nome="Alfa", documento="22.222.222/0001-22")
    corpo = client_admin.post(
        "/clientes", json=_payload(nome="Beta", documento="22.222.222/0001-22")
    ).json()

    avisos = corpo["possiveisDuplicidades"]
    assert [a["id"] for a in avisos] == [primeiro["id"]]
    assert avisos[0]["motivo"] == "documento"


def test_aviso_por_nome_e_documento(client_admin: TestClient) -> None:
    _criar(client_admin, nome="Gama", documento="33.333.333/0001-33")
    corpo = client_admin.post(
        "/clientes", json=_payload(nome="Gama", documento="33.333.333/0001-33")
    ).json()
    assert corpo["possiveisDuplicidades"][0]["motivo"] == "nome_documento"


def test_aviso_ignora_pontuacao_do_documento(client_admin: TestClient) -> None:
    _criar(client_admin, nome="Delta", documento="44.444.444/0001-44")
    corpo = client_admin.post(
        "/clientes", json=_payload(nome="Epsilon", documento="44444444000144")
    ).json()
    assert corpo["possiveisDuplicidades"][0]["motivo"] == "documento"


def test_aviso_e_case_insensitive_no_nome(client_admin: TestClient) -> None:
    _criar(client_admin, nome="Zeta Comercio")
    corpo = client_admin.post("/clientes", json=_payload(nome="ZETA COMERCIO")).json()
    assert corpo["possiveisDuplicidades"][0]["motivo"] == "nome"


def test_sem_semelhante_a_lista_de_avisos_vem_vazia(client_admin: TestClient) -> None:
    corpo = _criar(client_admin, documento="55.555.555/0001-55")
    assert corpo["possiveisDuplicidades"] == []


def test_aviso_considera_arquivado(client_admin: TestClient) -> None:
    """Reativar um homônimo arquivado é justamente quando o operador precisa ser avisado."""
    primeiro = _criar(client_admin, nome="Eta Servicos")
    client_admin.post(f"/clientes/{primeiro['id']}/arquivar", json={"motivoArquivamento": "x"})

    corpo = client_admin.post("/clientes", json=_payload(nome="Eta Servicos")).json()
    avisos = corpo["possiveisDuplicidades"]
    assert avisos[0]["id"] == primeiro["id"]
    assert avisos[0]["status"] == "arquivado"


def test_aviso_no_patch_nao_inclui_o_proprio_registro(client_admin: TestClient) -> None:
    criado = _criar(client_admin, nome="Theta")
    corpo = client_admin.patch(f"/clientes/{criado['id']}", json={"segmento": "Varejo"}).json()
    assert corpo["possiveisDuplicidades"] == []


def test_aviso_no_patch_quando_renomeia_para_nome_existente(client_admin: TestClient) -> None:
    existente = _criar(client_admin, nome="Iota Original")
    outro = _criar(client_admin, nome="Kappa")

    corpo = client_admin.patch(f"/clientes/{outro['id']}", json={"nome": "Iota Original"}).json()
    assert corpo["nome"] == "Iota Original"  # renomeou mesmo assim
    assert corpo["possiveisDuplicidades"][0]["id"] == existente["id"]


def test_listagem_nao_calcula_avisos(client_admin: TestClient) -> None:
    """Avisos só nas respostas de escrita — em listagem seria uma consulta por linha."""
    _criar(client_admin, nome="Lambda")
    _criar(client_admin, nome="Lambda")
    listagem = client_admin.get("/clientes", params={"search": "Lambda"}).json()
    assert all(c["possiveisDuplicidades"] == [] for c in listagem)


# ======================================================================================
# Grupo de Cliente (N:N)
# ======================================================================================

def test_criar_com_grupos(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    primeiro = _grupo(db_session, empresa)
    segundo = _grupo(db_session, empresa)
    corpo = _criar(client_admin, grupoClienteIds=[primeiro.id, segundo.id])
    assert sorted(corpo["grupoClienteIds"]) == sorted([primeiro.id, segundo.id])


def test_grupo_inexistente_rejeitado(client_admin: TestClient) -> None:
    resposta = client_admin.post("/clientes", json=_payload(grupoClienteIds=[str(uuid.uuid4())]))
    assert resposta.status_code == 422, resposta.text


def test_grupo_arquivado_rejeitado_em_vinculo_novo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    arquivado = _grupo(db_session, empresa, status="arquivado")
    resposta = client_admin.post("/clientes", json=_payload(grupoClienteIds=[arquivado.id]))
    assert resposta.status_code == 422, resposta.text


def test_grupo_de_outra_empresa_rejeitado(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    alheio = _grupo(db_session, outra_empresa)
    resposta = client_admin.post("/clientes", json=_payload(grupoClienteIds=[alheio.id]))
    assert resposta.status_code == 422, resposta.text


def test_sincronizacao_de_grupos_adiciona_e_remove(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    a = _grupo(db_session, empresa)
    b = _grupo(db_session, empresa)
    c = _grupo(db_session, empresa)
    criado = _criar(client_admin, grupoClienteIds=[a.id, b.id])

    resposta = client_admin.patch(f"/clientes/{criado['id']}", json={"grupoClienteIds": [b.id, c.id]})
    assert resposta.status_code == 200, resposta.text
    assert sorted(resposta.json()["grupoClienteIds"]) == sorted([b.id, c.id])


def test_vinculo_com_grupo_arquivado_e_preservado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Arquivar o grupo não rompe vínculo existente — só impede vínculo novo."""
    grupo = _grupo(db_session, empresa)
    criado = _criar(client_admin, grupoClienteIds=[grupo.id])

    db_session.execute(
        text("UPDATE grupos_cliente SET status = 'arquivado' WHERE id = :i"), {"i": grupo.id}
    )
    db_session.flush()

    lido = client_admin.get(f"/clientes/{criado['id']}").json()
    assert lido["grupoClienteIds"] == [grupo.id]


def test_filtro_por_grupo(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    grupo = _grupo(db_session, empresa)
    dentro = _criar(client_admin, grupoClienteIds=[grupo.id])
    fora = _criar(client_admin)

    ids = [c["id"] for c in client_admin.get("/clientes", params={"grupoClienteId": grupo.id}).json()]
    assert dentro["id"] in ids
    assert fora["id"] not in ids


# ======================================================================================
# Identidade: codigoInterno e codigoReferencia
# ======================================================================================

def test_api_publica_recusa_campos_gerados_no_backend(client_admin: TestClient) -> None:
    """empresaId, codigoInterno e os campos de referência devolvem 422 — nunca são
    ignorados em silêncio (extra='forbid')."""
    for campo, valor in [
        ("empresaId", str(uuid.uuid4())),
        ("codigoInterno", "#9999"),
        ("codigoReferencia", "C26000099"),
        ("anoReferencia", 26),
        ("sequencialReferencia", 99),
        ("actorUsuarioId", str(uuid.uuid4())),
        ("status", "ativo"),
    ]:
        resposta = client_admin.post("/clientes", json=_payload(**{campo: valor}))
        assert resposta.status_code == 422, f"{campo} deveria ser recusado: {resposta.text}"


def test_codigo_referencia_e_imutavel(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    # Nem via PATCH direto...
    assert client_admin.patch(
        f"/clientes/{criado['id']}", json={"codigoReferencia": "C26999999"}
    ).status_code == 422
    # ...nem por efeito colateral de outra alteração.
    client_admin.patch(f"/clientes/{criado['id']}", json={"nome": "Renomeado"})
    assert client_admin.get(f"/clientes/{criado['id']}").json()["codigoReferencia"] == criado["codigoReferencia"]


def test_codigo_interno_gerado_quando_nao_ha_legado(client_admin: TestClient) -> None:
    """Criação pela API deriva o codigoInterno da referência — sem consumir outra sequência."""
    criado = _criar(client_admin)
    assert criado["codigoInterno"] == criado["codigoReferencia"]


# ======================================================================================
# Responsável comercial
# ======================================================================================

def test_responsavel_inexistente_rejeitado(client_admin: TestClient) -> None:
    resposta = client_admin.post("/clientes", json=_payload(responsavelComercialId=str(uuid.uuid4())))
    assert resposta.status_code == 422, resposta.text


def test_responsavel_valido_aceito(client_admin: TestClient, usuario_admin) -> None:
    corpo = _criar(client_admin, responsavelComercialId=usuario_admin.id)
    assert corpo["responsavelComercialId"] == usuario_admin.id


# ======================================================================================
# Isolamento por empresa e autorização
# ======================================================================================

def test_listagem_nao_vaza_outra_empresa(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa, empresa: Empresa
) -> None:
    meu = _criar(client_admin)
    agora = datetime.now(timezone.utc)
    alheio_id = str(uuid.uuid4())
    db_session.execute(
        text(
            "INSERT INTO clientes (id, empresa_id, codigo_interno, codigo_referencia, ano_referencia,"
            " sequencial_referencia, nome, nome_normalizado, tipo_documento, status, cor_identificacao,"
            " cliente_referencial, avisar_conclusao_por_email, created_at, updated_at)"
            " VALUES (:id, :emp, 'C26900001', 'C26900001', 26, 900001, 'Alheio', 'alheio', 'cnpj',"
            " 'ativo', 'blue', false, false, :a, :a)"
        ),
        {"id": alheio_id, "emp": outra_empresa.id, "a": agora},
    )
    db_session.flush()

    ids = [c["id"] for c in client_admin.get("/clientes", params={"limit": 200}).json()]
    assert meu["id"] in ids
    assert alheio_id not in ids

    # Acesso direto por id também não vaza.
    assert client_admin.get(f"/clientes/{alheio_id}").status_code in (403, 404)


def test_operador_nao_administra_clientes(client_operador: TestClient) -> None:
    assert client_operador.post("/clientes", json=_payload()).status_code == 403
    assert client_operador.get("/clientes").status_code == 403


def test_gestor_administra_clientes(client_gestor: TestClient) -> None:
    assert client_gestor.post("/clientes", json=_payload()).status_code == 201


def test_diretorio_acessivel_a_qualquer_autenticado(client_operador: TestClient) -> None:
    """O diretório é projeção mínima para seletores — operador precisa dele."""
    assert client_operador.get("/clientes/diretorio").status_code == 200


def test_sem_token_e_401(app) -> None:
    with TestClient(app) as anonimo:
        assert anonimo.get("/clientes").status_code == 401


# ======================================================================================
# Diretório e pesquisa
# ======================================================================================

def test_diretorio_inclui_arquivados(client_admin: TestClient) -> None:
    """Referências históricas precisam continuar resolvendo o nome."""
    criado = _criar(client_admin)
    client_admin.post(f"/clientes/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    diretorio = client_admin.get("/clientes/diretorio").json()
    encontrado = next((c for c in diretorio if c["id"] == criado["id"]), None)
    assert encontrado is not None
    assert encontrado["status"] == "arquivado"


def test_pesquisa_por_codigo_referencia(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    achados = client_admin.get("/clientes", params={"search": criado["codigoReferencia"]}).json()
    assert criado["id"] in [c["id"] for c in achados]


def test_pesquisa_por_codigo_referencia_case_insensitive(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    achados = client_admin.get("/clientes", params={"search": criado["codigoReferencia"].lower()}).json()
    assert criado["id"] in [c["id"] for c in achados]


def test_pesquisa_por_nome(client_admin: TestClient) -> None:
    criado = _criar(client_admin, nome="Padaria Estrela do Norte")
    achados = client_admin.get("/clientes", params={"search": "estrela do norte"}).json()
    assert criado["id"] in [c["id"] for c in achados]


def test_pesquisa_por_documento_ignora_pontuacao(client_admin: TestClient) -> None:
    criado = _criar(client_admin, documento="12.345.678/0001-90")
    achados = client_admin.get("/clientes", params={"search": "12345678"}).json()
    assert criado["id"] in [c["id"] for c in achados]


def test_pesquisa_por_documento_formatado(client_admin: TestClient) -> None:
    criado = _criar(client_admin, documento="39.346.861/0245-08")
    achados = client_admin.get("/clientes", params={"search": "39.346.861/0245-08"}).json()
    assert criado["id"] in [c["id"] for c in achados]


def test_pesquisa_por_documento_parcial_acima_do_minimo(client_admin: TestClient) -> None:
    criado = _criar(client_admin, documento="98.765.432/0245-11")
    achados = client_admin.get("/clientes", params={"search": "0245", "limit": 200}).json()
    assert criado["id"] in [c["id"] for c in achados]


def test_pesquisa_por_nome_com_numero_nao_vira_busca_de_documento(client_admin: TestClient) -> None:
    """`Contrato 2026` é nome, não documento — não pode varrer `%2026%` em documento."""
    alvo = _criar(client_admin, nome="Contrato 2026 Especial")
    outro = _criar(client_admin, nome="Sem relacao aqui", documento="20.261.111/0001-11")

    achados = client_admin.get("/clientes", params={"search": "Contrato 2026", "limit": 200}).json()
    ids = [c["id"] for c in achados]
    assert alvo["id"] in ids
    assert outro["id"] not in ids, "documento não pode ser alcançado por termo com letras"


@pytest.mark.parametrize("termo", ["1", "12"])
def test_poucos_digitos_nunca_alcancam_por_documento(client_admin: TestClient, termo: str) -> None:
    """Com poucos dígitos, todo resultado tem de se justificar por TEXTO.

    A busca textual continua valendo e é legítima — `codigoReferencia` (`C26000012`) contém
    dígitos, então "1" casa por código. O que a regra proíbe é alcançar alguém **só** pelo
    documento: é isso que tornava a busca abrangente demais.
    """
    _criar(client_admin, nome="Alvo Sem Digito No Nome", documento="11.222.333/0001-12")

    achados = client_admin.get("/clientes", params={"search": termo, "limit": 200}).json()

    for cliente in achados:
        casou_por_texto = any(
            termo in (cliente.get(campo) or "")
            for campo in ("nome", "razaoSocial", "codigoReferencia", "codigoInterno")
        )
        assert casou_por_texto, (
            f"{cliente['codigoReferencia']} só pode ter vindo pelo documento "
            f"{cliente.get('documento')!r} — termo {termo!r} não deveria ativar busca por documento"
        )


def test_regressao_qa_fase2b_nao_amplia_resultados(client_admin: TestClient) -> None:
    """Regressão do incidente da validação manual da Fase 2B.

    `"QA FASE2B"` tinha o dígito "2" extraído e virava `documento_normalizado ILIKE '%2%'`,
    que casa com praticamente todo CNPJ: a busca devolveu 91 clientes em vez de 3, e uma
    operação em lote sobre esse resultado arquivou 87 registros indevidos.

    A busca só pode devolver o que casa por TEXTO.
    """
    alvo = _criar(client_admin, nome="QA FASE2B CLIENTE TESTE")
    ruido = [
        _criar(client_admin, nome=f"Ruido sem relacao {i}", documento=f"1{i}.222.333/0001-9{i}")
        for i in range(3)
    ]

    achados = client_admin.get("/clientes", params={"search": "QA FASE2B", "limit": 200}).json()
    ids = [c["id"] for c in achados]

    assert ids == [alvo["id"]], "a busca não pode alcançar nada além do que casa por texto"
    for cliente in ruido:
        assert cliente["id"] not in ids


def test_busca_respeita_isolamento_por_empresa(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    """Endurecer a busca não pode ter afrouxado o escopo por empresa."""
    meu = _criar(client_admin, documento="55.666.777/0001-88")
    agora = datetime.now(timezone.utc)
    alheio_id = str(uuid.uuid4())
    db_session.execute(
        text(
            "INSERT INTO clientes (id, empresa_id, codigo_interno, codigo_referencia, ano_referencia,"
            " sequencial_referencia, nome, nome_normalizado, tipo_documento, documento,"
            " documento_normalizado, status, cor_identificacao, cliente_referencial,"
            " avisar_conclusao_por_email, created_at, updated_at)"
            " VALUES (:id, :emp, 'C26900002', 'C26900002', 26, 900002, 'Alheio Busca', 'alheio busca',"
            " 'cnpj', '55.666.777/0001-88', '55666777000188', 'ativo', 'blue', false, false, :a, :a)"
        ),
        {"id": alheio_id, "emp": outra_empresa.id, "a": agora},
    )
    db_session.flush()

    achados = client_admin.get("/clientes", params={"search": "55666777000188", "limit": 200}).json()
    ids = [c["id"] for c in achados]
    assert meu["id"] in ids
    assert alheio_id not in ids


# ======================================================================================
# Contatos (value objects em JSONB)
# ======================================================================================

def test_contatos_persistem_como_value_objects(client_admin: TestClient) -> None:
    contatos = [
        {
            "id": "c1",
            "nome": "Fernanda",
            "email": "f@ex.com",
            "telefone": "(62) 90000-0000",
            "cargo": "Marketing",
            "recebeEntregas": True,
        }
    ]
    criado = _criar(client_admin, contatos=contatos)
    assert criado["contatos"][0]["nome"] == "Fernanda"
    assert criado["contatos"][0]["recebeEntregas"] is True

    substituidos = client_admin.patch(f"/clientes/{criado['id']}", json={"contatos": []})
    assert substituidos.json()["contatos"] == []


# ======================================================================================
# Eventos — não há tabela de histórico; os eventos SÃO o histórico
# ======================================================================================

def _eventos(db: Session, cliente_id: str) -> list[str]:
    db.expire_all()
    linhas = db.execute(
        text("SELECT tipo FROM eventos WHERE entidade_id = :i ORDER BY occurred_at, tipo"),
        {"i": cliente_id},
    ).all()
    return [linha[0] for linha in linhas]


def test_eventos_publicados_no_ciclo_de_vida(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    grupo = _grupo(db_session, empresa)
    criado = _criar(client_admin, grupoClienteIds=[grupo.id])
    assert "cliente.criado" in _eventos(db_session, criado["id"])
    assert "cliente.grupo_adicionado" in _eventos(db_session, criado["id"])

    client_admin.patch(f"/clientes/{criado['id']}", json={"nome": "Outro Nome"})
    assert "cliente.alterado" in _eventos(db_session, criado["id"])

    client_admin.patch(f"/clientes/{criado['id']}", json={"grupoClienteIds": []})
    assert "cliente.grupo_removido" in _eventos(db_session, criado["id"])

    client_admin.post(f"/clientes/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert "cliente.arquivado" in _eventos(db_session, criado["id"])

    client_admin.post(f"/clientes/{criado['id']}/restaurar")
    assert "cliente.restaurado" in _eventos(db_session, criado["id"])


def test_evento_nao_e_publicado_sem_alteracao_real(
    client_admin: TestClient, db_session: Session
) -> None:
    criado = _criar(client_admin)
    antes = len(_eventos(db_session, criado["id"]))
    client_admin.patch(f"/clientes/{criado['id']}", json={"nome": criado["nome"]})
    assert len(_eventos(db_session, criado["id"])) == antes


def test_evento_carrega_codigo_referencia(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)
    db_session.expire_all()
    payload = db_session.execute(
        text("SELECT payload FROM eventos WHERE entidade_id = :i AND tipo = 'cliente.criado'"),
        {"i": criado["id"]},
    ).scalar_one()
    assert payload["codigo_referencia"] == criado["codigoReferencia"]


# ======================================================================================
# Rollback da sequência
# ======================================================================================

def test_falha_na_criacao_nao_queima_sequencia(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """O contador participa da transação do service: criação recusada não avança número."""
    antes = _criar(client_admin)["sequencialReferencia"]

    # Recusada DEPOIS da validação de nome, na validação de grupo — dentro da transação.
    recusada = client_admin.post("/clientes", json=_payload(grupoClienteIds=[str(uuid.uuid4())]))
    assert recusada.status_code == 422

    depois = _criar(client_admin)["sequencialReferencia"]
    assert depois == antes + 1, "a tentativa recusada não pode ter consumido um número"


# ======================================================================================
# Concorrência
# ======================================================================================

def test_criacoes_concorrentes_nao_repetem_sequencial(test_engine) -> None:
    """8 criações simultâneas recebem sequenciais distintos.

    Concorrência real contra o Postgres de teste: cada thread com sua própria conexão e
    commit próprio — não dá para usar `client_admin`, porque a suíte compartilha uma única
    Session entre as threads. O `INSERT ... ON CONFLICT DO UPDATE` do contador serializa
    pelo lock da linha.
    """
    from sqlalchemy.orm import Session as SessionRaw

    from app.models.empresa import Empresa as EmpresaModel
    from app.schemas.cliente import ClienteCreate
    from app.services.cliente_service import ClienteService

    agora = datetime.now(timezone.utc)
    empresa_id = str(uuid.uuid4())
    with SessionRaw(bind=test_engine) as setup:
        setup.add(
            EmpresaModel(
                id=empresa_id,
                codigo_interno=f"CONC{uuid.uuid4().hex[:6].upper()}",
                nome="Empresa Concorrência",
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
    service = ClienteService()

    def criar() -> None:
        with SessionRaw(bind=test_engine) as sessao:
            barreira.wait()  # maximiza a chance de colisão real
            cliente = service.create_cliente(
                sessao,
                ClienteCreate.model_validate(_payload()),
                empresa_id=empresa_id,
            )
            with trava:
                obtidos.append(cliente.sequencial_referencia)

    threads = [threading.Thread(target=criar) for _ in range(total)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sorted(obtidos) == list(range(1, total + 1)), f"sequenciais duplicados/faltando: {obtidos}"
    finally:
        with SessionRaw(bind=test_engine) as limpeza:
            limpeza.execute(text("DELETE FROM clientes WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM eventos WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(
                text("DELETE FROM sequencias_referencia WHERE empresa_id = :e"), {"e": empresa_id}
            )
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
            limpeza.commit()
