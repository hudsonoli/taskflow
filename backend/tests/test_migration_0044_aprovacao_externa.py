"""Migration 0044 (Portal Externo de Aprovação — Fase 9B): upgrade a partir do estado de produção (`b7d3f19c2a58`), sem backfill nem
alteração de tabelas existentes, constraints (token único, decisão × revogação, índice único parcial por etapa), PK do artefato, FKs
`SET NULL`/`CASCADE` e downgrade, contra um banco SCRATCH descartável (mesmo padrão de test_migration_0043_workflow_etapa.py)."""

from __future__ import annotations

import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from tests.fixtures.database import _conexao_manutencao, obter_url_teste_validada
from tests.test_migration_0041_plataforma import _BancoScratch

REV_ANTERIOR = "b7d3f19c2a58"
REV_0044 = "c8e2a47d1f93"
PREFIXO_SCRATCH = "taskfloww_scratch_0044_"
HASH_A = "a" * 64
HASH_B = "b" * 64
SHA = "c" * 64


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


def _semear_base(conexao) -> None:
    conexao.execute(
        "INSERT INTO empresas (id, nome, codigo_interno, slug, status, created_at, updated_at) "
        "VALUES ('emp-a', 'Empresa A', 'EMPA', 'empa', 'ativa', now(), now())"
    )
    conexao.execute(
        "INSERT INTO usuarios (id, empresa_id, codigo_interno, nome, email, perfil_base, status, created_at, updated_at) "
        "VALUES ('u-1', 'emp-a', 'u1', 'Pessoa', 'p@teste.local', 'operador', 'ativo', now(), now())"
    )
    conexao.execute(
        "INSERT INTO demandas (id, empresa_id, codigo_referencia, ano_referencia, sequencial_referencia, numero_operacional, "
        "identificador, nome, status, prioridade, sinalizada, created_at, updated_at) "
        "VALUES ('d-1', 'emp-a', 'T26000001', 26, 1, 1, '#1', 'Tarefa 1', 'planejada', 'media', false, now(), now())"
    )
    for n in (1, 2):
        conexao.execute(
            "INSERT INTO demanda_workflow_etapas (id, demanda_id, ordem, nome, tipo, quantidade_antes_deadline, unidade_prazo, status, "
            "created_at, updated_at) VALUES (%s, 'd-1', %s, %s, 'aprovacao', 1, 'dias_corridos', 'pendente', now(), now())",
            (f"e-{n}", n, f"Etapa {n}"),
        )
    for n in (1, 2, 3):
        conexao.execute(
            "INSERT INTO demanda_arquivos (id, demanda_id, nome_original, nome_fisico, content_type, tamanho_bytes, tipo, created_at) "
            "VALUES (%s, 'd-1', %s, %s, 'image/png', 10, 'layout', now())",
            (f"a-{n}", f"arte{n}.png", f"a-{n}.png"),
        )


def _aprovacao(conexao, aprovacao_id: str = "ap-1", etapa: str = "e-1", token_hash: str = HASH_A) -> None:
    conexao.execute(
        "INSERT INTO aprovacoes_externas (id, empresa_id, demanda_id, workflow_etapa_id, token_hash, criada_em, expira_em, "
        "criada_por_usuario_id) VALUES (%s, 'emp-a', 'd-1', %s, %s, now(), now() + interval '7 days', 'u-1')",
        (aprovacao_id, etapa, token_hash),
    )


def _subir(banco: _BancoScratch) -> None:
    resultado = banco.alembic("upgrade", REV_0044)
    assert resultado.returncode == 0, resultado.stderr


def test_upgrade_cria_tabelas_sem_alterar_dados_existentes(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    colunas_antes = {t: banco_scratch.colunas(t) for t in ("demandas", "demanda_workflow_etapas", "demanda_arquivos")}
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)

    _subir(banco_scratch)
    assert REV_0044 in banco_scratch.revisao_atual()
    assert banco_scratch.existe_tabela("aprovacoes_externas") and banco_scratch.existe_tabela("aprovacao_externa_arquivos")
    assert {t: banco_scratch.colunas(t) for t in colunas_antes} == colunas_antes  # nenhuma coluna alterada
    with banco_scratch.conectar() as conexao:
        assert conexao.execute("SELECT count(*) FROM aprovacoes_externas").fetchone() == (0,)  # sem backfill
        assert conexao.execute("SELECT count(*) FROM aprovacao_externa_arquivos").fetchone() == (0,)
        assert conexao.execute("SELECT count(*) FROM demanda_arquivos").fetchone() == (3,)
        assert conexao.execute("SELECT count(*) FROM demanda_workflow_etapas").fetchone() == (2,)


def test_token_hash_unico_e_obrigatorio(banco_scratch: _BancoScratch) -> None:
    _subir(banco_scratch)
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _aprovacao(conexao, "ap-1", "e-1", HASH_A)
        with pytest.raises(psycopg.errors.UniqueViolation):
            _aprovacao(conexao, "ap-2", "e-2", HASH_A)  # mesmo hash em outra etapa
        _aprovacao(conexao, "ap-2", "e-2", HASH_B)
        with pytest.raises(psycopg.errors.NotNullViolation):
            conexao.execute(
                "INSERT INTO aprovacoes_externas (id, empresa_id, demanda_id, workflow_etapa_id, criada_em, expira_em) "
                "VALUES ('ap-x', 'emp-a', 'd-1', 'e-1', now(), now() + interval '1 day')"
            )


def test_indice_unico_parcial_uma_aberta_por_etapa(banco_scratch: _BancoScratch) -> None:
    _subir(banco_scratch)
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _aprovacao(conexao, "ap-1", "e-1", HASH_A)
        with pytest.raises(psycopg.errors.UniqueViolation):
            _aprovacao(conexao, "ap-2", "e-1", HASH_B)  # segunda aberta na mesma etapa

        # expirada (expira_em no passado) continua ocupando o índice: a expiração é derivada
        conexao.execute("UPDATE aprovacoes_externas SET criada_em = now() - interval '10 days', expira_em = now() - interval '3 days'")
        with pytest.raises(psycopg.errors.UniqueViolation):
            _aprovacao(conexao, "ap-2", "e-1", HASH_B)

        # revogada libera a vaga
        conexao.execute("UPDATE aprovacoes_externas SET revogada_em = now(), revogada_motivo = 'substituida' WHERE id = 'ap-1'")
        _aprovacao(conexao, "ap-2", "e-1", HASH_B)
        # decidida também libera a vaga para o índice (a decisão é final, mas o histórico não bloqueia nova tentativa... na etapa)
        conexao.execute(
            "UPDATE aprovacoes_externas SET decisao = 'aprovada', decidida_em = now(), nome_aprovador = 'Maria Cliente' WHERE id = 'ap-2'"
        )
        _aprovacao(conexao, "ap-3", "e-1", "d" * 64)
        # outra etapa não é afetada
        _aprovacao(conexao, "ap-4", "e-2", "e" * 64)


def test_checks_de_decisao_e_revogacao(banco_scratch: _BancoScratch) -> None:
    _subir(banco_scratch)
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _aprovacao(conexao, "ap-1", "e-1", HASH_A)

        # decisão fora do domínio
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET decisao = 'talvez', decidida_em = now(), nome_aprovador = 'Maria' WHERE id = 'ap-1'")
        # decisão exige decidida_em
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET decisao = 'aprovada', nome_aprovador = 'Maria Cliente' WHERE id = 'ap-1'")
        # decidida_em sem decisão
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET decidida_em = now() WHERE id = 'ap-1'")
        # decisão exige nome do aprovador
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET decisao = 'aprovada', decidida_em = now() WHERE id = 'ap-1'")
        # ajustes exigem motivo
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute(
                "UPDATE aprovacoes_externas SET decisao = 'ajustes_solicitados', decidida_em = now(), nome_aprovador = 'Maria Cliente' WHERE id = 'ap-1'"
            )
        conexao.execute(
            "UPDATE aprovacoes_externas SET decisao = 'ajustes_solicitados', decidida_em = now(), nome_aprovador = 'Maria Cliente', "
            "motivo = 'Trocar o logotipo' WHERE id = 'ap-1'"
        )
        # decidida não pode ser revogada
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET revogada_em = now(), revogada_motivo = 'manual' WHERE id = 'ap-1'")

        _aprovacao(conexao, "ap-2", "e-2", HASH_B)
        # revogação exige motivo e motivo exige revogação
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET revogada_em = now() WHERE id = 'ap-2'")
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET revogada_motivo = 'manual' WHERE id = 'ap-2'")
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET revogada_em = now(), revogada_motivo = 'qualquer' WHERE id = 'ap-2'")
        # decisão em uma revogada também é recusada
        conexao.execute("UPDATE aprovacoes_externas SET revogada_em = now(), revogada_motivo = 'etapa_decidida_internamente' WHERE id = 'ap-2'")
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute("UPDATE aprovacoes_externas SET decisao = 'aprovada', decidida_em = now(), nome_aprovador = 'Maria Cliente' WHERE id = 'ap-2'")
        # validade precisa ser posterior à criação
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute(
                "INSERT INTO aprovacoes_externas (id, empresa_id, demanda_id, workflow_etapa_id, token_hash, criada_em, expira_em) "
                "VALUES ('ap-3', 'emp-a', 'd-1', 'e-2', %s, now(), now() - interval '1 hour')",
                ("f" * 64,),
            )


def test_artefatos_pk_unicidade_e_checks(banco_scratch: _BancoScratch) -> None:
    _subir(banco_scratch)
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _aprovacao(conexao, "ap-1", "e-1", HASH_A)

        def artefato(ordem: int, arquivo_id: str | None, sha: str = SHA) -> None:
            conexao.execute(
                "INSERT INTO aprovacao_externa_arquivos (aprovacao_externa_id, ordem, arquivo_id, nome_original, tamanho_bytes, content_type, sha256) "
                "VALUES ('ap-1', %s, %s, 'arte.png', 10, 'image/png', %s)",
                (ordem, arquivo_id, sha),
            )

        artefato(1, "a-1")
        with pytest.raises(psycopg.errors.UniqueViolation):
            artefato(1, "a-2")  # PK (aprovacao, ordem)
        with pytest.raises(psycopg.errors.UniqueViolation):
            artefato(2, "a-1")  # mesmo arquivo duas vezes
        with pytest.raises(psycopg.errors.CheckViolation):
            artefato(0, "a-2")  # ordem >= 1
        with pytest.raises(psycopg.errors.CheckViolation):
            artefato(2, "a-2", sha="XYZ")  # sha256 hexadecimal minúsculo de 64 chars
        with pytest.raises(psycopg.errors.CheckViolation):
            artefato(2, "a-2", sha="C" * 64)  # maiúsculas recusadas
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            artefato(2, "inexistente")
        artefato(2, "a-2")
        # NULLs (arquivos já excluídos) não colidem entre si
        artefato(3, None)
        artefato(4, None)
        with pytest.raises(psycopg.errors.NotNullViolation):
            conexao.execute(
                "INSERT INTO aprovacao_externa_arquivos (aprovacao_externa_id, ordem, arquivo_id, nome_original, tamanho_bytes, content_type) "
                "VALUES ('ap-1', 5, 'a-3', 'x.png', 1, 'image/png')"
            )


def test_fks_set_null_e_cascade(banco_scratch: _BancoScratch) -> None:
    _subir(banco_scratch)
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
        _aprovacao(conexao, "ap-1", "e-1", HASH_A)
        conexao.execute(
            "INSERT INTO aprovacao_externa_arquivos (aprovacao_externa_id, ordem, arquivo_id, nome_original, tamanho_bytes, content_type, sha256) "
            "VALUES ('ap-1', 1, 'a-1', 'arte1.png', 10, 'image/png', %s)",
            (SHA,),
        )
        # excluir o arquivo preserva o snapshot e zera só a referência viva
        conexao.execute("DELETE FROM demanda_arquivos WHERE id = 'a-1'")
        assert conexao.execute(
            "SELECT arquivo_id, nome_original, tamanho_bytes, content_type, sha256 FROM aprovacao_externa_arquivos"
        ).fetchone() == (None, "arte1.png", 10, "image/png", SHA)

        # excluir o usuário preserva a solicitação (criador/revogador viram NULL)
        conexao.execute("UPDATE aprovacoes_externas SET revogada_em = now(), revogada_motivo = 'manual', revogada_por_usuario_id = 'u-1'")
        conexao.execute("DELETE FROM usuarios WHERE id = 'u-1'")
        assert conexao.execute("SELECT criada_por_usuario_id, revogada_por_usuario_id FROM aprovacoes_externas").fetchone() == (None, None)

        # FKs de contexto não têm cascade: a evidência bloqueia a remoção da etapa/demanda/empresa
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conexao.execute("DELETE FROM demanda_workflow_etapas WHERE id = 'e-1'")
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conexao.execute("DELETE FROM empresas WHERE id = 'emp-a'")

        # remover a solicitação leva os artefatos junto
        conexao.execute("DELETE FROM aprovacoes_externas WHERE id = 'ap-1'")
        assert conexao.execute("SELECT count(*) FROM aprovacao_externa_arquivos").fetchone() == (0,)


def test_downgrade_remove_so_as_tabelas_novas(banco_scratch: _BancoScratch) -> None:
    assert banco_scratch.alembic("upgrade", REV_ANTERIOR).returncode == 0
    with banco_scratch.conectar() as conexao:
        _semear_base(conexao)
    _subir(banco_scratch)
    with banco_scratch.conectar() as conexao:
        _aprovacao(conexao, "ap-1", "e-1", HASH_A)

    resultado = banco_scratch.alembic("downgrade", REV_ANTERIOR)
    assert resultado.returncode == 0, resultado.stderr
    assert REV_ANTERIOR in banco_scratch.revisao_atual() and REV_0044 not in banco_scratch.revisao_atual()
    assert not banco_scratch.existe_tabela("aprovacoes_externas") and not banco_scratch.existe_tabela("aprovacao_externa_arquivos")
    with banco_scratch.conectar() as conexao:
        assert conexao.execute("SELECT count(*) FROM demanda_arquivos").fetchone() == (3,)
        assert conexao.execute("SELECT count(*) FROM demanda_workflow_etapas").fetchone() == (2,)
        assert conexao.execute("SELECT count(*) FROM demandas").fetchone() == (1,)
    # e sobe de novo, limpo
    _subir(banco_scratch)
    assert banco_scratch.existe_tabela("aprovacoes_externas")
