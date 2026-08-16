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
from app.models.empresa import Empresa
from app.models.usuario import Usuario


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
    _upload(client_admin, demanda["id"], nome="b.png", conteudo=b"fake-png-bytes", content_type="image/png")

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
