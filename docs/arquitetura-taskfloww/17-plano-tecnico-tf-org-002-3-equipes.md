# 17 — Plano Técnico TF-ORG-002.3 — Equipes

> Plano técnico de implementação. Não é arquitetura, não é DDL, não é
> migration, não altera código e não altera os Documentos 13, 14, 15 ou 16.
> Todas as decisões de domínio já foram tomadas anteriormente; este
> documento apenas as converte em uma sequência técnica executável.

## 1. Objetivo

Este documento detalha o roteiro técnico da etapa **TF-ORG-002.3 —
Equipes**, definida pelo Documento 14 (seção 5) como a terceira etapa da
sequência oficial de implementação do épico TF-ORG-002.

Relação com os documentos anteriores:

- **Documento 13** (`13-dominio-organizacional-oficial.md`) define, para
  Equipe: seção 6.3 ("A arquitetura oficial adotada pelo projeto
  estabelece que toda Equipe possui exatamente um Departamento de
  referência vigente"), seção 7.3 (Responsabilidade, Dependências, Regras
  — "possui exatamente um Departamento de referência vigente"), seção 8.2
  ("Departamento 1 ─── 0..N Equipes / Equipe 1 ─── 1 Departamento de
  referência"), e a divergência 13.3 ("a entidade persistida Equipe possui
  Empresa, código, nome, descrição e status, mas não `departamento_id`").
  Este plano não reinterpreta essa semântica — apenas a aplica.
- **Documento 14** (`14-plano-implementacao-organizacao.md`) define, para
  TF-ORG-002.3: objetivo "Consolidar Equipes e promover sua convergência
  para a direção arquitetural oficial, preservando os usos operacionais
  existentes durante a transição"; dependências "TF-ORG-002.2, Empresa,
  Departamentos, Usuários, Workflow, Projetos, Kanban, Agenda e Central de
  Tráfego"; resultado esperado "Equipes e sua relação organizacional
  alinhadas ao documento 13, com compatibilidade operacional preservada."
- **Documento 15** (`15-diagnostico-convergencia-organizacional.md`)
  inventariou o estado atual de Equipes (seções 3.2, 4.3, 5.4, 8.3) e
  atribuiu a esta etapa (seção 10, bloco "TF-ORG-002.3"): a ausência de
  `departamento_id`; a ausência de `tipo_vinculo`/distinção de convidado em
  `usuario_equipes`; o papel `coordenador` sem definição de domínio; o
  campo `EquipeDraft.departamentoId` desconectado no mock de frontend; o
  vocabulário de status divergente (`ativo`/`encerrado` em
  `usuario_equipes` vs. `ativo`/`inativo` nos demais vínculos); e a
  ausência total de integração do frontend com `/equipes`.
- **Documento 16** (`16-plano-tecnico-tf-org-002-2-departamentos.md`)
  implementou, em `DepartamentoService.inativar_departamento`, a validação
  de vínculos ativos de Usuário e de sessões de trabalho ativas, deixando
  registrado em comentário explícito no código (confirmado nesta análise,
  seção 5 abaixo) que a validação de Equipes ativas pertence a esta etapa.
  O `PROJECT_STATUS.md` confirma TF-ORG-002.2 como concluída e repete essa
  mesma pendência como "exclusiva da TF-ORG-002.3".

### 1.1 Escopo obrigatório desta etapa (confirmação)

Conforme solicitado, este plano cobre exclusivamente:

1. inclusão de `departamento_id` em Equipe;
2. relacionamento obrigatório entre Equipe ativa e Departamento;
3. validação de existência, status ativo e mesma Empresa do Departamento;
4. migration incremental e segura;
5. estratégia de convergência/backfill das Equipes existentes;
6. exposição de `departamentoId` nos schemas e respostas da API;
7. filtro de Equipes por Departamento;
8. validação na reativação de Equipe;
9. bloqueio da inativação de Departamento com Equipes ativas;
10. testes de model, service, API, migration e regressão;
11. atualização de documentação e `PROJECT_STATUS.md` **após** a
    implementação (não nesta etapa de planejamento).

Os itens explicitamente fora deste escopo estão na seção 4.

## 2. Contexto Atual

O TaskFloww V2 está na fase de convergência do domínio organizacional
(épico TF-ORG-002). TF-ORG-002.1 (diagnóstico) e TF-ORG-002.2
(Departamentos) já foram concluídas e homologadas. O `PROJECT_STATUS.md`
registra a TF-ORG-002.2 como concluída, com 611 testes aprovados e a
seguinte pendência explícita, textual:

> "Pendência exclusiva da TF-ORG-002.3: Validação de Equipes ativas após a
> criação de departamento_id em Equipe."

Esta é a auditoria técnica mais recente disponível sobre a TF-ORG-002.3: a
própria entrega da etapa anterior já declarou, em código e em
documentação de status, exatamente a lacuna que esta etapa deve fechar. A
verificação de código feita para este plano (seção 5) confirma que essa
lacuna continua aberta e que nenhuma implementação de `departamento_id` em
Equipe foi iniciada.

## 3. Decisões Congeladas

Decisões já tomadas nos Documentos 13, 14, 15 e 16, que este plano não
reabre:

- Empresa é a raiz de isolamento; todo relacionamento novo usa IDs, nunca
  nomes ou strings de mock (Documento 13, seções 4.1, 4.4).
- Toda Equipe possui exatamente um Departamento de referência vigente
  (Documento 13, seções 6.3, 7.3, 8.2) — esta é a arquitetura oficial
  adotada pelo projeto, ainda não refletida pela implementação atual
  (Documento 13, divergência 13.3).
- Membros de Equipe convidados de outro Departamento são exceção
  explícita, marcada no vínculo (Documento 13, seções 7.3, 9.12) — a
  representação física dessa exceção (`tipo_vinculo` em `usuario_equipes`)
  **não** é decidida por este plano.
- Mudanças de Departamento de referência de uma Equipe devem ser
  explícitas e auditáveis (Documento 13, seção 7.3, regra "mudança do
  Departamento de referência deve ser auditada") — a forma física dessa
  auditoria é ponto pendente do próprio Documento 13 (seção 14.9) e
  **não** é decidida por este plano.
- RBAC (`require_admin` para escrita, `require_admin_or_gestor` para
  leitura) e isolamento por Empresa (`ensure_same_empresa`,
  `ensure_resource_empresa`) continuam sendo a única fonte de autorização;
  nenhuma regra desta etapa deriva permissão do vínculo Equipe-Departamento
  (Documento 13, seção 11).
- Compatibilidade antes de remoção; alterações pequenas e revisáveis;
  arquitetura antes do código (Documento 14, seção 4).
- Nenhuma implementação deve iniciar sem escopo técnico aprovado; commit e
  push dependem de autorização explícita (Documento 14, seção 11).

## 4. Fora de Escopo

Os itens abaixo são explicitamente excluídos da TF-ORG-002.3. Ficam
registrados como pendências futuras (seção 16) e **não bloqueiam** a
referência mínima Equipe → Departamento definida nesta etapa:

- **Distinção entre membro normal e convidado** em `usuario_equipes`
  (campo equivalente a `tipo_vinculo`): pertence a uma etapa própria de
  vínculos, não a esta. Sem essa distinção, um membro de Equipe cujo
  Departamento principal diverge do Departamento de referência da Equipe
  continuará sendo tratado como hoje — sem marcação de exceção — o que já
  é o comportamento atual e não piora com esta etapa.
- **Alteração do papel `coordenador`** em `usuario_equipes.papel`: sua
  definição de domínio permanece em aberto (Documento 15, seção 8.4);
  nada nesta etapa depende de resolver isso.
- **Convergência dos status de `UsuarioEquipe`**
  (`ativo`/`encerrado` vs. `ativo`/`inativo`): pertence a TF-ORG-002.5 —
  Vínculos (Documento 15, seção 10, bloco "TF-ORG-002.5").
- **Squads**: fora do escopo do TF-ORG-002 inteiro (Documento 14, seção
  2).
- **Integração real do frontend** (telas, componentes, hooks, tipos):
  pertence a TF-ORG-002.8 — Integração Frontend. `EquipesView.tsx`
  continua 100% mock após esta etapa.
- **BFF**: nenhuma rota Next.js (`app/api/*`) para Equipes existe hoje;
  criar uma pertence também a TF-ORG-002.8.
- **Mudanças em Projetos, Kanban, Agenda ou Central de Tráfego**: esses
  módulos não são tocados nesta etapa, mesmo sendo dependências
  declaradas de TF-ORG-002.3 no Documento 14 — a dependência ali listada é
  de leitura futura (esses módulos poderão consumir a relação
  Equipe-Departamento depois), não de alteração nesta etapa.
- **Mudança de Departamento de uma Equipe já criada**: nesta etapa,
  `departamento_id` é definido na criação e **não pode ser alterado** via
  PATCH (decisão técnica explícita, seção 8.4 e 8.5). Uma Equipe não pode
  trocar de Departamento de referência através desta etapa.
- **Histórico avançado de movimentação entre Departamentos**: como a
  troca de Departamento de uma Equipe não é implementada nesta etapa
  (item anterior), não há histórico de movimentação a projetar. Isso
  permanece pendente para quando a troca for aprovada (Documento 13,
  seção 14.9).
- **Endpoint de arquivamento (`/equipes/{id}/arquivar`)**: mesmo padrão já
  registrado como fora de escopo em Departamentos (Documento 16, seção
  4.2) — o estado `arquivada` de Equipe permanece inalcançável via API,
  de forma consistente com Departamento, Cargo, Agência e Empresa.
- **`sigla` em Equipe**: `EquipeDraft` (frontend legado) possui `sigla`,
  mas a entidade persistida `Equipe` não. O Documento 13 não exige
  `sigla` para Equipe (seção 7.3 não a lista como campo obrigatório).
  Adicionar esse campo não pertence ao escopo desta etapa, que é
  exclusivamente sobre `departamento_id`.

## 5. Estado Atual do Código

Verificado por leitura direta dos arquivos, nesta análise:

**Model** (`backend/app/models/equipe.py`): `Equipe` possui `id`,
`empresa_id`, `codigo_interno`, `nome`, `descricao`, `status`
(`ativa`/`inativa`/`arquivada`), timestamps e campos de inativação. **Não
possui `departamento_id`.**

**Migration** (`backend/alembic/versions/20260716_1a14_cria_tabela_equipes.py`):
cria a tabela `equipes` sem `departamento_id`. A cadeia de migrations
atual tem como topo (`head`) a revisão `20260716_1a16`
(`cria_tabela_clientes`), que sucede `20260716_1a15`
(`cria_usuario_equipes`), que sucede `20260716_1a14`
(`cria_tabela_equipes`).

**Schemas** (`backend/app/schemas/equipe.py`): `EquipeCreate` aceita
`empresaId`, `codigoInterno`, `nome`, `descricao`, com
`extra="forbid"`. `EquipeUpdate` aceita os mesmos três campos editáveis
(sem `empresaId`), também com `extra="forbid"`. `EquipeResponse` expõe os
campos do model. **Nenhum schema referencia Departamento.**

**Service** (`backend/app/services/equipe_service.py`): `create_equipe`
valida Empresa ativa (`_ensure_empresa_accepts_equipe`) e unicidade de
`codigo_interno`/`nome` por Empresa — mesmo padrão de
`DepartamentoService`. `inativar_equipe`/`reativar_equipe` validam apenas
a transição de `status` da própria Equipe. **Nenhuma validação de
Departamento existe.**

**Repository** (`backend/app/repositories/equipe_repository.py`):
`list()` aceita `empresa_id`, `status`, `busca`, `limit`, `offset`. **Não
aceita filtro por `departamento_id`** (porque a coluna não existe).

**Rotas** (`backend/app/api/routes/equipes.py`): `POST /equipes`,
`GET /equipes`, `GET /equipes/{id}`, `PATCH /equipes/{id}`
(`PATCH_ALLOWED_FIELDS = {"codigoInterno", "nome", "descricao"}`),
`POST /equipes/{id}/inativar`, `POST /equipes/{id}/reativar`. Mesmo
padrão de autorização de Departamento
(`require_admin`/`require_admin_or_gestor`,
`ensure_same_empresa`/`ensure_resource_empresa`).

**DepartamentoService** (`backend/app/services/departamento_service.py`,
já confirmado após a implementação de TF-ORG-002.2): `inativar_departamento`
já consulta `usuario_departamento_repository.list_by_departamento(...,
status="ativo")` e `sessao_trabalho_repository.list(...,
status="ativa", limit=1)`, bloqueando com `DepartamentoConflictError`
quando encontra qualquer um dos dois. Contém o comentário literal:

```python
# Equipe ainda não possui departamento_id; a validação de Equipes ativas pertence à TF-ORG-002.3.
```

Esse comentário é o ponto de entrada exato que esta etapa deve substituir
pela validação real (seção 8, Fase 5 / tarefa TF-ORG-002.3J).

**Testes:** além de `test_equipes.py` e `test_departamentos.py`, os
arquivos `test_equipe_model.py`, `test_usuario_equipe_model.py`,
`test_usuario_equipe_service.py` e `test_usuario_equipes.py` constroem
objetos `Equipe` diretamente. Durante a fase nullable, esses construtores
continuam compatíveis; quando o model convergir para `nullable=False` na
TF-ORG-002.3I, todos devem informar um `departamento_id` válido. Os helpers
`make_equipe`/`persist_equipe` (`test_equipes.py`) e
`make_departamento`/`persist_departamento` (`test_departamentos.py`) seguem
o mesmo padrão usado em toda a suíte (função `persist()` de
`conftest.py`).

**Padrão de validação cruzada já estabelecido:** `UsuarioDepartamentoService`
(`backend/app/services/usuario_departamento_service.py`, linha ~301) já
valida um Departamento referenciado por outra entidade com exatamente o
padrão que esta etapa deve replicar para Equipe:

```python
if departamento is None or departamento.empresa_id != empresa_id or departamento.status != DEPARTAMENTO_STATUS_ATIVA:
    raise UsuarioDepartamentoInvalidDataError("Departamento não encontrado ou inativo")
```

onde `DEPARTAMENTO_STATUS_ATIVA` é importado como
`from app.services.departamento_service import STATUS_ATIVA as DEPARTAMENTO_STATUS_ATIVA`.
Este plano usa esse mesmo padrão para `EquipeService` (seção 8, Fase 2).

**Testes de migration:** não existe, em nenhum lugar da suíte, um teste
que execute `alembic upgrade`/`downgrade` diretamente — os testes
constroem o schema via `Base.metadata.create_all(bind=engine)`
(`conftest.py`, fixture `session_factory`), usando SQLite em memória e os
models do SQLAlchemy diretamente, não as migrations. Isso significa que
**a suíte `pytest` não valida a migration Alembic em si** — apenas o
model. A migration precisa ser validada separadamente, contra PostgreSQL
real (`docker-compose.yml` confirma `postgres:16-alpine` como banco real;
SQLite é usado exclusivamente em teste). Esse ponto é tratado
explicitamente na seção 14 (Comandos de Validação) e na seção 12 (Riscos).

## 6. Estratégia de Migration

Duas migrations distintas, em momentos distintos do rollout — nunca uma
única migration que adicione a coluna já como `NOT NULL`:

**Migration 1 (Fase 1 — aditiva, TF-ORG-002.3A):**
- adicionar `equipes.departamento_id` como `String(36)`, **`nullable=True`**;
- criar `ForeignKeyConstraint(["departamento_id"], ["departamentos.id"])`,
  com nome explícito
  `fk_equipes_departamento_id_departamentos` e sem `ondelete` explícito —
  mesmo padrão sem ação de exclusão já usado para
  `usuario_departamentos.departamento_id` (Departamento nunca é excluído
  fisicamente; um `ondelete` não é necessário nem desejável aqui);
  criar o índice `ix_equipes_departamento_id`;
- **não alterar** a migration original
  `20260716_1a14_cria_tabela_equipes.py` — a nova migration é aditiva,
  com `revision = "20260719_1a17"` e
  `down_revision = "20260716_1a16"` (o `head` atual da cadeia, confirmado
  na seção 5), preservando a ordem cronológica real.
- `downgrade()` remove o índice, a FK pelo nome explícito
  `fk_equipes_departamento_id_departamentos` e a coluna, nessa ordem.

**Migration 2 (Fase 4 — enforcement, TF-ORG-002.3I):**
- só é criada **depois** que a Fase 3 (backfill, seção 7) confirmar que
  não existe nenhuma linha de `equipes` com `departamento_id IS NULL`;
- `op.alter_column("equipes", "departamento_id", existing_type=sa.String(length=36), nullable=False)`;
- `down_revision` será o `head` da cadeia no momento em que a Fase 4 for
  de fato implementada (não fixado por este plano, pois depende de quais
  migrations tiverem sido criadas por outras etapas até lá);
- `downgrade()` reverte para `nullable=True` — não recria dados.

Nenhuma das duas migrations desta etapa toca em qualquer outra tabela.
Nenhuma delas usa `batch_alter_table` — o banco real do projeto é
PostgreSQL (`docker-compose.yml`, serviço `taskfloww_db`,
`postgres:16-alpine`), que suporta `ALTER TABLE ... ADD COLUMN` e
`ALTER COLUMN ... SET NOT NULL` diretamente; `batch_alter_table` só seria
necessário para SQLite, que este projeto usa apenas em teste (via
`Base.metadata.create_all`, não via Alembic — seção 5).

## 7. Estratégia de Backfill

Fase 3 (TF-ORG-002.3H) — convergência das Equipes existentes por
**procedimento SQL controlado e auditável**. Esse é o único mecanismo
oficial de backfill desta etapa; não haverá PATCH, endpoint, comando de
aplicação ou chamada a service para alterar o Departamento de uma Equipe
legada.

1. **Inventariar** todas as `equipes` com `departamento_id IS NULL` por
   Empresa, através de uma consulta somente leitura (`SELECT id,
   empresa_id, codigo_interno, nome, status FROM equipes WHERE
   departamento_id IS NULL`). A consulta deve ser executada pelo cliente
   PostgreSQL disponível no ambiente, sem criar código de aplicação.
2. **Não inferir automaticamente** o Departamento a partir dos membros da
   Equipe (`usuario_equipes`), do nome da Equipe, ou de qualquer outro
   dado correlato. O Documento 13 (seção 7.3) exige que a associação seja
   auditável e explícita — uma inferência automática por heurística não
   atende a esse requisito e pode produzir vínculos organizacionais
   incorretos que seriam depois usados por Central de Tráfego, Kanban e
   relatórios (Documento 13, seções 12.7, 12.10, 12.11).
3. **Não usar IDs do mock de frontend** (`dep-atendimento`,
   `departamento-atendimento` etc., de `usuario-mock.ts`/`trafego-mock.ts`
   — Documento 15, seções 5.2 e 8.4) como se fossem `departamentos.id`
   reais. Esses IDs nunca existiram no backend; usá-los produziria uma FK
   inválida (rejeitada pela constraint da Fase 1) ou, pior, um
   `departamento_id` sintático mas semanticamente vazio caso alguém
   criasse um Departamento real só para "encaixar" o ID do mock — o que
   também é proibido: nenhum Departamento deve ser criado apenas para
   viabilizar o backfill sem representar uma decisão organizacional real.
4. **Processo explícito e auditável de associação:** para cada Equipe
   encontrada no inventário (passo 1):
   - um responsável humano com conhecimento da estrutura real da Empresa
     decide o Departamento correto, sem inferência por código;
   - o mapeamento explícito `equipe_id → departamento_id`, o ambiente, o
     responsável e o revisor ficam registrados como evidência operacional
     da execução;
   - antes da escrita, uma consulta confirma que Equipe e Departamento
     existem, pertencem à mesma Empresa e que o Departamento está ativo;
   - a escrita ocorre por `UPDATE` SQL controlado, dentro de transação,
     restringindo cada alteração pela identidade da Equipe e da Empresa;
   - a quantidade de linhas alteradas e a consulta final de pendências são
     registradas junto da evidência operacional;
   - uma segunda pessoa revisa o mapeamento e o resultado antes da
     conclusão, seguindo o fluxo do Documento 14, seção 11.

   O procedimento não emite evento de domínio de movimentação: ele
   estabelece o vínculo inicial de dados legados durante a convergência e
   não representa troca posterior de Departamento. A evidência operacional
   do backfill preserva a auditoria desta associação inicial sem antecipar
   a decisão pendente do Documento 13, seção 14.9.
5. **Ambientes sem Equipes existentes:** se o inventário do passo 1
   retornar zero linhas em um dado ambiente (esperado, por exemplo, em
   qualquer banco criado do zero após esta etapa, e possivelmente também
   no ambiente atual, já que o Documento 15 seção 5.5 confirma que não há
   consumidor real de `/equipes` hoje), a Fase 3 é considerada
   automaticamente concluída para esse ambiente — sem exigir nenhuma ação
   adicional além de confirmar e registrar a contagem zero. A Fase 4
   (enforcement) pode prosseguir imediatamente nesse caso.
6. **Critério de conclusão da Fase 3:** a mesma consulta do passo 1
   retorna zero linhas em todos os ambientes relevantes, com registro de
   quem validou o resultado.

## 8. Alterações por Camada

### 8.1 Model

`backend/app/models/equipe.py` — adicionar:

```python
departamento_id: Mapped[str | None] = mapped_column(
    ForeignKey("departamentos.id", name="fk_equipes_departamento_id_departamentos"),
    nullable=True,
)
```

com `relationship("Departamento")` adicional, seguindo o padrão já usado
para `empresa = relationship("Empresa")` na mesma classe. O campo
permanece `str | None` durante as Fases 1–3. Na Fase 4
(TF-ORG-002.3I), depois do enforcement de `NOT NULL` no banco, o model deve
ser promovido para:

```python
departamento_id: Mapped[str] = mapped_column(
    ForeignKey("departamentos.id", name="fk_equipes_departamento_id_departamentos"),
    nullable=False,
)
```

Essa convergência é obrigatória para que o schema criado por
`Base.metadata.create_all` nos testes represente a mesma nulabilidade
garantida pelo PostgreSQL.

### 8.2 Schemas

`backend/app/schemas/equipe.py`:

- `EquipeCreate` passa a exigir `departamento_id: UUID = Field(alias="departamentoId")`
  (sem default) — campo obrigatório desde a Fase 2, mesmo com a coluna do
  banco ainda nullable na Fase 1–3 (a obrigatoriedade é imposta pela
  aplicação antes de ser imposta pelo banco — expand/contract já usado
  implicitamente no restante do domínio organizacional).
- `EquipeUpdate` **não recebe** nenhum campo de Departamento — nem
  `departamentoId` nem `departamento_id` — em nenhuma fase desta etapa.
  Combinado com `extra="forbid"` (já existente) e com
  `PATCH_ALLOWED_FIELDS` (já existente na rota), qualquer tentativa de
  enviar `departamentoId` no `PATCH /equipes/{id}` é rejeitada com HTTP
  422 **sem exigir alteração na allowlist**. Na rota atual, a allowlist
  rejeita o campo antes do parse; em validações diretas do schema,
  `extra="forbid"` garante a mesma rejeição.
- `EquipeResponse` passa a expor
  `departamento_id: UUID | None = Field(default=None, alias="departamentoId")`
  durante as Fases 1–3 (pode ser `None` para Equipes legadas ainda não
  convergidas). Na Fase 4 (tarefa TF-ORG-002.3I), depois do `NOT NULL` no
  banco, o tipo é promovido para `UUID` (obrigatório), refletindo a
  garantia real do banco.

### 8.3 Repository

`backend/app/repositories/equipe_repository.py` — estender `list()` com
um novo parâmetro opcional `departamento_id: str | None = None`, aplicando
`statement.where(Equipe.departamento_id == departamento_id)` quando
informado. Mesmo padrão já usado para `status`. Esse único método
atende, ao mesmo tempo:

- o filtro de Equipes por Departamento na API (item 7 do escopo,
  tarefa TF-ORG-002.3G);
- a consulta que `DepartamentoService` usará para verificar Equipes
  ativas vinculadas antes de inativar um Departamento (item 9 do escopo,
  tarefa TF-ORG-002.3J) — chamando `equipe_repository.list(db,
  empresa_id=..., departamento_id=..., status="ativa", limit=1)`.

Nenhum novo método é necessário além dessa extensão de parâmetro — mesmo
princípio de reaproveitamento já aplicado no Documento 16 (seção 4.2, "Não
inventar arquitetura").

### 8.4 Service — `EquipeService`

`backend/app/services/equipe_service.py`:

- `list_equipes` recebe `departamento_id: str | None = None` e o encaminha
  sem alterar os demais filtros para
  `EquipeRepository.list(..., departamento_id=departamento_id)`.
- novo método privado `_ensure_departamento_valido(self, db, empresa_id,
  departamento_id)`, replicando exatamente o padrão de
  `UsuarioDepartamentoService` (seção 5): busca o Departamento por
  `departamento_repository.get_by_id`, e levanta `EquipeInvalidDataError`
  ("Departamento não encontrado ou inativo") quando o Departamento não
  existir, pertencer a outra Empresa, ou não estiver com `status ==
  STATUS_ATIVA` (reaproveitando `from app.services.departamento_service
  import STATUS_ATIVA as DEPARTAMENTO_STATUS_ATIVA`, mesmo import já
  usado por `UsuarioDepartamentoService`).
- `EquipeService.__init__` recebe uma nova dependência opcional
  `departamento_repository: DepartamentoRepository | None = None`.
- `create_equipe` chama `_ensure_departamento_valido` antes de persistir
  a Equipe, com o `departamento_id` vindo de `data.departamento_id`
  (`EquipeCreate`, agora obrigatório).
- `reativar_equipe` chama `_ensure_departamento_valido` com o
  `departamento_id` já persistido na Equipe, **antes** de alterar
  `status` para `ativa` — impedindo que uma Equipe seja reativada
  enquanto seu Departamento de referência estiver inativo/arquivado ou
  tiver deixado de existir (item 8 do escopo).
- `update_equipe` **não é alterado** para aceitar `departamento_id` —
  `EquipeUpdate` já não possui esse campo (seção 8.2), então nenhuma
  lógica adicional é necessária no service para bloquear a troca.
- `inativar_equipe` **não é alterado** por esta etapa — inativar uma
  Equipe não depende do Departamento (a relação inversa, Departamento
  dependendo de Equipes ativas, é tratada em `DepartamentoService`, seção
  8.6).
- `to_response` passa a incluir `departamentoId=equipe.departamento_id`.

### 8.5 API

`backend/app/api/routes/equipes.py`:

- `GET /equipes` ganha um novo query param opcional
  `departamento_id: UUID | None = Query(default=None,
  alias="departamentoId")`. Antes de chamar
  `equipe_service.list_equipes`, a rota converte o UUID informado para
  `str`, exatamente como já faz com `empresa_id`, e repassa
  `departamento_id=str(departamento_id) if departamento_id is not None
  else None`.
- `POST /equipes` **não muda de assinatura** — `EquipeCreate` já passa a
  exigir `departamentoId` no corpo (seção 8.2); a rota apenas repassa o
  payload validado, como já faz hoje.
- `PATCH /equipes/{id}` **não muda** — a ausência de `departamentoId` em
  `EquipeUpdate` (seção 8.2) já garante o bloqueio (item de escopo
  "PATCH não deve permitir trocar departamentoId nesta etapa"); nenhuma
  alteração de código é esperada em `PATCH_ALLOWED_FIELDS` ou em
  `handle_equipe_error`.
- `POST /equipes/{id}/reativar` **não muda de assinatura** — o novo
  cenário de erro (`EquipeInvalidDataError`, quando o Departamento não
  está mais válido) já é mapeado para HTTP 422 pelo `handle_equipe_error`
  existente (`isinstance(exc, EquipeInvalidEmpresaError |
  EquipeInvalidDataError)`), sem exigir alteração de rota.

### 8.6 DepartamentoService (Fase 5)

`backend/app/services/departamento_service.py`:

- `DepartamentoService.__init__` recebe uma nova dependência opcional
  `equipe_repository: EquipeRepository | None = None`.
- `inativar_departamento` substitui o comentário citado na seção 5 por
  uma terceira verificação, no mesmo padrão das duas já existentes:

```python
equipes_ativas = self.equipe_repository.list(
    db,
    empresa_id=departamento.empresa_id,
    departamento_id=departamento.id,
    status="ativa",
    limit=1,
)
if equipes_ativas:
    raise DepartamentoConflictError("Departamento possui Equipes ativas vinculadas")
```

- Preserva exatamente o comportamento já estabelecido pelo Documento 16
  para os outros dois casos: **estado do Departamento não é alterado**,
  **nenhum evento é publicado**, e o **HTTP 409 já existente**
  (`DepartamentoConflictError` → `handle_departamento_error`) é reusado
  sem qualquer mudança de contrato de rota.
- Com esta alteração, a seção 9.9 do Documento 13 ("Um Departamento não
  deve ser inativado silenciosamente quando possuir: Equipes ativas;
  vínculos ativos de Usuários; Head ativo; Gestores organizacionais
  ativos; objetos operacionais que dependam dele") passa a cobrir as
  dependências ativas identificadas até esta etapa: vínculos, sessões de
  trabalho e Equipes. Dependências operacionais adicionais descobertas
  futuramente devem ser registradas e tratadas sem afirmar que o inventário
  atual é necessariamente exaustivo.

### 8.7 Migrations

Ver seção 6. Resumo dos arquivos: uma migration nova na Fase 1
(TF-ORG-002.3A) e uma migration nova na Fase 4 (TF-ORG-002.3I). A
migration original de Equipe (`20260716_1a14_cria_tabela_equipes.py`)
**não é alterada** em nenhuma das duas.

### 8.8 Testes

Os testes devem acompanhar a subtarefa que introduz cada comportamento; as
tarefas K e L consolidam a cobertura acumulada, e M executa a regressão
final. Arquivos afetados:

- `backend/tests/test_equipe_model.py`: acompanha a inclusão nullable no
  model e, em TF-ORG-002.3I, sua promoção obrigatória para não-null.
- `backend/tests/test_equipes.py`: helpers `equipe_payload`/`make_equipe`
  passam a incluir `departamento_id`/`departamentoId`; novos casos de
  criação (sucesso, Departamento inexistente, Departamento de outra
  Empresa, Departamento inativo/arquivado), de reativação (mesmos
  cenários), de filtro por `departamentoId`, e de rejeição de
  `departamentoId` no PATCH.
- `backend/tests/test_departamentos.py`: novos casos de bloqueio de
  inativação com Equipe ativa vinculada, e de sucesso quando a única
  Equipe vinculada já está inativa/arquivada.
- `backend/tests/test_usuario_equipe_model.py`,
  `backend/tests/test_usuario_equipe_service.py` e
  `backend/tests/test_usuario_equipes.py`: seus construtores de Equipe
  devem informar `departamento_id` quando a TF-ORG-002.3I tornar o campo
  obrigatório no model.

## 9. Compatibilidade e Transição

- **Contrato de API de leitura:** `EquipeResponse` ganha um campo novo
  (`departamentoId`), o que é uma extensão aditiva e não quebra nenhum
  consumidor existente (não há consumidor real hoje — Documento 15, seção
  5.5).
- **Contrato de API de escrita (criação):** `POST /equipes` passa a
  exigir `departamentoId` no corpo. Isso é uma mudança de contrato — mas,
  como não há nenhum consumidor real de `/equipes` hoje (nem frontend, nem
  BFF, nem outro serviço — Documento 15, seções 5.4 e 5.5), essa mudança
  não quebra nada em produção. Isso deve ser reavaliado explicitamente se,
  entre o planejamento e a implementação desta etapa, surgir um novo
  consumidor real.
- **Contrato de API de escrita (atualização):** inalterado em assinatura;
  `departamentoId` continua fora de `EquipeUpdate`, preservando o
  comportamento atual de bloqueio de campos não permitidos.
- **Equipes existentes (dado):** nenhuma Equipe existente é apagada,
  renomeada ou tem seu `status` alterado por esta etapa. Equipes
  criadas antes da Fase 1 ficam com `departamento_id = NULL` até o
  backfill explícito da Fase 3 (seção 7).
- **Departamentos:** nenhuma alteração em `Departamento`, exceto a nova
  dependência opcional `equipe_repository` em `DepartamentoService` (seção
  8.6) e o novo cenário de bloqueio na inativação — que só se manifesta
  quando existir de fato uma Equipe ativa vinculada, cenário que só passa
  a existir depois desta etapa.
- **Usuários e vínculos:** nenhuma alteração em `usuarios`,
  `usuario_departamentos`, `usuario_cargos` ou `usuario_equipes`.
- **Frontend:** nenhuma alteração; `EquipesView.tsx` continua consumindo
  exclusivamente `equipe-mock.ts` (Documento 15, seção 5.4); esta etapa
  não altera esse comportamento nem exige que ele mude.
- **Rollback funcional:**
  - Fase 1 (migration aditiva): reversível por `alembic downgrade`, sem
    perda de dado (a coluna nova está vazia até a Fase 3).
  - Fases 2–3 (validações e backfill): reversíveis removendo a exigência
    de `departamentoId` em `EquipeCreate` e revertendo o código do
    service — nenhum dado é perdido, pois o backfill é aditivo
    (preenche `departamento_id`, não apaga nada).
  - Fase 4 (enforcement `NOT NULL`): só deve ser aplicada depois de
    confirmado o critério de conclusão da Fase 3 (seção 7, item 6); se
    for necessário reverter, `alembic downgrade` remove o `NOT NULL` sem
    perda de dado.
  - Fase 5 (bloqueio em `DepartamentoService`): reversível removendo a
    terceira verificação — mesmo princípio já usado no Documento 16.

## 10. Ordem Exata de Implementação

```text
TF-ORG-002.3A  Migration aditiva (departamento_id nullable + FK + índice)
        ↓
TF-ORG-002.3B  Model: campo departamento_id em Equipe + teste de model
        ↓
TF-ORG-002.3C  Repository/service: filtro departamento_id na listagem
        ↓
TF-ORG-002.3D  Schemas: departamentoId obrigatório em Create, exposto em Response
        ↓
TF-ORG-002.3E  Service: validação de Departamento na criação de Equipe
        ↓
TF-ORG-002.3F  Service: validação de Departamento na reativação de Equipe
        ↓
TF-ORG-002.3G  API: filtro departamentoId em GET /equipes + confirmação do PATCH
        ↓
TF-ORG-002.3H  Convergência: inventário e backfill explícito das Equipes legadas
        ↓
TF-ORG-002.3I  Enforcement: migration NOT NULL + promoção do schema de resposta
        ↓
TF-ORG-002.3J  DepartamentoService: bloqueio de inativação com Equipes ativas
        ↓
TF-ORG-002.3K  Consolidação dos testes de model/service/API de Equipe
        ↓
TF-ORG-002.3L  Consolidação dos testes de bloqueio em Departamento
        ↓
TF-ORG-002.3M  Regressão completa da suíte + validação real da migration
        ↓
TF-ORG-002.3N  Atualização de documentação e PROJECT_STATUS.md
```

TF-ORG-002.3J depende apenas de TF-ORG-002.3C (o filtro de repository já
existir) — tecnicamente poderia ser implementada em paralelo a D–I, mas
este plano a posiciona depois de H/I para que os testes de bloqueio
(TF-ORG-002.3L) já rodem contra um cenário onde `departamento_id` é
consistentemente exigido, evitando confusão entre "Equipe sem
Departamento por ainda não ter sido convergida" e "Equipe ativa vinculada
bloqueando a inativação do Departamento".

## 11. Divisão em Subtarefas

### TF-ORG-002.3A — Migration aditiva

**Objetivo:** adicionar `equipes.departamento_id` (nullable), FK para
`departamentos.id` e índice, sem alterar a migration original de Equipe.

**Arquivos:** novo arquivo em `backend/alembic/versions/` (`down_revision
= "20260716_1a16"`).

**Dependências:** nenhuma.

**Critério de conclusão:** ainda antes de qualquer backfill,
`alembic upgrade` aplica a coluna, a FK nomeada e o índice contra
PostgreSQL real; o round-trip expand (`upgrade da revisão A → downgrade
para 20260716_1a16 → upgrade da revisão A`) reverte e reaplica sem erro;
nenhuma outra tabela é tocada.

### TF-ORG-002.3B — Model

**Objetivo:** adicionar `departamento_id` e `relationship("Departamento")`
a `Equipe`.

**Arquivos:** `backend/app/models/equipe.py`;
`backend/tests/test_equipe_model.py`.

**Dependências:** TF-ORG-002.3A (a coluna precisa existir no schema real
para o model refletir a mesma estrutura, ainda que os testes usem
`Base.metadata.create_all`, que não depende da migration ter sido
aplicada, apenas do model estar correto).

**Critério de conclusão:** `Equipe.departamento_id` existe, é `str | None`,
e os testes de model comprovam que uma Equipe pode ser criada com e sem
esse valor durante a fase nullable.

### TF-ORG-002.3C — Repository

**Objetivo:** estender `EquipeRepository.list()` com filtro opcional
`departamento_id`; adicionar o mesmo argumento opcional a
`EquipeService.list_equipes()` e encaminhá-lo ao repository.

**Arquivos:** `backend/app/repositories/equipe_repository.py`;
`backend/app/services/equipe_service.py`;
`backend/tests/test_equipes.py`.

**Dependências:** TF-ORG-002.3B.

**Critério de conclusão:** `list(db, empresa_id=..., departamento_id=X)`
retorna apenas Equipes com esse `departamento_id`; chamado sem o
parâmetro, o comportamento é idêntico ao atual; o service encaminha o
filtro sem modificar os demais argumentos.

### TF-ORG-002.3D — Schemas

**Objetivo:** tornar `departamentoId` obrigatório em `EquipeCreate`,
expor em `EquipeResponse`, confirmar ausência em `EquipeUpdate`.

**Arquivos:** `backend/app/schemas/equipe.py`;
`backend/tests/test_equipes.py`.

**Dependências:** TF-ORG-002.3B.

**Critério de conclusão:** `EquipeCreate` sem `departamentoId` é rejeitado
por validação Pydantic (422); `EquipeResponse.departamentoId` aparece no
JSON de saída; `EquipeUpdate` continua sem o campo.

### TF-ORG-002.3E — Service: validação na criação

**Objetivo:** implementar `_ensure_departamento_valido` e chamá-lo em
`create_equipe`.

**Arquivos:** `backend/app/services/equipe_service.py`;
`backend/tests/test_equipes.py`.

**Dependências:** TF-ORG-002.3D.

**Critério de conclusão:** criar Equipe com Departamento inexistente,
de outra Empresa, ou inativo/arquivado levanta `EquipeInvalidDataError`
(422); criar com Departamento ativo da mesma Empresa persiste
`departamento_id` corretamente.

### TF-ORG-002.3F — Service: validação na reativação

**Objetivo:** chamar `_ensure_departamento_valido` em `reativar_equipe`
antes de alterar o `status`.

**Arquivos:** `backend/app/services/equipe_service.py`;
`backend/tests/test_equipes.py`.

**Dependências:** TF-ORG-002.3E.

**Critério de conclusão:** reativar uma Equipe cujo Departamento foi
inativado/arquivado ou removido levanta `EquipeInvalidDataError`, sem
alterar `status` da Equipe; reativar com Departamento ativo funciona
normalmente.

### TF-ORG-002.3G — API: filtro e confirmação do PATCH

**Objetivo:** adicionar `departamentoId` como query param de
`GET /equipes`; confirmar que `PATCH /equipes/{id}` rejeita
`departamentoId`.

**Arquivos:** `backend/app/api/routes/equipes.py`;
`backend/tests/test_equipes.py`.

**Dependências:** TF-ORG-002.3C, TF-ORG-002.3D.

**Critério de conclusão:** a rota converte o UUID de `departamentoId` para
`str` antes de chamar o service;
`GET /equipes?empresaId=...&departamentoId=...` filtra corretamente;
`PATCH /equipes/{id}` com `departamentoId` no corpo retorna 422
("Campos não permitidos no PATCH de Equipe").

### TF-ORG-002.3H — Convergência (backfill)

**Objetivo:** executar exclusivamente o procedimento SQL controlado e
auditável descrito na seção 7 em cada ambiente relevante, associando
`departamento_id` às Equipes legadas ou confirmando contagem zero.

**Arquivos:** nenhum arquivo de código — este é um procedimento
operacional, não uma alteração de repositório.

**Dependências:** TF-ORG-002.3A a TF-ORG-002.3G implantadas.

**Critério de conclusão:** consulta de inventário (seção 7, passo 1)
retorna zero linhas, com evidência do mapeamento, da execução e da
validação por duas pessoas quando houver dados alterados.

### TF-ORG-002.3I — Enforcement (`NOT NULL`)

**Objetivo:** criar a segunda migration (seção 6), tornando
`departamento_id` obrigatório no banco; promover
`EquipeResponse.departamento_id` para `UUID` não-opcional; promover
obrigatoriamente o model para `Mapped[str]` com `nullable=False`.

**Arquivos:** novo arquivo em `backend/alembic/versions/`;
`backend/app/schemas/equipe.py`; `backend/app/models/equipe.py`;
`backend/tests/test_equipe_model.py`;
`backend/tests/test_equipes.py`;
`backend/tests/test_usuario_equipe_model.py`;
`backend/tests/test_usuario_equipe_service.py`;
`backend/tests/test_usuario_equipes.py`.

**Dependências:** TF-ORG-002.3H concluída (critério de conclusão da Fase
3, seção 7, item 6).

**Critério de conclusão:** `alembic upgrade head` aplica `NOT NULL` sem
erro (porque não há mais linha nula); tentar inserir uma Equipe sem
`departamento_id` diretamente no banco falha por constraint; o model e
todos os construtores de teste refletem a obrigatoriedade; o round-trip
contract reverte somente o `NOT NULL` para a revisão expand e o reaplica,
sem remover a coluna nem destruir o backfill.

### TF-ORG-002.3J — DepartamentoService: bloqueio por Equipes ativas

**Objetivo:** substituir o comentário citado na seção 5 pela terceira
verificação em `inativar_departamento` (seção 8.6).

**Arquivos:** `backend/app/services/departamento_service.py`;
`backend/tests/test_departamentos.py`.

**Dependências:** TF-ORG-002.3C (filtro de repository).

**Critério de conclusão:** inativar um Departamento com Equipe `ativa`
vinculada levanta `DepartamentoConflictError` (409), sem alterar o estado
do Departamento nem publicar evento; inativar sem Equipes ativas
vinculadas continua funcionando.

### TF-ORG-002.3K — Testes de Equipe

**Objetivo:** consolidar e revisar a cobertura de model, service e API
adicionada junto às subtarefas B–G e I, completando somente lacunas dos
casos descritos na seção 8.8.

**Arquivos:** `backend/tests/test_equipe_model.py`;
`backend/tests/test_equipes.py`;
`backend/tests/test_usuario_equipe_model.py`;
`backend/tests/test_usuario_equipe_service.py`;
`backend/tests/test_usuario_equipes.py`.

**Casos mínimos:**
1. Criar Equipe com Departamento ativo da mesma Empresa → sucesso,
   `departamentoId` presente na resposta.
2. Criar Equipe sem `departamentoId` → 422 (validação Pydantic).
3. Criar Equipe com Departamento inexistente → 422
   (`EquipeInvalidDataError`).
4. Criar Equipe com Departamento de outra Empresa → 422.
5. Criar Equipe com Departamento inativo → 422.
6. Criar Equipe com Departamento arquivado → 422.
7. Reativar Equipe com Departamento ainda ativo → sucesso.
8. Reativar Equipe cujo Departamento foi inativado → 422, sem alterar
   `status` da Equipe.
9. `GET /equipes?departamentoId=X` retorna somente Equipes desse
   Departamento.
10. `PATCH /equipes/{id}` com `departamentoId` no corpo → 422.

**Dependências:** TF-ORG-002.3A a TF-ORG-002.3J.

**Critério de conclusão:** os dez casos presentes e todos os arquivos de
teste afetados passando no container oficial.

### TF-ORG-002.3L — Testes de Departamento (bloqueio por Equipes)

**Objetivo:** consolidar a cobertura do novo bloqueio de
`inativar_departamento` adicionada junto à TF-ORG-002.3J.

**Arquivos:** `backend/tests/test_departamentos.py`.

**Casos mínimos:**
1. Inativar Departamento com Equipe `ativa` vinculada → 409, sem alterar
   estado.
2. Inativar Departamento cuja única Equipe vinculada já está `inativa`
   ou `arquivada` → sucesso.
3. Inativar Departamento sem nenhuma Equipe, vínculo ou sessão → sucesso
   (regressão dos comportamentos já cobertos por TF-ORG-002.2).

**Dependências:** TF-ORG-002.3J.

**Critério de conclusão:** os três casos presentes e passando em
`pytest tests/test_departamentos.py` no container oficial.

### TF-ORG-002.3M — Regressão completa e validação real da migration

**Objetivo:** garantir ausência de regressão em toda a suíte e validar as
duas migrations contra PostgreSQL real (não apenas contra o model via
SQLite de teste — seção 5).

**Arquivos:** nenhum (execução).

**Dependências:** TF-ORG-002.3A a TF-ORG-002.3L.

**Critério de conclusão:** `pytest` completo sem falhas; a migration
expand já possui seu round-trip validado antes do backfill na
TF-ORG-002.3A; após o backfill, a validação da migration contract executa
`upgrade` da revisão de enforcement, `downgrade` somente até a revisão
expand e novo `upgrade` da revisão de enforcement. A coluna
`departamento_id` e os dados de backfill nunca são removidos nessa
validação.

### TF-ORG-002.3N — Documentação e status

**Objetivo:** atualizar `PROJECT_STATUS.md` registrando a conclusão da
TF-ORG-002.3 e a cobertura das dependências ativas identificadas na seção
9.9 do Documento 13 para Departamento (vínculos, sessões e Equipes). Não
alterar os Documentos 13, 14, 15, 16 ou 17.

**Arquivos:** `PROJECT_STATUS.md`.

**Dependências:** TF-ORG-002.3A a TF-ORG-002.3M concluídas e homologadas.

**Critério de conclusão:** `PROJECT_STATUS.md` reflete a conclusão, sem
reescrever histórico de etapas anteriores.

## 12. Riscos e Mitigação

- **Migration não validada pela suíte `pytest`:** como a suíte usa
  `Base.metadata.create_all` (SQLite em memória) em vez de Alembic
  (seção 5), um erro na migration real (ex.: nome de tabela/coluna
  incorreto, ordem de FK) só apareceria ao rodar `alembic upgrade head`
  manualmente. Mitigação: TF-ORG-002.3A valida o round-trip da migration
  expand antes do backfill; TF-ORG-002.3I/M valida apenas o round-trip da
  migration contract depois do backfill, sempre contra PostgreSQL real.
- **Quebra de contrato de criação (`POST /equipes` passa a exigir
  `departamentoId`):** risco baixo — nenhum consumidor real existe hoje
  (Documento 15, seção 5.5). Mitigação: reavaliar explicitamente se
  surgir consumidor real antes da implementação.
- **Backfill incorreto ou apressado:** associar Equipes ao Departamento
  errado por pressa ou automação indevida corrompe silenciosamente dados
  usados depois por Central de Tráfego e relatórios. Mitigação: seção 7
  define um único procedimento SQL controlado, proíbe inferência
  automática e exige evidência operacional e revisão por duas pessoas
  antes de considerar a Fase 3 concluída.
- **Enforcement (`NOT NULL`) aplicado antes do backfill estar completo:**
  quebraria a migration em produção (constraint violation) ou, pior,
  travaria Equipes legadas em estado inconsistente. Mitigação:
  TF-ORG-002.3I é explicitamente bloqueada por TF-ORG-002.3H (seção 10);
  a migration de enforcement só deve ser escrita depois de confirmado o
  critério de conclusão da Fase 3.
- **Confusão entre "Equipe sem Departamento por falta de backfill" e
  "Equipe válida sem Departamento" durante a janela de transição
  (Fases 1–3):** enquanto `departamento_id` for nullable no banco,
  qualquer consulta que assuma que toda Equipe tem Departamento
  (inclusive o próprio bloqueio de TF-ORG-002.3J) pode se comportar de
  forma inesperada para Equipes legadas ainda não convergidas — uma
  Equipe `ativa` sem `departamento_id` simplesmente não aparece em
  nenhum filtro por `departamento_id`, mas também não bloqueia a
  inativação de nenhum Departamento (porque não está vinculada a
  nenhum). Isso é aceitável durante a transição e deixa de ser possível
  após TF-ORG-002.3I.
- **Regressão de RBAC:** risco muito baixo — nenhuma alteração em
  `require_admin`, `require_admin_or_gestor`, `ensure_same_empresa` ou
  `ensure_resource_empresa`, em nenhuma das duas rotas (`/equipes`,
  `/departamentos`).
- **Índice `ix_equipes_departamento_id` degradando performance de
  escrita:** risco desprezível na escala atual do projeto (sem dado de
  produção real, Documento 15 seção 5.5); mesmo padrão de índice já usado
  em todas as outras FKs de Empresa/vínculo no projeto.
- **Divergência de vocabulário de status entre Equipe (`ativa`) e o
  filtro usado por `DepartamentoService`/`EquipeRepository.list`:** a
  verificação de TF-ORG-002.3J usa `status="ativa"` (grafia feminina, o
  vocabulário real de `Equipe.status`), não `"ativo"` (usado pelos
  vínculos de Usuário). Mitigação: já registrado corretamente neste plano
  (seção 8.6); qualquer implementação deve replicar exatamente essa
  grafia, sob risco de a verificação nunca encontrar resultado.

## 13. Critérios de Aceite

- [ ] `equipes.departamento_id` existe, com FK para `departamentos.id` e
      índice, aplicado por migration incremental que não altera a
      migration original de Equipe.
- [ ] Toda Equipe criada após a Fase 2 exige `departamentoId` válido
      (existente, ativo, mesma Empresa).
- [ ] Reativação de Equipe valida o Departamento da mesma forma que a
      criação.
- [ ] `PATCH /equipes/{id}` continua rejeitando `departamentoId`.
- [ ] `GET /equipes` filtra por `departamentoId` quando informado.
- [ ] `EquipeResponse` expõe `departamentoId`.
- [ ] `EquipeResponse.departamentoId` usa `UUID` e o filtro recebido pela
      rota é convertido para `str` antes de chegar ao service.
- [ ] Backfill das Equipes legadas concluído (ou contagem zero
      confirmada) antes de qualquer `NOT NULL` ser aplicado.
- [ ] `equipes.departamento_id` é `NOT NULL` no banco ao final da etapa,
      sem nenhuma Equipe ativa sem Departamento; o model usa
      `Mapped[str]` com `nullable=False`.
- [ ] `DepartamentoService.inativar_departamento` bloqueia Equipes
      ativas, preservando estado, não publicando evento em conflito, e
      reaproveitando o HTTP 409 já existente.
- [ ] Nenhum campo, tabela, contrato ou comportamento fora deste escopo
      foi alterado (ver seção 4).
- [ ] Isolamento por Empresa preservado em toda validação nova.
- [ ] RBAC sem regressão.
- [ ] Testes adicionados junto às subtarefas correspondentes e cobertura
      consolidada nas seções 11 (K, L), todos passando.
- [ ] Suíte completa do backend sem regressões.
- [ ] Migrations validadas contra PostgreSQL real: round-trip expand antes
      do backfill e round-trip apenas do contract depois do backfill, sem
      remover a coluna nem os dados convergidos.
- [ ] Os Documentos 13, 14, 15, 16 e este próprio Documento 17 permanecem
      inalterados durante a implementação.
- [ ] `PROJECT_STATUS.md` atualizado somente ao final, na tarefa
      TF-ORG-002.3N.
- [ ] Etapa revisada e homologada pelo fluxo oficial (Documento 14, seção
      11: Hudson → ChatGPT → Claude → Codex → ChatGPT → Hudson).

## 14. Comandos de Validação

```bash
# Testes (unitário/integração via SQLite em memória)
docker compose exec taskfloww_api pytest

# Testes dos arquivos afetados, com caminhos relativos ao /app do container
docker compose exec taskfloww_api pytest \
  tests/test_equipe_model.py \
  tests/test_equipes.py \
  tests/test_usuario_equipe_model.py \
  tests/test_usuario_equipe_service.py \
  tests/test_usuario_equipes.py \
  tests/test_departamentos.py

# Migration expand — validar na TF-ORG-002.3A, antes do backfill
docker compose exec taskfloww_api alembic upgrade 20260719_1a17
docker compose exec taskfloww_api alembic downgrade 20260716_1a16
docker compose exec taskfloww_api alembic upgrade 20260719_1a17
docker compose exec taskfloww_api alembic current

# Migration contract — validar após o backfill, sem remover a coluna
# Substituir <revisao_contract> pela revisão criada na TF-ORG-002.3I.
docker compose exec taskfloww_api alembic upgrade <revisao_contract>
docker compose exec taskfloww_api alembic downgrade 20260719_1a17
docker compose exec taskfloww_api alembic upgrade <revisao_contract>
docker compose exec taskfloww_api alembic current

# Inventário de backfill (Fase 3, seção 7, passo 1) — executar via cliente
# psql/ferramenta equivalente contra o banco real, não como parte do código:
# SELECT id, empresa_id, codigo_interno, nome, status
# FROM equipes
# WHERE departamento_id IS NULL;
```

## 15. Arquivos Previstos

**Novos:**
- `backend/alembic/versions/20260719_1a17_adiciona_departamento_id_equipes.py`
  (TF-ORG-002.3A)
- `backend/alembic/versions/<revisao>_torna_departamento_id_obrigatorio_equipes.py`
  (TF-ORG-002.3I)

**Alterados:**
- `backend/app/models/equipe.py`
- `backend/app/schemas/equipe.py`
- `backend/app/repositories/equipe_repository.py`
- `backend/app/services/equipe_service.py`
- `backend/app/api/routes/equipes.py`
- `backend/app/services/departamento_service.py`
- `backend/tests/test_equipe_model.py`
- `backend/tests/test_equipes.py`
- `backend/tests/test_usuario_equipe_model.py`
- `backend/tests/test_usuario_equipe_service.py`
- `backend/tests/test_usuario_equipes.py`
- `backend/tests/test_departamentos.py`
- `PROJECT_STATUS.md` (somente na tarefa final, TF-ORG-002.3N)

**Explicitamente não alterados por esta etapa:**
- `backend/app/models/usuario_equipe.py`, `usuario_departamento.py`,
  `usuario_cargo.py`, `usuario.py`, `departamento.py`, `cargo.py`,
  `agencia.py`, `empresa.py`, `cliente.py`, `sessao_trabalho.py`.
- `backend/app/services/usuario_equipe_service.py` e demais services de
  vínculo.
- `backend/alembic/versions/20260716_1a14_cria_tabela_equipes.py`
  (migration original de Equipe).
- Qualquer arquivo em `frontend/src/**`.
- Documentos 13, 14, 15 e 16.

## 16. Pendências Futuras

Registradas aqui para rastreabilidade, sem bloquear esta etapa:

- Distinção entre membro normal e convidado em `usuario_equipes`
  (`tipo_vinculo`) — TF-ORG-002.5 ou etapa própria de vínculos.
- Definição de domínio do papel `coordenador` em `usuario_equipes.papel`.
- Convergência do vocabulário de status entre `usuario_departamentos`,
  `usuario_cargos` e `usuario_equipes` — TF-ORG-002.5.
- Squads — fora do escopo do TF-ORG-002 inteiro.
- Integração real do frontend com `/equipes` e `/departamentos` — TF-ORG-002.8.
- Criação de BFF para Equipes e Departamentos — TF-ORG-002.8.
- Consumo da relação Equipe-Departamento por Projetos, Kanban, Agenda e
  Central de Tráfego — TF-ORG-002.13 (Documento 13) / etapas
  operacionais futuras.
- Mudança de Departamento de referência de uma Equipe já criada, com
  histórico de movimentação — Documento 13, seção 14.9, pendente de
  decisão formal.
- `sigla` em Equipe (presente hoje apenas em `EquipeDraft`, mock de
  frontend) — decisão de domínio própria, não coberta pelo Documento 13.
- Endpoint de arquivamento (`/equipes/{id}/arquivar`) — mesmo padrão já
  registrado como pendência compartilhada por todas as entidades de
  catálogo (Documento 16, seção 4.2).

## 17. Condições para Commit e Push

Este documento não autoriza, por si só, a execução de nenhuma das tarefas
listadas na seção 11. Nenhuma migration, alteração de model, schema,
repository, service, rota ou teste deve ser criada a partir deste plano
sem aprovação explícita adicional.

Commit e push, quando a implementação for aprovada, seguem
integralmente o fluxo oficial do Documento 14 (seção 11):

```text
Hudson → ChatGPT (arquitetura/revisão) → Claude (análise técnica) →
Codex (implementação) → ChatGPT (revisão) → Hudson (homologação)
```

Regras adicionais aplicáveis, já vigentes no projeto:

- nunca desenvolver diretamente na branch `main`;
- cada subtarefa (TF-ORG-002.3A–N) deve ser avaliada e homologada
  individualmente antes de avançar para a próxima, especialmente entre
  TF-ORG-002.3H (backfill) e TF-ORG-002.3I (enforcement), onde um avanço
  prematuro pode quebrar a migration em produção (seção 12);
  commit e push dependem de autorização explícita, tarefa a tarefa;
- a TF-ORG-002.3N (atualização de `PROJECT_STATUS.md`) só deve ocorrer
  depois de todas as demais tarefas homologadas.
