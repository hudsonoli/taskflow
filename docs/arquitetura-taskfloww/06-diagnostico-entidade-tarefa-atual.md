# 06 — Diagnóstico da Entidade Tarefa (Atual)

> Documento de auditoria. Não contém proposta de implementação nem alteração de código.
> Base: leitura direta do código em `/docker/taskfloww` nesta data, mais os documentos já existentes
> [`00-estado-atual.md`](./00-estado-atual.md), [`01-motores-centrais.md`](./01-motores-centrais.md),
> [`02-modelo-dados-futuro.md`](./02-modelo-dados-futuro.md), [`03-roadmap-implementacao.md`](./03-roadmap-implementacao.md).
> Este documento não repete o que já está coberto em `00`–`03`; ele aprofunda especificamente o recorte "Tarefa"
> e registra o que mudou no código desde a auditoria de `00` (2026-07-11) até hoje (2026-07-15, commit `710ab65`).
> Data desta auditoria: 2026-07-15.

## Legenda de classificação

| Rótulo | Significado |
|---|---|
| **implementado** | Existe e funciona de ponta a ponta (ainda que sobre mock) |
| **parcial** | Existe parte relevante, falta uma camada (backend, persistência, integração) |
| **mockado** | Existe como dado/tela estática, sem lógica de domínio real por trás |
| **ausente** | Nenhum vestígio no repositório |

---

## 0. Achado central: dualidade de nome "Demanda" vs. "Tarefa"

A entidade que o novo modelo funcional chama de **Tarefa** já existe hoje no código sob o nome **`Demanda`** — mas o nome usado para o usuário final, nas rotas e em parte da documentação, já é **"Tarefa(s)"**. Isso não é uma inconsistência acidental isolada, é um padrão espalhado por várias camadas:

| Camada | Nome usado | Evidência |
|---|---|---|
| Tipo TypeScript / entidade de código | `Demanda` | `frontend/src/types/demanda.ts` |
| Componentes | `Demanda*` (`DemandasView`, `DemandaFormSections`, `DemandaDetailsDrawer`...) | `frontend/src/components/demandas/` |
| Rota Next.js | `/tarefas` | `frontend/src/app/tarefas/page.tsx` |
| Item de menu | "Tarefas" | `frontend/src/components/layout/Sidebar.tsx:45` |
| Tela de configuração relacionada | "Tipos de **Tarefa**" (`/configuracoes/tipos-tarefa`) | `frontend/src/app/configuracoes/tipos-tarefa/page.tsx` |
| Campo em `Projeto` | `tipoTarefaId` / `tipoTarefaNome` (não `tipoDemandaId`) | `frontend/src/types/projeto.ts:42-43` |
| Documentação de banco conceitual | tabela `Tarefas` / `tarefas` | `docs/database-model.md`, `docs/skills/database-rules.md` |
| Título deste programa de trabalho | "TaskFloww" (Task = Tarefa) | — |

**Implicação prática para a migração**: não existe hoje nenhuma entidade chamada `Tarefa` a ser criada do zero — existe uma entidade `Demanda` madura (a mais completa do repositório, ver seção 3) que precisa ser **renomeada e estendida**, não recriada. Qualquer plano de migração precisa decidir explicitamente, como primeiro passo, se o nome de código passa a ser `Tarefa` (alinhando com o produto) ou se `Demanda` é mantido como nome técnico interno com "Tarefa" só como rótulo de UI — essa decisão não é tomada por este documento (ver `08`, subtarefa 1).

Neste documento, o termo **Demanda** é usado quando descreve código/tipo hoje existente, e **Tarefa** quando descreve o conceito do novo modelo funcional solicitado.

---

## 1. Como a entidade Tarefa (Demanda) está implementada hoje

### 1.1 Backend — inexistente

Confirmado por leitura direta: `backend/app/models/`, `backend/app/schemas/`, `backend/app/api/routes/`, `backend/app/services/`, `backend/app/repositories/`, `backend/app/domain/` e `backend/alembic/versions/` existem como diretórios **vazios** (só contêm `__pycache__`, não rastreado pelo Git). O único código Python versionado no backend é:

```
backend/main.py          (51 linhas — FastAPI + healthcheck)
backend/Dockerfile
backend/requirements.txt (fastapi, uvicorn, sqlalchemy, psycopg2-binary, python-multipart, pydantic, redis)
backend/AGENTS.md
```

`main.py` expõe apenas `GET /`, `GET /health`, `GET /status` (ping em Postgres/Redis). **Não existe nenhuma rota, model, schema ou migration relacionada a Demanda/Tarefa.** `backend/alembic/versions/` não tem nenhum arquivo de migration.

**Classificação: ausente.**

### 1.2 Banco de dados — inexistente

Nenhuma tabela de negócio existe. `docs/database-model.md` e `docs/skills/database-rules.md` citam `Tarefas`/`tarefas` como nome conceitual de tabela futura, sem colunas definidas, e **divergem entre si** na lista completa de tabelas (já registrado em `00-estado-atual.md`, seção 4).

**Classificação: ausente** (schema de negócio) / **documentado mas não implementado** (nome de tabela).

### 1.3 Frontend — a implementação real da Tarefa hoje

Tudo o que existe de "Tarefa" hoje vive em `frontend/`, como tipo TypeScript + mock + componentes React. É o módulo mais maduro do repositório entre os operacionais (mais maduro que Projetos).

**Tipo (`frontend/src/types/demanda.ts`, 93 linhas):**

```ts
Demanda {
  id, empresaId, agenciaId, projetoId, clienteId,
  codigoInterno, nome, briefing,
  status: DemandaStatus,               // 8 valores, ver 1.4
  prioridade: DemandaPrioridade,       // baixa | media | alta
  usuarioResponsavelIds: string[],
  departamentoResponsavelIds: string[],
  workflowEtapas: DemandaWorkflowEtapa[],
  etapaAtualId: string,
  prazoEtapaAtual: string,
  dataCriacao, dataInicio, dataFimPrevista,
  createdAt, updatedAt,
  historico: DemandaHistoricoEvento[],
}
```

`DemandaWorkflowEtapa` (linhas 19-27): `id, nome, ordem, usuarioResponsavelIds, departamentoResponsavelIds, prazoHoras, status`. É um **array embutido no objeto**, não uma entidade própria — cada demanda carrega sua cópia integral das etapas (sem referência a um template compartilhado em tempo real).

Dois tipos **declarados mas nunca usados em nenhum componente** (esboço declarativo, não funcional):
- `DemandaSessaoTrabalhoConceitual` (linha 40-49) — pensado para a futura Central de Tráfego.
- `DemandaVisibilidadeConceitual` (linha 51-55) — pensado para regra de visibilidade por etapa/perfil.

**Rota:** `frontend/src/app/tarefas/page.tsx` → renderiza `DemandasView` (2 linhas, sem lógica).

**Componentes (`frontend/src/components/demandas/`, 10 arquivos):**

| Arquivo | Papel |
|---|---|
| `DemandasView.tsx` | Orquestra estado (array `Demanda[]` em `useState`), busca, filtro de status, alternância lista/kanban, abre modal/drawer |
| `DemandasTable.tsx` | Listagem tabular |
| `DemandasToolbar.tsx` | Busca, filtro de status, alternância de modo de visão (`DemandasViewMode = "lista" \| "kanban"`) |
| `DemandasStats.tsx` | Cards de contagem agregada |
| `DemandasKanban.tsx` | Kanban **novo** (ver seção 5) |
| `DemandaKanbanColumn.tsx` / `DemandaKanbanCard.tsx` | Coluna e cartão do Kanban novo |
| `NovaDemandaModal.tsx` | Criação/edição (usa `DemandaFormDraft`) |
| `DemandaDetailsDrawer.tsx` | Painel de detalhe com 5 abas: **Dados, Briefing, Workflow, Responsáveis, Histórico** |
| `DemandaFormSections.tsx` (555 linhas) | As 5 seções acima, implementadas como funções exportadas (`DadosDemandaSection`, `BriefingDemandaSection`, `WorkflowDemandaSection`, `ResponsaveisDemandaSection`, `HistoricoDemandaSection`) |

**Mock (`frontend/src/lib/demandas-mock.ts`, 214 linhas):** reexporta helpers de `lib/projetos-mock.ts` (`resolveClienteProjetoNome`, `resolveDepartamentosProjetoNomes`, `resolveResponsaveisProjetoNomes`, `departamentosProjetoDisponiveis`, `responsaveisProjetoDisponiveis`, `generateId`, `generateCodigoInterno`) e define **apenas 3 demandas mock** (`demanda-1`, `demanda-2`, `demanda-3`), cada uma com workflow de 3 etapas fixas (Atendimento → Criação → Revisão).

**Classificação geral: parcial** — CRUD mock completo e funcional em memória (React state), sem nenhuma persistência, sem backend, sem banco.

### 1.4 Campos e "tabelas" atuais (schema de fato = tipo TypeScript)

Como não há banco real, o schema de fato hoje é o tipo TypeScript. Campos e valores de enum:

- `DemandaStatus`: `rascunho | planejada | em_execucao | pausada | bloqueada | aguardando_cliente | concluida | cancelada` (8 valores).
- `DemandaPrioridade`: `baixa | media | alta`.
- `DemandaWorkflowEtapaStatus`: `pendente | em_execucao | pausada | concluida` (4 valores — **sem** "bloqueada", diferente do status da demanda como um todo).

---

## 2. Arquivos que dependem da Tarefa (Demanda) hoje

### Backend
Nenhum arquivo depende de Demanda no backend — o backend não tem conhecimento de nenhuma entidade de negócio (seção 1.1).

### Frontend — tipos
- `frontend/src/types/demanda.ts` (definição própria).
- `frontend/src/types/projeto.ts:39-50` — `ProjetoModeloCampanhaItem` referencia `nomeDemanda`, `tipoTarefaId`, `tipoTarefaNome`, `workflowSugeridoId`, `responsavelOuSetorSugeridoId` (backlog de demandas por projeto — ver seção 3).
- `frontend/src/types/trafego.ts` — `TrafegoAgoraItem.demandaId`, `TrafegoCargaItem`, campos apontando para uma demanda por ID, mas **sem importar o tipo `Demanda`** (ver seção 6.3, conflito de mock isolado).

### Frontend — mocks/lib
- `frontend/src/lib/demandas-mock.ts` (fonte primária).
- `frontend/src/lib/projetos-mock.ts` — fornece `departamentosProjetoDisponiveis`, `responsaveisProjetoDisponiveis`, `tiposTarefaProjetoDisponiveis`, reaproveitados por `demandas-mock.ts`.
- `frontend/src/lib/trafego-mock.ts` — mock **paralelo e desconectado** com sua própria lista de "demandas" fictícias (`trafegoDemandasMock`), sem referenciar `demandasMock` real (ver seção 6.3).

### Frontend — componentes/páginas
- `frontend/src/app/tarefas/page.tsx` (rota).
- `frontend/src/components/demandas/*.tsx` (10 arquivos, seção 1.3).
- `frontend/src/components/kanban/*.tsx` (4 arquivos: `KanbanBoard.tsx`, `KanbanColumn.tsx`, `KanbanCard.tsx`, `TaskDetailModal.tsx`) — implementação **antiga**, com tipo próprio `KanbanTask` que **não é** `Demanda`; nenhuma página monta esse componente hoje (confirmado por busca: a única referência a `KanbanBoard` no projeto é dentro do próprio arquivo).
- `frontend/src/components/trafego/*.tsx` (8 arquivos) — consomem `TrafegoAgoraItem`/`TrafegoCargaItem`/`TrafegoResumo`, referenciam `demandaId` como string solta, não o tipo `Demanda`.
- `frontend/src/components/layout/Sidebar.tsx:45` — item de menu "Tarefas" → `/tarefas`.
- `frontend/src/components/layout/QuickCreateMenu.tsx` — não lido em detalhe nesta auditoria; candidato a depender de Demanda para criação rápida (**não confirmado**).

### Frontend — hooks
Nenhum hook customizado (`useDemandas`, `useTarefas` etc.) foi encontrado. Todo o estado é `useState` local dentro de `DemandasView.tsx`; não há camada de hook/serviço isolando acesso a dado, ao contrário do que `01-motores-centrais.md` (seção 3, riscos) recomenda para quando a API real existir.

### Configurações relacionadas (hoje desconectadas do tipo `Demanda`)
- `frontend/src/app/configuracoes/tipos-tarefa/page.tsx` — array `taskTypes` **100% hardcoded** dentro do componente (`name, department, defaultSla, workflow, status`), sem tipo TypeScript, sem mock, sem nenhuma relação de dado com `Demanda`.
- `frontend/src/app/configuracoes/workflows/page.tsx` — array `workflows` **100% hardcoded** (linha 11), com `stages: string[]` por workflow, sem nenhuma relação com `DemandaWorkflowEtapa`.
- `frontend/src/app/configuracoes/sla/page.tsx` e `frontend/src/app/configuracoes/prioridades/page.tsx` — não lidos linha a linha nesta auditoria, mas confirmados como telas hardcoded independentes em `00-estado-atual.md` (não confirmado se algo mudou desde 2026-07-11; recomenda-se reverificar antes da Fase 4 do `08`).

---

## 3. Relacionamento atual com Projeto, Cliente, Usuário, Departamento, Equipe/Squad, Workflow e Status

| Entidade | Relação hoje com Demanda | Evidência | Maturidade |
|---|---|---|---|
| **Projeto** | `Demanda.projetoId` (1 projeto → N demandas, via FK simples) | `types/demanda.ts:61` | Implementado (mock) |
| **Cliente** | `Demanda.clienteId` — **duplicado**, já que o cliente também é alcançável via `projeto.clienteId`; hoje os dois campos são preenchidos de forma independente (`DemandasView.tsx` grava ambos ao criar) | `types/demanda.ts:62`, `DemandasView.tsx:90-91` | Implementado, mas **redundante** — risco de inconsistência se `Demanda.clienteId` divergir do `Demanda.projeto.clienteId` (nenhuma validação encontrada) |
| **Usuário** | `Demanda.usuarioResponsavelIds: string[]` (nível demanda) + `DemandaWorkflowEtapa.usuarioResponsavelIds: string[]` (nível etapa) — dois arrays paralelos, sem um "responsável principal" distinto dos demais | `types/demanda.ts:68`, `:23` | Parcial — múltiplos responsáveis existem, mas sem hierarquia (principal vs. apoio) nem conceito de **participante** (alguém que acompanha sem ser responsável) |
| **Departamento** | `Demanda.departamentoResponsavelIds: string[]` (nível demanda e nível etapa) — mas `Departamento` **não existe como entidade própria**; é só `DepartamentoOption` (`id, nome, ativo`) referenciada informalmente em `types/usuario.ts:49-53`, e os IDs usados em `demandas-mock.ts` (`dep-atendimento`, `dep-criacao`...) nem batem com os IDs usados em `trafego-mock.ts` (`departamento-atendimento`, `departamento-criacao`...) | `types/demanda.ts:69`, `:24` | **Ausente como entidade real** — Fase 3.14 do `PROJECT_STATUS.md`, ainda não iniciada (ver seção 6.5) |
| **Equipe/Squad** | **Não existe relação alguma.** `Demanda` não tem `equipeId` nem `squadId` em nenhum nível (nem na demanda, nem na etapa). O único vestígio de "squad" no repositório inteiro é um campo de **texto livre** `UsuarioDraft.squad: string` (`types/usuario.ts:63`) — não é uma entidade, não é um ID, não tem cadastro próprio, e não é usado em nenhum filtro ou responsabilidade de Demanda | `types/usuario.ts:63` | **Ausente** — ver seção 7, conflito #1 |
| **Workflow** | Cada demanda carrega sua própria cópia embutida de etapas (`workflowEtapas: DemandaWorkflowEtapa[]`) — não referencia nenhum template de `/configuracoes/workflows` (que é hardcoded e paralelo) | `types/demanda.ts:70`, `WorkflowDemandaSection` em `DemandaFormSections.tsx:208-460` | Parcial (funcional na UI) / **duas fontes de verdade desconectadas** (já registrado em `01`, seção 1, "Riscos") |
| **Status** | `Demanda.status: DemandaStatus` (8 valores) é o campo usado por **dois Kanbans diferentes** de formas diferentes — o Kanban antigo (`KanbanBoard.tsx`) usa 4 colunas fixas não relacionadas a `DemandaStatus`; o Kanban novo (`DemandasKanban.tsx`) agrupa por `DemandaStatus` (6 colunas), **não** pela etapa de workflow (`etapaAtualId`) — ver seção 5 | `types/demanda.ts:1-9` | Parcial — existe, mas dois conceitos concorrentes decidem "onde a demanda aparece": `status` (campo livre editável em qualquer tela) vs. `etapaAtualId` (controlado pela seção Workflow) |

**Observação estrutural**: `Equipe` (`types/equipe.ts`) já tem `departamentoId` (uma equipe pertence a um departamento) e `membros: EquipeMembro[]`, mas **nenhuma Demanda referencia `Equipe`** — o campo mais próximo de "squad" no fluxo operacional de Demanda inexiste.

---

## 4. Funcionalidades: implementado / parcial / mockado / ausente

| Funcionalidade pedida no novo modelo | Classificação | Detalhe |
|---|---|---|
| Cliente agrupa Projetos | **implementado** (mock) | `Projeto.clienteId` |
| Projeto agrupa Tarefas | **implementado** (mock) | `Demanda.projetoId` |
| Tarefa = entrega/demanda ao cliente | **implementado** (conceito já é exatamente isso hoje) | `Demanda` |
| Workflow próprio por Tarefa | **parcial** | array embutido, sem template real (seção 3) |
| Etapas configuráveis e ordenadas | **implementado** (mock, por demanda) | `WorkflowDemandaSection` |
| Etapa atual determina posição no Kanban | **parcial / conflitante** | `etapaAtualId` existe, mas nenhum Kanban hoje é orientado por etapa (ver seção 5) |
| Etapa atual determina posição na pauta | **ausente** | não existe conceito de "pauta" no código (ver seção 6.1) |
| Responsável principal | **ausente** | só array plano `usuarioResponsavelIds`, sem distinção de "principal" |
| Múltiplos responsáveis | **implementado** (mock) | `usuarioResponsavelIds[]` |
| Participantes (não responsáveis) | **ausente** | nenhum campo equivalente |
| Departamento responsável | **parcial** | campo existe, entidade `Departamento` não existe |
| Squad responsável | **ausente** | só texto livre em `Usuario`, sem uso em Demanda (seção 3) |
| Tarefa individual / de departamento / de squad | **ausente** | não há discriminador de "tipo de titularidade" da tarefa |
| Checklist | **ausente** | confirmado, nenhuma ocorrência funcional |
| Comentários | **ausente** | confirmado, nenhum campo em `Demanda` nem aba na UI |
| Anexos | **ausente** em Demanda (existe só em `Projeto.arquivos`, mock estático) | `types/projeto.ts:19-27` |
| Prioridade | **implementado** (mock) | `DemandaPrioridade` |
| Prazo | **implementado** (mock, só na etapa atual — `prazoEtapaAtual`) | sem prazo por etapa individual visível fora do array `workflowEtapas` |
| Histórico | **parcial** | array mock só-leitura, sem geração automática por ação real (mesmo padrão em 5 entidades, ver `01`, seção 4) |
| Aprovação/ajuste/reprovação/refação como não-colunas-fixas | **conflitante com o código atual** | hoje `DemandaStatus` **é** um enum fechado tratado como coluna fixa no Kanban novo — ver seção 7, conflito #3 |
| Revisões/ciclos de ajuste na mesma etapa | **ausente** | `DemandaWorkflowEtapaStatus` não tem conceito de ciclo/contador de revisão |
| Nome de revisão configurável por empresa | **ausente** | nenhum campo de configuração por empresa relacionado a nomenclatura |
| Versionamento de workflow (mudança não altera tarefas já iniciadas) | **ausente** | como não há template real referenciado em tempo real (etapas são copiadas ad-hoc), o risco descrito não está mitigado por design — está apenas ausente por não existir a referência viva que causaria o problema |
| Histórico agregado no Projeto/Cliente | **ausente** | `Projeto.historico` e `Cliente.historico` são arrays independentes, preenchidos manualmente no mock, sem nenhuma agregação a partir de eventos de Demanda |

---

## 5. Kanban: três implementações paralelas (achado novo desde `00`)

A auditoria `00-estado-atual.md` (2026-07-11) descreveu **duas** implementações desconectadas de Kanban. Desde então (commits `1e9ab8f`, `36b7c55`, `68eded9`, `c281953`, todos de 2026-07-13), uma **terceira** foi adicionada e é a única hoje efetivamente acessível pela navegação:

| Implementação | Arquivos | Fonte de dado | Agrupamento | Montada em rota? |
|---|---|---|---|---|
| **Antiga (`kanban/`)** | `KanbanBoard.tsx`, `KanbanColumn.tsx`, `KanbanCard.tsx`, `TaskDetailModal.tsx` | Array `initialTasks` hardcoded, tipo próprio `KanbanTask` (campos `title, client, project, assignee...`) | 4 colunas fixas (`backlog, em-andamento, revisao, concluido`) | **Não** — órfã, só referenciada por si mesma |
| **Nova (`demandas/`)** | `DemandasKanban.tsx`, `DemandaKanbanColumn.tsx`, `DemandaKanbanCard.tsx` | `Demanda[]` real (mesmo array filtrado da tabela) | 6 colunas por `DemandaStatus` (`rascunho/planejada`, `em_execucao`, `pausada/bloqueada`, `aguardando_cliente`, `concluida`, `cancelada`) | **Sim** — via `DemandasView`, alternável por `DemandasToolbar` (`viewMode: "lista" \| "kanban"`) |
| **Central de Tráfego (`trafego/`)** | `TrafegoAgoraTable.tsx`, `TrafegoCargaDepartamentos.tsx`, `TrafegoCargaUsuarios.tsx` | `trafego-mock.ts`, com `trafegoDemandasMock` **fictício** (5 nomes de demanda que não existem em `demandasMock`) | Tabela/cards por sessão de trabalho, não Kanban propriamente | Sim, rota `/trafego` |

**Achado relevante**: a implementação nova (`DemandasKanban.tsx:85`) já contém, no próprio código, um comentário reconhecendo a limitação: *"A visão por pauta e departamento será conectada quando houver usuário autenticado e permissões reais."* — ou seja, o próprio autor do commit já sinalizou que Kanban por pauta/departamento é um requisito conhecido e pendente, coerente com o que este documento está formalizando agora.

O drag-and-drop (`@dnd-kit/core`) só existe na implementação **antiga e órfã** — o Kanban hoje efetivamente em uso (`DemandasKanban.tsx`) é **somente leitura**, com o rótulo explícito "Somente leitura" na própria UI (linha 89).

---

## 6. Impacto sobre pautas, listas, carga de trabalho e permissões

### 6.1 Minha Pauta / Pauta do Departamento / Pauta da Squad / Pauta do Head / Pauta Geral

**Classificação: ausente**, em todas as variantes. Nenhuma ocorrência do termo "pauta" como conceito de tela ou filtro de escopo foi encontrada em `frontend/src/app/`, `frontend/src/components/` (fora de comentários avulsos em `DemandasKanban.tsx` e `NovaDemandaModal.tsx`, sem lógica associada) ou no menu (`Sidebar.tsx`). O item de menu existente é um único "Tarefas" (`/tarefas`), sem sub-modo por escopo. O requisito mais próximo já documentado é a regra de visibilidade "colaborador vê só a etapa atual" (`docs/requirements/projetos-demandas-dashboard.md`, seção 3.6, e `01-motores-centrais.md`, seção 1) — mas isso nunca foi implementado como filtro de tela, só como texto de requisito.

Não há, hoje, nenhum conceito de "Head" (perfil, papel ou escopo) em lugar nenhum do código — nem em `PerfilAcesso` (seção 6.5), nem em `EquipeAcesso`, nem em `DepartamentoOption`.

### 6.2 Kanban

Ver seção 5 — hoje fragmentado em 3 implementações, nenhuma delas orientada por escopo de pauta, nenhuma com filtro por cliente/projeto/responsável/prioridade/atraso/etapa (os filtros descritos em `docs/requirements/projetos-demandas-dashboard.md`, seção 4, e `01`, seção 2, continuam **ausentes** em todas as três implementações).

### 6.3 Lista

`DemandasTable.tsx` é a lista principal, funcional sobre o mock, com busca (`matchesDemanda`, `DemandasView.tsx:42-53`) e filtro de status (`DemandaStatusFiltro`). Não há filtro por projeto, cliente, responsável, departamento ou squad na lista — só busca textual livre e filtro de status.

### 6.4 Carga de trabalho

O conceito mais próximo de "carga de trabalho" já implementado é a **Central de Tráfego** (`/trafego`), que evoluiu significativamente desde `00-estado-atual.md` (que a classificava como "documentado mas não implementado, só um tipo comentado"). Hoje existe:
- `types/trafego.ts`: `TrafegoAgoraItem` (sessão ativa por demanda/usuário/departamento/etapa), `TrafegoCargaItem` (agregação por usuário ou departamento: sessões ativas, demandas distintas, tempo ativo total), `TrafegoResumo`.
- `components/trafego/` (8 componentes: header, filtros, tabela "agora", cards de carga por usuário/departamento, card de tempo operacional).
- Rota `/trafego`, item de menu "Tráfego" na seção "Operação" do `Sidebar.tsx:51`.

**Conflito crítico**: `lib/trafego-mock.ts` define seu **próprio** conjunto de usuários, departamentos e "demandas" (`trafegoUsuariosMock`, `trafegoDepartamentosMock`, `trafegoDemandasMock`) — nomes e IDs que **não existem** em `demandas-mock.ts`, `usuario-mock.ts` ou `projetos-mock.ts`. É, na prática, um quarto universo de dado mock isolado (mesmo padrão de erro já diagnosticado para o Kanban antigo em `01`). Squad não é um eixo de agrupamento em nenhum lugar da Central de Tráfego (`TrafegoAgrupamentoTipo = "usuario" | "departamento"`, sem `"equipe"` nem `"squad"` — `types/trafego.ts:7`).

### 6.5 Permissões por perfil, escopo e usuário

**Classificação: parcial (perfil) / ausente (escopo e usuário).**

- `frontend/src/lib/access-control.ts` define `PerfilAcesso` com **9 valores**: `Owner, SuperAdmin, Admin, Diretoria, Gerente, Gestor, Financeiro, Operador, Cliente` — que **diverge** da lista de 6 perfis documentada em `CLAUDE.md`/`PROJECT_STATUS.md` (`SuperAdmin, Admin, Diretoria, Gestor, Operador, Cliente`): adiciona `Owner`, `Gerente` (distinto de `Gestor`) e `Financeiro`, sem que essa divergência esteja registrada em nenhum documento.
- Essa camada hoje só resolve **duas** decisões binárias de visibilidade: `hasAdministrativeAccess` (aba Administrativa de Cliente) e `hasDashboardAccess` (item Dashboard da Sidebar). **Nenhuma** delas está relacionada a Tarefa/Demanda.
- Não existe nenhuma checagem de permissão em `DemandasView.tsx`, `DemandaFormSections.tsx`, `DemandaDetailsDrawer.tsx` ou em qualquer componente de Demanda — qualquer usuário mockado vê e edita qualquer campo.
- **Escopo** (visibilidade restrita por cliente/projeto/departamento/squad do próprio usuário) não existe em nenhuma forma.
- **Permissão por usuário individual** existe como estrutura de dado (`UsuarioDraft.permissoes: PermissaoItem[]`, `types/usuario.ts:1-10` — `grupo, modulo, leitura, escrita, excluir, aprovar, extras`), mas **não é lida em nenhum componente** — é puramente decorativa hoje (mesmo achado do `00`, seção 10, ainda válido).

### 6.6 Permissões temporárias

**Classificação: ausente.** Nenhuma menção, campo, tipo ou tela relacionada a permissão com validade/expiração foi encontrada em nenhum lugar do repositório.

---

## 7. Conflitos entre a implementação atual e o novo modelo funcional

1. **Squad não é uma entidade.** O novo modelo exige que uma Tarefa possa ter squad responsável e suportar "tarefa de squad" como modalidade própria. Hoje `squad` é um campo de texto livre em `Usuario` (`types/usuario.ts:63`), o que **viola diretamente** a regra de `CLAUDE.md` ("nunca usar nome como chave... sempre utilizar IDs para relacionamentos") já no ponto de partida. Não há cadastro de Squad, não há `squadId` em `Equipe`, `Departamento` ou `Demanda`.

2. **Não existe distinção entre Responsável principal, Responsáveis e Participantes.** Hoje só há um array plano (`usuarioResponsavelIds`). O novo modelo pede três papéis distintos (principal, múltiplos responsáveis, participantes) — nenhum dos três é modelado com essa granularidade hoje.

3. **Aprovação/ajuste/reprovação/refação já são tratados como valores fechados de enum, na prática usados como "colunas".** O novo modelo explicitamente proíbe isso ("não devem ser tratados apenas como colunas fixas... uma tarefa pode passar por várias revisões ou ciclos de ajuste na mesma etapa"). O Kanban novo (`DemandasKanban.tsx`) já reforça esse padrão indesejado ao agrupar por `DemandaStatus` — se "aguardando_cliente" e "bloqueada" viram colunas fixas de Kanban, qualquer ciclo de revisão dentro da mesma etapa fica sem lugar para existir no modelo atual.

4. **Não há versionamento de workflow.** O novo modelo exige que alterar o modelo de workflow não altere silenciosamente tarefas já iniciadas. Hoje isso "funciona por acidente": cada `Demanda.workflowEtapas` é uma cópia solta, sem vínculo vivo com nenhum template — então nada realmente propaga mudança nenhuma. O risco que o requisito quer evitar não está mitigado por design (não existe o mecanismo de propagação vivo para ser controlado); ele simplesmente não existe ainda, porque o template real (`/configuracoes/workflows`) está desconectado de qualquer instância real.

5. **Nome de revisão configurável por empresa não existe.** Toda label hoje é hardcoded em português, direto no componente (`workflowEtapaStatusLabels` em `lib/demandas-mock.ts:57-65`, `statusDemandaLabels` na mesma origem) — não há conceito de configuração por empresa para nomenclatura de nenhum campo.

6. **Kanban orientado por `DemandaStatus`, não por etapa de workflow.** O novo modelo é explícito: "a etapa atual determina onde a tarefa aparece no Kanban e na pauta". O Kanban hoje ativo (`DemandasKanban.tsx`) agrupa por `status`, um campo independente de `etapaAtualId` — os dois podem divergir livremente hoje (nada impede uma demanda com `status: "em_execucao"` e `etapaAtualId` apontando para uma etapa já `"concluida"`).

7. **Não há conceito de pauta em nenhuma forma** (seção 6.1) — toda a hierarquia pedida (Minha Pauta, Pauta do Departamento, Pauta da Squad, Pauta do Head, Pauta Geral) precisa ser criada do zero, tanto como consulta/filtro quanto como tela.

8. **Histórico não agrega no Projeto nem no Cliente.** `Projeto.historico` e `Cliente.historico` são listas independentes preenchidas manualmente no mock — nenhuma automação hoje conectaria eventos de Demanda a esses históricos, mesmo que o Motor de Eventos (`01`, seção 4) viesse a existir sem esse requisito ser adicionado explicitamente ao seu design.

9. **Checklist, comentários e anexos em Tarefa: inexistentes.** Confirmado (seção 4) — os três são requisitos explícitos do novo modelo e hoje têm zero implementação em Demanda (anexo existe parcialmente só em Projeto).

10. **Quatro conjuntos de mock desconectados usando IDs de departamento diferentes**: `dep-atendimento` (`projetos-mock.ts`/`demandas-mock.ts`) vs. `departamento-atendimento` (`trafego-mock.ts`) vs. `DepartamentoOption` solto em `usuario.ts` sem lista mock própria centralizada. Qualquer migração de Tarefa que envolva Departamento precisa primeiro decidir uma fonte única — hoje não existe.

11. **Perfis de acesso divergentes entre documentação e código** (seção 6.5) — `PerfilAcesso` no código já tem 9 valores; qualquer regra de permissão por perfil sobre Tarefa desenhada a partir de `CLAUDE.md` (6 perfis) ficaria desalinhada com o que o código já usa hoje.

---

## 8. Confirmação de escopo desta auditoria

- Nenhum arquivo de código foi alterado.
- Nenhum comando de escrita foi executado (apenas `ls`, `find`, `grep`, `wc`, `git log`, leitura de arquivos).
- Este documento cobre exclusivamente leitura; a lista completa de arquivos lidos está registrada na resposta de fechamento desta tarefa.
