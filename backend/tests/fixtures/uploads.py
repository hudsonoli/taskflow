"""Isola onde os testes de arquivo de Demanda escrevem em disco.

Sem isto, cada rodada da suíte deixaria arquivo físico órfão em `uploads/demandas/**` do
repositório real: o rollback da sessão de teste desfaz a linha no banco (ver
tests/fixtures/database.py), mas não desfaz uma escrita em disco — são sistemas diferentes,
só o primeiro é transacional aqui.
"""

import pytest

import app.services.demanda_arquivo_service as demanda_arquivo_service


@pytest.fixture(autouse=True)
def uploads_isolados(tmp_path, monkeypatch):
    monkeypatch.setattr(demanda_arquivo_service, "UPLOADS_ROOT", tmp_path / "uploads")
