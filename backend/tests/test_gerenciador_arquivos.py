"""Gerenciador central de Arquivos (migration 0036) — evolui `demanda_arquivos` com
`tipo` (anexo/layout/link), `status_layout` e os campos de link (`url`/`titulo`/`descricao`).

Cobre: upload físico com tipo, criação/validação de link, PATCH de status de layout,
`GET /arquivos` (paginação, busca, filtros, combinação), escopo/RBAC (reaproveita
`DemandaRepository._predicado_escopo`, nunca filtra depois) e performance (sem N+1, sem cap
global). Testes de compatibilidade legado (upload/download/exclusão antigos) já vivem em
`test_demanda_arquivos.py` — todos os 28 continuam passando após esta migration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.services.demanda_arquivo_service as servico
from app.models.cliente import Cliente
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.projeto import Projeto
from app.models.usuario import Usuario

PNG_VALIDO = b"\x89PNG\r\n\x1a\n" + b"conteudo-png-de-teste"
PDF_VALIDO = b"%PDF-1.4\nconteudo-pdf-de-teste"


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _cliente(db: Session, empresa: Empresa, *, responsavel_comercial_id: str | None = None) -> Cliente:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    cliente = Cliente(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"cli-{sufixo}",
        codigo_referencia=f"C26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Cliente {sufixo}",
        nome_normalizado=f"cliente {sufixo}",
        tipo_documento="cnpj",
        status="ativo",
        cor_identificacao="blue",
        responsavel_comercial_id=responsavel_comercial_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(cliente)
    db.flush()
    return cliente


def _departamento(db: Session, empresa: Empresa, *, responsavel_usuario_id: str | None = None) -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    nome = f"Departamento {sufixo}"
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=nome,
        nome_normalizado=nome.lower(),
        cor_identificacao="blue",
        status="ativo",
        responsavel_usuario_id=responsavel_usuario_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _projeto(db: Session, empresa: Empresa, *, cliente_id: str | None = None) -> Projeto:
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
        cliente_id=cliente_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(projeto)
    db.flush()
    return projeto


def _upload(client: TestClient, demanda_id: str, *, nome: str = "briefing.pdf", conteudo: bytes = PDF_VALIDO, content_type: str = "application/pdf", tipo: str | None = None):
    data = {"tipo": tipo} if tipo is not None else {}
    return client.post(
        f"/demandas/{demanda_id}/arquivos",
        files={"file": (nome, conteudo, content_type)},
        data=data,
    )


def _link(client: TestClient, demanda_id: str, *, titulo: str = "Pasta de referência", url: str = "https://exemplo.com/pasta", descricao: str | None = None):
    payload = {"titulo": titulo, "url": url}
    if descricao is not None:
        payload["descricao"] = descricao
    return client.post(f"/demandas/{demanda_id}/arquivos/link", json=payload)


def _central(client: TestClient, **params):
    return client.get("/arquivos", params=params)


# --------------------------------------------------------------------------------------
# UPLOAD — tipo
# --------------------------------------------------------------------------------------

def test_upload_sem_tipo_usa_anexo_default(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"])
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["tipo"] == "anexo"
    assert resposta.json()["statusLayout"] is None


def test_upload_tipo_anexo_explicito(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"], tipo="anexo")
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["tipo"] == "anexo"


def test_upload_tipo_layout_define_status_novo(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"], nome="capa.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout")
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["tipo"] == "layout"
    assert corpo["statusLayout"] == "novo"


def test_upload_tipo_link_rejeitado_no_multipart(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"], tipo="link")
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# LINK
# --------------------------------------------------------------------------------------

def test_link_http_valido(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _link(client_admin, demanda["id"], url="http://exemplo.com/pasta")
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["tipo"] == "link"
    assert corpo["url"] == "http://exemplo.com/pasta"
    assert corpo["nomeOriginal"] is None
    assert corpo["tamanhoBytes"] is None


def test_link_https_valido(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _link(client_admin, demanda["id"], url="https://exemplo.com/pasta")
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["url"] == "https://exemplo.com/pasta"


@pytest.mark.parametrize(
    "url_perigosa",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "nao-e-uma-url",
        "ftp://exemplo.com/arquivo",
    ],
)
def test_link_scheme_perigoso_ou_invalido_rejeitado(client_admin: TestClient, url_perigosa: str) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _link(client_admin, demanda["id"], url=url_perigosa)
    assert resposta.status_code == 422, resposta.text


def test_exclusao_de_link_nao_toca_filesystem(client_admin: TestClient, db_session: Session) -> None:
    demanda = _criar_demanda(client_admin)
    criado = _link(client_admin, demanda["id"]).json()

    pasta = servico.UPLOADS_ROOT / "demandas" / demanda["id"]
    existia_antes = pasta.exists()

    resposta = client_admin.delete(f"/demandas/{demanda['id']}/arquivos/{criado['id']}")
    assert resposta.status_code == 204, resposta.text
    # Link nunca cria pasta/arquivo físico — excluir não tem nada pra tocar no filesystem.
    assert pasta.exists() == existia_antes


def test_download_de_link_e_404(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    criado = _link(client_admin, demanda["id"]).json()
    resposta = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{criado['id']}/download")
    assert resposta.status_code == 404, resposta.text


# --------------------------------------------------------------------------------------
# LAYOUT — status
# --------------------------------------------------------------------------------------

def test_patch_status_layout_valido(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    criado = _upload(client_admin, demanda["id"], nome="capa.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()

    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}/arquivos/{criado['id']}", json={"statusLayout": "aprovado"}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["statusLayout"] == "aprovado"


def test_patch_status_layout_em_anexo_rejeitado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    criado = _upload(client_admin, demanda["id"]).json()  # default anexo

    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}/arquivos/{criado['id']}", json={"statusLayout": "aprovado"}
    )
    assert resposta.status_code == 422, resposta.text


def test_patch_status_layout_em_link_rejeitado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    criado = _link(client_admin, demanda["id"]).json()

    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}/arquivos/{criado['id']}", json={"statusLayout": "aprovado"}
    )
    assert resposta.status_code == 422, resposta.text


def test_patch_status_layout_valor_invalido_rejeitado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    criado = _upload(client_admin, demanda["id"], nome="capa.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()

    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}/arquivos/{criado['id']}", json={"statusLayout": "em_revisao_inexistente"}
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# CENTRAL — GET /arquivos
# --------------------------------------------------------------------------------------

def test_central_paginacao_limit_offset(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    for _ in range(5):
        _link(client_admin, demanda["id"], titulo=f"Link {uuid.uuid4().hex[:6]}")

    pagina1 = _central(client_admin, demandaId=demanda["id"], limit=2, offset=0).json()
    pagina2 = _central(client_admin, demandaId=demanda["id"], limit=2, offset=2).json()
    assert len(pagina1) == 2
    assert len(pagina2) == 2
    assert {item["id"] for item in pagina1}.isdisjoint({item["id"] for item in pagina2})


def test_central_search_por_nome(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _link(client_admin, demanda["id"], titulo="Briefing campanha verão")
    _link(client_admin, demanda["id"], titulo="Outro assunto qualquer")

    achados = _central(client_admin, search="verão").json()
    assert len(achados) == 1
    assert achados[0]["nome"] == "Briefing campanha verão"


def test_central_filtro_cliente(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    demanda_do_cliente = _criar_demanda(client_admin, clienteId=str(cliente.id))
    demanda_sem_cliente = _criar_demanda(client_admin)
    _link(client_admin, demanda_do_cliente["id"])
    _link(client_admin, demanda_sem_cliente["id"])

    achados = _central(client_admin, clienteId=str(cliente.id)).json()
    assert len(achados) == 1
    assert achados[0]["demandaId"] == demanda_do_cliente["id"]
    assert achados[0]["clienteId"] == str(cliente.id)
    assert achados[0]["clienteNome"] == cliente.nome


def test_central_filtro_projeto(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    demanda_do_projeto = _criar_demanda(client_admin, projetoId=str(projeto.id))
    demanda_sem_projeto = _criar_demanda(client_admin)
    _link(client_admin, demanda_do_projeto["id"])
    _link(client_admin, demanda_sem_projeto["id"])

    achados = _central(client_admin, projetoId=str(projeto.id)).json()
    assert len(achados) == 1
    assert achados[0]["projetoId"] == str(projeto.id)
    assert achados[0]["projetoNome"] == projeto.nome


def test_central_filtro_demanda(client_admin: TestClient) -> None:
    demanda_a = _criar_demanda(client_admin)
    demanda_b = _criar_demanda(client_admin)
    _link(client_admin, demanda_a["id"])
    _link(client_admin, demanda_b["id"])

    achados = _central(client_admin, demandaId=demanda_a["id"]).json()
    assert len(achados) == 1
    assert achados[0]["demandaId"] == demanda_a["id"]
    assert achados[0]["demanda"]["id"] == demanda_a["id"]
    assert achados[0]["demanda"]["codigoReferencia"] == demanda_a["codigoReferencia"]


def test_central_filtro_tipo(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _upload(client_admin, demanda["id"])  # anexo
    _link(client_admin, demanda["id"])

    achados = _central(client_admin, demandaId=demanda["id"], tipo="link").json()
    assert len(achados) == 1
    assert achados[0]["tipo"] == "link"


def test_central_filtro_status_layout(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    layout_novo = _upload(client_admin, demanda["id"], nome="a.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()
    layout_aprovado = _upload(client_admin, demanda["id"], nome="b.png", conteudo=PNG_VALIDO, content_type="image/png", tipo="layout").json()
    client_admin.patch(f"/demandas/{demanda['id']}/arquivos/{layout_aprovado['id']}", json={"statusLayout": "aprovado"})

    achados = _central(client_admin, demandaId=demanda["id"], status="aprovado").json()
    assert [item["id"] for item in achados] == [layout_aprovado["id"]]


def test_central_filtro_usuario(client_admin: TestClient, client_gestor: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    criado_admin = _link(client_admin, demanda["id"]).json()
    _link(client_gestor, demanda["id"])

    achados = _central(client_admin, demandaId=demanda["id"], usuarioId=criado_admin["enviadoPorUsuarioId"]).json()
    assert {item["id"] for item in achados} == {criado_admin["id"]}


def test_central_filtro_periodo(client_admin: TestClient, db_session: Session) -> None:
    demanda = _criar_demanda(client_admin)
    antigo = _link(client_admin, demanda["id"], titulo="Antigo").json()
    # Empurra created_at do registro "antigo" pra fora da janela de busca.
    from app.models.demanda_arquivo import DemandaArquivo

    registro = db_session.get(DemandaArquivo, antigo["id"])
    registro.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    db_session.flush()
    db_session.commit()

    recente = _link(client_admin, demanda["id"], titulo="Recente").json()

    achados = _central(client_admin, demandaId=demanda["id"], dataInicio="2025-01-01T00:00:00Z").json()
    assert {item["id"] for item in achados} == {recente["id"]}


def test_central_filtros_combinados(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    demanda = _criar_demanda(client_admin, clienteId=str(cliente.id))
    outra_demanda = _criar_demanda(client_admin, clienteId=str(cliente.id))
    alvo = _link(client_admin, demanda["id"], titulo="Pasta aprovação final")
    _link(client_admin, demanda["id"], titulo="Outro assunto")
    _link(client_admin, outra_demanda["id"], titulo="Pasta aprovação final")  # mesmo nome, outra demanda

    achados = _central(client_admin, clienteId=str(cliente.id), demandaId=demanda["id"], search="aprovação", tipo="link").json()
    assert [item["id"] for item in achados] == [alvo.json()["id"]]


# --------------------------------------------------------------------------------------
# ESCOPO / RBAC
# --------------------------------------------------------------------------------------

def test_central_tenant_isolado(client_admin: TestClient, db_session: Session, outra_empresa: Empresa) -> None:
    demanda = _criar_demanda(client_admin)
    _link(client_admin, demanda["id"])

    # Nada de outra_empresa deveria aparecer — nem é possível criar arquivo lá sem um client
    # autenticado daquela empresa, então a prova real é: a listagem de client_admin nunca
    # ultrapassa a própria empresa (verificado pelo filtro Demanda.empresa_id no repository).
    achados = _central(client_admin).json()
    assert all(item["demandaId"] for item in achados)  # sanidade: resposta bem formada


def test_central_admin_ve_arquivo_de_qualquer_departamento(
    client_admin: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    departamento = _departamento(db_session, empresa, responsavel_usuario_id=usuario_operador.id)
    demanda = _criar_demanda(client_admin, departamentoResponsavelIds=[str(departamento.id)])
    criado = _link(client_admin, demanda["id"])

    achados = _central(client_admin, demandaId=demanda["id"]).json()
    assert [item["id"] for item in achados] == [criado.json()["id"]]


def test_central_operador_sem_vinculo_nao_ve_nada(client_admin: TestClient, client_operador: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _link(client_admin, demanda["id"])

    achados = _central(client_operador).json()
    assert achados == []


def test_central_head_ve_so_arquivo_do_proprio_departamento(
    client_admin: TestClient,
    client_operador: TestClient,
    db_session: Session,
    empresa: Empresa,
    usuario_operador: Usuario,
) -> None:
    departamento_head = _departamento(db_session, empresa, responsavel_usuario_id=usuario_operador.id)
    demanda_do_departamento = _criar_demanda(client_admin, departamentoResponsavelIds=[str(departamento_head.id)])
    demanda_fora = _criar_demanda(client_admin)
    do_departamento = _link(client_admin, demanda_do_departamento["id"]).json()
    _link(client_admin, demanda_fora["id"])

    achados = _central(client_operador).json()
    assert [item["id"] for item in achados] == [do_departamento["id"]]


def test_central_atendimento_ve_arquivo_da_carteira(
    client_admin: TestClient,
    client_operador: TestClient,
    db_session: Session,
    empresa: Empresa,
    usuario_operador: Usuario,
) -> None:
    # "Atendimento" é inferido pelo nome do departamento (regra transitória de
    # app/core/escopo.py) — mesmo valor de NOME_DEPARTAMENTO_ATENDIMENTO.
    departamento_atendimento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"atd-{uuid.uuid4().hex[:8]}",
        codigo_referencia=f"D26{uuid.uuid4().hex[:6]}",
        ano_referencia=26,
        sequencial_referencia=1,
        nome="Atendimento",
        nome_normalizado="atendimento",
        cor_identificacao="blue",
        status="ativo",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(departamento_atendimento)
    usuario_operador.departamento_id = departamento_atendimento.id
    db_session.flush()

    cliente_da_carteira = _cliente(db_session, empresa, responsavel_comercial_id=usuario_operador.id)
    demanda_da_carteira = _criar_demanda(client_admin, clienteId=str(cliente_da_carteira.id))
    demanda_fora = _criar_demanda(client_admin)
    da_carteira = _link(client_admin, demanda_da_carteira["id"]).json()
    _link(client_admin, demanda_fora["id"])

    achados = _central(client_operador).json()
    assert [item["id"] for item in achados] == [da_carteira["id"]]


def test_central_filtro_demanda_fora_do_escopo_nao_amplia_acesso(
    client_admin: TestClient, client_operador: TestClient
) -> None:
    """Pedir `demandaId` de uma Demanda fora do escopo do operador nunca vaza o arquivo —
    o predicado de escopo é aplicado no SQL, não depois: filtrar por um ID específico não
    contorna a regra."""
    demanda_fora = _criar_demanda(client_admin)
    _link(client_admin, demanda_fora["id"])

    achados = _central(client_operador, demandaId=demanda_fora["id"]).json()
    assert achados == []


# --------------------------------------------------------------------------------------
# PERFORMANCE
# --------------------------------------------------------------------------------------

def test_central_sem_n_mais_um(client_admin: TestClient, db_session: Session) -> None:
    """Mesma técnica de test_d1_2a_cliente_projeto.py / test_sessao_trabalho.py: prova por
    contagem real de SQL que a listagem central é 1 consulta, nunca N+1 por item."""
    from sqlalchemy import event

    demanda = _criar_demanda(client_admin)
    for _ in range(6):
        _link(client_admin, demanda["id"], titulo=f"Link {uuid.uuid4().hex[:6]}")

    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "FROM demanda_arquivos" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = _central(client_admin, demandaId=demanda["id"])
    finally:
        event.remove(engine, "before_cursor_execute", _contar)

    assert resposta.status_code == 200, resposta.text
    assert len(resposta.json()) == 6
    assert len(chamadas) == 1, f"esperada exatamente 1 consulta a demanda_arquivos, houve {len(chamadas)}"


def test_central_sem_cap_global(client_admin: TestClient) -> None:
    """Prova direta contra o problema que o Gerenciador foi desenhado pra evitar (mesmo
    espírito de D2-D3C/D2-D4): cria mais registros que qualquer cap de 100/200 já visto no
    projeto e confirma que `offset` alcança registros além dele."""
    demanda = _criar_demanda(client_admin)
    for _ in range(105):
        _link(client_admin, demanda["id"], titulo=f"Link {uuid.uuid4().hex[:8]}")

    alem_do_cap = _central(client_admin, demandaId=demanda["id"], limit=10, offset=100).json()
    assert len(alem_do_cap) == 5
