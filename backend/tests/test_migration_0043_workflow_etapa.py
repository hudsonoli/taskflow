"""Migration 0043 (progressão do snapshot de Workflow — Fase 8A): upgrade a partir do estado de produção (`e4a7c1d93b60`), backfill
mínimo (sem inventar histórico), unicidade de (demanda, ordem), check de conclusão, FK `SET NULL` e downgrade, contra um banco SCRATCH
descartável (mesmo padrão de test_migration_0042_numeracao.py: nunca toca o banco de desenvolvimento nem o `taskfloww_test`)."""

from __future__ import annotations

import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch

REV_ANTERIOR = "e4a7c1d93b60"
REV_0043 = "b7d3f19c2a58"
PREFIXO_SCRATCH = "taskfloww_scratch_0043_"
COLUNAS_NOVAS = {"iniciada_em", "concluida_em", "concluida_por_usuario_id"}


@pytest.fixture()
def banco_scratch():
    url_teste = obter_url_teste_validada()
    nome = f"{PREFIXO_SCRATCH}{uuid.uuid4().hex[:8]}"
    assert nome.startswith(PREFIXO_SCRATCH)
    url = urlunsplit(urlsplit(url_teste)._replace(path=f"/{nome}"))
    with _conexao_manutencao(url_teste) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield _BancoScratch(nome, url)
    finally:
        with _conexao_manutencao(url_teste) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _semear_base(conexao, *, demandas: int = 2) -> None:
    conexao.execute(
        "INSERT INTO empresas (id, nome, codigo_interno, slug, status, created_at, updated_at) "
        "VALUES ('emp-a', 'Empresa A', 'EMPA', 'empa', 'ativa', now(), now())"
    )
    conexao.execute(
        "INSERT INTO usuarios (id, empresa_id, codigo_interno, nome, email, perfil_base, status, created_at, updated_at) "
        "VALUES ('u-1', 'emp-a', 'u1', 'Pessoa', 'p@teste.local', 'operador', 'ativo', now(), now())"
    )
    for n in range(1, demandas + 1):
        conexao.execute(
            "INSERT INTO demandas (id, empresa_id, codigo_referencia, ano_referencia, sequencial_referencia, numero_operacional, "
            "identificador, nome, status, prioridade, sinalizada, created_at, updated_at) "
            "VALUES (%s, 'emp-a', %s, 26, %s, %s, %s, %s, 'planejada', 'media', false, now(), now())",
            (f"d-{n}", f"T26{n:06d}", n, n, f"#{n}", f"Tarefa {n}"),
        )


def _etapa(conexao, etapa_id: str, demanda_id: str, ordem: int, status: str = "pendente") -> None:
    conexao.execute(
        "INSERT INTO demanda_workflow_etapas (id, demanda_id, ordem, nome, tipo, quantidade_antes_deadline, unidade_prazo, status, "
        "created_at, updated_at) VALUES (%s, %s, %s, %s, 'execucao', 1, 'dias_corridos', %s, now() - interval '2 days', "
        "now() - interval '1 day')",
        (etapa_id, demanda_id, ordem, f"Etapa {ordem}", status),
    )


def test_upgrade_nao_inventa_historico_e_backfill_da_concluida(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _etapa(conexao, "e-1", "d-1", 1)
        _etapa(conexao, "e-2", "d-1", 2)
        _etapa(conexao, "e-3", "d-2", 1, status="em_execucao")
        _etapa(conexao, "e-4", "d-2", 2, status="concluida")  # excepcional: nenhuma ação a concluía antes

    resultado = banco_scratch.alembic("upgrade", REV_0043)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_0043 in banco_scratch.revisao_atual()
    assert COLUNAS_NOVAS <= banco_scratch.colunas("demanda_workflow_etapas")

    with banco_scratch.conectar() as conexao:
        linhas = {
            r[0]: r[1:]
            for r in conexao.execute(
                "SELECT id, status, iniciada_em, concluida_em, concluida_por_usuario_id, updated_at FROM demanda_workflow_etapas"
            )
        }
        # etapas não concluídas: tudo NULL — inclusive a etapa atual histórica (início desconhecido, nunca fictício)
        for etapa_id in ("e-1", "e-2", "e-3"):
            _status, iniciada, concluida, por, _upd = linhas[etapa_id]
            assert (iniciada, concluida, por) == (None, None, None), etapa_id
        # concluída histórica: concluida_em = updated_at e ator desconhecido
        status, iniciada, concluida, por, atualizado = linhas["e-4"]
        assert status == "concluida" and iniciada is None and por is None
        assert concluida == atualizado
        # status e ordem intactos
        assert {i: l[0] for i, l in linhas.items()} == {"e-1": "pendente", "e-2": "pendente", "e-3": "em_execucao", "e-4": "concluida"}


def test_ordem_duplicada_nao_e_aceita_depois_da_migration(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _etapa(conexao, "e-1", "d-1", 1)
    assert banco_scratch.alembic("upgrade", REV_0043).returncode == 0
    with banco_scratch.conectar() as conexao:
        with pytest.raises(psycopg.errors.UniqueViolation):
            _etapa(conexao, "e-dup", "d-1", 1)
        _etapa(conexao, "e-outra-demanda", "d-2", 1)  # mesma ordem em OUTRA demanda é normal
        _etapa(conexao, "e-2", "d-1", 2)


def test_check_concluida_exige_concluida_em(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_0043).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _etapa(conexao, "e-1", "d-1", 1)
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE demanda_workflow_etapas SET status = 'concluida' WHERE id = 'e-1'")
        conexao.execute("UPDATE demanda_workflow_etapas SET status = 'concluida', concluida_em = now() WHERE id = 'e-1'")
        # concluida_por_usuario_id continua opcional (backfill / usuário removido)
        assert conexao.execute("SELECT concluida_por_usuario_id FROM demanda_workflow_etapas WHERE id = 'e-1'").fetchone() == (None,)


def test_fk_concluida_por_set_null_ao_remover_usuario(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_0043).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _etapa(conexao, "e-1", "d-1", 1)
        conexao.execute(
            "UPDATE demanda_workflow_etapas SET status = 'concluida', concluida_em = now(), concluida_por_usuario_id = 'u-1' WHERE id = 'e-1'"
        )
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conexao.execute("UPDATE demanda_workflow_etapas SET concluida_por_usuario_id = 'inexistente' WHERE id = 'e-1'")
        conexao.execute("DELETE FROM usuarios WHERE id = 'u-1'")
        assert conexao.execute("SELECT status, concluida_por_usuario_id FROM demanda_workflow_etapas WHERE id = 'e-1'").fetchone() == (
            "concluida",
            None,
        )


def test_duplicata_pre_existente_faz_a_migration_falhar_sem_alterar_dados(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _etapa(conexao, "e-1", "d-1", 1)
        _etapa(conexao, "e-2", "d-1", 1)  # índice antigo não era único
    resultado = banco_scratch.alembic("upgrade", REV_0043)
    assert resultado.returncode != 0
    assert "ordem duplicada" in (resultado.stderr + resultado.stdout)
    assert REV_ANTERIOR in banco_scratch.revisao_atual() and REV_0043 not in banco_scratch.revisao_atual()
    assert not (COLUNAS_NOVAS & banco_scratch.colunas("demanda_workflow_etapas"))
    with banco_scratch.conectar() as conexao:  # nada foi corrigido/reordenado
        assert sorted(conexao.execute("SELECT id, ordem FROM demanda_workflow_etapas")) == [("e-1", 1), ("e-2", 1)]


def test_downgrade_restaura_o_schema_anterior_e_preserva_status(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _etapa(conexao, "e-1", "d-1", 1)
        _etapa(conexao, "e-2", "d-1", 2)
    assert banco_scratch.alembic("upgrade", REV_0043).returncode == 0
    with banco_scratch.conectar() as conexao:
        conexao.execute("UPDATE demanda_workflow_etapas SET status = 'concluida', concluida_em = now(), concluida_por_usuario_id = 'u-1' WHERE id = 'e-1'")

    resultado = banco_scratch.alembic("downgrade", REV_ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_ANTERIOR in banco_scratch.revisao_atual() and REV_0043 not in banco_scratch.revisao_atual()
    assert not (COLUNAS_NOVAS & banco_scratch.colunas("demanda_workflow_etapas"))
    with banco_scratch.conectar() as conexao:
        assert dict(conexao.execute("SELECT id, status FROM demanda_workflow_etapas")) == {"e-1": "concluida", "e-2": "pendente"}
        indices = {n for (n,) in conexao.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'demanda_workflow_etapas'")}
        assert "ix_demanda_workflow_etapas_demanda_ordem" in indices  # índice não-único original restaurado
        assert "uq_demanda_workflow_etapas_demanda_ordem" not in indices
        _etapa(conexao, "e-dup", "d-1", 1)  # volta a aceitar (comportamento anterior)

    # e sobe de novo? com duplicata criada agora, a migration recusa (comportamento esperado e seguro)
    assert banco_scratch.alembic("upgrade", REV_0043).returncode != 0
