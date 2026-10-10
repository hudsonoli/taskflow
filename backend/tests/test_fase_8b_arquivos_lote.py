"""Fase 8B — Arquivos em lote: seleção por IDs ou "todos os resultados do filtro", download em ZIP e exclusão múltipla.

Provas: o universo do lote é o da listagem (mesmos filtros/escopo/tenant); ID não autorizado derruba a operação inteira (404, nada alterado);
ZIP válido, com nomes saneados e únicos, sem carregar arquivos em memória e sem sobras temporárias; arquivo físico ausente → 409 sem ZIP incompleto;
tetos → 413; exclusão com pré-validação total, uma transação e um evento por arquivo; contexto (Cliente/Projeto/Demanda) nunca é ampliado por filtro.
"""

from __future__ import annotations

import inspect
import io
import re
import tempfile
import uuid
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.services.arquivo_lote_service as lote_modulo
import app.services.demanda_arquivo_service as arquivo_modulo
from app.models.demanda_arquivo import DemandaArquivo
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.services.arquivo_lote_service import nome_seguro_para_zip, nomes_unicos_para_zip
from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_d1_criacao_demandas import _client_para, _operador_comum
from tests.test_gerenciador_arquivos import (
    PDF_VALIDO,
    PNG_VALIDO,
    _central,
    _cliente,
    _criar_demanda,
    _departamento,
    _link,
    _projeto,
    _upload,
)


# ======================================================================================
# helpers
# ======================================================================================


def _enviar(client: TestClient, demanda_id: str, nome: str = "arte.pdf", *, conteudo: bytes | None = None, tipo: str | None = None) -> dict:
    ehpng = nome.lower().endswith(".png")
    base = PNG_VALIDO if ehpng else PDF_VALIDO
    corpo = conteudo if conteudo is not None else base + uuid.uuid4().hex.encode()
    resposta = _upload(client, demanda_id, nome=nome, conteudo=corpo, content_type="image/png" if ehpng else "application/pdf", tipo=tipo)
    assert resposta.status_code == 201, resposta.text
    return {**resposta.json(), "_conteudo": corpo}


def _ids(*itens: dict) -> dict:
    return {"mode": "ids", "ids": [i["id"] for i in itens]}


def _todos(filtros: dict | None = None, *, excluded: list[str] | None = None, contexto: dict | None = None) -> dict:
    corpo: dict = {"mode": "all_filtered", "excludedIds": excluded or []}
    if filtros:
        corpo["filtros"] = filtros
    if contexto:
        corpo["contexto"] = contexto
    return corpo


def _zip(resposta) -> zipfile.ZipFile:
    assert resposta.status_code == 200, resposta.text
    return zipfile.ZipFile(io.BytesIO(resposta.content))


def _existentes(db: Session, *ids: str) -> int:
    return db.scalar(select(func.count()).select_from(DemandaArquivo).where(DemandaArquivo.id.in_(ids))) or 0


def _caminho(arquivo: dict) -> Path:
    from app.services.demanda_arquivo_service import DemandaArquivoService

    # nome físico = {id}{ext}; a extensão vem do nome enviado
    pasta = Path(arquivo_modulo.UPLOADS_ROOT) / "demandas" / arquivo["demandaId"]
    achados = list(pasta.glob(f"{arquivo['id']}*"))
    assert len(achados) == 1, achados
    return achados[0]


def _temporarios_zip() -> set[str]:
    return {p.name for p in Path(tempfile.gettempdir()).glob("tfzip-*.zip")}


@pytest.fixture()
def sem_sobra_de_zip():
    antes = _temporarios_zip()
    yield
    assert _temporarios_zip() - antes == set(), "sobrou ZIP temporário"


# ======================================================================================
# download — IDs explícitos
# ======================================================================================


def test_download_ids_gera_zip_valido_com_cabecalhos_seguros(client_admin: TestClient, sem_sobra_de_zip) -> None:
    demanda = _criar_demanda(client_admin)
    a = _enviar(client_admin, demanda["id"], "contrato.pdf")
    b = _enviar(client_admin, demanda["id"], "foto.png")
    _enviar(client_admin, demanda["id"], "fora.pdf")  # existe mas NÃO foi selecionado

    resposta = client_admin.post("/arquivos/download-lote", json=_ids(a, b))
    zf = _zip(resposta)
    assert zf.testzip() is None
    assert sorted(zf.namelist()) == ["contrato.pdf", "foto.png"]
    assert zf.read("contrato.pdf") == a["_conteudo"] and zf.read("foto.png") == b["_conteudo"]

    assert resposta.headers["content-type"] == "application/zip"
    disposicao = resposta.headers["content-disposition"]
    assert re.fullmatch(r'attachment; filename="taskfloww-arquivos-\d{8}-\d{4}\.zip"', disposicao), disposicao
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.headers["x-lote-arquivos"] == "2" and resposta.headers["x-lote-links-ignorados"] == "0"


def test_nomes_duplicados_nao_se_sobrescrevem_e_preservam_extensao(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    outra = _criar_demanda(client_admin)
    itens = [
        _enviar(client_admin, demanda["id"], "arte.pdf"),
        _enviar(client_admin, outra["id"], "arte.pdf"),
        _enviar(client_admin, demanda["id"], "ARTE.pdf"),  # difere só por maiúsculas: também não pode colidir
        _enviar(client_admin, demanda["id"], "imagem.png"),
    ]
    zf = _zip(client_admin.post("/arquivos/download-lote", json=_ids(*itens)))
    nomes = zf.namelist()
    assert len(nomes) == len(set(n.lower() for n in nomes)) == 4
    assert sorted(n.lower() for n in nomes) == ["arte (2).pdf", "arte (3).pdf", "arte.pdf", "imagem.png"]  # sufixo numerado, extensão preservada
    assert all(n.endswith(".pdf") for n in nomes if n != "imagem.png")
    conteudos = {zf.read(n) for n in nomes}
    assert conteudos == {i["_conteudo"] for i in itens}  # nenhum sobrescreveu o outro


@pytest.mark.parametrize(
    "nome_no_banco, esperado_sem",
    [
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("..\\..\\windows\\evil.pdf", "evil.pdf"),
        ("/abs/caminho/arquivo.pdf", "arquivo.pdf"),
        ("a" + chr(7) + "b" + chr(31) + ".pdf", "ab.pdf"),
        ("..", "arquivo.pdf"),
        ("   ", "arquivo.pdf"),
        ("C:\\Users\\x\\rel*ato?.pdf", "relato.pdf"),
    ],
)
def test_path_traversal_e_caracteres_perigosos_no_nome_do_zip(client_admin: TestClient, db_session: Session, nome_no_banco: str, esperado_sem: str) -> None:
    demanda = _criar_demanda(client_admin)
    arquivo = _enviar(client_admin, demanda["id"], "ok.pdf")
    registro = db_session.get(DemandaArquivo, arquivo["id"])
    registro.nome_original = nome_no_banco  # dado legado/hostil já persistido
    db_session.commit()

    zf = _zip(client_admin.post("/arquivos/download-lote", json=_ids(arquivo)))
    (entrada,) = zf.namelist()
    assert entrada == esperado_sem
    assert "/" not in entrada and "\\" not in entrada and ".." not in entrada and not entrada.startswith(".")
    assert zf.read(entrada) == arquivo["_conteudo"]


def test_funcoes_de_nome_saneiam_e_deduplicam() -> None:
    assert nome_seguro_para_zip("a" * 300 + ".pdf").endswith(".pdf") and len(nome_seguro_para_zip("a" * 300 + ".pdf")) <= 120
    assert nome_seguro_para_zip("CON.pdf") == "_CON.pdf"
    assert nome_seguro_para_zip(None, ".pdf") == "arquivo.pdf"
    assert nome_seguro_para_zip("relatório final.pdf") == "relatório final.pdf"
    unicos = nomes_unicos_para_zip(["x.pdf", "x.pdf", "X.PDF", "x (2).pdf"])
    assert len({n.lower() for n in unicos}) == 4 and unicos[0] == "x.pdf" and unicos[1] == "x (2).pdf"
    assert nomes_unicos_para_zip(["sem_extensao", "sem_extensao"]) == ["sem_extensao", "sem_extensao (2)"]


def test_links_nao_entram_no_zip_e_so_links_e_404(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    arq = _enviar(client_admin, demanda["id"], "a.pdf")
    link = _link(client_admin, demanda["id"]).json()
    resposta = client_admin.post("/arquivos/download-lote", json=_ids(arq, link))
    assert _zip(resposta).namelist() == ["a.pdf"]
    assert resposta.headers["x-lote-links-ignorados"] == "1"
    assert client_admin.post("/arquivos/download-lote", json=_ids(link)).status_code == 404


def test_arquivo_fisico_ausente_409_sem_zip_incompleto(client_admin: TestClient, sem_sobra_de_zip) -> None:
    demanda = _criar_demanda(client_admin)
    a = _enviar(client_admin, demanda["id"], "a.pdf")
    b = _enviar(client_admin, demanda["id"], "b.pdf")
    _caminho(b).unlink()  # sumiu do armazenamento
    resposta = client_admin.post("/arquivos/download-lote", json=_ids(a, b))
    assert resposta.status_code == 409
    detalhe = resposta.json()["detail"]
    assert detalhe["code"] == "ARQUIVO_FISICO_AUSENTE" and detalhe["quantidade"] == 1
    assert "1 arquivo" in detalhe["message"]
    assert resposta.headers["content-type"].startswith("application/json")  # nada de ZIP parcial


def test_falha_no_meio_da_montagem_nao_deixa_temporario(client_admin: TestClient, monkeypatch, sem_sobra_de_zip) -> None:
    demanda = _criar_demanda(client_admin)
    a = _enviar(client_admin, demanda["id"], "a.pdf")
    b = _enviar(client_admin, demanda["id"], "b.pdf")

    original = zipfile.ZipFile.write
    chamadas = {"n": 0}

    def quebra_na_segunda(self, *args, **kwargs):
        chamadas["n"] += 1
        if chamadas["n"] == 2:
            raise FileNotFoundError("sumiu entre a conferência e a leitura")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "write", quebra_na_segunda)
    resposta = client_admin.post("/arquivos/download-lote", json=_ids(a, b))
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "ARQUIVO_FISICO_AUSENTE"


# ======================================================================================
# streaming: nada de ler arquivos inteiros em memória
# ======================================================================================


def test_zip_nao_le_arquivos_inteiros_em_memoria(client_admin: TestClient, monkeypatch) -> None:
    demanda = _criar_demanda(client_admin)
    itens = [_enviar(client_admin, demanda["id"], f"f{i}.pdf") for i in range(3)]

    def proibido(*args, **kwargs):
        raise AssertionError("leitura integral em memória")

    monkeypatch.setattr(Path, "read_bytes", proibido)
    monkeypatch.setattr(Path, "read_text", proibido)
    zf = _zip(client_admin.post("/arquivos/download-lote", json=_ids(*itens)))
    assert len(zf.namelist()) == 3

    codigo = inspect.getsource(lote_modulo)
    codigo_sem_comentarios = re.sub(r'""".*?"""', "", codigo, flags=re.S)
    assert ".read_bytes(" not in codigo_sem_comentarios and ".read()" not in codigo_sem_comentarios
    assert "zf.write(" in codigo and "tempfile.mkstemp" in codigo  # arquivo temporário + escrita em blocos
    assert "BytesIO" not in codigo_sem_comentarios and "writestr(" not in codigo_sem_comentarios


def test_compressao_barata_para_formatos_ja_comprimidos(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    png = _enviar(client_admin, demanda["id"], "i.png")
    pdf = _enviar(client_admin, demanda["id"], "d.pdf")
    zf = _zip(client_admin.post("/arquivos/download-lote", json=_ids(png, pdf)))
    tipos = {i.filename: i.compress_type for i in zf.infolist()}
    assert tipos["i.png"] == zipfile.ZIP_STORED and tipos["d.pdf"] == zipfile.ZIP_DEFLATED


# ======================================================================================
# all_filtered / excludedIds / mesmo universo da listagem
# ======================================================================================


def test_all_filtered_inclui_paginas_nao_carregadas_e_respeita_excluidos(client_admin: TestClient, db_session: Session) -> None:
    demanda = _criar_demanda(client_admin)
    itens = [_enviar(client_admin, demanda["id"], f"p{i}.pdf") for i in range(7)]

    # listagem em páginas de 3: a seleção "todos" cobre as 7, não só a primeira página
    pagina = _central(client_admin, demandaId=demanda["id"], limit=3).json()
    assert len(pagina) == 3
    resumo = client_admin.post("/arquivos/resumo-lote", json=_todos({"demandaId": demanda["id"]})).json()
    assert resumo["total"] == 7 and resumo["links"] == 0 and resumo["arquivosFisicos"] == 7

    excluidos = [itens[0]["id"], itens[6]["id"]]
    resumo2 = client_admin.post("/arquivos/resumo-lote", json=_todos({"demandaId": demanda["id"]}, excluded=excluidos)).json()
    assert resumo2["total"] == 5
    zf = _zip(client_admin.post("/arquivos/download-lote", json=_todos({"demandaId": demanda["id"]}, excluded=excluidos)))
    assert sorted(zf.namelist()) == sorted(f"p{i}.pdf" for i in range(1, 6))

    # id excluído que nem pertence ao universo é ignorado sem erro
    assert client_admin.post("/arquivos/resumo-lote", json=_todos({"demandaId": demanda["id"]}, excluded=[str(uuid.uuid4())])).json()["total"] == 7


def test_mesmo_universo_da_listagem_para_varios_filtros(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa)
    db_session.commit()
    d1 = _criar_demanda(client_admin, clienteId=str(cliente.id), nome="Campanha Verão")
    d2 = _criar_demanda(client_admin, projetoId=str(projeto.id), nome="Site institucional")
    _enviar(client_admin, d1["id"], "contrato-verao.pdf")
    _enviar(client_admin, d1["id"], "layout1.png", tipo="layout")
    _enviar(client_admin, d2["id"], "contrato-site.pdf")
    _enviar(client_admin, d2["id"], "layout2.png", tipo="layout")
    _link(client_admin, d2["id"])

    casos = [
        {},
        {"search": "contrato"},
        {"tipo": "layout"},
        {"tipo": "anexo", "search": "site"},
        {"clienteId": str(cliente.id)},
        {"projetoId": str(projeto.id)},
        {"tipoExcluir": "link"},
        {"status": "novo"},
        {"clienteIdExcluir": str(cliente.id)},
    ]
    for filtros in casos:
        listados = _central(client_admin, limit=200, **filtros).json()
        resumo = client_admin.post("/arquivos/resumo-lote", json=_todos(filtros)).json()
        assert resumo["total"] == len(listados), filtros
        assert resumo["links"] == sum(1 for i in listados if i["tipo"] == "link"), filtros


def test_busca_por_nome_faz_parte_do_universo_selecionado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _enviar(client_admin, demanda["id"], "contrato-a.pdf")
    _enviar(client_admin, demanda["id"], "contrato-b.pdf")
    _enviar(client_admin, demanda["id"], "briefing.pdf")
    zf = _zip(client_admin.post("/arquivos/download-lote", json=_todos({"search": "contrato", "demandaId": demanda["id"]})))
    assert sorted(zf.namelist()) == ["contrato-a.pdf", "contrato-b.pdf"]


def test_all_filtered_com_zero_resultados_404_e_nada_acontece(client_admin: TestClient) -> None:
    corpo = _todos({"search": "nada-que-case-" + uuid.uuid4().hex})
    assert client_admin.post("/arquivos/resumo-lote", json=corpo).json()["total"] == 0
    assert client_admin.post("/arquivos/download-lote", json=corpo).status_code == 404
    assert client_admin.post("/arquivos/excluir-lote", json=corpo).status_code == 404


# ======================================================================================
# contexto (Demanda / Projeto / Cliente) nunca é ampliado por filtro
# ======================================================================================


def test_contexto_demanda_projeto_cliente_limita_e_filtro_nao_amplia(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    cliente = _cliente(db_session, empresa)
    projeto = _projeto(db_session, empresa, cliente_id=str(cliente.id))
    db_session.commit()
    d_ctx = _criar_demanda(client_admin, clienteId=str(cliente.id), projetoId=str(projeto.id))
    d_fora = _criar_demanda(client_admin)
    dentro = _enviar(client_admin, d_ctx["id"], "dentro.pdf")
    fora = _enviar(client_admin, d_fora["id"], "fora.pdf")

    for contexto in ({"clienteId": str(cliente.id)}, {"projetoId": str(projeto.id)}, {"demandaId": d_ctx["id"]}):
        zf = _zip(client_admin.post("/arquivos/download-lote", json=_todos(contexto=contexto)))
        assert zf.namelist() == ["dentro.pdf"], contexto
        # um filtro avançado que APONTA para fora do contexto não amplia: AND ⇒ nada
        ampliado = _todos({"demandaId": d_fora["id"]}, contexto=contexto)
        assert client_admin.post("/arquivos/resumo-lote", json=ampliado).json()["total"] == 0
        assert client_admin.post("/arquivos/download-lote", json=ampliado).status_code == 404

    # IDs explícitos também respeitam o contexto: um ID de fora do contexto derruba a operação
    with_ids = {**_ids(dentro, fora), "contexto": {"demandaId": d_ctx["id"]}}
    assert client_admin.post("/arquivos/download-lote", json=with_ids).status_code == 404
    assert client_admin.post("/arquivos/excluir-lote", json=with_ids).status_code == 404
    assert _existentes(db_session, dentro["id"], fora["id"]) == 2


# ======================================================================================
# tenant e escopo
# ======================================================================================


def test_cross_tenant_nada_entra_no_zip_e_nada_e_excluido(app, client_admin: TestClient, db_session: Session, outra_empresa: Empresa) -> None:
    demanda = _criar_demanda(client_admin)
    meu = _enviar(client_admin, demanda["id"], "meu.pdf")

    intruso = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="lote-intruso")
    db_session.commit()
    cliente_b = _client_para(app, intruso)
    dem_b = _criar_demanda(cliente_b)
    dele = _enviar(cliente_b, dem_b["id"], "dele.pdf")

    # B tenta pegar o arquivo de A por ID → 404 (indistinguível de inexistente)
    assert cliente_b.post("/arquivos/download-lote", json=_ids(meu)).status_code == 404
    assert cliente_b.post("/arquivos/excluir-lote", json=_ids(meu)).status_code == 404
    # misto: um ID dele + um de A → falha inteira
    assert cliente_b.post("/arquivos/download-lote", json=_ids(dele, meu)).status_code == 404
    assert cliente_b.post("/arquivos/excluir-lote", json=_ids(dele, meu)).status_code == 404
    assert _existentes(db_session, meu["id"], dele["id"]) == 2

    # all_filtered de B só enxerga o de B (a consulta já nasce no tenant do token), mesmo pedindo a demanda de A
    zf = _zip(cliente_b.post("/arquivos/download-lote", json=_todos()))
    assert zf.namelist() == ["dele.pdf"]
    assert cliente_b.post("/arquivos/resumo-lote", json=_todos({"demandaId": demanda["id"]})).json()["total"] == 0


def test_escopo_operador_sem_vinculo_e_head_so_do_proprio_departamento(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario, client_operador: TestClient
) -> None:
    dep = _departamento(db_session, empresa, responsavel_usuario_id=usuario_operador.id)
    d_head = _criar_demanda(client_admin, departamentoResponsavelIds=[str(dep.id)])
    d_fora = _criar_demanda(client_admin)
    do_head = _enviar(client_admin, d_head["id"], "head.pdf")
    de_fora = _enviar(client_admin, d_fora["id"], "fora.pdf")

    # Head: todos do universo dele; um ID fora do escopo derruba a operação inteira
    assert _zip(client_operador.post("/arquivos/download-lote", json=_todos())).namelist() == ["head.pdf"]
    assert client_operador.post("/arquivos/download-lote", json=_ids(do_head, de_fora)).status_code == 404
    assert client_operador.post("/arquivos/excluir-lote", json=_ids(do_head, de_fora)).status_code == 404
    assert _existentes(db_session, do_head["id"], de_fora["id"]) == 2

    # operador sem nenhum vínculo: nada
    solto = _operador_comum(db_session, empresa, sufixo="lote-solto")
    db_session.commit()
    c_solto = _client_para(app, solto)
    assert c_solto.post("/arquivos/download-lote", json=_ids(de_fora)).status_code == 404
    assert c_solto.post("/arquivos/download-lote", json=_todos()).status_code == 404
    assert c_solto.post("/arquivos/resumo-lote", json=_todos()).json()["total"] == 0


def test_leitura_pela_pauta_global_nao_amplia_o_lote(app, client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    """O lote usa o escopo-BASE: o parâmetro `escopo=pauta` (leitura de detalhe) não existe aqui e não abre nada."""
    from tests.test_d1_criacao_demandas import _atendimento

    ana = _operador_comum(db_session, empresa, sufixo="lote-ana")
    _atendimento(db_session, empresa, ana)
    outro = _departamento(db_session, empresa)
    db_session.commit()
    demanda = _criar_demanda(client_admin, departamentoResponsavelIds=[str(outro.id)])
    arq = _enviar(client_admin, demanda["id"], "x.pdf")
    c_ana = _client_para(app, ana)
    assert c_ana.get(f"/demandas/{demanda['id']}", params={"escopo": "pauta"}).status_code == 200  # lê pela Pauta...
    assert c_ana.post("/arquivos/download-lote", params={"escopo": "pauta"}, json=_ids(arq)).status_code == 404  # ...mas o lote não
    assert c_ana.post("/arquivos/excluir-lote", params={"escopo": "pauta"}, json=_ids(arq)).status_code == 404


# ======================================================================================
# exclusão
# ======================================================================================


def test_excluir_ids_remove_registros_arquivos_e_gera_um_evento_por_arquivo(client_admin: TestClient, db_session: Session) -> None:
    demanda = _criar_demanda(client_admin)
    a = _enviar(client_admin, demanda["id"], "a.pdf")
    b = _enviar(client_admin, demanda["id"], "b.png")
    link = _link(client_admin, demanda["id"]).json()
    mantido = _enviar(client_admin, demanda["id"], "mantido.pdf")
    caminhos = [_caminho(a), _caminho(b)]

    resposta = client_admin.post("/arquivos/excluir-lote", json=_ids(a, b, link))
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {"excluidos": 3, "arquivosFisicosNaoRemovidos": 0}
    assert _existentes(db_session, a["id"], b["id"], link["id"]) == 0 and _existentes(db_session, mantido["id"]) == 1
    assert all(not c.exists() for c in caminhos) and _caminho(mantido).exists()

    eventos = list(db_session.scalars(select(Evento).where(Evento.entidade_id == demanda["id"], Evento.tipo == "demanda.arquivo_removido")).all())
    assert len(eventos) == 3  # um por arquivo, não um evento gigante
    assert {e.payload["arquivoId"] for e in eventos} == {a["id"], b["id"], link["id"]}
    assert all(e.payload["lote"] is True for e in eventos)


def test_excluir_all_filtered_respeita_excluidos_e_filtros(client_admin: TestClient, db_session: Session) -> None:
    demanda = _criar_demanda(client_admin)
    outra = _criar_demanda(client_admin)
    itens = [_enviar(client_admin, demanda["id"], f"x{i}.pdf") for i in range(5)]
    intocado = _enviar(client_admin, outra["id"], "outra-demanda.pdf")

    corpo = _todos({"demandaId": demanda["id"]}, excluded=[itens[1]["id"]])
    assert client_admin.post("/arquivos/excluir-lote", json=corpo).json()["excluidos"] == 4
    restantes = {r for (r,) in db_session.execute(select(DemandaArquivo.id).where(DemandaArquivo.demanda_id == demanda["id"]))}
    assert restantes == {itens[1]["id"]}
    assert _existentes(db_session, intocado["id"]) == 1


def test_excluir_pre_valida_tudo_um_nao_autorizado_nada_e_excluido(app, client_admin: TestClient, db_session: Session, outra_empresa: Empresa) -> None:
    demanda = _criar_demanda(client_admin)
    a = _enviar(client_admin, demanda["id"], "a.pdf")
    b = _enviar(client_admin, demanda["id"], "b.pdf")
    inexistente = {"id": str(uuid.uuid4())}
    resposta = client_admin.post("/arquivos/excluir-lote", json=_ids(a, inexistente, b))
    assert resposta.status_code == 404
    assert _existentes(db_session, a["id"], b["id"]) == 2 and _caminho(a).exists() and _caminho(b).exists()


def test_exclusao_e_atomica_no_banco_falha_no_meio_nao_deixa_nada_pela_metade(client_admin: TestClient, db_session: Session, monkeypatch) -> None:
    from app.services.demanda_arquivo_service import DemandaArquivoService

    demanda = _criar_demanda(client_admin)
    itens = [_enviar(client_admin, demanda["id"], f"t{i}.pdf") for i in range(3)]
    db_session.commit()
    chamadas = {"n": 0}
    original = DemandaArquivoService.publicar_evento

    def falha_no_segundo(self, *args, **kwargs):
        chamadas["n"] += 1
        if chamadas["n"] == 2:
            raise RuntimeError("falha simulada ao publicar evento")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(DemandaArquivoService, "publicar_evento", falha_no_segundo)
    with pytest.raises(RuntimeError):
        client_admin.post("/arquivos/excluir-lote", json=_ids(*itens))
    monkeypatch.setattr(DemandaArquivoService, "publicar_evento", original)  # (não usar monkeypatch.undo: desfaria o isolamento de uploads)
    assert _existentes(db_session, *[i["id"] for i in itens]) == 3  # rollback total
    assert all(_caminho(i).exists() for i in itens)  # nenhum físico foi apagado antes do commit


def test_falha_de_disco_depois_do_commit_e_contada_e_nao_desfaz_o_banco(client_admin: TestClient, db_session: Session, monkeypatch) -> None:
    demanda = _criar_demanda(client_admin)
    a = _enviar(client_admin, demanda["id"], "a.pdf")
    b = _enviar(client_admin, demanda["id"], "b.pdf")
    alvo = _caminho(a)
    original = Path.unlink

    def unlink_falha(self, *args, **kwargs):
        if self == alvo:
            raise PermissionError("disco somente leitura")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink_falha)
    resposta = client_admin.post("/arquivos/excluir-lote", json=_ids(a, b))
    monkeypatch.setattr(Path, "unlink", original)
    assert resposta.status_code == 200
    assert resposta.json() == {"excluidos": 2, "arquivosFisicosNaoRemovidos": 1}  # nada silencioso
    assert _existentes(db_session, a["id"], b["id"]) == 0  # o banco é a verdade: ambos já não existem para ninguém


def test_excluir_com_arquivo_fisico_ja_ausente_nao_e_erro(client_admin: TestClient, db_session: Session) -> None:
    demanda = _criar_demanda(client_admin)
    a = _enviar(client_admin, demanda["id"], "a.pdf")
    _caminho(a).unlink()
    resposta = client_admin.post("/arquivos/excluir-lote", json=_ids(a))
    assert resposta.status_code == 200 and resposta.json()["excluidos"] == 1
    assert _existentes(db_session, a["id"]) == 0


def test_exclusao_individual_continua_funcionando_depois_da_exclusao_em_lote(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    a = _enviar(client_admin, demanda["id"], "a.pdf")
    b = _enviar(client_admin, demanda["id"], "b.pdf")
    assert client_admin.post("/arquivos/excluir-lote", json=_ids(a)).status_code == 200
    assert client_admin.delete(f"/demandas/{demanda['id']}/arquivos/{b['id']}").status_code == 204
    assert client_admin.delete(f"/demandas/{demanda['id']}/arquivos/{a['id']}").status_code == 404


# ======================================================================================
# tetos
# ======================================================================================


def test_limites_do_zip_e_da_exclusao_413_sem_efeito(client_admin: TestClient, db_session: Session, monkeypatch, sem_sobra_de_zip) -> None:
    demanda = _criar_demanda(client_admin)
    itens = [_enviar(client_admin, demanda["id"], f"l{i}.pdf") for i in range(4)]

    monkeypatch.setattr(lote_modulo, "ZIP_MAX_FILES", 3)
    resposta = client_admin.post("/arquivos/download-lote", json=_todos({"demandaId": demanda["id"]}))
    assert resposta.status_code == 413 and resposta.json()["detail"]["code"] == "LIMITE_EXCEDIDO"
    monkeypatch.setattr(lote_modulo, "ZIP_MAX_FILES", 500)

    monkeypatch.setattr(lote_modulo, "ZIP_MAX_TOTAL_BYTES", 10)
    assert client_admin.post("/arquivos/download-lote", json=_ids(*itens)).status_code == 413
    monkeypatch.setattr(lote_modulo, "ZIP_MAX_TOTAL_BYTES", 500 * 1024 * 1024)

    monkeypatch.setattr(lote_modulo, "EXCLUSAO_MAX_FILES", 3)
    assert client_admin.post("/arquivos/excluir-lote", json=_todos({"demandaId": demanda["id"]})).status_code == 413
    assert _existentes(db_session, *[i["id"] for i in itens]) == 4  # nada excluído

    monkeypatch.setattr(lote_modulo, "EXCLUSAO_MAX_FILES", 2000)
    resumo = client_admin.post("/arquivos/resumo-lote", json=_todos({"demandaId": demanda["id"]})).json()
    assert (resumo["limiteZipArquivos"], resumo["limiteZipBytes"], resumo["limiteExclusao"]) == (500, 500 * 1024 * 1024, 2000)


# ======================================================================================
# payload inválido → 422
# ======================================================================================


def _lixo_uuid() -> str:
    return str(uuid.uuid4())


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"mode": "outro"},
        {"mode": "ids"},
        {"mode": "ids", "ids": []},
        {"mode": "ids", "ids": ["nao-e-uuid"]},
        {"mode": "ids", "ids": ["dup", "dup"]},
        {"mode": "ids", "ids": ["x"], "excludedIds": ["y"]},
        {"mode": "ids", "ids": ["x"], "filtros": {"search": "a"}},
        {"mode": "all_filtered", "ids": ["x"]},
        {"mode": "all_filtered", "filtros": {"naoExiste": "1"}},
        {"mode": "all_filtered", "filtros": {"tipo": "invalido"}},
        {"mode": "all_filtered", "filtros": {"clienteId": "nao-uuid"}},
        {"mode": "all_filtered", "filtros": {"dataInicio": "2026-01-01T00:00:00"}},  # sem fuso
        {"mode": "all_filtered", "excludedIds": ["nao-uuid"]},
        {"mode": "all_filtered", "contexto": {"projetoId": "nao-uuid"}},
        {"mode": "all_filtered", "campoExtra": 1},
    ],
)
def test_payload_invalido_422_em_todos_os_endpoints(client_admin: TestClient, corpo: dict) -> None:
    corpo = dict(corpo)
    if corpo.get("ids") == ["dup", "dup"]:
        u = _lixo_uuid()
        corpo["ids"] = [u, u]
    elif corpo.get("ids") == ["x"]:
        corpo["ids"] = [_lixo_uuid()]
    if corpo.get("excludedIds") == ["y"]:
        corpo["excludedIds"] = [_lixo_uuid()]
    for rota in ("resumo-lote", "download-lote", "excluir-lote"):
        assert client_admin.post(f"/arquivos/{rota}", json=corpo).status_code == 422, (rota, corpo)


def test_tetos_do_contrato_de_selecao(client_admin: TestClient) -> None:
    muitos = [_lixo_uuid() for _ in range(501)]
    assert client_admin.post("/arquivos/download-lote", json={"mode": "ids", "ids": muitos}).status_code == 422
    assert client_admin.post("/arquivos/download-lote", json={"mode": "ids", "ids": muitos[:500]}).status_code == 404  # no teto: passa a validação
    excecoes = [_lixo_uuid() for _ in range(1001)]
    assert client_admin.post("/arquivos/download-lote", json=_todos(excluded=excecoes)).status_code == 422


def test_sem_token_401(client: TestClient) -> None:
    for rota in ("resumo-lote", "download-lote", "excluir-lote"):
        assert client.post(f"/arquivos/{rota}", json={"mode": "all_filtered"}).status_code in (401, 403)


# ======================================================================================
# performance: sem N+1
# ======================================================================================


def test_sem_n_mais_um_na_exclusao_e_no_resumo(client_admin: TestClient, db_session: Session) -> None:
    from sqlalchemy import event

    demanda = _criar_demanda(client_admin)
    itens = [_enviar(client_admin, demanda["id"], f"q{i}.pdf") for i in range(8)]
    contagem = {"n": 0}

    def contar(conn, cursor, statement, parameters, context, executemany):
        contagem["n"] += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", contar)
    try:
        assert client_admin.post("/arquivos/resumo-lote", json=_ids(*itens)).status_code == 200
        assert contagem["n"] <= 6
        contagem["n"] = 0
        assert client_admin.post("/arquivos/download-lote", json=_ids(*itens)).status_code == 200
        assert contagem["n"] <= 8
    finally:
        event.remove(engine, "before_cursor_execute", contar)
