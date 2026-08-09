# Reconstrução do banco a partir do zero

> Este documento existe por causa de um erro concreto. Na prova de banco vazio da Fase 2C os
> seeds rodaram com `usuarios` antes de `departamentos`. **Nada falhou.** O comando imprimiu
> "Usuários criados: 38" e terminou com sucesso — mas os 38 ficaram sem departamento, porque
> `seed_usuarios` resolvia o vínculo por nome e, não encontrando, gravava `NULL` em silêncio.
>
> Um banco sintaticamente válido e semanticamente errado é a pior forma de falha: não há o
> que investigar, porque nada se queixou.

O objetivo desta página é que a reconstrução seja **determinística** e que executá-la errado
seja **impossível de passar despercebido**.

---

## O comando

```bash
alembic upgrade head
python -m app.cli.seed_all
```

É isso. `seed_all` orquestra os sete seeds na ordem oficial e imprime um resumo com o que
cada passo criou e as contagens finais. Ele para no primeiro erro e sai com código diferente
de zero.

Rodar um seed isolado continua funcionando (`python -m app.cli.seed_clientes`), mas aí a
ordem é responsabilidade de quem chama — e os seeds vão reclamar se as dependências não
estiverem lá.

---

## Ordem oficial e por que cada passo depende do anterior

| # | Seed | Depende de | Por quê |
|---|---|---|---|
| 1 | `bootstrap` | — | cria a **Empresa** e a conta de sistema. Tudo é multiempresa e pende do `empresa_id` |
| 2 | `departamentos` | empresa | precisa existir **antes** dos usuários, que o referenciam pelo nome |
| 3 | `usuarios` | empresa, **departamentos** | o JSON traz o *nome* do departamento; o seed o converte em `departamento_id` |
| 4 | `equipes` | empresa, **departamentos**, **usuarios** | resolve departamento, líder e membros por `codigoInterno` |
| 5 | `grupos_cliente` | empresa | precisa existir **antes** dos clientes, que o referenciam |
| 6 | `clientes` | empresa, **grupos_cliente**, **usuarios** | resolve os grupos (N:N) e o responsável comercial |
| 7 | `fornecedores` | empresa | nenhum domínio o referencia; fica por último por ser o mais recente |

A ordem está declarada em `SEEDS`, em `backend/app/cli/seed_all.py`. Alterá-la quebra
`test_ordem_oficial_e_a_declarada` — de propósito.

### Resolução de referência: nunca por UUID, nunca por adivinhação

Os JSONs de seed **não carregam UUID**: os IDs técnicos mudam a cada ambiente, e o objetivo é
que `alembic upgrade head` + `seed_all` reconstruam um banco inteiro. As referências são
resolvidas por `codigoInterno` (ou, no caso de departamento em usuários, pelo nome
normalizado, herança da planilha de origem).

Referência que não resolve **aborta o seed**. Nunca:

- cria a entidade que falta automaticamente;
- aproxima por similaridade de nome;
- segue em frente gravando `NULL` ou uma lista menor.

---

## Fail-fast: o que acontece na ordem errada

### `seed_usuarios` sem `seed_departamentos`

```
DepartamentoNaoResolvidoError: Não é possível semear usuários:
38 vínculo(s) de departamento não resolvem.
  usuario-1 <hudson@taskfloww.local>: departamento 'Diretoria' não encontrado
  usuario-2 <ana.costa@taskfloww.local>: departamento 'Atendimento' não encontrado
  ...
Rode `python -m app.cli.seed_departamentos` antes — ou use o orquestrador oficial
`python -m app.cli.seed_all`, que garante a ordem.
```

A checagem roda **antes de qualquer escrita** e reporta **todos** os casos de uma vez — não
o primeiro, que obrigaria a rodar de novo a cada correção. Nenhum usuário é gravado.

### `seed_equipes` sem `departamentos`/`usuarios`

Mesma forma, com `ReferenciaDeEquipeNaoResolvidaError`. Cobre departamento, líder **e cada
membro**: antes, um membro não resolvido era filtrado da lista e a equipe nascia com menos
gente do que o dado de origem manda. Uma equipe com dois membros em vez de quatro é pior que
nenhuma equipe, porque parece certa.

### `NULL` continua legítimo

`departamento_id = NULL` é permitido quando **o dado de origem realmente não tem
departamento** — hoje só a conta de sistema. O fail-fast distingue os dois casos: campo
vazio/ausente passa, campo preenchido que não resolve aborta.

---

## Idempotência

Todo seed verifica existência antes de criar e, nos domínios com código de referência,
**antes de consumir a sequência**. Rodar `seed_all` duas vezes:

- cria **zero** registros;
- não altera nenhuma contagem;
- **não avança nenhum contador** — `C26000126` continua sendo o último cliente.

Isso importa porque o contador é monotônico por design: um seed que consumisse número a cada
execução deixaria buracos permanentes na numeração de negócio.

---

## Validações esperadas numa base recém-reconstruída

| Domínio | Registros | Faixa de código |
|---|---|---|
| Empresas | 1 | — |
| Departamentos | 7 | `D26000001` .. `D26000007` |
| Usuários | 39 | — |
| Equipes | 3 | `E26000001` .. `E26000003` |
| Grupos de cliente | 8 | — |
| Clientes | 126 | `C26000001` .. `C26000126` |
| Fornecedores | 135 | `F26000001` .. `F26000135` |

Vínculos: `equipe_membros` **4**, `cliente_grupos` **111**.

Invariantes:

- **38 usuários com departamento**; o único sem é a conta de sistema;
- todas as sequências começam em `000001`, sem lacunas (`max(sequencial) == count(*)`);
- cada contador em `sequencias_referencia` é igual à contagem do domínio;
- zero registros arquivados;
- zero vínculos cruzando empresa.

Conferência rápida:

```sql
SELECT count(*) FROM usuarios WHERE departamento_id IS NOT NULL;  -- 38
SELECT tipo_entidade, ultimo_numero FROM sequencias_referencia ORDER BY 1;
SELECT max(sequencial_referencia) - count(*) AS lacunas FROM clientes;  -- 0
```

Tudo isso está coberto por `backend/tests/test_seed_all.py`, que roda contra o banco de
teste a cada `pytest`.

---

## Banco novo do zero

```bash
# 1. criar o banco vazio
docker exec taskfloww-postgres psql -U taskfloww -d postgres -c 'CREATE DATABASE meu_banco OWNER taskfloww;'

# 2. apontar o ambiente (backend/.env — nunca versionado)
#    DATABASE_URL=postgresql+psycopg://.../meu_banco

# 3. reconstruir
alembic upgrade head
python -m app.cli.seed_all

# 4. conferir
alembic current   # deve bater com alembic heads
alembic check     # "No new upgrade operations detected."
```

`BOOTSTRAP_DEFAULT_PASSWORD` precisa estar definida — sem ela o seed para em vez de inventar
uma senha (ver `app/core/config.py`). Todas as contas criadas nascem com essa senha e com
troca obrigatória no primeiro acesso, exceto a conta de sistema.

**Reconstruir gera UUIDs novos.** Sessões abertas contra o banco anterior deixam de valer e
qualquer senha trocada lá não existe na base nova.

---

## Referências

- `backend/app/cli/seed_all.py` — a ordem oficial, executável
- `backend/tests/test_seed_all.py` — ordem, fail-fast, idempotência e contagens
- [padrao-arquivamento.md](padrao-arquivamento.md) — soft-delete e motivo obrigatório
- [padrao-entidades-externas.md](padrao-entidades-externas.md) — identidade e resolução de referência
- [pendencias-arquiteturais.md](pendencias-arquiteturais.md) — divergências conhecidas entre domínios
