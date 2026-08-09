"""Executa todos os seeds oficiais na ordem correta.

## Por que este comando existe

A ordem dos seeds não é convenção: é dependência real, e executá-la errado **não** produzia
erro. `seed_usuarios` resolvia o departamento por nome e, não encontrando, gravava `NULL` —
então rodá-lo antes de `seed_departamentos` gerava 38 usuários sem vínculo e terminava
imprimindo "Usuários criados: 38". Um banco sintaticamente válido e semanticamente errado.

Isso foi corrigido em dois lugares que se reforçam:

1. `seed_usuarios` agora aborta com `DepartamentoNaoResolvidoError` (a rede de proteção);
2. este orquestrador existe para que ninguém precise lembrar a ordem (a prevenção).

## Ordem oficial e o motivo de cada passo

| # | Seed | Depende de | Por quê |
|---|------|-----------|---------|
| 1 | `bootstrap` | — | cria a Empresa e a conta de sistema; tudo é multiempresa e pende dela |
| 2 | `departamentos` | empresa | precisa vir antes de usuários, que os referenciam por nome |
| 3 | `usuarios` | empresa, departamentos | resolve `departamento` (nome) → `departamento_id` |
| 4 | `equipes` | empresa, departamentos, usuarios | resolve departamento, líder e membros por `codigoInterno` |
| 5 | `grupos_cliente` | empresa | precisa vir antes de clientes, que os referenciam |
| 6 | `clientes` | empresa, grupos_cliente, usuarios | resolve grupos e responsável comercial |
| 7 | `fornecedores` | empresa | nenhum domínio o referencia; poderia rodar mais cedo, mas fica por último por ser o mais recente |

## O que este módulo NÃO faz

Não reimplementa nada. Cada passo chama a função do seed correspondente, sem tocar em
regra de negócio, geração de código de referência ou idempotência — tudo isso continua
morando no seed de cada domínio.

Os números do resumo vêm de `count(*)` no banco, medidos antes e depois de cada passo.
Não se interpreta a saída de texto dos seeds: formato de mensagem é apresentação, e
apresentação muda.

## Idempotência

Cada seed já verifica existência antes de criar (e, nos domínios com código de referência,
**antes de consumir a sequência**). Rodar `seed_all` duas vezes cria zero registros e não
avança nenhum contador.

Uso: python -m app.cli.seed_all
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import text

from app.cli.seed_bootstrap import seed_bootstrap
from app.cli.seed_clientes import seed_clientes
from app.cli.seed_departamentos import seed_departamentos
from app.cli.seed_equipes import seed_equipes
from app.cli.seed_fornecedores import seed_fornecedores
from app.cli.seed_grupos_cliente import seed_grupos_cliente
from app.cli.seed_usuarios import seed_usuarios
from app.db.session import get_session_factory

# A ordem desta tupla É a ordem oficial. Alterá-la altera o contrato de reconstrução —
# ver docs/reconstrucao-banco.md e os testes em tests/test_seed_all.py.
SEEDS: tuple[tuple[str, Callable[..., None]], ...] = (
    ("bootstrap", seed_bootstrap),
    ("departamentos", seed_departamentos),
    ("usuarios", seed_usuarios),
    ("equipes", seed_equipes),
    ("grupos_cliente", seed_grupos_cliente),
    ("clientes", seed_clientes),
    ("fornecedores", seed_fornecedores),
)

# Tabelas contadas no resumo. Não inclui `eventos`: ele cresce a cada escrita e mediria
# atividade, não população.
TABELAS_CONTADAS: tuple[str, ...] = (
    "empresas",
    "departamentos",
    "usuarios",
    "equipes",
    "equipe_membros",
    "grupos_cliente",
    "clientes",
    "cliente_grupos",
    "fornecedores",
)


@dataclass
class ResultadoPasso:
    nome: str
    # Delta por tabela, só das que mudaram. Guardado desagregado de propósito: um passo
    # toca mais de uma tabela (clientes cria `clientes` E `cliente_grupos`), e somar tudo
    # num número só produz "clientes: criou 237", que não quer dizer nada.
    criados_por_tabela: dict[str, int] = field(default_factory=dict)
    erro: str | None = None
    linhas: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.erro is None

    @property
    def criados(self) -> int:
        return sum(self.criados_por_tabela.values())

    def resumo_criados(self) -> str:
        if not self.criados_por_tabela:
            return "nada a criar (idempotente)"
        return ", ".join(f"{tabela} +{qtd}" for tabela, qtd in self.criados_por_tabela.items())


@dataclass
class ResultadoSeedAll:
    passos: list[ResultadoPasso]
    contagens: dict[str, int]

    @property
    def ok(self) -> bool:
        return all(passo.ok for passo in self.passos)

    @property
    def total_criados(self) -> int:
        return sum(passo.criados for passo in self.passos)


def _contar(db) -> dict[str, int]:
    return {
        tabela: db.execute(text(f"SELECT count(*) FROM {tabela}")).scalar_one()
        for tabela in TABELAS_CONTADAS
    }


def seed_all(output=print) -> ResultadoSeedAll:
    """Roda os sete seeds na ordem oficial. Para no primeiro erro.

    Parar é deliberado: os passos são dependentes, então seguir depois de uma falha só
    produziria uma cascata de erros derivados escondendo a causa real.
    """
    factory = get_session_factory()
    passos: list[ResultadoPasso] = []

    with factory() as db:
        antes_geral = _contar(db)

    for indice, (nome, funcao) in enumerate(SEEDS, start=1):
        output(f"\n[{indice}/{len(SEEDS)}] {nome}")
        output("-" * 60)

        with factory() as db:
            antes = _contar(db)

        linhas: list[str] = []

        def capturar(mensagem="", _linhas=linhas):
            _linhas.append(str(mensagem))
            output(f"  {mensagem}")

        try:
            funcao(output=capturar)
        except Exception as exc:  # noqa: BLE001 — o resumo precisa reportar qualquer falha
            passos.append(
                ResultadoPasso(nome=nome, erro=f"{type(exc).__name__}: {exc}", linhas=linhas)
            )
            output(f"\n  ✗ FALHOU: {type(exc).__name__}: {exc}")
            break

        with factory() as db:
            depois = _contar(db)

        deltas = {t: depois[t] - antes[t] for t in TABELAS_CONTADAS if depois[t] != antes[t]}
        passos.append(ResultadoPasso(nome=nome, criados_por_tabela=deltas, linhas=linhas))

    with factory() as db:
        contagens = _contar(db)

    resultado = ResultadoSeedAll(passos=passos, contagens=contagens)
    _imprimir_resumo(resultado, antes_geral, output)
    return resultado


def _imprimir_resumo(resultado: ResultadoSeedAll, antes: dict[str, int], output) -> None:
    output("\n" + "=" * 60)
    output("RESUMO")
    output("=" * 60)

    output("\nPassos:")
    for passo in resultado.passos:
        if passo.ok:
            output(f"  ok      {passo.nome:<16} {passo.resumo_criados()}")
        else:
            output(f"  ERRO    {passo.nome:<16} {passo.erro}")

    nao_executados = [nome for nome, _ in SEEDS[len(resultado.passos):]]
    for nome in nao_executados:
        output(f"  -       {nome:<16} não executado (abortado antes)")

    output("\nContagens finais:")
    for tabela in TABELAS_CONTADAS:
        total = resultado.contagens[tabela]
        delta = total - antes[tabela]
        sufixo = f"  (+{delta})" if delta else ""
        output(f"  {tabela:<18} {total:>6}{sufixo}")

    output("")
    if resultado.ok:
        output(
            f"Concluído. {resultado.total_criados} registro(s) criado(s)."
            if resultado.total_criados
            else "Concluído. Nenhum registro criado — base já estava semeada (idempotente)."
        )
    else:
        output("Concluído COM ERRO. Nada além do passo que falhou foi executado.")


if __name__ == "__main__":
    import sys

    resultado = seed_all()
    # Código de saída diferente de zero para CI e scripts detectarem a falha.
    sys.exit(0 if resultado.ok else 1)
