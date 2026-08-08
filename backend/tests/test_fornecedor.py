"""Fornecedor — último cadastro comercial a sair do mock (Fase 2C).

Cobre o contrato inteiro: CRUD, arquivamento, isolamento por empresa, autorização,
imutabilidade do código de referência, possíveis duplicidades, pesquisa e eventos de domínio.

Dois pontos merecem atenção especial e têm seção própria:

- **pesquisa** — a interpretação do termo é delegada a `app/core/busca.py`. Os testes aqui
  garantem que o repository não recriou a regra por conta própria, que foi a causa do
  incidente do Cliente (ver `test_nenhum_termo_alfanumerico_vira_filtro_de_documento`);
- **diretório** — ao contrário de Cliente, não inclui arquivados. Arquivado nunca pode ser
  oferecido como opção de vínculo novo.
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


def _payload(**extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    return {
        "nome": f"Fornecedor {sufixo}",
        "tipoDocumento": "cnpj",
        "corIdentificacao": "blue",
        **extra,
    }


def _criar(client: TestClient, **extra) -> dict:
    resposta = client.post("/fornecedores", json=_payload(**extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ======================================================================================
# CRUD
# ======================================================================================

def test_criar_fornecedor(client_admin: TestClient) -> None:
    corpo = _criar(client_admin, categoria="Gráfica", contatoNome="Renata", site="union.com.br")
    assert corpo["status"] == "ativo"
    assert corpo["categoria"] == "Gráfica"
    assert corpo["contatoNome"] == "Renata"
    assert corpo["site"] == "union.com.br"
    assert corpo["possiveisDuplicidades"] == []
    uuid.UUID(corpo["id"])


def test_criar_fornecedor_ja_inativo(client_admin: TestClient) -> None:
    """Cadastro histórico pode nascer inativo — a interface sempre ofereceu os dois."""
    assert _criar(client_admin, status="inativo")["status"] == "inativo"


def test_codigo_referencia_no_formato_F_ano_sequencial(client_admin: TestClient) -> None:
    corpo = _criar(client_admin)
    codigo = corpo["codigoReferencia"]
    assert codigo.startswith("F"), codigo
    assert len(codigo) == 9, codigo  # F + 2 (ano) + 6 (sequencial)
    assert codigo[1:].isdigit(), codigo
    assert corpo["sequencialReferencia"] == int(codigo[3:])


def test_sequencial_avanca_sem_buracos(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin)["sequencialReferencia"]
    segundo = _criar(client_admin)["sequencialReferencia"]
    assert segundo == primeiro + 1


def test_sequencia_de_fornecedor_e_independente_da_de_cliente(client_admin: TestClient) -> None:
    """Contadores são por (empresa, tipo_entidade, ano): criar cliente não move fornecedor."""
    antes = _criar(client_admin)["sequencialReferencia"]
    resposta = client_admin.post(
        "/clientes", json={"nome": "Cliente X", "tipoDocumento": "cnpj", "corIdentificacao": "blue"}
    )
    assert resposta.status_code == 201, resposta.text
    assert _criar(client_admin)["sequencialReferencia"] == antes + 1


def test_editar_fornecedor(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(
        f"/fornecedores/{criado['id']}", json={"nome": "Nome Novo", "categoria": "Fotografia"}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["nome"] == "Nome Novo"
    assert resposta.json()["categoria"] == "Fotografia"


def test_codigo_referencia_e_imutavel_no_patch(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    alterado = client_admin.patch(f"/fornecedores/{criado['id']}", json={"nome": "Outro"}).json()
    assert alterado["codigoReferencia"] == criado["codigoReferencia"]
    assert alterado["sequencialReferencia"] == criado["sequencialReferencia"]
    assert alterado["anoReferencia"] == criado["anoReferencia"]


def test_get_por_id(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.get(f"/fornecedores/{criado['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["codigoReferencia"] == criado["codigoReferencia"]


def test_get_de_id_inexistente_devolve_404(client_admin: TestClient) -> None:
    assert client_admin.get(f"/fornecedores/{uuid.uuid4()}").status_code == 404


# ======================================================================================
# Contrato público — extra="forbid"
# ======================================================================================

@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("empresaId", str(uuid.uuid4())),
        ("actorUsuarioId", str(uuid.uuid4())),
        ("codigoInterno", "fornecedor-forjado"),
        ("codigoReferencia", "F26999999"),
        ("anoReferencia", 26),
        ("sequencialReferencia", 999),
    ],
)
def test_campo_proibido_na_criacao_devolve_422(client_admin: TestClient, campo: str, valor) -> None:
    """Ignorar em silêncio seria pior: o cliente da API acharia que o valor foi aceito."""
    resposta = client_admin.post("/fornecedores", json=_payload(**{campo: valor}))
    assert resposta.status_code == 422, resposta.text


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("empresaId", str(uuid.uuid4())),
        ("codigoInterno", "fornecedor-forjado"),
        ("codigoReferencia", "F26999999"),
    ],
)
def test_campo_proibido_no_patch_devolve_422(client_admin: TestClient, campo: str, valor) -> None:
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/fornecedores/{criado['id']}", json={campo: valor})
    assert resposta.status_code == 422, resposta.text


def test_status_arquivado_nao_e_aceito_pelo_patch(client_admin: TestClient) -> None:
    """Arquivar tem rota própria e exige motivo — não se chega lá por PATCH de status."""
    criado = _criar(client_admin)
    resposta = client_admin.patch(f"/fornecedores/{criado['id']}", json={"status": "arquivado"})
    assert resposta.status_code == 422, resposta.text


def test_status_suspenso_nao_existe_em_fornecedor(client_admin: TestClient) -> None:
    """Regressão da decisão de modelagem: `suspenso` é de Cliente, não de Fornecedor."""
    resposta = client_admin.post("/fornecedores", json=_payload(status="suspenso"))
    assert resposta.status_code == 422, resposta.text


# ======================================================================================
# Possíveis duplicidades — aviso, nunca bloqueio
# ======================================================================================

def test_mesmo_nome_cria_normalmente_com_aviso(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin, nome="Gráfica Union")
    segundo = client_admin.post("/fornecedores", json=_payload(nome="Gráfica Union"))

    assert segundo.status_code == 201, "nome repetido é cadastro legítimo, nunca 409"
    avisos = segundo.json()["possiveisDuplicidades"]
    assert len(avisos) == 1
    assert avisos[0]["id"] == primeiro["id"]
    assert avisos[0]["motivo"] == "nome"
    assert avisos[0]["codigoReferencia"] == primeiro["codigoReferencia"]


def test_aviso_carrega_sequencial_pronto_para_o_rotulo(client_admin: TestClient) -> None:
    """Sem isto o frontend recortaria `codigoReferencia[3:]` para montar `#12-Nome`, que é o
    que frontend/src/lib/formatarReferencia.ts proíbe."""
    primeiro = _criar(client_admin, nome="Delta Gráfica")
    aviso = client_admin.post("/fornecedores", json=_payload(nome="Delta Gráfica")).json()[
        "possiveisDuplicidades"
    ][0]
    assert aviso["sequencialReferencia"] == primeiro["sequencialReferencia"]


def test_mesmo_documento_cria_normalmente_com_aviso(client_admin: TestClient) -> None:
    primeiro = _criar(client_admin, nome="Alfa", documento="12.345.678/0001-90")
    segundo = client_admin.post(
        "/fornecedores", json=_payload(nome="Beta", documento="12345678000190")
    )

    assert segundo.status_code == 201
    avisos = segundo.json()["possiveisDuplicidades"]
    assert [a["motivo"] for a in avisos] == ["documento"]
    assert avisos[0]["id"] == primeiro["id"]
    # O documento do outro cadastro vem junto: é o que deixa o operador decidir sem abrir.
    assert avisos[0]["documento"] == "12.345.678/0001-90"


def test_mesmo_nome_e_documento_reporta_motivo_combinado(client_admin: TestClient) -> None:
    _criar(client_admin, nome="Gama Ltda", documento="11.222.333/0001-44")
    segundo = client_admin.post(
        "/fornecedores", json=_payload(nome="Gama Ltda", documento="11.222.333/0001-44")
    )
    assert segundo.status_code == 201
    assert [a["motivo"] for a in segundo.json()["possiveisDuplicidades"]] == ["nome_documento"]


def test_nome_diferente_e_sem_documento_nao_gera_aviso(client_admin: TestClient) -> None:
    _criar(client_admin, nome="Delta")
    corpo = _criar(client_admin, nome="Epsilon")
    assert corpo["possiveisDuplicidades"] == []


def test_documento_ausente_nao_casa_com_outro_ausente(client_admin: TestClient) -> None:
    """Dois cadastros sem documento não são parecidos por isso — 16 dos 133 importados
    não têm documento, e avisar em todos tornaria o aviso ruído."""
    _criar(client_admin, nome="Sem Doc Um")
    assert _criar(client_admin, nome="Sem Doc Dois")["possiveisDuplicidades"] == []


def test_patch_nao_avisa_sobre_o_proprio_registro(client_admin: TestClient) -> None:
    criado = _criar(client_admin, nome="Zeta", documento="55.666.777/0001-88")
    alterado = client_admin.patch(f"/fornecedores/{criado['id']}", json={"categoria": "Mídia"})
    assert alterado.status_code == 200
    assert alterado.json()["possiveisDuplicidades"] == []


def test_aviso_inclui_arquivado(client_admin: TestClient) -> None:
    """Recadastrar algo que já existe arquivado é justamente quando avisar importa."""
    primeiro = _criar(client_admin, nome="Ômega Produções")
    client_admin.post(
        f"/fornecedores/{primeiro['id']}/arquivar", json={"motivoArquivamento": "Encerrou"}
    )

    segundo = client_admin.post("/fornecedores", json=_payload(nome="Ômega Produções"))
    assert segundo.status_code == 201
    avisos = segundo.json()["possiveisDuplicidades"]
    assert len(avisos) == 1
    assert avisos[0]["status"] == "arquivado"


def test_duplicidade_nao_aparece_na_listagem(client_admin: TestClient) -> None:
    """Calcular por linha custaria uma consulta cada — só criação e alteração trazem avisos."""
    _criar(client_admin, nome="Repetido SA")
    _criar(client_admin, nome="Repetido SA")
    listados = client_admin.get("/fornecedores", params={"limit": 200}).json()
    assert all(item["possiveisDuplicidades"] == [] for item in listados)


# ======================================================================================
# Arquivamento — soft delete, nunca delete físico
# ======================================================================================

def test_arquivar_exige_motivo(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    assert client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={}).status_code == 422
    assert (
        client_admin.post(
            f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "  "}
        ).status_code
        == 422
    )


def test_arquivar_guarda_auditoria_e_status_anterior(client_admin: TestClient) -> None:
    criado = _criar(client_admin, status="inativo")
    corpo = client_admin.post(
        f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "Contrato encerrado"}
    ).json()

    assert corpo["status"] == "arquivado"
    assert corpo["motivoArquivamento"] == "Contrato encerrado"
    assert corpo["arquivadoAt"] is not None
    assert corpo["arquivadoPorUsuarioId"] is not None
    assert corpo["statusAnteriorArquivamento"] == "inativo"


def test_arquivado_sai_da_listagem_padrao(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    ids = [f["id"] for f in client_admin.get("/fornecedores", params={"limit": 200}).json()]
    assert criado["id"] not in ids

    arquivados = client_admin.get(
        "/fornecedores", params={"status": "arquivado", "limit": 200}
    ).json()
    assert criado["id"] in [f["id"] for f in arquivados]


def test_arquivar_nao_apaga_fisicamente(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    total = db_session.execute(
        text("SELECT count(*) FROM fornecedores WHERE id = :i"), {"i": criado["id"]}
    ).scalar_one()
    assert total == 1, "arquivamento é soft-delete — a linha continua no banco"


def test_arquivado_nao_pode_ser_editado(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    resposta = client_admin.patch(f"/fornecedores/{criado['id']}", json={"nome": "Novo"})
    assert resposta.status_code == 409, resposta.text


def test_arquivar_duas_vezes_devolve_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    segunda = client_admin.post(
        f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "y"}
    )
    assert segunda.status_code == 409, segunda.text


def test_restaurar_devolve_o_status_anterior(client_admin: TestClient) -> None:
    criado = _criar(client_admin, status="inativo")
    client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    corpo = client_admin.post(f"/fornecedores/{criado['id']}/restaurar").json()
    assert corpo["status"] == "inativo"
    assert corpo["restauradoAt"] is not None
    assert corpo["restauradoPorUsuarioId"] is not None
    assert corpo["arquivadoAt"] is None
    assert corpo["motivoArquivamento"] is None
    assert corpo["statusAnteriorArquivamento"] is None


def test_restaurar_preserva_o_codigo_de_referencia(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    restaurado = client_admin.post(f"/fornecedores/{criado['id']}/restaurar").json()
    assert restaurado["codigoReferencia"] == criado["codigoReferencia"]


def test_restaurar_o_que_nao_esta_arquivado_devolve_409(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    assert client_admin.post(f"/fornecedores/{criado['id']}/restaurar").status_code == 409


# ======================================================================================
# Autorização e isolamento por empresa
# ======================================================================================

def test_operador_nao_administra_fornecedores(client_operador: TestClient) -> None:
    assert client_operador.post("/fornecedores", json=_payload()).status_code == 403
    assert client_operador.get("/fornecedores").status_code == 403


def test_gestor_administra_fornecedores(client_gestor: TestClient) -> None:
    assert client_gestor.post("/fornecedores", json=_payload()).status_code == 201


def test_sem_autenticacao_nao_acessa(client: TestClient) -> None:
    assert client.get("/fornecedores").status_code == 401


def test_fornecedor_de_outra_empresa_devolve_404(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    """Cross-tenant é tratado como inexistente — não vaza a existência do registro."""
    alheio_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)
    db_session.execute(
        text(
            """
            INSERT INTO fornecedores (
                id, empresa_id, codigo_interno, codigo_referencia, ano_referencia,
                sequencial_referencia, nome, nome_normalizado, tipo_documento, status,
                cor_identificacao, created_at, updated_at
            ) VALUES (
                :id, :emp, 'alheio-1', 'F26099999', 26, 99999, 'Alheio', 'alheio', 'cnpj',
                'ativo', 'blue', :a, :a
            )
            """
        ),
        {"id": alheio_id, "emp": outra_empresa.id, "a": agora},
    )
    db_session.flush()

    assert client_admin.get(f"/fornecedores/{alheio_id}").status_code == 404
    assert (
        client_admin.patch(f"/fornecedores/{alheio_id}", json={"nome": "X"}).status_code == 404
    )


# ======================================================================================
# Pesquisa — a regra mora em app/core/busca.py, não aqui
# ======================================================================================

def test_pesquisa_por_nome(client_admin: TestClient) -> None:
    criado = _criar(client_admin, nome="Estúdio Vértice Produções")
    achados = client_admin.get("/fornecedores", params={"search": "vértice produ"}).json()
    assert [f["id"] for f in achados] == [criado["id"]]


def test_pesquisa_por_codigo_referencia(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    achados = client_admin.get(
        "/fornecedores", params={"search": criado["codigoReferencia"]}
    ).json()
    assert [f["id"] for f in achados] == [criado["id"]]


def test_pesquisa_por_codigo_referencia_case_insensitive(client_admin: TestClient) -> None:
    criado = _criar(client_admin)
    achados = client_admin.get(
        "/fornecedores", params={"search": criado["codigoReferencia"].lower()}
    ).json()
    assert [f["id"] for f in achados] == [criado["id"]]


def test_pesquisa_por_documento_ignora_pontuacao(client_admin: TestClient) -> None:
    criado = _criar(client_admin, documento="12.345.678/0001-90")
    achados = client_admin.get("/fornecedores", params={"search": "12345678000190"}).json()
    assert criado["id"] in [f["id"] for f in achados]


def test_pesquisa_por_documento_formatado(client_admin: TestClient) -> None:
    criado = _criar(client_admin, documento="39.346.861/0245-08")
    achados = client_admin.get("/fornecedores", params={"search": "39.346.861/0245-08"}).json()
    assert criado["id"] in [f["id"] for f in achados]


def test_pesquisa_por_documento_parcial_acima_do_minimo(client_admin: TestClient) -> None:
    criado = _criar(client_admin, documento="98.765.432/0245-11")
    achados = client_admin.get("/fornecedores", params={"search": "0245", "limit": 200}).json()
    assert criado["id"] in [f["id"] for f in achados]


@pytest.mark.parametrize(
    "termo",
    [
        "QA FASE2B",         # o incidente do Cliente, repetido aqui de propósito
        "#2001",             # codigoInterno: "#" não é pontuação de documento
        "Fornecedor 2026",   # nome com número
        "F26000001",         # codigoReferencia
        "Loja 24h",          # número colado em letra
    ],
)
def test_nenhum_termo_alfanumerico_vira_filtro_de_documento(
    client_admin: TestClient, termo: str
) -> None:
    """Regressão obrigatória do incidente descrito em app/core/busca.py.

    `"QA FASE2B"` teve os dígitos extraídos como `"2"` e virou `documento_normalizado ILIKE
    '%2%'`, que casa com quase todo CNPJ: a busca devolveu 91 clientes em vez de 3 e uma
    operação em lote sobre o resultado arquivou 87 registros indevidos.

    A invariante aqui não é "achou zero" — busca textual legitimamente casa código e nome.
    É que **todo resultado tem de se justificar pelo texto**: nenhum pode ter entrado apenas
    por conter aqueles dígitos no documento. Se o repository voltar a extrair dígitos por
    conta própria, o ruído abaixo aparece e o teste quebra.
    """
    for i in range(5):
        _criar(client_admin, nome=f"Ruido sem relacao {i}", documento=f"2{i}.222.333/0001-9{i}")

    achados = client_admin.get("/fornecedores", params={"search": termo, "limit": 200}).json()

    alvo = termo.lower()
    for achado in achados:
        justificado = (
            alvo in achado["nome"].lower()
            or alvo in achado["codigoReferencia"].lower()
            or alvo in achado["codigoInterno"].lower()
        )
        assert justificado, (
            f"{achado['nome']} entrou no resultado de {termo!r} sem casar por texto — só "
            "poderia ter vindo por documento, e a regra de app/core/busca.py foi contornada"
        )


@pytest.mark.parametrize("termo", ["777", "888", "999"])
def test_poucos_digitos_nunca_alcancam_por_documento(client_admin: TestClient, termo: str) -> None:
    """Abaixo de MIN_DIGITOS_DOCUMENTO a busca parcial casaria com quase toda a base.

    Os termos são três dígitos altos de propósito: o `codigoReferencia` do alvo é
    `F260000NN` com sequencial baixo, então nem o nome nem os códigos contêm "777"/"888"/
    "999". Se o alvo aparecer, foi pelo documento — que é justamente o que não pode
    acontecer com menos de quatro dígitos.
    """
    alvo = _criar(client_admin, nome="Alvo Sem Digito No Nome", documento="77.788.899/0001-99")
    assert termo not in alvo["codigoReferencia"], "premissa do teste: o código não tem o termo"

    achados = client_admin.get("/fornecedores", params={"search": termo, "limit": 200}).json()
    assert alvo["id"] not in [f["id"] for f in achados]


def test_quatro_digitos_ja_alcancam_por_documento(client_admin: TestClient) -> None:
    """O outro lado do limite: com quatro dígitos a busca parcial de documento liga."""
    alvo = _criar(client_admin, nome="Alvo Sem Digito No Nome", documento="77.788.899/0001-99")
    achados = client_admin.get("/fornecedores", params={"search": "7778", "limit": 200}).json()
    assert alvo["id"] in [f["id"] for f in achados]


def test_busca_respeita_isolamento_por_empresa(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    meu = _criar(client_admin, documento="55.666.777/0001-88")
    agora = datetime.now(timezone.utc)
    db_session.execute(
        text(
            """
            INSERT INTO fornecedores (
                id, empresa_id, codigo_interno, codigo_referencia, ano_referencia,
                sequencial_referencia, nome, nome_normalizado, tipo_documento, documento,
                documento_normalizado, status, cor_identificacao, created_at, updated_at
            ) VALUES (
                :id, :emp, 'alheio-2', 'F26099998', 26, 99998, 'Alheio', 'alheio', 'cnpj',
                '55.666.777/0001-88', '55666777000188', 'ativo', 'blue', :a, :a
            )
            """
        ),
        {"id": str(uuid.uuid4()), "emp": outra_empresa.id, "a": agora},
    )
    db_session.flush()

    achados = client_admin.get(
        "/fornecedores", params={"search": "55666777000188", "limit": 200}
    ).json()
    assert [f["id"] for f in achados] == [meu["id"]]


# ======================================================================================
# Diretório — exclui arquivados (divergência deliberada de Cliente)
# ======================================================================================

def test_diretorio_lista_ativos_e_inativos(client_admin: TestClient) -> None:
    ativo = _criar(client_admin)
    inativo = _criar(client_admin, status="inativo")
    ids = [f["id"] for f in client_admin.get("/fornecedores/diretorio").json()]
    assert ativo["id"] in ids
    assert inativo["id"] in ids


def test_diretorio_nao_inclui_arquivados(client_admin: TestClient) -> None:
    """Arquivado nunca pode ser oferecido como opção de vínculo novo.

    Diverge de `/clientes/diretorio`, que inclui arquivados porque Demanda e Projeto guardam
    referências históricas a resolver. Nenhum domínio referencia fornecedor, então o
    diretório serve só para montar opções — e opção arquivada é erro.
    """
    criado = _criar(client_admin)
    client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})

    ids = [f["id"] for f in client_admin.get("/fornecedores/diretorio").json()]
    assert criado["id"] not in ids


def test_diretorio_e_acessivel_a_operador(client_operador: TestClient) -> None:
    """Seleção de vínculo não é ato administrativo — só a lista completa exige admin/gestor."""
    assert client_operador.get("/fornecedores/diretorio").status_code == 200


def test_diretorio_nao_expoe_dados_administrativos(client_admin: TestClient) -> None:
    _criar(client_admin, observacoes="Condição de pagamento negociada", email="x@y.com")
    item = client_admin.get("/fornecedores/diretorio").json()[0]
    assert set(item) == {
        "id",
        "codigoInterno",
        "codigoReferencia",
        "sequencialReferencia",
        "nome",
        "categoria",
        "corIdentificacao",
        "status",
    }


# ======================================================================================
# Eventos de domínio — não há tabela de histórico
# ======================================================================================

def _tipos_de_evento(db: Session, fornecedor_id: str) -> list[str]:
    linhas = db.execute(
        text("SELECT tipo FROM eventos WHERE entidade_id = :i ORDER BY occurred_at, tipo"),
        {"i": fornecedor_id},
    ).scalars()
    return list(linhas)


def test_eventos_publicados_no_ciclo_de_vida(
    client_admin: TestClient, db_session: Session
) -> None:
    criado = _criar(client_admin)
    assert _tipos_de_evento(db_session, criado["id"]) == ["fornecedor.criado"]

    client_admin.patch(f"/fornecedores/{criado['id']}", json={"nome": "Outro Nome"})
    assert "fornecedor.alterado" in _tipos_de_evento(db_session, criado["id"])

    client_admin.post(f"/fornecedores/{criado['id']}/arquivar", json={"motivoArquivamento": "x"})
    assert "fornecedor.arquivado" in _tipos_de_evento(db_session, criado["id"])

    client_admin.post(f"/fornecedores/{criado['id']}/restaurar")
    assert "fornecedor.restaurado" in _tipos_de_evento(db_session, criado["id"])


def test_evento_nao_e_publicado_sem_alteracao_real(
    client_admin: TestClient, db_session: Session
) -> None:
    criado = _criar(client_admin)
    client_admin.patch(f"/fornecedores/{criado['id']}", json={"nome": criado["nome"]})
    assert _tipos_de_evento(db_session, criado["id"]) == ["fornecedor.criado"]


def test_evento_carrega_codigo_referencia(client_admin: TestClient, db_session: Session) -> None:
    criado = _criar(client_admin)
    payload = db_session.execute(
        text("SELECT payload FROM eventos WHERE entidade_id = :i"), {"i": criado["id"]}
    ).scalar_one()
    assert payload["codigo_referencia"] == criado["codigoReferencia"]


# ======================================================================================
# Rollback da sequência
# ======================================================================================

def test_falha_na_criacao_nao_queima_sequencia(client_admin: TestClient) -> None:
    """O contador participa da transação do service: criação recusada não avança número."""
    antes = _criar(client_admin)["sequencialReferencia"]

    # Recusada na validação do schema, antes de qualquer escrita.
    recusada = client_admin.post("/fornecedores", json=_payload(uf="LONGO DEMAIS"))
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
    from app.schemas.fornecedor import FornecedorCreate
    from app.services.fornecedor_service import FornecedorService

    agora = datetime.now(timezone.utc)
    empresa_id = str(uuid.uuid4())
    with SessionRaw(bind=test_engine) as setup:
        setup.add(
            EmpresaModel(
                id=empresa_id,
                codigo_interno=f"CONF{uuid.uuid4().hex[:6].upper()}",
                nome="Empresa Concorrência Fornecedor",
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
    service = FornecedorService()

    def criar() -> None:
        with SessionRaw(bind=test_engine) as sessao:
            barreira.wait()  # maximiza a chance de colisão real
            fornecedor = service.create_fornecedor(
                sessao,
                FornecedorCreate.model_validate(_payload()),
                empresa_id=empresa_id,
            )
            with trava:
                obtidos.append(fornecedor.sequencial_referencia)

    threads = [threading.Thread(target=criar) for _ in range(total)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sorted(obtidos) == list(range(1, total + 1)), (
            f"sequenciais duplicados/faltando: {obtidos}"
        )
    finally:
        with SessionRaw(bind=test_engine) as limpeza:
            limpeza.execute(text("DELETE FROM fornecedores WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM eventos WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(
                text("DELETE FROM sequencias_referencia WHERE empresa_id = :e"), {"e": empresa_id}
            )
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
            limpeza.commit()
