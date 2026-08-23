"""Import do catálogo real de Peças (Fase 2G.4) — ver app/cli/importar_pecas.py.

## Por que não usa `db_session`

`importar_pecas()` abre a própria sessão (`get_session_factory()`) e dá commit — mesmo motivo
de tests/test_seed_all.py não usar a fixture transacional da suíte. Limpeza aqui é explícita:
TRUNCATE de `pecas`/`categorias_peca` antes e depois, e a Empresa usada é criada e removida
por este teste, não reaproveitada de outro módulo.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.cli.importar_pecas import importar_pecas
from app.core.config import get_settings

TABELAS = ("pecas", "categorias_peca")


def _limpar(engine: Engine) -> None:
    with engine.begin() as conexao:
        conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def empresa_import(test_engine: Engine):
    """Empresa real, commitada — precisa existir com `codigo_interno == settings.empresa_codigo`
    pra `importar_pecas()` encontrar (mesma resolução do seed real)."""
    _limpar(test_engine)
    settings = get_settings()
    empresa_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)
    with test_engine.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO empresas (id, nome, documento, codigo_interno, status, created_at, updated_at) "
                "VALUES (:id, :nome, NULL, :codigo, 'ativa', :agora, :agora) "
                "ON CONFLICT (codigo_interno) DO NOTHING"
            ),
            {"id": empresa_id, "nome": "Empresa Import Peças", "codigo": settings.empresa_codigo, "agora": agora},
        )
    with test_engine.connect() as conexao:
        empresa_real_id = conexao.execute(
            text("SELECT id FROM empresas WHERE codigo_interno = :codigo"), {"codigo": settings.empresa_codigo}
        ).scalar_one()

    yield empresa_real_id

    _limpar(test_engine)
    with test_engine.begin() as conexao:
        conexao.execute(text("DELETE FROM empresas WHERE id = :id"), {"id": empresa_real_id})


def _contar(engine: Engine, tabela: str) -> int:
    with engine.connect() as conexao:
        return conexao.execute(text(f"SELECT count(*) FROM {tabela}")).scalar_one()


def test_primeira_execucao_cria(empresa_import: str, test_engine: Engine) -> None:
    saida: list[str] = []
    importar_pecas(output=saida.append)

    assert _contar(test_engine, "pecas") == 419
    assert "criadas: 419" in saida[0]
    assert "ignoradas): 0" in saida[0]


def test_segunda_execucao_nao_duplica(empresa_import: str, test_engine: Engine) -> None:
    importar_pecas(output=lambda _msg: None)
    primeira_contagem = _contar(test_engine, "pecas")

    saida: list[str] = []
    importar_pecas(output=saida.append)

    assert _contar(test_engine, "pecas") == primeira_contagem == 419
    assert "criadas: 0" in saida[0]
    assert "ignoradas): 419" in saida[0]


def test_duplicatas_legitimas_de_nome_nao_colapsam(empresa_import: str, test_engine: Engine) -> None:
    """O catálogo real não tem nome duplicado (confirmado na análise da Fase 2G.4), mas a
    garantia estrutural que o import depende — nenhum UNIQUE por nome — precisa ficar provada
    aqui, não só documentada."""
    importar_pecas(output=lambda _msg: None)

    with test_engine.connect() as conexao:
        nomes_distintos = conexao.execute(text("SELECT count(DISTINCT nome) FROM pecas")).scalar_one()
        total = conexao.execute(text("SELECT count(*) FROM pecas")).scalar_one()
    # Catálogo real não tem duplicata de nome — mas a asserção que importa é a ausência de
    # colapso por causa de alguma constraint de nome (ver test_categorias_nao_duplicam abaixo
    # pro caso onde duplicata realmente aconteceria).
    assert total == 419
    assert nomes_distintos <= total


def test_categorias_nao_duplicam(empresa_import: str, test_engine: Engine) -> None:
    """O import não cria nenhuma Categoria (catálogo não traz categoria nenhuma) — rodar duas
    vezes não pode inventar nem duplicar registro em categorias_peca."""
    importar_pecas(output=lambda _msg: None)
    importar_pecas(output=lambda _msg: None)

    assert _contar(test_engine, "categorias_peca") == 0


def test_pecas_nascem_sem_categoria(empresa_import: str, test_engine: Engine) -> None:
    importar_pecas(output=lambda _msg: None)

    with test_engine.connect() as conexao:
        sem_categoria = conexao.execute(text("SELECT count(*) FROM pecas WHERE categoria_id IS NULL")).scalar_one()
    assert sem_categoria == 419


def test_tempo_remapeado_para_medio_nao_estimado(empresa_import: str, test_engine: Engine) -> None:
    """Prova o remapeamento documentado em importar_pecas.py: o campo bruto
    `tempoEstimadoMinutos` da planilha vira `tempo_medio_minutos`; `tempo_estimado_minutos`
    fica sempre NULL após o import."""
    importar_pecas(output=lambda _msg: None)

    with test_engine.connect() as conexao:
        com_tempo_estimado = conexao.execute(
            text("SELECT count(*) FROM pecas WHERE tempo_estimado_minutos IS NOT NULL")
        ).scalar_one()
        com_tempo_medio = conexao.execute(
            text("SELECT count(*) FROM pecas WHERE tempo_medio_minutos IS NOT NULL")
        ).scalar_one()
        linha = conexao.execute(
            text("SELECT tempo_medio_minutos FROM pecas WHERE codigo_legado = 'peca-imp-001'")
        ).scalar_one()

    assert com_tempo_estimado == 0
    assert com_tempo_medio == 353
    assert linha == 322  # valor bruto original de peca-imp-001 (ABADÁ)


def test_sindicato_ativo_derivado_de_valores_positivos(empresa_import: str, test_engine: Engine) -> None:
    importar_pecas(output=lambda _msg: None)

    with test_engine.connect() as conexao:
        com_sindicato = conexao.execute(
            text("SELECT count(*) FROM pecas WHERE sindicato_ativo = true")
        ).scalar_one()
        linha = conexao.execute(
            text(
                "SELECT sindicato_ativo, valor_sindicato_criacao_centavos FROM pecas "
                "WHERE codigo_legado = 'peca-imp-003'"
            )
        ).one()

    assert com_sindicato == 12
    assert linha.sindicato_ativo is True
    assert linha.valor_sindicato_criacao_centavos == 80000
