"""Reconstrução de banco vazio — ordem oficial dos seeds e fail-fast.

## O que estes testes protegem

Um banco reconstruído na ordem errada **não dava erro**. `seed_usuarios` resolvia o
departamento por nome e, não encontrando, gravava `NULL`: rodá-lo antes de
`seed_departamentos` produzia 38 usuários sem vínculo e imprimia "Usuários criados: 38".
`seed_equipes` tinha a mesma classe de problema — pulava a equipe cuja dependência faltava,
registrava "invalida" e saía com sucesso.

Os dois casos produzem um banco que passa em qualquer checagem estrutural e está errado no
conteúdo. Estes testes existem para que a falha volte a ser barulhenta.

## Por que não usam `db_session`

Os seeds abrem a própria sessão e dão `commit()`. A fixture transacional da suíte não os
alcança, então aqui a limpeza é explícita: TRUNCATE antes e depois. Roda contra
`taskfloww_test` (mesma URL validada em tests/fixtures/database.py), nunca contra
desenvolvimento.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.cli.seed_all import SEEDS, seed_all
from app.cli.seed_bootstrap import seed_bootstrap
from app.cli.seed_departamentos import seed_departamentos
from app.cli.seed_equipes import ReferenciaDeEquipeNaoResolvidaError, seed_equipes
from app.cli.seed_usuarios import DepartamentoNaoResolvidoError, seed_usuarios

# Ordem inversa de dependência para o TRUNCATE ... CASCADE não depender de sorte.
TABELAS_DOMINIO = (
    "eventos",
    "sessoes_trabalho",
    "cliente_grupos",
    "clientes",
    "fornecedores",
    "grupos_cliente",
    "equipe_membros",
    "equipes",
    "usuario_credenciais",
    "usuarios",
    "departamentos",
    "sequencias_referencia",
    "empresas",
)


def _limpar(engine: Engine) -> None:
    with engine.begin() as conexao:
        conexao.execute(text(f"TRUNCATE {', '.join(TABELAS_DOMINIO)} RESTART IDENTITY CASCADE"))


def _consultar(engine: Engine, sql: str):
    with engine.connect() as conexao:
        return conexao.execute(text(sql)).all()


def _escalar(engine: Engine, sql: str):
    with engine.connect() as conexao:
        return conexao.execute(text(sql)).scalar_one()


@pytest.fixture()
def banco_vazio(test_engine: Engine):
    """Base sem nenhum registro, limpa também na saída para não vazar entre módulos."""
    _limpar(test_engine)
    yield test_engine
    _limpar(test_engine)


@pytest.fixture(scope="module")
def base_reconstruida(test_engine: Engine):
    """Roda `seed_all` DUAS vezes e devolve os dois resultados.

    Escopo de módulo porque a primeira execução custa alguns segundos (argon2 em 38
    credenciais). Uma execução só serve tanto às asserções de ordem correta quanto às de
    idempotência — repetir o setup por teste não provaria nada a mais.
    """
    _limpar(test_engine)
    primeira = seed_all(output=lambda *_: None)
    segunda = seed_all(output=lambda *_: None)
    yield primeira, segunda
    _limpar(test_engine)


# ======================================================================================
# A. Ordem correta — reconstrução completa a partir do vazio
# ======================================================================================

def test_seed_all_reconstroi_a_base_inteira(base_reconstruida, test_engine: Engine) -> None:
    primeira, _ = base_reconstruida
    assert primeira.ok, [p.erro for p in primeira.passos if not p.ok]

    assert primeira.contagens == {
        "empresas": 1,
        "departamentos": 7,
        "usuarios": 39,
        "equipes": 3,
        "equipe_membros": 4,
        "grupos_cliente": 8,
        "clientes": 126,
        "cliente_grupos": 111,
        "fornecedores": 135,
    }


def test_todos_os_usuarios_do_seed_ficam_vinculados(base_reconstruida, test_engine: Engine) -> None:
    """O bug original: 38 usuários com departamento NULL e nenhum erro."""
    vinculados = _escalar(test_engine, "SELECT count(*) FROM usuarios WHERE departamento_id IS NOT NULL")
    assert vinculados == 38


def test_apenas_a_conta_de_sistema_fica_sem_departamento(base_reconstruida, test_engine: Engine) -> None:
    sem_departamento = _consultar(
        test_engine,
        "SELECT email, is_system_account FROM usuarios WHERE departamento_id IS NULL",
    )
    assert len(sem_departamento) == 1
    assert sem_departamento[0].is_system_account is True


def test_nenhum_vinculo_orfao(base_reconstruida, test_engine: Engine) -> None:
    """FK cobre o caso normal; isto pega o vínculo que aponta para outra empresa."""
    orfaos = _escalar(
        test_engine,
        """
        SELECT count(*) FROM usuarios u
        JOIN departamentos d ON d.id = u.departamento_id
        WHERE d.empresa_id <> u.empresa_id
        """,
    )
    assert orfaos == 0


@pytest.mark.parametrize(
    ("tabela", "prefixo", "total"),
    [
        ("departamentos", "D", 7),
        ("equipes", "E", 3),
        ("clientes", "C", 126),
        ("fornecedores", "F", 135),
    ],
)
def test_codigos_comecam_em_1_e_nao_tem_lacuna(
    base_reconstruida, test_engine: Engine, tabela: str, prefixo: str, total: int
) -> None:
    linha = _consultar(
        test_engine,
        f"""
        SELECT min(sequencial_referencia) AS menor,
               max(sequencial_referencia) AS maior,
               count(*) AS total,
               min(codigo_referencia) AS primeiro
        FROM {tabela}
        """,
    )[0]
    assert linha.menor == 1
    assert linha.total == total
    assert linha.maior == total, "buraco na sequência"
    assert linha.primeiro == f"{prefixo}26000001"


def test_contadores_refletem_a_quantidade_criada(base_reconstruida, test_engine: Engine) -> None:
    contadores = dict(
        _consultar(test_engine, "SELECT tipo_entidade, ultimo_numero FROM sequencias_referencia")
    )
    assert contadores == {"departamento": 7, "equipe": 3, "cliente": 126, "fornecedor": 135}


def test_ordem_oficial_e_a_declarada(base_reconstruida) -> None:
    """Trava explícita: mudar a ordem tem de quebrar um teste, não passar despercebido."""
    primeira, _ = base_reconstruida
    esperada = [
        "bootstrap",
        "departamentos",
        "usuarios",
        "equipes",
        "grupos_cliente",
        "clientes",
        "fornecedores",
    ]
    assert [nome for nome, _ in SEEDS] == esperada
    assert [passo.nome for passo in primeira.passos] == esperada


# ======================================================================================
# E. Idempotência
# ======================================================================================

def test_segunda_execucao_nao_cria_nada(base_reconstruida) -> None:
    _, segunda = base_reconstruida
    assert segunda.ok
    assert segunda.total_criados == 0
    assert all(passo.criados == 0 for passo in segunda.passos), [
        (p.nome, p.criados_por_tabela) for p in segunda.passos if p.criados
    ]


def test_segunda_execucao_nao_altera_contagens(base_reconstruida) -> None:
    primeira, segunda = base_reconstruida
    assert segunda.contagens == primeira.contagens


def test_segunda_execucao_nao_avanca_contadores(base_reconstruida, test_engine: Engine) -> None:
    contadores = dict(
        _consultar(test_engine, "SELECT tipo_entidade, ultimo_numero FROM sequencias_referencia")
    )
    assert contadores == {"departamento": 7, "equipe": 3, "cliente": 126, "fornecedor": 135}


# ======================================================================================
# B. Ordem errada — usuários sem departamentos
# ======================================================================================

def test_usuarios_sem_departamentos_aborta(banco_vazio: Engine) -> None:
    seed_bootstrap(output=lambda *_: None)

    with pytest.raises(DepartamentoNaoResolvidoError) as erro:
        seed_usuarios(output=lambda *_: None)

    assert "seed_all" in str(erro.value), "a mensagem precisa apontar a saída"


def test_ordem_errada_nao_grava_vinculo_perdido(banco_vazio: Engine) -> None:
    """Aborta ANTES de escrever: nenhum usuário do seed entra com departamento nulo."""
    seed_bootstrap(output=lambda *_: None)
    with pytest.raises(DepartamentoNaoResolvidoError):
        seed_usuarios(output=lambda *_: None)

    # Só a conta de sistema, criada pelo bootstrap — que legitimamente não tem departamento.
    restantes = _consultar(banco_vazio, "SELECT email, is_system_account FROM usuarios")
    assert len(restantes) == 1
    assert restantes[0].is_system_account is True


# ======================================================================================
# C. Departamento informado que não existe
# ======================================================================================

def test_departamento_inexistente_identifica_usuario_e_departamento(banco_vazio: Engine) -> None:
    """Cadastro parcial de departamentos: os que faltam têm de aparecer nominalmente."""
    seed_bootstrap(output=lambda *_: None)
    seed_departamentos(output=lambda *_: None)

    # Remove um departamento que sabidamente tem usuários apontando para ele.
    with banco_vazio.begin() as conexao:
        conexao.execute(
            text("UPDATE usuarios SET departamento_id = NULL WHERE departamento_id IS NOT NULL")
        )
        conexao.execute(text("DELETE FROM departamentos WHERE lower(nome) = 'criação'"))

    with pytest.raises(DepartamentoNaoResolvidoError) as erro:
        seed_usuarios(output=lambda *_: None)

    mensagem = str(erro.value)
    assert "Criação" in mensagem, "precisa nomear o departamento que faltou"
    assert "usuario-3" in mensagem or "carlos.lima@taskfloww.local" in mensagem, (
        "precisa identificar o registro afetado"
    )


def test_departamento_inexistente_nao_grava_nada(banco_vazio: Engine) -> None:
    seed_bootstrap(output=lambda *_: None)
    seed_departamentos(output=lambda *_: None)
    with banco_vazio.begin() as conexao:
        conexao.execute(text("DELETE FROM departamentos WHERE lower(nome) = 'criação'"))

    antes = _escalar(banco_vazio, "SELECT count(*) FROM usuarios")
    with pytest.raises(DepartamentoNaoResolvidoError):
        seed_usuarios(output=lambda *_: None)
    assert _escalar(banco_vazio, "SELECT count(*) FROM usuarios") == antes


# ======================================================================================
# D. Departamento realmente nulo continua permitido
# ======================================================================================

def test_usuario_sem_departamento_na_origem_e_aceito(banco_vazio: Engine, monkeypatch) -> None:
    """`None` só é gravado quando o dado de origem não tem departamento.

    O elenco oficial não tem esse caso (os 38 têm departamento), então ele é construído
    aqui — a regra precisa valer mesmo assim, senão o fail-fast estaria proibindo um dado
    legítimo em vez de proibir a ordem errada.
    """
    import app.cli.seed_usuarios as modulo

    seed_bootstrap(output=lambda *_: None)
    seed_departamentos(output=lambda *_: None)

    monkeypatch.setattr(
        modulo,
        "USUARIOS_DEMO",
        [
            {
                "codigo_interno": "usuario-sem-dep",
                "nome": "Sem Departamento",
                "email": "sem.departamento@taskfloww.local",
                "departamento": None,
                "perfil": "operador",
            }
        ],
    )
    monkeypatch.setattr(modulo, "_carregar_usuarios_importados", lambda: [])

    seed_usuarios(output=lambda *_: None)

    linha = _consultar(
        banco_vazio,
        "SELECT departamento_id FROM usuarios WHERE email = 'sem.departamento@taskfloww.local'",
    )
    assert len(linha) == 1
    assert linha[0].departamento_id is None


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_departamento_em_branco_nao_e_tratado_como_nao_encontrado(
    banco_vazio: Engine, monkeypatch, valor
) -> None:
    import app.cli.seed_usuarios as modulo

    seed_bootstrap(output=lambda *_: None)
    seed_departamentos(output=lambda *_: None)
    monkeypatch.setattr(
        modulo,
        "USUARIOS_DEMO",
        [
            {
                "codigo_interno": "usuario-branco",
                "nome": "Campo Em Branco",
                "email": "branco@taskfloww.local",
                "departamento": valor,
                "perfil": "operador",
            }
        ],
    )
    monkeypatch.setattr(modulo, "_carregar_usuarios_importados", lambda: [])

    seed_usuarios(output=lambda *_: None)  # não pode levantar

    assert _escalar(
        banco_vazio, "SELECT count(*) FROM usuarios WHERE email = 'branco@taskfloww.local'"
    ) == 1


# ======================================================================================
# F. Equipe aborta se as dependências não existirem
# ======================================================================================

def test_equipes_sem_departamentos_e_usuarios_aborta(banco_vazio: Engine) -> None:
    seed_bootstrap(output=lambda *_: None)

    with pytest.raises(ReferenciaDeEquipeNaoResolvidaError) as erro:
        seed_equipes(output=lambda *_: None)

    assert "não encontrado" in str(erro.value)


def test_equipes_com_membro_faltando_aborta_em_vez_de_criar_incompleta(banco_vazio: Engine) -> None:
    """Antes, membro não resolvido era filtrado da lista e a equipe nascia menor.

    Uma equipe com dois membros em vez de quatro é pior que nenhuma equipe: parece certa.
    """
    seed_bootstrap(output=lambda *_: None)
    seed_departamentos(output=lambda *_: None)
    seed_usuarios(output=lambda *_: None)

    # Renomear o codigoInterno é mais fiel ao caso real (a planilha muda, o cadastro não)
    # e não esbarra na FK da credencial, ao contrário de apagar o usuário.
    with banco_vazio.begin() as conexao:
        conexao.execute(
            text("UPDATE usuarios SET codigo_interno = 'usuario-4-renomeado' WHERE codigo_interno = 'usuario-4'")
        )

    with pytest.raises(ReferenciaDeEquipeNaoResolvidaError) as erro:
        seed_equipes(output=lambda *_: None)

    assert "usuario-4" in str(erro.value)
    assert _escalar(banco_vazio, "SELECT count(*) FROM equipes") == 0


def test_equipes_nao_grava_nada_quando_aborta(banco_vazio: Engine) -> None:
    seed_bootstrap(output=lambda *_: None)
    with pytest.raises(ReferenciaDeEquipeNaoResolvidaError):
        seed_equipes(output=lambda *_: None)

    assert _escalar(banco_vazio, "SELECT count(*) FROM equipes") == 0
    assert _escalar(banco_vazio, "SELECT count(*) FROM equipe_membros") == 0
    # A sequência de equipe não pode ter sido tocada.
    assert (
        _escalar(
            banco_vazio,
            "SELECT count(*) FROM sequencias_referencia WHERE tipo_entidade = 'equipe'",
        )
        == 0
    )


# ======================================================================================
# Orquestrador — comportamento de falha
# ======================================================================================

def test_seed_all_para_no_primeiro_erro(banco_vazio: Engine, monkeypatch) -> None:
    """Passos dependentes: seguir depois de uma falha só produz erros derivados."""
    import app.cli.seed_all as modulo

    def explodir(output=print):
        raise RuntimeError("falha simulada em departamentos")

    monkeypatch.setattr(
        modulo,
        "SEEDS",
        (
            ("bootstrap", modulo.SEEDS[0][1]),
            ("departamentos", explodir),
            ("usuarios", modulo.SEEDS[2][1]),
        ),
    )

    resultado = modulo.seed_all(output=lambda *_: None)

    assert not resultado.ok
    assert [p.nome for p in resultado.passos] == ["bootstrap", "departamentos"]
    assert "falha simulada" in resultado.passos[-1].erro
    # usuarios não rodou — nenhum usuário além da conta de sistema.
    assert _escalar(banco_vazio, "SELECT count(*) FROM usuarios") == 1
