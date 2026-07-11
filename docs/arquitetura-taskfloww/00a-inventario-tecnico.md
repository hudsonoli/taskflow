# 00a — Inventário Técnico Completo

> Documento de auditoria. Nenhuma funcionalidade foi implementada, nenhum arquivo existente foi alterado, nenhuma migration foi criada.
> Todo o projeto foi lido antes da escrita deste documento (frontend, backend, docs, docker, configuração). Onde uma leitura foi impedida por permissão de sistema, isso é registrado explicitamente em vez de suposto.
> Este documento complementa e atualiza pontualmente [`00-estado-atual.md`](./00-estado-atual.md): desde aquele documento, um novo módulo de Workflow real (mock) foi commitado (`80ba94f feat(workflow): adiciona motor de workflow mock`), detalhado aqui.
> Data da auditoria: 2026-07-11.

---

# 1. Estrutura geral do projeto

## Árvore resumida

```
/docker/taskfloww
├── AGENTS.md
├── CLAUDE.md
├── PROJECT_STATUS.md
├── docker-compose.yml
├── db_data/                    (volume Postgres — sem permissão de leitura para este usuário)
├── redis/                      (volume Redis — appendonlydir sem permissão de leitura)
├── docker/
│   ├── api/                    (vazio)
│   └── frontend/               (vazio)
├── designs/
│   ├── boxx/                   (vazio)
│   └── iclips/                 (vazio)
├── legacy/v1/                  (documentação da versão anterior, 5 arquivos .md)
├── docs/
│   ├── CLAUDE.md
│   ├── database-model.md
│   ├── skills/                 (7 arquivos: architecture, coding-standards, database-rules,
│   │                            taskflow-rules, ui-boxx, git-workflow, produto)
│   ├── agents/                 (7 arquivos: perfis de agente de IA para o projeto)
│   ├── requirements/
│   │   └── projetos-demandas-dashboard.md
│   └── arquitetura-taskfloww/  (esta pasta — 00, 00a, 01, 02, 03)
├── backend/
│   ├── main.py                 (único arquivo de código do backend)
│   └── AGENTS.md
└── frontend/
    ├── package.json, tsconfig.json, next.config.ts, eslint.config.mjs, postcss.config.mjs
    ├── AGENTS.md, CLAUDE.md, README.md
    └── src/
        ├── app/                (rotas Next.js App Router)
        ├── components/         (layout, dashboard, kanban, workflows, demandas, projetos,
        │                        usuarios, clientes, equipes, fornecedores, grupos-clientes,
        │                        agenda, conta, design-system, workspace, ui)
        ├── lib/                 (mocks e helpers, 9 arquivos *-mock.ts)
        └── types/               (9 arquivos *.ts)
```

Não existe `frontend/src/hooks/` nem `frontend/src/context/` nem qualquer diretório de estado global — apesar de `docs/skills/architecture.md` documentar `hooks/` como parte da estrutura esperada, o diretório nunca foi criado.

## Módulos existentes

Cadastro/operacional: Usuários, Clientes, Grupos de Clientes, Equipes, Fornecedores, Agências (config), Projetos, Demandas (Tarefas), Workflow (motor mock por demanda + tela de configuração hardcoded, desconectados entre si — ver seção 9), Kanban (isolado, sem rota), Agenda (Central de Contatos), Dashboard, Relatórios (placeholder), Conta (Perfil, Notificações, Alterar Senha), Design System (vitrine interna de componentes).

## Organização do backend

Um único arquivo, `backend/main.py` (51 linhas). Não há pastas `models/`, `schemas/`, `routers/`, `services/`, `core/` — o conceito de "organização do backend" hoje é inexistente; existe apenas um script que sobe um `FastAPI()`, cria um `engine` SQLAlchemy e um client Redis, e define 3 rotas de healthcheck.

## Organização do frontend

Segue o padrão documentado em `docs/skills/architecture.md` e `CLAUDE.md`:
- `src/app/**/page.tsx` — apenas roteamento, delega para um componente `View`.
- `src/components/<modulo>/` — `View`, `Table`/`List`, `Modal`, `FormSections`, `Stats`, `Toolbar`, `DetailsDrawer` por módulo.
- `src/components/ui/` — design system interno (átomos): `Badge`, `Button`, `Card`, `EmptyState`, `EntityFieldRow`, `EntitySidePanel`, `EntitySummaryPanel`, `Input`, `Modal`, `MultiSelect`, `PageHeader`, `Section`, `Select`, `Switch`, `Tabs`, `Textarea`.
- `src/components/workspace/` — framework reutilizável de página operacional: `WorkspacePage`, `WorkspaceSection`, `WorkspaceStats`, `WorkspaceTable`, `WorkspaceToolbar`, `WorkspaceEmptyState`.
- `src/lib/*-mock.ts` — dado mock + helpers de resolução de nome/geração de ID por módulo.
- `src/types/*.ts` — contratos de dados por módulo.

---

# 2. Stack utilizada

| Camada | Tecnologia | Versão (conforme `package.json`/`docker-compose.yml`) |
|---|---|---|
| Linguagem frontend | TypeScript | `^5` |
| Linguagem backend | Python | `3.12-slim` (imagem Docker) |
| Framework frontend | Next.js (App Router) | `16.2.10` |
| Biblioteca de UI | React / React DOM | `19.2.4` |
| Framework backend | FastAPI | instalado via `pip install` inline no `docker-compose.yml`, sem versão fixada |
| Servidor ASGI | Uvicorn (`[standard]`) | sem versão fixada |
| ORM | SQLAlchemy | instalado via pip, sem versão fixada; **nenhum model definido** |
| Banco de dados | PostgreSQL | `postgres:16-alpine` (imagem Docker); **sem nenhuma tabela de negócio** |
| Cache/fila | Redis | `redis:7-alpine`; usado só via `redis.from_url` + `ping()` no healthcheck |
| Autenticação | — | **inexistente** (ver seção 6) |
| Estilo | Tailwind CSS | `^4`, via `@tailwindcss/postcss` |
| Drag-and-drop | `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` | `^6.3.1` / `^10.0.0` / `^3.2.2` |
| Ícones | `lucide-react` | `^1.23.0` |
| Utilitário de classe CSS | `clsx` | `^2.1.1` |
| Lint | ESLint + `eslint-config-next` | `^9` / `16.2.10` |
| Infraestrutura | Docker Compose | `version: "3.8"`, 4 serviços |

Observações relevantes de dependência:
- `zod` aparece em `frontend/node_modules/` mas **não é dependência direta** do `package.json` — é transitivo (provável dependência de tooling). Nenhum arquivo em `frontend/src` importa `zod`; validação de formulário hoje é feita manualmente ou não é feita.
- Não há biblioteca de gerenciamento de estado global (`zustand`, `redux`, `jotai`, React Context) em nenhum lugar do código — confirmado por busca (`createContext`, `useContext`, `Provider`) sem nenhuma ocorrência em `frontend/src`.
- Não há biblioteca de gráfico instalada (`chart.js`, `recharts`, `victory` etc.) apesar de `DashboardChart.tsx` conter um comentário `{/* TODO: integrar Chart.js */}`.
- Não há biblioteca de teste instalada (`jest`, `vitest`, `@testing-library/*`, `playwright`, `pytest`) em nenhum dos dois lados do projeto.

---

# 3. Backend

Há um único módulo de fato: o próprio `backend/main.py`. Analisado como módulo único:

### Módulo: API raiz (`backend/main.py`)

- **Finalidade**: expor um serviço FastAPI mínimo para validar que a infraestrutura (API, Postgres, Redis) está de pé — não implementa nenhuma regra de negócio.
- **Arquivos principais**: `backend/main.py` (única fonte); `backend/AGENTS.md` (regras de convenção para quando o backend crescer, hoje sem código a que se aplicar de fato).
- **Dependências**: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg2-binary`, `python-multipart`, `pydantic`, `redis` — todas instaladas via `pip install` inline no comando do serviço `taskfloww_api` em `docker-compose.yml` (não há `requirements.txt` nem `pyproject.toml` no repositório — a lista de dependências só existe dentro do `docker-compose.yml`).
- **Rotas**:
  - `GET /` → `{"message": "Bem-vindo ao Taskfloww API"}`
  - `GET /health` → `{"status": "ok"}`
  - `GET /status` → testa `SELECT 1` no Postgres e `PING` no Redis, retornando o status de cada um.
- **Serviços**: nenhum — a lógica de conexão (`engine = create_engine(...)`, `redis_client = redis.from_url(...)`) está no escopo do módulo, junto com as rotas, sem nenhuma camada de serviço separada.

Não há mais nenhum módulo backend a analisar — todo o restante do backend descrito nos documentos de arquitetura (`01`, `02`, `03`) é proposta futura, não código existente.

---

# 4. Frontend

Organizado por módulo, com páginas, componentes, hooks, providers, stores e layouts (quando existentes — a maioria dos módulos não tem hook/provider/store próprio, pois todo estado é local via `useState` dentro do componente `View`).

## Dashboard

- **Páginas**: `frontend/src/app/page.tsx` → `DashboardView`.
- **Componentes**: `components/dashboard/DashboardView.tsx`, `DashboardGreeting.tsx`, `DashboardStats.tsx` (números hardcoded: `tarefas: 128, projetos: 24, clientes: 86, sla: 97`), `DashboardAgenda.tsx`, `DashboardActivities.tsx`, `DashboardChart.tsx` (placeholder visual, `{/* TODO: integrar Chart.js */}`), `DashboardShortcuts.tsx`, `StatCard.tsx`.
- **Hooks/Providers/Stores**: nenhum.

## Tarefas / Demandas

- **Páginas**: `app/tarefas/page.tsx` → `DemandasView`.
- **Componentes**: `components/demandas/DemandasView.tsx`, `DemandasStats.tsx`, `DemandasTable.tsx`, `DemandasToolbar.tsx`, `NovaDemandaModal.tsx`, `DemandaDetailsDrawer.tsx`, `DemandaFormSections.tsx` (contém `DadosDemandaSection`, `BriefingDemandaSection`, `WorkflowDemandaSection` — este último agora delega para `WorkflowEditor` — , `ResponsaveisDemandaSection`, `HistoricoDemandaSection`).
- **Estado**: `useState<Demanda[]>(demandasMock)` local em `DemandasView` — sem persistência entre navegações (ver seção 9).

## Workflow (motor mock por demanda) — módulo novo desde o último inventário

- **Componentes**: `components/workflows/WorkflowEditor.tsx` (orquestrador principal — aplica template, transiciona etapa, bloqueia/desbloqueia, reordena), `WorkflowStepCard.tsx` (card de etapa editável), `WorkflowTemplateSelector.tsx` (seleção + aplicação de template), `WorkflowTransitionControls.tsx` (avançar/voltar/bloquear/desbloquear), `WorkflowHistory.tsx` (lista de transições).
- **Tipos**: `frontend/src/types/workflow.ts` — `WorkflowEtapa`, `WorkflowEtapaStatus` (`pendente|atual|concluida|bloqueada` — vocabulário **diferente** do antigo `DemandaWorkflowEtapaStatus`, que existia antes da mudança e usava `pendente|em_execucao|pausada|concluida`), `WorkflowTemplate`, `WorkflowInstancia`, `WorkflowTransicaoHistorico`, `WorkflowVisibilidadeConceitual`, `WorkflowSessaoTrabalhoConceitual` (comentário no código: "Preparação conceitual para Central de Tráfego futura. Não há SessaoTrabalho real nesta fase.").
- **Mock**: `frontend/src/lib/workflows-mock.ts` — 3 templates reais (`Criação padrão`, `Mídia paga`, `Conteúdo`), cada um com 4–6 etapas com responsáveis/prazo próprios; funções `cloneWorkflowEtapas`, `createWorkflowInstanceFromTemplate`, `createWorkflowInstanceFromSteps`, `createWorkflowTransitionHistory`.
- **Consumo**: `Demanda.workflow: WorkflowInstancia` e `Demanda.workflowHistorico: WorkflowTransicaoHistorico[]` (`types/demanda.ts`) — cada Demanda agora carrega sua própria instância de workflow, clonada de um template no momento da criação (`DemandasView.tsx`, função `createDemandaFromDraft`).
- **Ponto de atenção direto**: `frontend/src/app/configuracoes/workflows/page.tsx` **não foi alterado** por este commit e continua sendo um componente 100% hardcoded, com 3 workflows fictícios **diferentes** dos 3 templates reais de `workflows-mock.ts` (`Marketing Padrão`/`Produção Gráfica`/`Clínica Clare` vs. `Criação padrão`/`Mídia paga`/`Conteúdo`) e vocabulário de etapa próprio (`stages: string[]`, sem relação com `WorkflowEtapa`). O sistema hoje tem **duas fontes de verdade de workflow ativas e desconectadas ao mesmo tempo** — detalhado na seção 9.

## Kanban

- **Componentes**: `components/kanban/KanbanBoard.tsx`, `KanbanColumn.tsx`, `KanbanCard.tsx`, `TaskDetailModal.tsx` — **sem alteração** desde o último inventário; segue isolado, com tipo próprio `KanbanTask` e array `initialTasks` hardcoded dentro do próprio `KanbanBoard.tsx`. Nenhuma página monta este componente. `DemandasView.tsx` (linha da `PageHeader`) já reconhece isso textualmente: *"O Kanban existente permanece disponível na base para uma próxima alternância por abas."*

## Projetos

- **Páginas**: `app/projetos/page.tsx` → `ProjetosView`.
- **Componentes**: `ProjetosView.tsx`, `ProjetosStats.tsx`, `ProjetosTable.tsx`, `ProjetosToolbar.tsx`, `NovoProjetoModal.tsx`, `ProjetoDetailsDrawer.tsx` (abas: Dados, Resumo, Modelo de Campanha, Equipe, Arquivos, Histórico), `ProjetoFormSections.tsx`.
- **Estado**: `useState<Projeto[]>(projetosMock)` local, mesmo padrão de perda de estado entre navegações que Demandas.

## Usuários, Clientes, Grupos de Clientes, Equipes, Fornecedores

- **Páginas**: `app/configuracoes/usuarios/page.tsx`, `app/configuracoes/clientes/page.tsx`, `app/configuracoes/grupos-clientes/page.tsx`, `app/configuracoes/equipes/page.tsx`, `app/fornecedores/page.tsx` (nota: fora de `/configuracoes`, único módulo de cadastro nessa condição).
- **Componentes**: cada um segue `XView.tsx` + `NovoXModal.tsx` + `NovoXButton.tsx` + `XFormSections.tsx` (Fornecedores e Grupos de Clientes têm ainda `FornecedoresView`/`GruposClientesView` como listagem própria).
- **Sem changes** desde o último inventário.

## Agências, Workflows (config), SLA, Prioridades, Tipos de Tarefa, Permissões

- **Páginas**: todas sob `app/configuracoes/*`. `agencias`, `usuarios`, `clientes` etc. têm view real; `workflows` e `sla` têm dado hardcoded direto no componente de página (sem `lib/*-mock.ts` correspondente — violação da própria convenção documentada); `prioridades` e `tipos-tarefa` não foram lidos em detalhe nesta rodada (fora do escopo de mudança); `permissoes` é `EmptyState` puro.

## Agenda

- **Páginas**: `app/agenda/page.tsx` → `AgendaView`.
- **Componentes**: `AgendaView.tsx`, `AgendaStats.tsx`, `AgendaToolbar.tsx`, `AgendaList.tsx`.
- **Tipos/mock**: `types/agenda.ts`, `lib/agenda-mock.ts`.
- Busca client-side com normalização de acento (`normalize`/`matchesContato`), sem criação de contato manual confirmada na toolbar.

## Conta

- **Páginas**: `app/conta/perfil/page.tsx`, `app/conta/notificacoes/page.tsx`, `app/conta/alterar-senha/page.tsx`.
- **Componentes**: `PerfilView.tsx`, `NotificacoesView.tsx` (4 canais, `useState` local, sem persistência), `AlterarSenhaView.tsx`.
- **Mock de usuário atual**: `frontend/src/lib/conta-mock.ts` — `currentUser` é um objeto **fixo** (`João Silva`, `Administrador`, `usuario@taskfloww.local`), sem nenhuma lógica de sessão; `logout()` é literalmente `console.log("logout")` com comentário `// TODO: integrar com autenticação`.

## Design System

- **Páginas**: `app/design-system/page.tsx`.
- **Componentes**: `DesignSystemColors.tsx`, `DesignSystemTypography.tsx`, `DesignSystemButtons.tsx`, `DesignSystemBadges.tsx`, `DesignSystemCards.tsx`, `DesignSystemInputs.tsx`, `DesignSystemWorkspace.tsx` — vitrine interna de componentes de UI, não é um módulo de produto.

## Layout (Shell)

- **Componentes**: `Shell.tsx` (compõe `Sidebar` + `Header` + `children`), `Sidebar.tsx` (menu fixo de 7 itens: Dashboard, Tarefas, Projetos, Agenda, Fornecedores, Relatórios, Configurações — ícones via `lucide-react`, ativo detectado via `usePathname()`), `Header.tsx`, `HeaderActions.tsx`, `HeaderSearch.tsx`, `Breadcrumb.tsx`, `UserMenu.tsx` (menu de conta com `currentUser` mock, sem sessão real).

## Hooks, Providers, Stores (transversal)

- **Hooks customizados**: nenhum arquivo `use*.ts` encontrado em `frontend/src` fora dos hooks nativos do React (`useState`, `useEffect`, `useMemo`, `useRef`, `useId`) usados diretamente dentro dos componentes.
- **Providers/Context**: nenhum — confirmado por busca em todo `frontend/src` (`createContext`, `Provider`, `useContext`: zero ocorrências).
- **Stores**: nenhum — nenhuma biblioteca de estado global instalada ou utilizada.

---

# 5. Banco de dados

- **Tabelas**: nenhuma tabela de negócio existe. O container `taskfloww_db` (Postgres 16-alpine) está de pé (validável via `/status`), mas nenhum código do repositório cria, referencia ou consulta qualquer tabela além do `SELECT 1` de healthcheck em `backend/main.py`.
- **Relacionamentos**: nenhum a nível de banco. Os "relacionamentos" hoje existentes são só conceituais, expressos como campos `*Id: string` dentro dos tipos TypeScript (`clienteId`, `projetoId`, `usuarioResponsavelIds` etc.), sem qualquer `FOREIGN KEY` real.
- **Índices**: nenhum.
- **Constraints**: nenhuma.
- **Migrations existentes**: nenhuma. Não há Alembic, não há pasta `migrations/`, não há nenhum arquivo `.sql` de schema em todo o repositório.
- **Acesso ao volume de dados**: `db_data/` (volume do Postgres) e `redis/appendonlydir/` (volume do Redis) **não puderam ser lidos** por este usuário do sistema (`Permission denied`) — não é possível confirmar ou negar conteúdo residual dentro desses volumes a partir da leitura de arquivo; a ausência de schema é inferida do código (nenhuma migration, nenhum model), não da inspeção direta do volume.

---

# 6. Fluxo de autenticação

**Não há fluxo de autenticação implementado.** Descrição do que existe hoje, item a item:

- **Login**: não existe nenhuma tela, rota ou formulário de login em todo o frontend (`app/` não tem `login/` nem `auth/`). Não existe endpoint de login no backend.
- **JWT**: nenhuma biblioteca de JWT está instalada (nem `python-jose`/`pyjwt` no backend, nem `jsonwebtoken`/similar no frontend). Nenhum token é gerado, armazenado (`localStorage`, cookie) ou validado em nenhum lugar do código.
- **Usuário atual**: `frontend/src/lib/conta-mock.ts` exporta um objeto `currentUser` **fixo e hardcoded** (`João Silva`, `Administrador`), consumido por `UserMenu.tsx` para exibir nome/cargo/e-mail/avatar. Não há sessão, não há verificação de identidade — qualquer um que acesse a aplicação "é" esse usuário fixo.
- **Permissões**: existe **estrutura de dado** (`PermissaoItem` em `types/usuario.ts`: `grupo, modulo, leitura, escrita, excluir, aprovar, extras`; `EquipeAcesso` em `types/equipe.ts`), mas **nenhuma checagem de permissão é executada em tempo de renderização ou de ação** em nenhum componente — nenhuma tela esconde ou desabilita ação com base em perfil. A tela `/configuracoes/permissoes` é um `EmptyState` puro.
- **Middleware**: não existe `frontend/middleware.ts` (mecanismo nativo do Next.js para proteger rotas) nem qualquer dependency/middleware de autenticação no FastAPI (`backend/main.py` não tem nenhum `Depends()` de autenticação, nenhum `APIRouter` protegido).
- **Logout**: `frontend/src/lib/conta-mock.ts`, função `logout()` — corpo inteiro é `console.log("logout")`, com comentário `// TODO: integrar com autenticação` no próprio código.

Esta ausência é uma decisão de fase explícita, não uma lacuna acidental — confirmado em `PROJECT_STATUS.md` ("Nesta fase ainda não existe autenticação") e `CLAUDE.md`/`docs/skills/taskflow-rules.md` (autenticação é "Fase 5", futura).

---

# 7. Fluxo CRUD

## Fluxo hoje (real, observado no código)

```
Frontend (View, ex.: ProjetosView.tsx)
   │  useState<Projeto[]>(projetosMock)   ← array mock estático importado de lib/projetos-mock.ts
   ▼
Frontend (funções locais, ex.: createProjetoFromDraft / updateProjetoFromDraft)
   │  cálculo em memória, sem I/O
   ▼
setProjetos(...)                          ← nova referência de array em memória do componente
   │
   ▼
(fim do fluxo — nenhuma API, nenhum Service, nenhum ORM, nenhum banco é tocado)
```

Não existem as camadas **API**, **Service** nem **ORM** para nenhuma entidade de negócio hoje — o fluxo CRUD completo descrito no roadmap (`Frontend → API → Service → ORM → Banco`) **não existe em nenhum módulo do produto**. A única rota que de fato toca banco/Redis é `GET /status` em `backend/main.py`, e mesmo essa não passa por Service nem ORM real (o `SELECT 1` é executado diretamente dentro da função da rota, via `engine.connect()`).

## Consequência prática já observável (ver também seção 9)

Como o estado vive apenas em `useState` inicializado a partir do array exportado (`demandasMock`, `projetosMock` etc.), e esse array exportado nunca é mutado (as funções sempre retornam um novo objeto/array), **qualquer criação ou edição feita pelo usuário é perdida ao desmontar o componente** (navegar para outra rota e voltar). Isso não é uma limitação teórica — é o comportamento real do código hoje, em todos os módulos que seguem esse padrão (Demandas, Projetos, Usuários, Clientes, Equipes, Fornecedores, Grupos de Clientes).

## Fluxo intencionado (ainda não implementado)

O fluxo completo `Frontend → API → Service → ORM → Banco` é o que os documentos `01-motores-centrais.md` e `02-modelo-dados-futuro.md` propõem para as próximas fases — nenhuma dessas camadas existe hoje para nenhuma entidade de negócio.

---

# 8. Pontos de extensão

Onde, no código atual, futuras funcionalidades poderiam ser conectadas — sem implementar nada disso agora:

- **Motor de eventos**: os pontos de criação manual de "histórico" já existentes (`createHistoricoDemanda` em `DemandasView.tsx`, `createHistoricoProjeto` em `ProjetosView.tsx`, `createWorkflowTransitionHistory` em `workflows-mock.ts`) são, hoje, três implementações independentes do mesmo conceito — são o ponto natural onde um motor de eventos centralizado substituiria chamadas espalhadas por uma emissão única.
- **Notificações**: `frontend/src/components/conta/NotificacoesView.tsx` já define os 4 canais (`Sistema, Email, WhatsApp, Push`) e seus valores-padrão — é o ponto de partida direto para persistir preferência real e, depois, para disparo de notificação.
- **Central de Tráfego**: hoje **dois** tipos conceituais preparam esse terreno de forma independente — `DemandaSessaoTrabalhoConceitual` (`types/demanda.ts`) e `WorkflowSessaoTrabalhoConceitual` (`types/workflow.ts`, adicionado no commit mais recente). Nenhum dos dois é usado por nenhum componente; ambos são apenas declarações de tipo com comentário explicando que são conceituais.
- **Auditoria**: os 6 tipos de histórico hoje existentes (`DemandaHistoricoEvento`, `ProjetoHistoricoEvento`, `HistoricoUsuario`, `HistoricoCliente`, `HistoricoEquipe`, e agora também `WorkflowTransicaoHistorico`) são o ponto de extensão natural para um modelo de auditoria único.
- **IA**: nenhuma menção em código — apenas em documentação (`CLAUDE.md`, seção "Integrações Futuras": "Inteligência Artificial", "Dashboard Executivo"). Não há nenhum ponto de código preparado para IA hoje.

---

# 9. Pontos frágeis

## Duplicação

- **Dois workflows desconectados, ativos ao mesmo tempo**: `frontend/src/app/configuracoes/workflows/page.tsx` (hardcoded, 3 workflows fictícios: `Marketing Padrão`/`Produção Gráfica`/`Clínica Clare`) vs. `frontend/src/lib/workflows-mock.ts` (3 templates reais aplicáveis a Demandas: `Criação padrão`/`Mídia paga`/`Conteúdo`). Nenhuma relação entre os dois. Esta duplicação **já existia** antes (documentada em `01-motores-centrais.md`) e **piorou** com o commit mais recente, porque agora o segundo lado da duplicação (o motor por demanda) ficou muito mais completo e funcional, aumentando a distância entre os dois modelos.
- **Dois tipos conceituais de sessão de trabalho** para a mesma futura Central de Tráfego: `DemandaSessaoTrabalhoConceitual` (`types/demanda.ts`) e `WorkflowSessaoTrabalhoConceitual` (`types/workflow.ts`) — redundância introduzida pelo commit mais recente, sem que o tipo antigo tenha sido removido ou reconciliado com o novo.
- **Vocabulário de status de etapa divergente**: o novo `WorkflowEtapaStatus` (`pendente|atual|concluida|bloqueada`) substituiu, dentro de `Demanda.workflow`, o antigo formato de etapa embutido diretamente em `Demanda` (que usava `pendente|em_execucao|pausada|concluida`) — mas a tela `/configuracoes/workflows` nunca usou nenhum dos dois vocabulários (usa `stages: string[]` livre), então agora há, na prática, **três** representações diferentes de "estado de uma etapa" convivendo no mesmo repositório.
- **6 tipos de histórico/evento quase idênticos** (ver seção 8), incluindo o `WorkflowTransicaoHistorico` recém-adicionado, que se sobrepõe conceitualmente ao histórico genérico de Demanda.
- **Helpers de resolução de nome duplicados** por módulo (`resolveXNome`), um padrão repetido em quase todo `lib/*-mock.ts`.

## Acoplamento

- `frontend/src/lib/workflows-mock.ts` importa `departamentosProjetoDisponiveis`/`responsaveisProjetoDisponiveis`/`generateId` diretamente de `lib/projetos-mock.ts`, e depois **reexporta** esses mesmos símbolos (`export { departamentosProjetoDisponiveis, generateId, responsaveisProjetoDisponiveis }`) — um acoplamento cruzado entre módulos mock que deveria vir de uma fonte única (Usuários/Departamentos), não de "Projetos" servindo como hub acidental de dados de outros domínios.
- `backend/main.py` mistura setup de infraestrutura (criação de `engine`, client Redis) e definição de rota no mesmo arquivo, sem nenhuma separação de camada — qualquer crescimento do backend a partir daqui herda esse acoplamento se não for reestruturado antes.

## Riscos

- **Nenhum teste automatizado existe em todo o projeto** — nem frontend (`jest`/`vitest`/`@testing-library`/`playwright`), nem backend (`pytest`). Toda validação hoje depende de `npm run lint`/`npm run build`/`npm run typecheck` (conforme exigido em `AGENTS.md`) e inspeção manual.
- **PII já modelada sem proteção**: `UsuarioInformacoes` (`types/usuario.ts`) contém CPF, RG, dados bancários e chave PIX como campos mock — ainda sem risco real hoje (não há persistência), mas o desenho já antecipa esse dado sensível sem nenhuma camada de controle de acesso desenhada.
- **Uso de `window.confirm`** em `WorkflowEditor.tsx` (função `applyTemplate`) para confirmar uma ação destrutiva (substituir workflow atual) — funciona, mas é um padrão de UI não acessível e inconsistente com o resto do design system (`Modal`, `EntitySidePanel`), que não é usado para essa confirmação.
- **Pastas vestigiais**: `docker/api/` e `docker/frontend/` existem no repositório mas estão **vazias** — sugerem uma intenção de Dockerfile customizado por serviço que nunca foi concretizada (o `docker-compose.yml` atual usa imagens base diretamente, com comando inline, não essas pastas).
- **`next.config.ts`** tem `allowedDevOrigins: ["10.153.110.10"]` — IP fixo de ambiente de desenvolvimento hardcoded na configuração versionada.

## Dependências fortes

- Versões recentes de Next.js (`16.2.10`) e React (`19.2.4`) — checar maturidade/suporte de ecossistema (bibliotecas de terceiros, ex.: futura biblioteca de gráfico) antes de assumir compatibilidade automática nas próximas fases.
- Todas as dependências do backend (`fastapi`, `sqlalchemy`, `redis` etc.) são instaladas via `pip install` inline no `docker-compose.yml`, **sem versão fixada** e sem `requirements.txt`/`pyproject.toml` — cada `docker compose up` pode potencialmente puxar uma versão diferente das bibliotecas, o que é um risco de reprodutibilidade.

## Gargalos

- **Perda de estado entre navegações** (detalhado na seção 7) — hoje já é um comportamento real e perceptível em Demandas, Projetos, Usuários, Clientes, Equipes, Fornecedores e Grupos de Clientes: qualquer alteração feita pelo usuário se perde ao trocar de rota e voltar, porque o estado vive só em `useState` local, reinicializado a partir do array mock estático a cada montagem do componente.
- Nenhuma paginação em nenhuma tabela/listagem hoje — aceitável com poucos registros mock, torna-se gargalo real assim que houver dado de produção.

---

# 10. Convenções atuais

## Nomenclatura

- Campos de dado em português (`nome`, `descricao`, `responsavelIds`, `prazoHoras`), consistente com o domínio de negócio (agência brasileira).
- Tipos TypeScript em PascalCase (`Demanda`, `WorkflowEtapa`, `ClienteDraft`).
- Componentes React em PascalCase, um por arquivo (`DemandasView.tsx`).
- Mocks em kebab-case com sufixo `-mock.ts` (`demandas-mock.ts`, `workflows-mock.ts`).
- Tipos em kebab-case (`demanda.ts`, `workflow.ts`).
- IDs mock gerados via helper `generateId(prefixo)` (ex.: `generateId("workflow-etapa")`), presente em múltiplos módulos (originado em `lib/projetos-mock.ts`, reexportado por outros).

## Organização

- Padrão de composição `Page → View → Table/List → Modal → FormSections` aplicado de forma consistente em Usuários, Clientes, Equipes, Fornecedores, Grupos de Clientes, Projetos e Demandas.
- `src/components/workspace/*` como framework reutilizável de página operacional (`WorkspacePage`, `WorkspaceSection`, `WorkspaceStats`, `WorkspaceTable`, `WorkspaceToolbar`, `WorkspaceEmptyState`), adotado pelos módulos mais recentes (Projetos, Demandas) — módulos mais antigos (ex.: Workflows, SLA em `/configuracoes`) não usam esse framework, ainda com HTML/Tailwind escrito diretamente na página.

## Padrões

- Todo componente com estado usa `"use client"` explícito no topo do arquivo.
- Estilização exclusivamente via Tailwind (classe utilitária inline) — nenhum arquivo `.module.css` ou CSS-in-JS.
- Relacionamento sempre por ID (`clienteId`, não `nomeCliente`) — regra de `CLAUDE.md` seguida de forma consistente em todos os tipos observados.
- Toda entidade principal carrega `id`/`empresaId` (a maioria também `agenciaId`) e `createdAt`/`updatedAt`.
- Múltiplos responsáveis representados como `usuarioResponsavelIds: string[]` + `departamentoResponsavelIds: string[]`, sempre com `MultiSelect` (`components/ui/MultiSelect.tsx`) como componente de UI correspondente.

## Exceções

- **Fornecedores** (`app/fornecedores/page.tsx`) é o único cadastro fora de `/configuracoes` — todos os demais cadastros equivalentes (Clientes, Equipes, Grupos de Clientes) vivem sob `/configuracoes`.
- **Kanban** não segue o padrão `Page → View`: não tem nenhuma `page.tsx` que o monte.
- **`/configuracoes/workflows`** e **`/configuracoes/sla`** não seguem a convenção "dado mock vive em `lib/*-mock.ts`" — os arrays (`workflows`, `slaRules`) estão declarados diretamente dentro do componente de página, violando a própria regra documentada em `CLAUDE.md` ("`src/lib` — responsável por mocks... Nunca colocar componentes React dentro de lib" implica o inverso também: dado mock não deveria morar dentro do componente).
- **`/equipe`** (nível superior, fora de Configurações) é um `EmptyState` ("Módulo em construção"), enquanto `/configuracoes/equipes` é o cadastro real — duas rotas com nome semelhante e maturidade muito diferente, risco de confusão de navegação.

---

# 11. Recomendações

Apenas recomendações — nenhuma implementação foi realizada como parte deste documento.

1. **Unificar os dois workflows antes de qualquer nova funcionalidade de workflow.** A divergência entre `/configuracoes/workflows` e `workflows-mock.ts` aumentou neste último ciclo; quanto mais tempo os dois evoluírem em paralelo, maior o custo de reconciliação futura (isso já era um risco apontado em `01-motores-centrais.md`, e se confirmou).
2. **Reconciliar os dois tipos conceituais de sessão de trabalho** (`DemandaSessaoTrabalhoConceitual` e `WorkflowSessaoTrabalhoConceitual`) em um único lugar antes de qualquer implementação de Central de Tráfego — hoje isso exigiria uma decisão de qual arquivo/tipo é a fonte de verdade.
3. **Definir e documentar o vocabulário único de status de etapa** antes da Fase 1 do roadmap (`03-roadmap-implementacao.md`) — hoje há três representações diferentes de "estado de etapa" no repositório.
4. **Introduzir camada de serviço no backend desde o primeiro endpoint de negócio**, evitando repetir o padrão hoje visto em `main.py` (lógica de infraestrutura e rota no mesmo arquivo/escopo).
5. **Avaliar a introdução de testes mínimos** (ao menos testes de contrato/tipo) antes de iniciar a Fase 1 do roadmap — hoje não há nenhuma rede de segurança automatizada em todo o projeto.
6. **Tratar a perda de estado entre navegações como um problema real, não teórico**, já visível hoje em 7 módulos — decidir se a solução de curto prazo (antes da API real) é mover o estado para um nível mais alto (contexto/layout) ou se compensa esperar pela Fase 1 do roadmap.
7. **Padronizar a rota de Fornecedores** para `/configuracoes/fornecedores`, alinhando com os demais cadastros.
8. **Revisar as pastas vestigiais `docker/api/` e `docker/frontend/`** — decidir se serão usadas para Dockerfiles customizados futuramente ou removidas, para não deixar estrutura órfã no repositório.
9. **Fixar versões de dependência do backend** (`requirements.txt`/`pyproject.toml`) em vez de depender do `pip install` inline e sem versão no `docker-compose.yml`, antes de qualquer ambiente além do local de desenvolvimento depender dessa instalação.

---

## Resumo da análise

O TaskFloww V2 é hoje uma aplicação **majoritariamente frontend**, com um design system e um padrão de módulo (`Page → View → Table → Modal → FormSections`) maduros e consistentes, operando inteiramente sobre dados mock em memória. O backend existe apenas como prova de infraestrutura (healthcheck de API/Postgres/Redis), sem nenhum model, schema, rota de negócio ou persistência real. Desde a última auditoria (`00-estado-atual.md`), um módulo de Workflow real (ainda mock) foi adicionado — um avanço funcional significativo (templates reais, clonagem de instância, transição/bloqueio manual, histórico de transição) que, ao mesmo tempo, tornou mais visível a divergência já existente com a tela `/configuracoes/workflows`, que permanece hardcoded e desatualizada em relação ao novo modelo.

## Principais riscos encontrados

1. Duas fontes de verdade de Workflow ativas e cada vez mais distantes uma da outra.
2. Perda real de estado do usuário ao navegar entre rotas, em 7 módulos diferentes, hoje — não é uma hipótese futura.
3. Zero testes automatizados em todo o projeto (frontend e backend).
4. Ausência total de autenticação, sessão e checagem de permissão — por decisão de fase, mas com PII já modelada (`UsuarioInformacoes`) para quando a persistência real chegar.
5. Duplicação conceitual crescente (sessão de trabalho, histórico, vocabulário de status de etapa) que tende a se multiplicar se cada novo módulo continuar sendo desenvolvido de forma isolada.

## Principais oportunidades de melhoria

1. Resolver a divergência de Workflow como pré-requisito antes de iniciar a Fase 1 do roadmap (`03-roadmap-implementacao.md`), já que a Fase 1 depende de "estrutura base de workflow".
2. Aproveitar o framework `components/workspace/*` (já maduro) como padrão único para os módulos que ainda não o adotam (`/configuracoes/workflows`, `/configuracoes/sla`).
3. Introduzir uma camada mínima de contrato de teste antes de crescer mais o backend, dado que ele parte hoje de zero.
4. Consolidar os pontos de extensão já identificados (histórico, sessão de trabalho conceitual, preferências de notificação) em vez de deixá-los se multiplicar por módulo.

## Confirmação

Nenhuma implementação foi realizada, nenhum arquivo existente foi alterado e nenhuma migration foi criada nesta etapa — apenas este documento de inventário foi escrito, em `docs/arquitetura-taskfloww/00a-inventario-tecnico.md`.