"""Arquivos de Demanda (Fase 2E.3) — metadado em `demanda_arquivos`, conteúdo em disco.

Substitui a antiga suíte de `uploads.py`. Cobre a consistência conteúdo⇄metadado (upload
escreve disco antes do banco; falha no banco limpa o disco), a eliminação de path traversal
por construção (nome físico nunca vem do cliente) e o download por endpoint autenticado —
ver docs/pendencias-arquiteturais.md item 9 e app/services/demanda_arquivo_service.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import demanda_arquivos as rotas
import app.services.demanda_arquivo_service as servico
from app.models.demanda import Demanda
from app.models.demanda_arquivo import DemandaArquivo
from app.models.empresa import Empresa
from app.models.usuario import Usuario

# Assinaturas reais — mesmas usadas pelo service (Fase S1-B). Corpo depois da assinatura é
# arbitrário, só a checagem de prefixo importa para `_validar_assinatura`.
PNG_VALIDO = b"\x89PNG\r\n\x1a\n" + b"conteudo-png-de-teste-apos-assinatura"
JPEG_VALIDO = b"\xff\xd8\xff" + b"conteudo-jpeg-de-teste-apos-assinatura"
PDF_VALIDO = b"%PDF-1.4\nconteudo-pdf-de-teste"
HTML_MALICIOSO = b"<html><body><script>document.title='ataque';</script></body></html>"


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _upload(client: TestClient, demanda_id: str, *, nome: str = "briefing.pdf", conteudo: bytes = b"%PDF-1.4 conteudo de teste", content_type: str = "application/pdf"):
    return client.post(
        f"/demandas/{demanda_id}/arquivos",
        files={"file": (nome, conteudo, content_type)},
    )


def _pasta_fisica(demanda_id: str) -> Path:
    # `servico.UPLOADS_ROOT` é lido em tempo de chamada — reflete o valor isolado por
    # `uploads_isolados` (tests/fixtures/uploads.py), nunca a pasta real do repositório.
    return servico.UPLOADS_ROOT / "demandas" / demanda_id


def _inserir_registro_historico(
    db_session: Session, demanda_id: str, *, nome_fisico: str, nome_original: str, content_type: str, conteudo_fisico: bytes
) -> str:
    """Simula um registro pré-existente à Fase S1-B, inserido direto (sem passar pelo
    endpoint de upload, que já bloquearia o mismatch) — o cenário real é um `content_type`
    gravado ANTES desta fase, quando ainda vinha do header do cliente sem validação."""
    arquivo_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)
    db_session.add(
        DemandaArquivo(
            id=arquivo_id,
            demanda_id=demanda_id,
            nome_original=nome_original,
            nome_fisico=nome_fisico,
            content_type=content_type,
            tamanho_bytes=len(conteudo_fisico),
            enviado_por_usuario_id=None,
            created_at=agora,
        )
    )
    db_session.flush()
    pasta = _pasta_fisica(demanda_id)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome_fisico).write_bytes(conteudo_fisico)
    return arquivo_id


# --------------------------------------------------------------------------------------
# Upload, metadado e listagem
# --------------------------------------------------------------------------------------

def test_upload_valido_persiste_metadado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"])

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["nomeOriginal"] == "briefing.pdf"
    assert corpo["demandaId"] == demanda["id"]
    assert corpo["tamanhoBytes"] == len(b"%PDF-1.4 conteudo de teste")
    assert corpo["contentType"] == "application/pdf"
    assert corpo["enviadoPorUsuarioId"] is not None
    # Sem `url` no payload — download é só pelo endpoint autenticado (ver docstring do schema).
    assert "url" not in corpo


def test_arquivo_fisico_gravado_com_nome_derivado_do_id(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    corpo = _upload(client_admin, demanda["id"]).json()

    pasta = _pasta_fisica(demanda["id"])
    arquivos_em_disco = list(pasta.iterdir())
    assert len(arquivos_em_disco) == 1
    # Nome físico é `{id}{extensao}` — nunca o nome original enviado pelo cliente.
    assert arquivos_em_disco[0].name == f"{corpo['id']}.pdf"


def test_listar_arquivos(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _upload(client_admin, demanda["id"], nome="a.pdf")
    _upload(client_admin, demanda["id"], nome="b.png", conteudo=PNG_VALIDO, content_type="image/png")

    resposta = client_admin.get(f"/demandas/{demanda['id']}/arquivos")
    assert resposta.status_code == 200
    nomes = {item["nomeOriginal"] for item in resposta.json()}
    assert nomes == {"a.pdf", "b.png"}


def test_demanda_recem_criada_tem_arquivos_vazio(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    assert client_admin.get(f"/demandas/{demanda['id']}/arquivos").json() == []


def test_extensao_nao_permitida_e_recusada(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"], nome="script.exe", content_type="application/octet-stream")
    assert resposta.status_code == 422, resposta.text
    assert list(_pasta_fisica(demanda["id"]).glob("*")) == [] if _pasta_fisica(demanda["id"]).exists() else True


def test_arquivo_vazio_e_recusado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"], conteudo=b"")
    assert resposta.status_code == 422, resposta.text


def test_arquivo_maior_que_limite_e_recusado(client_admin: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Baixa o teto pra não precisar gerar 20 MB de payload no teste.
    monkeypatch.setattr(servico, "MAX_TAMANHO_BYTES", 10)

    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"], conteudo=b"x" * 100)
    assert resposta.status_code == 422, resposta.text


def test_nome_de_arquivo_malicioso_nao_escapa_da_pasta_da_demanda(client_admin: TestClient) -> None:
    """`nome_original` guarda só o basename (`Path(...).name`), e nunca influencia o caminho
    físico — o nome em disco é sempre `{id}{extensao}` (ver DemandaArquivoService.upload)."""
    demanda = _criar_demanda(client_admin)
    resposta = _upload(client_admin, demanda["id"], nome="../../../evil.pdf")
    assert resposta.status_code == 201, resposta.text

    corpo = resposta.json()
    assert corpo["nomeOriginal"] == "evil.pdf"
    assert "/" not in corpo["nomeOriginal"] and ".." not in corpo["nomeOriginal"]

    # Nada escapou de uploads/demandas/{id}/ — a pasta contém exatamente um arquivo, o
    # esperado, e não há arquivo novo em nenhum ancestral.
    pasta = _pasta_fisica(demanda["id"])
    assert len(list(pasta.iterdir())) == 1
    assert not (servico.UPLOADS_ROOT / "evil.pdf").exists()
    assert not (servico.UPLOADS_ROOT / "demandas" / "evil.pdf").exists()


# --------------------------------------------------------------------------------------
# Conteúdo real (assinatura de bytes) — Fase S1-B
# --------------------------------------------------------------------------------------

def test_conteudo_html_com_extensao_png_e_content_type_mentiroso_e_recusado(client_admin: TestClient) -> None:
    """Regressão do ataque reproduzido no diagnóstico S1: extensão permitida + Content-Type
    do cliente mentindo sobre o tipo + bytes reais de HTML. Antes desta fase: 201, servido
    de volta como `text/html; inline` (execução de conteúdo ativo). Depois: 422, nada
    persiste — nem linha de metadado, nem arquivo físico."""
    demanda = _criar_demanda(client_admin)

    resposta = _upload(
        client_admin, demanda["id"], nome="teste.png", conteudo=HTML_MALICIOSO, content_type="text/html"
    )

    assert resposta.status_code == 422, resposta.text
    assert client_admin.get(f"/demandas/{demanda['id']}/arquivos").json() == []
    pasta = _pasta_fisica(demanda["id"])
    assert not pasta.exists() or list(pasta.iterdir()) == []


def test_content_type_mentiroso_mas_bytes_reais_validos_e_aceito(client_admin: TestClient) -> None:
    """Prova a direção oposta do teste acima: o backend passa a confiar SÓ nos bytes, nunca
    no header do cliente — um Content-Type errado não impede um upload genuinamente válido."""
    demanda = _criar_demanda(client_admin)

    resposta = _upload(
        client_admin, demanda["id"], nome="foto.jpg", conteudo=JPEG_VALIDO, content_type="text/html"
    )

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["contentType"] == "image/jpeg"

    download = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{corpo['id']}/download")
    assert download.status_code == 200
    assert download.headers["content-type"] == "image/jpeg"
    assert download.headers["content-disposition"].startswith("inline")


def test_upload_png_valido_e_aceito_e_fica_inline(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    corpo = _upload(client_admin, demanda["id"], nome="foto.png", conteudo=PNG_VALIDO, content_type="image/png").json()
    assert corpo["contentType"] == "image/png"

    download = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{corpo['id']}/download")
    assert download.headers["content-type"] == "image/png"
    assert download.headers["content-disposition"].startswith("inline")


def test_upload_jpeg_valido_extensao_jpg_e_jpeg_ambas_aceitas_e_ficam_inline(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    for nome in ("foto.jpg", "foto.jpeg"):
        corpo = _upload(client_admin, demanda["id"], nome=nome, conteudo=JPEG_VALIDO, content_type="image/jpeg").json()
        assert corpo["contentType"] == "image/jpeg"

        download = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{corpo['id']}/download")
        assert download.headers["content-type"] == "image/jpeg"
        assert download.headers["content-disposition"].startswith("inline")


def test_upload_pdf_valido_e_aceito_mas_download_e_attachment(client_admin: TestClient) -> None:
    """PDF é formato ativo — nunca inline, mesmo sendo um PDF genuíno (Política S1-B)."""
    demanda = _criar_demanda(client_admin)
    corpo = _upload(client_admin, demanda["id"], nome="briefing.pdf", conteudo=PDF_VALIDO, content_type="application/pdf").json()
    assert corpo["contentType"] == "application/pdf"

    download = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{corpo['id']}/download")
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith("attachment")


def test_extensoes_perigosas_continuam_recusadas(client_admin: TestClient) -> None:
    """`.exe` já é coberto por `test_extensao_nao_permitida_e_recusada` — aqui só os tipos
    especificamente citados no diagnóstico S1 como candidatos a conteúdo ativo."""
    demanda = _criar_demanda(client_admin)
    for nome in ("arquivo.svg", "arquivo.html", "arquivo.xml"):
        resposta = _upload(client_admin, demanda["id"], nome=nome, conteudo=HTML_MALICIOSO, content_type="text/html")
        assert resposta.status_code == 422, f"{nome}: {resposta.text}"


# --------------------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------------------

def test_download_devolve_conteudo_original(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    conteudo = b"%PDF-1.4 conteudo especifico deste teste"
    corpo = _upload(client_admin, demanda["id"], conteudo=conteudo).json()

    resposta = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{corpo['id']}/download")
    assert resposta.status_code == 200
    assert resposta.content == conteudo
    assert resposta.headers["content-type"] == "application/pdf"
    assert "briefing.pdf" in resposta.headers.get("content-disposition", "")


def test_download_de_arquivo_inexistente_devolve_404(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{uuid.uuid4()}/download")
    assert resposta.status_code == 404


def test_download_sem_autenticacao_e_recusado(client: TestClient, client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    corpo = _upload(client_admin, demanda["id"]).json()

    resposta = client.get(f"/demandas/{demanda['id']}/arquivos/{corpo['id']}/download")
    assert resposta.status_code == 401


def test_download_de_registro_historico_neutraliza_content_type_malicioso(
    client_admin: TestClient, db_session: Session
) -> None:
    """Fase S1-B protege também registros gravados ANTES desta fase, sem migration: um
    `content_type` legado vindo do cliente (aqui, `text/html`, simulando exatamente o
    cenário reproduzido no diagnóstico) nunca é usado no download — só a extensão física,
    já validada no momento do upload original."""
    demanda = _criar_demanda(client_admin)
    arquivo_id = _inserir_registro_historico(
        db_session,
        demanda["id"],
        nome_fisico=f"{uuid.uuid4()}.png",
        nome_original="historico.png",
        content_type="text/html",
        conteudo_fisico=HTML_MALICIOSO,
    )

    resposta = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{arquivo_id}/download")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "image/png"
    assert resposta.headers["content-disposition"].startswith("inline")
    assert "text/html" not in resposta.headers["content-type"]


def test_download_de_extensao_legada_desconhecida_cai_em_octet_stream_attachment(
    client_admin: TestClient, db_session: Session
) -> None:
    """Defesa em profundidade: uma extensão fora do mapa atual (não deveria existir, dado
    que o upload sempre valida contra `ALLOWED_EXTENSIONS`) nunca vira inline com tipo
    arbitrário — cai no fallback seguro."""
    demanda = _criar_demanda(client_admin)
    arquivo_id = _inserir_registro_historico(
        db_session,
        demanda["id"],
        nome_fisico=f"{uuid.uuid4()}.txt",
        nome_original="legado.txt",
        content_type="text/plain",
        conteudo_fisico=b"conteudo legado qualquer",
    )

    resposta = client_admin.get(f"/demandas/{demanda['id']}/arquivos/{arquivo_id}/download")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/octet-stream"
    assert resposta.headers["content-disposition"].startswith("attachment")


# --------------------------------------------------------------------------------------
# Exclusão
# --------------------------------------------------------------------------------------

def test_excluir_remove_metadado_e_arquivo_fisico(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    corpo = _upload(client_admin, demanda["id"]).json()
    caminho = _pasta_fisica(demanda["id"]) / f"{corpo['id']}.pdf"
    assert caminho.is_file()

    resposta = client_admin.delete(f"/demandas/{demanda['id']}/arquivos/{corpo['id']}")
    assert resposta.status_code == 204
    assert not caminho.exists()
    assert client_admin.get(f"/demandas/{demanda['id']}/arquivos").json() == []


def test_excluir_com_arquivo_fisico_ja_ausente_nao_falha(client_admin: TestClient) -> None:
    """Se o conteúdo físico já sumiu por qualquer motivo externo, a exclusão do metadado
    segue normalmente — o metadado é a fonte da verdade (ver docstring do service)."""
    demanda = _criar_demanda(client_admin)
    corpo = _upload(client_admin, demanda["id"]).json()
    caminho = _pasta_fisica(demanda["id"]) / f"{corpo['id']}.pdf"
    caminho.unlink()  # simula desaparecimento externo do arquivo físico

    resposta = client_admin.delete(f"/demandas/{demanda['id']}/arquivos/{corpo['id']}")
    assert resposta.status_code == 204
    assert client_admin.get(f"/demandas/{demanda['id']}/arquivos").json() == []


def test_excluir_metadado_inexistente_devolve_404(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.delete(f"/demandas/{demanda['id']}/arquivos/{uuid.uuid4()}")
    assert resposta.status_code == 404


# --------------------------------------------------------------------------------------
# Consistência upload ⇄ falha de armazenamento
# --------------------------------------------------------------------------------------

def test_falha_no_banco_apos_escrever_arquivo_limpa_o_fisico(
    client_admin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Grava em disco primeiro; se o INSERT falhar depois, o arquivo recém-escrito é
    removido — nunca fica órfão em disco (ver instrução da fase, item 5)."""
    demanda = _criar_demanda(client_admin)

    def _falha(db, arquivo):
        raise RuntimeError("falha simulada de persistência")

    monkeypatch.setattr(rotas.arquivo_service.repository, "create", _falha)

    with pytest.raises(RuntimeError):
        _upload(client_admin, demanda["id"])

    pasta = _pasta_fisica(demanda["id"])
    assert not pasta.exists() or list(pasta.iterdir()) == []
    # Nenhum registro pendurado — o service nunca chega a commitar.
    monkeypatch.undo()
    assert client_admin.get(f"/demandas/{demanda['id']}/arquivos").json() == []


# --------------------------------------------------------------------------------------
# Escopo e isolamento
# --------------------------------------------------------------------------------------

def test_demanda_inexistente_devolve_404(client_admin: TestClient) -> None:
    assert client_admin.get(f"/demandas/{uuid.uuid4()}/arquivos").status_code == 404


def test_operador_sem_escopo_recebe_404(client_admin: TestClient, client_operador: TestClient) -> None:
    alheia = _criar_demanda(client_admin)
    assert client_operador.get(f"/demandas/{alheia['id']}/arquivos").status_code == 404


def test_operador_com_escopo_faz_upload_e_download(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar_demanda(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    corpo = _upload(client_operador, minha["id"]).json()

    resposta = client_operador.get(f"/demandas/{minha['id']}/arquivos/{corpo['id']}/download")
    assert resposta.status_code == 200


def test_demanda_de_outra_empresa_devolve_404(client_admin: TestClient, db_session: Session) -> None:
    agora = datetime.now(timezone.utc)
    outra = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa Arquivos",
        documento=None,
        codigo_interno=f"ARQ-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(outra)
    db_session.flush()

    intrusa = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        codigo_referencia="T26007777",
        ano_referencia=26,
        sequencial_referencia=7777,
        numero_operacional=7777,
        nome="Demanda de outra empresa",
        status="rascunho",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(intrusa)
    db_session.flush()

    assert client_admin.get(f"/demandas/{intrusa.id}/arquivos").status_code == 404
