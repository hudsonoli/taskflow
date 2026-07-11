# 00 — Estado Atual do TaskFloww V2

> Documento de auditoria. Não contém proposta de implementação.
> Gerado por leitura direta do código, configuração e documentação existentes em `/docker/taskfloww` (sem acesso a `db_data/` e `redis/appendonlydir/`, protegidos por permissão de sistema).
> Data da auditoria: 2026-07-11.

## Legenda de classificação

| Rótulo | Significado |
|---|---|
| **implementado** | Existe, funciona e é usado de ponta a ponta (ainda que sobre dados mock) |
| **parcialmente implementado** | Existe parte da funcionalidade (UI, tipo ou fluxo), mas falta uma camada relevante (backend, persistência, integração entre módulos) |
| **estrutura existente** | Há tipos, campos ou esqueleto preparado, mas sem tela, lógica ou uso real conectado |
| **documentado mas não implementado** | Descrito em `docs/`, comentários de código ou `PROJECT_STATUS.md`, sem nenhuma linha de implementação |
| **planejado** | Citado como próxima fase, sem estrutura nem documentação detalhada ainda |
| **inexistente** | Nenhum vestígio encontrado no repositório |
| **não confirmado** | Não foi possível verificar (bloqueio de permissão, ausência de acesso) |

---

## 1. Visão geral do repositório

- Diretório raiz: `/docker/taskfloww` (repositório Git local, sem remoto configurado até onde foi possível observar).
- Serviços Docker (`docker-compose.yml`): `taskfloww_front` (Next.js, porta 3010), `taskfloww_api` (FastAPI, porta 8010), `taskfloww_db` (Postgres 16), `taskfloww_redis` (Redis 7).
- O projeto está em **fase de prototipação de frontend com dados mock**. Isso é uma regra explícita e repetida em `AGENTS.md`, `CLAUDE.md` e `docs/skills/*`: "durante a fase de prototipação, NÃO criar migrations, banco, APIs reais, autenticação".
- Último commit: `8881565 feat(demandas): cria workspace e workflow mock`.

**Classificação geral: parcialmente implementado** (infraestrutura sobe e funciona; regras de negócio existem só no frontend, em memória/mock).

---

## 2. Frontend

**Stack:** Next.js (App Router) + React + TypeScript + Tailwind + `dnd-kit`.

**Classificação: implementado** (como shell de aplicação).

- Estrutura segue à risca o padrão documentado em `docs/skills/architecture.md` e `CLAUDE.md`: `src/app` (rotas), `src/components/<modulo>`, `src/types/<modulo>.ts`, `src/lib/<modulo>-mock.ts`.
- Shell de layout implementado: `src/components/layout/Shell.tsx`, `Sidebar.tsx`, `Header.tsx`, `HeaderActions.tsx`, `HeaderSearch.tsx`, `Breadcrumb.tsx`, `UserMenu.tsx`.
- Design system interno implementado em `src/app/design-system/page.tsx` e `src/components/design-system/*` (cores, tipografia, botões, badges, cards, inputs).
- Nenhuma chamada real a API foi encontrada (`fetch`, `axios`, `useQuery` etc. não aparecem apontando para `taskfloww_api`); todo dado vem de `src/lib/*-mock.ts`.

---

## 3. Backend

**Classificação: estrutura existente** (apenas esqueleto de infraestrutura, sem regra de negócio).

- Único arquivo: `backend/main.py` (51 linhas). Contém:
  - App FastAPI (`app = FastAPI(title="Taskfloww API")`).
  - Conexão SQLAlchemy (`create_engine`) e client Redis, ambos usados apenas para healthcheck.
  - Três rotas: `GET /` (mensagem de boas-vindas), `GET /health`, `GET /status` (testa conexão com Postgres e Redis).
- Não há `models.py`, `schemas.py`, `routers/`, `services/`, `crud/`, `alembic/` ou qualquer subpasta — o backend é literalmente um único arquivo.
- `backend/AGENTS.md` define regras para quando o backend for desenvolvido (não alterar contratos JSON, não criar migration sem autorização etc.), mas essas regras ainda não têm código a que se apliquem.

---

## 4. Banco de dados

**Classificação: estrutura existente (infraestrutura) / inexistente (schema de negócio)**.

- Container `taskfloww_db` (Postgres 16-alpine) sobe via Docker Compose, com volume `./db_data` (sem permissão de leitura para este usuário — **não confirmado** o conteúdo real do volume).
- Não há nenhuma migration, arquivo `.sql`, Alembic, script de schema ou ORM model no repositório.
- `docs/database-model.md` lista apenas nomes de tabelas conceituais, sem colunas, tipos ou relacionamentos:
  ```
  Agencias, Usuarios, Equipes, Clientes, Projetos, Workflows,
  WorkflowEtapas, Tarefas, Comentarios, Anexos, Permissoes, Auditoria
  ```
  → **documentado mas não implementado**.
- `docs/skills/database-rules.md` reforça: "Não criar tabelas, migrations ou models antes da fase aprovada", e lista uma segunda proposta de tabelas iniciais (`empresas, usuarios, clientes, projetos, tarefas, colunas_kanban, comentarios, anexos, historico_tarefas`) — as duas listas de `docs/` **divergem entre si**, o que é relevante para quando o schema real for desenhado.
- Redis está operacional apenas como dependência de infraestrutura (ping via `/status`); uso funcional (fila, cache, notificações) é **planejado**, citado em `docs/skills/database-rules.md`.

---

## 5. Rotas

**Frontend (Next.js App Router) — implementado.** Rotas confirmadas em `frontend/src/app/`:

```
/                                  (Dashboard)
/tarefas                           (Demandas)
/projetos
/relatorios                        (EmptyState)
/agenda
/equipe                            (EmptyState — placeholder)
/fornecedores
/conta/perfil
/conta/alterar-senha
/conta/notificacoes
/configuracoes
/configuracoes/agencias
/configuracoes/usuarios
/configuracoes/clientes
/configuracoes/grupos-clientes
/configuracoes/equipes
/configuracoes/workflows
/configuracoes/sla
/configuracoes/prioridades
/configuracoes/tipos-tarefa
/configuracoes/permissoes          (EmptyState)
/design-system
```

- Observação de inconsistência: **Clientes** e **Equipes** vivem só em `/configuracoes/...` (item removido do menu principal na Fase 3.13, conforme `PROJECT_STATUS.md`), enquanto **Fornecedores** tem rota própria fora de `/configuracoes` (`/fornecedores`), quebrando o padrão que o restante do cadastro segue.
- Não existe rota `/configuracoes/departamentos` (departamentos ainda não têm módulo próprio, ver seção 12).

**Backend (API REST) — parcialmente implementado.** Apenas `/`, `/health`, `/status`. Nenhuma rota de negócio (`/usuarios`, `/projetos`, `/demandas` etc.) existe.

---

## 6. Models (ORM / banco)

**Classificação: inexistente.** Nenhuma classe SQLAlchemy, nenhum arquivo `models.py`/`models/` no backend.

---

## 7. Schemas

**Backend (Pydantic) — inexistente.** Nenhum `schemas.py` ou `BaseModel` de domínio; `main.py` não define nenhum schema de request/response além das respostas literais em `dict`.

**Frontend (TypeScript types) — implementado como "schema" de fato.** `frontend/src/types/` contém os contratos de dados usados por toda a aplicação: `usuario.ts`, `cliente.ts`, `equipe.ts`, `fornecedor.ts`, `grupo-cliente.ts`, `projeto.ts`, `demanda.ts`, `agenda.ts`. Esses tipos são a fonte de verdade atual do modelo de dados do produto, mesmo sem existir banco por trás.

---

## 8. APIs

**Classificação: parcialmente implementado.** Ver seções 3 e 5. Existem apenas endpoints de healthcheck; nenhuma API de domínio (CRUD de usuários, clientes, projetos, demandas etc.) foi criada. Todo o CRUD hoje é simulado em memória no frontend (estado React + arrays mock), sem chamada de rede.

---

## 9. Autenticação

**Classificação: inexistente** (por decisão de projeto, não por lacuna acidental).

- `PROJECT_STATUS.md`: "Nesta fase ainda não existe autenticação. As permissões serão implementadas futuramente após a criação do módulo de usuários e autenticação."
- `CLAUDE.md` e `docs/skills/taskflow-rules.md` proíbem explicitamente criar autenticação nesta fase (Fase 5, futura).
- Não há login, sessão, JWT, cookie de auth, middleware de proteção de rota, nem variável de ambiente relacionada a segredo de autenticação no frontend ou backend.
- `frontend/src/app/conta/alterar-senha/page.tsx` e `AlterarSenhaView.tsx` existem como tela, mas sem lógica real de autenticação por trás (mock).

---

## 10. Permissões

**Classificação: estrutura existente (modelo de dados) + documentado mas não implementado (tela/funcional).**

- Modelo RBAC **descrito** em `CLAUDE.md`/`PROJECT_STATUS.md`: perfis `SuperAdmin, Admin, Diretoria, Gestor, Operador, Cliente`.
- Estrutura de dados já modelada no frontend:
  - `PermissaoItem` (`types/usuario.ts`): `grupo, modulo, leitura, escrita, excluir, aprovar, extras`.
  - `UsuarioDraft.permissoes: PermissaoItem[]`.
  - `EquipeAcesso` (`types/equipe.ts`): `visualizarTodosProjetos, aprovarSla, gerenciarMembros, visivelParaClientes`.
- Tela `/configuracoes/permissoes` é um `EmptyState` puro: "O controle de permissões será implementado futuramente" — nenhuma lógica de leitura/escrita/aprovação é aplicada em nenhuma tela hoje (nenhum componente checa perfil de usuário antes de renderizar ação).
- Regras de visibilidade por perfil (quem vê o menu Configurações, ocultar itens sem permissão) estão **documentadas** em `docs/requirements/projetos-demandas-dashboard.md` (seção 8) mas não codificadas.

---

## 11. Usuários

**Classificação: parcialmente implementado** (CRUD mock completo no frontend, sem persistência real).

- Rota: `/configuracoes/usuarios`.
- Componentes: `UsuariosView.tsx`, `NovoUsuarioModal.tsx`, `NovoUsuarioButton.tsx`, `UsuarioFormSections.tsx`.
- Tipo: `types/usuario.ts` — `UsuarioDraft` já modelado com `empresaId`, `clienteId?`, `departamentoId`, `squad`, `perfil`, `permissoes`, `enderecos`, `informacoes` (dados sensíveis: CPF, chave PIX, dados bancários — ver nota de segurança abaixo), `historico`.
- Mock: `lib/usuario-mock.ts`.
- **Nota de segurança:** `UsuarioInformacoes` inclui `cpf`, `chavePix`, `banco`, `agencia`, `conta`, `rg` como campos de dados mock. Nenhum segredo real foi encontrado no repositório (não há `.env` versionado nem credenciais reais), mas o modelo de dados já prevê PII sensível — relevante para LGPD quando o backend real for construído.

---

## 12. Equipes

**Classificação: parcialmente implementado** (mock, em `/configuracoes/equipes`) **+ inexistente** (rota de nível superior `/equipe`, que é apenas um `EmptyState` "Módulo em construção").

- Componentes: `EquipesView.tsx`, `NovaEquipeModal.tsx`, `NovaEquipeButton.tsx`, `EquipeFormSections.tsx`.
- Tipo: `types/equipe.ts` — `EquipeDraft` com `membros: EquipeMembro[]`, `acesso: EquipeAcesso`, `historico`.
- Mock: `lib/equipe-mock.ts`.

## Departamentos

**Classificação: planejado** (próxima fase documentada, sem módulo próprio ainda).

- Não existe rota, view, tipo dedicado ou mock exclusivo de "Departamento" como entidade própria.
- Existe apenas `DepartamentoOption` (`types/usuario.ts`: `id, nome, ativo`) usado como referência simples dentro de Usuários/Equipes/Projetos (`departamentoId`, `departamentoResponsavelIds`).
- `PROJECT_STATUS.md` define explicitamente a **Fase 3.14 — Departamentos V2** como próxima etapa, com objetivos já listados (`departamentoId`, `codigoInterno`, `sigla`, responsável, vínculo com equipes/usuários, histórico, permissões) — ainda não iniciada.

---

## 13. Clientes

**Classificação: parcialmente implementado.**

- Rota: `/configuracoes/clientes` (migrado de `/clientes` na Fase 3.13, conforme `PROJECT_STATUS.md`).
- Componentes: `ClientesView.tsx`, `NovoClienteModal.tsx`, `NovoClienteButton.tsx`, `ClienteFormSections.tsx`.
- Tipo: `types/cliente.ts` — `ClienteDraft` já com relacionamentos por ID (`equipeResponsavelId`, `responsavelComercialId`, `responsavelAtendimentoId`), `contatos: ClienteContato[]`, `endereco`, `historico`. Campos financeiros foram explicitamente removidos por estarem fora do escopo do TaskFloww (registrado em `PROJECT_STATUS.md`).
- Mock: `lib/cliente-mock.ts`.

## Grupos de Clientes

**Classificação: parcialmente implementado.** Rota `/configuracoes/grupos-clientes`; componentes em `components/grupos-clientes/`; tipo `types/grupo-cliente.ts`; mock `lib/grupo-cliente-mock.ts`.

---

## 14. Fornecedores

**Classificação: parcialmente implementado.**

- Rota: `/fornecedores` (fora de `/configuracoes`, ao contrário de Clientes/Equipes — inconsistência de padrão de navegação a observar).
- Componentes: `FornecedoresView.tsx`, `NovoFornecedorModal.tsx`, `NovoFornecedorButton.tsx`, `FornecedorFormSections.tsx`.
- Tipo: `types/fornecedor.ts`; mock: `lib/fornecedor-mock.ts`.

---

## 15. Projetos

**Classificação: parcialmente implementado** (o mais completo entre os módulos operacionais).

- Rota: `/projetos`. Componentes: `ProjetosView.tsx`, `ProjetosTable.tsx`, `ProjetosToolbar.tsx`, `ProjetosStats.tsx`, `NovoProjetoModal.tsx`, `ProjetoDetailsDrawer.tsx`, `ProjetoFormSections.tsx`.
- `ProjetoDetailsDrawer` tem abas: **Dados, Resumo, Modelo de Campanha, Equipe, Arquivos, Histórico**.
- Tipo `types/projeto.ts` já modela:
  - `responsavelIds: string[]` e `departamentoResponsavelIds: string[]` → **múltiplos responsáveis implementados** ao nível de tipo/UI (commit `f4cc6ec refactor(projetos): adiciona multiplos responsaveis`).
  - `arquivos: ProjetoArquivo[]` (anexos) — ver seção 18.
  - `modeloCampanha: ProjetoModeloCampanhaItem[]` — backlog de campanha recorrente, alinhado ao que `docs/requirements/projetos-demandas-dashboard.md` (seção 2.3) descreve como necessidade futura, mas já parcialmente modelado aqui.
  - `historico: ProjetoHistoricoEvento[]`.
- Mock: `lib/projetos-mock.ts`.
- Integração com Publi (PIT/CNPJ/OC) descrita em requirements é **documentado mas não implementado** — explicitamente fora de escopo desta fase.

---

## 16. Demandas

**Classificação: parcialmente implementado.**

- Rota: `/tarefas` → `DemandasView`.
- Componentes: `DemandasView.tsx`, `DemandasTable.tsx`, `DemandasToolbar.tsx`, `DemandasStats.tsx`, `NovaDemandaModal.tsx`, `DemandaDetailsDrawer.tsx`, `DemandaFormSections.tsx`.
- `DemandaDetailsDrawer` tem abas: **Dados, Briefing, Workflow, Responsáveis, Histórico**. Não há aba de Comentários, Anexos ou Checklist (ver seções 19–21).
- Tipo `types/demanda.ts` modela, além dos campos básicos: `usuarioResponsavelIds`, `departamentoResponsavelIds`, `workflowEtapas: DemandaWorkflowEtapa[]`, `etapaAtualId`, `historico`.
- O tipo já contém **estruturas conceituais explicitamente marcadas como não implementadas** (comentário no próprio código-fonte, `types/demanda.ts:39`):
  - `DemandaSessaoTrabalhoConceitual` — para a futura Central de Tráfego (ver seção 22).
  - `DemandaVisibilidadeConceitual` — para regras futuras de visibilidade por etapa/perfil.
- Mock: `lib/demandas-mock.ts`.

---

## 17. Kanban

**Classificação: estrutura existente**, com uma ressalva importante: **o Kanban está desconectado do módulo real de Demandas.**

- `components/kanban/KanbanBoard.tsx` implementa drag-and-drop funcional com `@dnd-kit/core` (`DndContext`, `PointerSensor`, `handleDragEnd`), 4 colunas fixas (`backlog, em-andamento, revisao, concluido`) e um array `initialTasks` **hardcoded dentro do próprio componente**, com um formato de dado (`title, client, project, assignee, priority, deadline, sla, taskType, rework`) diferente do tipo `Demanda` usado no resto do sistema (`nome, clienteId, projetoId, usuarioResponsavelIds` etc.).
- `KanbanCard.tsx` e `TaskDetailModal.tsx` consomem esse formato próprio (`KanbanTask`), não `Demanda`.
- Não há nenhuma página (`src/app/**/page.tsx`) que renderize `KanbanBoard` — não foi encontrada rota que monte esse componente; ele existe como componente isolado, não conectado à navegação nem aos dados mock de Demandas/Projetos.
- `docs/requirements/projetos-demandas-dashboard.md` (seção 4) descreve o Kanban desejado (por projeto/equipe/colaborador, filtros por cliente/prioridade/atraso/etapa, card enxuto) — isso é **documentado mas não implementado** sobre a base real de dados; o que existe hoje em `KanbanBoard.tsx` é um protótipo visual isolado, anterior a essa especificação.

---

## 18. Workflow

**Classificação: parcialmente implementado**, também com desconexão entre duas implementações paralelas:

1. **Workflow por demanda** (`WorkflowDemandaSection` em `DemandaFormSections.tsx`): permite adicionar/remover etapas (`DemandaWorkflowEtapa`), definir responsáveis (usuário/departamento) por etapa via `MultiSelect`, prazo em horas e etapa atual. É mock, mas funcional na UI e ligado ao tipo `Demanda`.
2. **Tela `/configuracoes/workflows`**: lista 3 workflows com nomes/etapas **totalmente hardcoded** no componente da página (`WorkflowsPage`), sem nenhuma relação com `DemandaWorkflowEtapa` nem com `lib/demandas-mock.ts`. É um cadastro-vitrine, não editável de fato (botão "Novo Workflow" sem ação implementada).

Não há motor de workflow real (sem transições automáticas, sem validação de etapa, sem SLA aplicado sobre etapa) — confirmado também pelo próprio comentário no código: "Etapas mock por demanda. Não há motor real, Kanban ou drag-and-drop nesta fase."

---

## 19. Responsáveis / Múltiplos responsáveis

**Classificação: implementado** (ao nível de tipo + UI, sem persistência real).

- Padrão consistente de "múltiplos responsáveis" via arrays de IDs + componente `MultiSelect` (`components/ui/MultiSelect.tsx`), reaproveitado em:
  - `Demanda.usuarioResponsavelIds` / `departamentoResponsavelIds` (geral e por etapa de workflow).
  - `Projeto.responsavelIds` / `departamentoResponsavelIds`.
- Resolução de nomes a partir de IDs é feita via helpers em `lib/*-mock.ts` (ex.: `resolveResponsaveisProjetoNomes`, `resolveDepartamentosProjetoNomes`), respeitando a regra de "nunca usar nome como chave" definida em `CLAUDE.md`.
- Isso é hoje o padrão mais maduro do repositório e um bom candidato a reaproveitar ao desenhar o schema real.

---

## 20. Comentários

**Classificação: documentado mas não implementado.**

- Citado como tabela futura em `docs/database-model.md` (`Comentarios`) e `docs/skills/database-rules.md` (`comentarios`).
- Nenhum campo em `Demanda`, `Projeto` ou qualquer outro tipo. Nenhum componente, mock ou aba de UI relacionada a comentários foi encontrado em nenhuma tela (inclusive `DemandaDetailsDrawer`, que seria o local natural).

---

## 21. Anexos

**Classificação: estrutura existente em Projetos / inexistente em Demandas.**

- **Projetos:** `ProjetoArquivo` (`types/projeto.ts`) modela `id, nome, tipo, tamanho, criadoEm, usuarioId, usuarioNome`; `ProjetoDetailsDrawer` tem aba **"Arquivos"** dedicada. Não foi confirmado se há upload real ou apenas listagem mock estática (não confirmado — não foi lido o componente de seção correspondente em detalhe para upload).
- **Demandas:** nenhum campo de anexo no tipo `Demanda`, nenhuma aba correspondente em `DemandaDetailsDrawer`.
- Citado como tabela futura (`Anexos`/`anexos`) em `docs/database-model.md` e `docs/skills/database-rules.md`.

---

## 22. Checklists

**Classificação: inexistente.** Nenhuma ocorrência de "checklist" (termo funcional) no código do produto. O único uso da palavra no repositório é o "Checklist obrigatório" de processo de desenvolvimento dentro de `CLAUDE.md` (lista de passos para o agente considerar um módulo concluído), que não tem relação com checklist de tarefa/demanda para o usuário final.

---

## 23. Histórico

**Classificação: parcialmente implementado.** Padrão consistente e repetido em quase todos os módulos, sempre como array mock somente-leitura:

- `HistoricoUsuario`, `HistoricoCliente`, `HistoricoEquipe`, `ProjetoHistoricoEvento`, `DemandaHistoricoEvento` — todos com forma quase idêntica: `id, usuarioId, usuario, dataHora, ip/ipOrigem, dispositivo, acao`.
- Renderizado em seções dedicadas (`HistoricoDemandaSection`, abas "Histórico" em Clientes/Equipes/Usuários/Projetos/Demandas).
- É só leitura de dados mock estáticos — nenhuma ação real do sistema gera um evento de histórico novo (não há dispatch/interceptor central de auditoria).
- `CLAUDE.md` (seção "Auditoria") confirma: "Ainda não implementar. Preparar a estrutura." — ou seja, a intenção documentada bate com o que foi encontrado.
- Existe uma tabela conceitual separada, `Auditoria`, em `docs/database-model.md`, que aparentemente cobriria esse mesmo escopo — mais uma sobreposição de conceitos entre documentos a esclarecer na arquitetura futura.

---

## 24. Timeline

**Classificação: inexistente.** Nenhuma ocorrência literal de "timeline" no código ou na documentação. O que existe hoje (seção 23, Histórico) é uma lista de eventos, não uma visualização de linha do tempo. Se o ranking do Flowe usa "timeline" como conceito de UI (feed cronológico visual), isso ainda não tem nem estrutura nem menção no TaskFloww.

---

## 25. Notificações

**Classificação: parcialmente implementado** (preferências de canal, sem motor de envio).

- Rota `/conta/notificacoes` → `NotificacoesView.tsx`: 4 canais (`Sistema, Email, WhatsApp, Push`) com toggle via `Switch`, estado local em memória (`useState`), sem persistência.
- Nenhum sistema de disparo de notificação (in-app, e-mail, push, WhatsApp) existe.
- Uso de Redis para notificações é **planejado** (`docs/skills/database-rules.md`: "Redis será usado futuramente para: filas, cache, notificações, jobs assíncronos").

---

## 26. Agenda

**Classificação: parcialmente implementado.**

- Rota `/agenda` → `AgendaView.tsx` ("Central de Contatos"). Agrega, via mock único (`lib/agenda-mock.ts`), contatos de tipos `clientes, fornecedores, usuarios, parceiros, freelancers, transportadoras, leads, outros` (`types/agenda.ts`).
- Busca client-side com normalização de acentos (`normalize()` + `matchesContato`) e filtro por tipo (`AgendaToolbar`) — **busca e filtro funcionam sobre o mock**, mas não foi encontrado botão/fluxo de criação de contato manual (`AgendaToolbar.tsx` só expõe botões de filtro por tipo, não um "Novo contato").
- `docs/requirements/projetos-demandas-dashboard.md` (seção 7) descreve o modelo pretendido (`origemTipo, origemId, empresaId, agenciaId, manual, favorito, ultimaInteracao`) como sugestão futura — os campos `favorito` e `ultimaInteracao` já existem no tipo atual (`types/agenda.ts`), então parte do modelo futuro já foi antecipada no tipo, mesmo sem lógica de "favoritar" implementada na UI (não confirmado se há botão de favoritar funcional).

---

## 27. Central de Tráfego

**Classificação: documentado mas não implementado** (nível mais embrionário: existe apenas como tipo TypeScript comentado, não como requisito textual detalhado).

- Único vestígio: `types/demanda.ts:39-49`, tipo `DemandaSessaoTrabalhoConceitual` (`demandaId, usuarioId, etapaId, inicioEm, pausaEm?, encerradaEm?, statusOrigem`), precedido do comentário explícito: *"Estrutura conceitual para Central de Tráfego futura. Não há cronômetro ou lógica real nesta fase."*
- Esse tipo não é usado em nenhum componente, mock ou array de dados — é puramente declarativo/reservado.
- Não há menção à "Central de Tráfego" em nenhum documento de `docs/` além dessa referência indireta no código.

---

## 28. Controle automático de tempo por status

**Classificação: documentado mas não implementado.**

- Relacionado diretamente à Central de Tráfego (seção 27) e ao conceito de "Prazo de retorno do cliente" descrito em `docs/requirements/projetos-demandas-dashboard.md` (seção 3.4): ação futura "Enviado ao cliente" que dispararia um contador independente, registrando envio/retorno/tempo total — **explicitamente não implementado nesta fase**.
- `DemandaWorkflowEtapa.prazoHoras` e `Demanda.prazoEtapaAtual` já existem como campos estáticos (prazo definido manualmente), mas não há nenhum job, cron, listener ou lógica que calcule tempo decorrido, dispare mudança de status automaticamente, ou persista duração real em cada etapa.
- Nenhum uso de `setInterval`, cron, fila (Redis) ou timestamp de início/fim de etapa foi encontrado além dos tipos conceituais citados.

---

## 29. Filtros

**Classificação: parcialmente implementado.**

- Implementado (client-side, sobre mock): filtro de status em Demandas (`DemandasToolbar`, via `DemandaStatusFiltro`), filtro de tipo em Agenda (`AgendaToolbar`). Presumível padrão semelhante em `ProjetosToolbar` (não lido em detalhe, mas segue mesmo padrão de `WorkspaceToolbar`).
- Documentado como necessidade futura e ainda não implementado: filtros de Kanban por cliente/projeto/responsável/prioridade/atraso/etapa (`docs/requirements/projetos-demandas-dashboard.md`, seção 4) — o Kanban atual (seção 17) não tem nenhum filtro.

---

## 30. Busca

**Classificação: parcialmente implementado.** Busca textual client-side sobre arrays mock, com normalização de acentuação, confirmada em `AgendaView.tsx` (`normalize`, `matchesContato`) e em `DemandasToolbar` (placeholder "Buscar por nome, código, projeto, cliente ou responsáveis" — não confirmado se a lógica de match no `DemandasView` cobre todos esses campos ou só nome). Não há busca full-text real, indexação, nem busca no backend (não existe backend de dados para buscar).

---

## 31. Dashboards

**Classificação: parcialmente implementado (estrutura visual) / inexistente (dados reais).**

- `DashboardView.tsx` compõe: `DashboardGreeting`, `DashboardStats`, `DashboardAgenda`, `DashboardActivities`, `DashboardChart`, `DashboardShortcuts`.
- `DashboardStats.tsx`: números **hardcoded** (`tarefas: 128, projetos: 24, clientes: 86, sla: 97`), não vem nem de mock estruturado nem de agregação real.
- `DashboardChart.tsx`: é literalmente um placeholder visual — "Área reservada para gráfico de desempenho", com comentário `{/* TODO: integrar Chart.js */}` no próprio código. Nenhuma biblioteca de gráfico está instalada ou integrada.
- `/relatorios` é um `EmptyState` puro ("Os relatórios serão criados em fases futuras").
- Os gráficos de gestão pretendidos (pizza por cliente/projeto, barras empilhadas por colaborador, linha de volume histórico) estão **detalhadamente documentados** em `docs/requirements/projetos-demandas-dashboard.md` (seção 5) mas **sem nenhuma implementação, nem mock de dados agregados preparado**.

---

## 32. Documentação existente

**Classificação: implementado** — a documentação é, proporcionalmente, a parte mais madura do repositório.

Inventário:
- `CLAUDE.md` (raiz) — regras de arquitetura, estrutura obrigatória de módulo, estado atual por fase, escopo e fora de escopo.
- `PROJECT_STATUS.md` — histórico de fases concluídas (2 a 3.13) com commits associados, e "Próxima Fase" (3.14 — Departamentos V2) e fases futuras (Workflows reais, Projetos, Backend, Autenticação).
- `docs/CLAUDE.md` — versão mais enxuta/redundante do `CLAUDE.md` raiz, com histórico de fases um pouco diferente (chega até Fase 3.13, mesma info central).
- `docs/database-model.md` — lista conceitual de tabelas (ver seção 4).
- `docs/requirements/projetos-demandas-dashboard.md` — requisito funcional detalhado (o mais rico do repositório) para Projetos, Demandas, Kanban, Workflow, Dashboard, Relatórios e Agenda.
- `docs/skills/` — `architecture.md`, `coding-standards.md`, `database-rules.md`, `taskflow-rules.md`, `ui-boxx.md`, `git-workflow.md`, `produto.md`: skills internas usadas para orientar agentes de IA no projeto.
- `docs/agents/` — perfis de agente (`component-builder.md`, `react-architect.md`, `crud-specialist.md`, `code-reviewer.md`, `docker-guardian.md`, `api-specialist.md`, `ui-guardian.md`) — não lidos em detalhe nesta auditoria (fora do escopo das 33 áreas solicitadas), mas presentes e relevantes para entender o fluxo de trabalho com IA já estabelecido no projeto.
- `legacy/v1/` — documentação da versão anterior do produto (`CLAUDE_v1.md`, `PROJECT_STATUS_v1.md`, `frontend_v1.md`, `clientes_v1.md`, `workflow_v1.md`) — não lida em detalhe; relevante como referência histórica caso o ranking do Flowe precise ser comparado com decisões já tomadas e abandonadas na v1.

**Inconsistência a registrar:** `CLAUDE.md` (raiz) e `docs/CLAUDE.md` coexistem com conteúdo semelhante mas não idêntico — risco de divergência silenciosa se um for atualizado e o outro não.

---

## 33. Arquivos AGENTS.md

**Classificação: implementado**, com uma falha de conteúdo a registrar (achado técnico, não corrigido nesta auditoria por estar fora do escopo/regras da tarefa):

- `AGENTS.md` (raiz): bem formado, define papel do agente, stack, escopo do produto, workflow obrigatório, regras de edição e validações.
- `backend/AGENTS.md` e `frontend/AGENTS.md`: **ambos os arquivos têm, como conteúdo real e commitado, um heredoc de shell não removido** — cada arquivo literalmente começa com `cat > backend/AGENTS.md <<'EOF'` (ou `frontend/AGENTS.md`) na linha 1 e termina com `EOF` na última linha, envolvendo o conteúdo pretendido. Ou seja, o comando usado para *gerar* o arquivo foi commitado junto com o conteúdo, em vez de só o conteúdo. Funcionalmente os dois arquivos ainda comunicam as regras pretendidas (basta ignorar as linhas de heredoc), mas tecnicamente estão malformados como Markdown puro.

---

## Resumo executivo (tabela por área)

| Área | Classificação |
|---|---|
| Frontend (shell/infra) | implementado |
| Backend | estrutura existente |
| Banco de dados (schema) | inexistente / documentado mas não implementado |
| Rotas frontend | implementado |
| Rotas API (backend) | parcialmente implementado (só healthcheck) |
| Models (ORM) | inexistente |
| Schemas (Pydantic) | inexistente |
| Schemas (TypeScript) | implementado |
| APIs de negócio | inexistente |
| Autenticação | inexistente (bloqueado por decisão de fase) |
| Permissões | estrutura existente / documentado mas não implementado |
| Usuários | parcialmente implementado |
| Equipes | parcialmente implementado |
| Departamentos | planejado |
| Clientes | parcialmente implementado |
| Fornecedores | parcialmente implementado |
| Projetos | parcialmente implementado |
| Demandas | parcialmente implementado |
| Kanban | estrutura existente (desconectado do dado real) |
| Workflow | parcialmente implementado (duas versões desconectadas) |
| Responsáveis / múltiplos responsáveis | implementado (mock) |
| Comentários | documentado mas não implementado |
| Anexos | estrutura existente (Projetos) / inexistente (Demandas) |
| Checklists | inexistente |
| Histórico | parcialmente implementado |
| Timeline | inexistente |
| Notificações | parcialmente implementado (preferências, sem motor) |
| Agenda | parcialmente implementado |
| Central de Tráfego | documentado mas não implementado |
| Controle automático de tempo por status | documentado mas não implementado |
| Filtros | parcialmente implementado |
| Busca | parcialmente implementado |
| Dashboards | parcialmente implementado (visual) / inexistente (dados reais) |
| Documentação existente | implementado |
| Arquivos AGENTS.md | implementado (com defeito de conteúdo) |

---

## Pontos de atenção para a próxima etapa (arquitetura)

Sem propor solução — apenas registrando o que a auditoria expõe como decisões pendentes:

1. **Kanban e Workflow existem em versões paralelas e desconectadas** do modelo de dados real (`Demanda`). Qualquer arquitetura nova precisa decidir qual vira a fonte de verdade.
2. **Duas listas de tabelas de banco divergentes** (`docs/database-model.md` vs. `docs/skills/database-rules.md`) e um conceito de `Auditoria`/`Histórico` potencialmente duplicado.
3. **Fornecedores foge do padrão de rota** (`/fornecedores` vs. `/configuracoes/*`).
4. **`CLAUDE.md` duplicado** (raiz e `docs/`) com risco de divergência.
5. **Departamentos** é uma dependência explícita (Fase 3.14) de Usuários, Equipes, Projetos e Demandas, que já referenciam `departamentoId`/`departamentoResponsavelIds` sem o módulo existir.
6. **PII sensível já modelada** (`UsuarioInformacoes`: CPF, dados bancários, PIX) exige atenção de LGPD/segurança quando a persistência real for desenhada.
