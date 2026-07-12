# Flowe — Roadmap Visual Priorizado para o TaskFloww

> Documento revisado a partir de `docs/referencias/flowe-para-taskfloww.md`.
> Escopo: transformar a análise visual e funcional do Flowe em um roadmap priorizado para o TaskFloww V2.
> Esta revisão não altera código, frontend, backend, Docker, banco ou o documento-fonte `flowe-para-taskfloww.md`.

## 1. Elementos para aplicar imediatamente

Itens com menor dependência técnica e boa aderência ao Design System/Workspace Framework já existente no TaskFloww.

- **Resumo do projeto no detalhe da demanda**: confirmado na análise real em `ProjectPanel.tsx` + `CardModal.tsx`; já está alinhado aos requisitos do TaskFloww e pode permanecer como padrão visual/documental antes da persistência real.
- **Prioridade visual alinhada ao TaskFloww**: aproveitar a ideia de borda/badge de `CardView.tsx`, mas manter apenas `baixa`, `media` e `alta`, com cores configuráveis futuramente.
- **Estados vazios padronizados**: aplicar o tom curto e acionável visto em Kanban, checklist, relatórios e agenda do Flowe, mas usando `WorkspaceEmptyState`/`EmptyState` do TaskFloww.
- **Feedback visual consistente**: usar badges, dots, contornos, estados hover e texto auxiliar dentro do Design System atual, sem importar a linguagem glass/macOS do Flowe.
- **Modais/drawers sob um padrão único**: preservar `Modal`, `EntitySidePanel` e `Tabs` como base; evitar repetir a fragmentação do Flowe entre `Modal.tsx`, `dialog.tsx` e `CardModal.tsx`.
- **Seleção pesquisável como evolução do MultiSelect**: o padrão de `SearchSelect.tsx` é útil, mas exige adaptação para acessibilidade e integração com os componentes atuais.

## 2. Elementos para aplicar junto ao Kanban V1

Itens diretamente ligados à futura visualização Kanban. Devem ser aplicados como projeção de Demandas/Workflow, não como um modelo paralelo `Board/Column/Card` copiado do Flowe.

- **Kanban por workflow**: usar `KanbanBoard.tsx`, `ColumnView.tsx` e `CardView.tsx` como referência visual, mas no TaskFloww as colunas devem refletir etapas/status configurados.
- **Cards enxutos com indicadores mínimos**: partir do requisito TaskFloww: nome da demanda, projeto vinculado, prioridade e prazo da etapa atual. Checklist, anexos, timer e tags entram apenas em fases posteriores.
- **Drag-and-drop com `@dnd-kit`**: a análise real confirma uso de `PointerSensor`, `KeyboardSensor` e `activationConstraint` de 6px. Reaproveitar o conceito, mas implementar rollback e feedback de erro.
- **Filtros que desabilitam drag-and-drop**: comportamento confirmado em `KanbanBoard.tsx`; evita reordenação em listas parcialmente ocultas.
- **Limite WIP visual**: confirmado em `ColumnView.tsx`; útil como alerta visual, mas não deve bloquear movimentação no Kanban V1.
- **Coluna de conclusão**: referência útil de `Column.isDone`, mas no TaskFloww deve ser substituída por regra de workflow/status, não por booleano isolado.

## 3. Elementos para aplicar junto à Central de Tráfego

Itens de alto valor operacional, mas dependentes de eventos, workflow persistente e dados confiáveis de tempo/status.

- **Visão pessoal tipo Meu Dia**: presente na análise do Flowe como página inicial agregada; no TaskFloww deve virar uma visão de pauta pessoal baseada em demandas atribuídas à etapa atual.
- **Alertas operacionais derivados**: referência em `AlertsBell`/`/api/alerts`; usar futuramente para atraso, prazo próximo e gargalos, sem implementar notificações reais nesta fase.
- **Tempo automático por status/etapa**: não existe como recurso pronto no Flowe; é uma síntese a partir de workflow/timestamps/timer. No TaskFloww deve derivar do Motor de Eventos.
- **Carga por colaborador e projeto**: visual confirmado no dashboard do Flowe por barras empilhadas; deve alimentar a Central de Tráfego com volume por responsável/departamento.
- **Linha histórica de demandas em fluxo**: confirmada no dashboard do Flowe com janela de 12 semanas; aderente aos requisitos do TaskFloww.

## 4. Elementos que dependem de backend

Itens que não devem virar mock definitivo. A análise real reforça que o Flowe já depende de rotas API e Prisma; no TaskFloww, a versão real deve nascer no backend FastAPI e na tabela `eventos` quando aplicável.

- **Kanban real**: depende de Demandas persistentes, Workflow persistente, transições, permissões e eventos.
- **Checklist persistente**: depende de checklists, itens, templates e auditoria por eventos.
- **Busca global**: depende de endpoint que indexe demandas, projetos, clientes, fornecedores e usuários; o Flowe busca quadros/demandas via `SidebarSearch.tsx` e `/api/search`.
- **Dashboard de gestão**: depende de agregações sobre Demandas, Projetos, responsáveis, Workflow e Eventos.
- **Relatórios operacionais**: dependem de queries reais, exportação e permissões; a referência do Flowe é `relatorios/page.tsx`, `lib/reports.ts` e rotas `/api/reports`.
- **Agenda híbrida**: depende da modelagem TaskFloww de contatos automáticos/manuais; o Flowe cobre mais calendário/reuniões que agenda de contatos.
- **Responsáveis por etapa**: depende de usuários, departamentos/equipes e relações por IDs em Demandas/Workflow.

## 5. Elementos que não devem ser copiados

- **`CardModal.tsx` monolítico**: a análise real identifica alto valor funcional, mas risco de manutenção por concentrar abas, anexos, checklist, workflow, custos e atividade.
- **Board como projeto**: `ProjectPanel.tsx` é valioso, mas o TaskFloww já define Projeto como entidade própria; Kanban deve ser visualização.
- **Métricas financeiras/custos/fee no núcleo**: aparecem no Flowe, mas TaskFloww não é ERP e não deve trazer financeiro sem fase explícita.
- **Carregamento integral do board**: o Flowe carrega a árvore do board; o TaskFloww deve prever paginação/consulta por coluna.
- **Drag-and-drop sem rollback robusto**: atualização otimista do Flowe precisa ser redesenhada para falhas de rede/API.
- **Múltiplos padrões de overlay**: evitar a coexistência descoordenada de modal base, dialog, popover e card modal.
- **Linguagem visual glass/macOS como padrão**: decisão estética do Flowe; no TaskFloww deve ser avaliada contra o Design System existente.
- **Prioridade `urgente`**: o Flowe usa quatro níveis; o TaskFloww tem três níveis documentados.

## 6. Riscos de inconsistência visual

- **Cards carregados demais**: `CardView.tsx` combina cliente, prioridade, tags, etapas, checklist, anexos, timer e avatares; o TaskFloww deve manter card enxuto.
- **Cores divergentes de prioridade**: Flowe usa vermelho/laranja/azul/cinza; TaskFloww requer baixa/média/alta em tons de azul configuráveis.
- **Overlays concorrentes**: replicar `Modal`, `dialog` e `CardModal` sem base única criaria inconsistência.
- **Estados vazios sem componente**: a análise confirma boas mensagens no Flowe, mas espalhadas por vários arquivos.
- **Dashboard como ilha visual**: gráficos SVG customizados são úteis, mas devem seguir `WorkspaceStats`, `WorkspaceSection` e tokens visuais do TaskFloww.
- **Kanban mobile pesado**: o Flowe usa scroll horizontal; o TaskFloww deve avaliar uma lista por etapa no mobile.
- **Feedback apenas por cor**: pontos, badges e bordas precisam ter texto/ícone para acessibilidade.
- **Termos de domínio divergentes**: Flowe usa `Board`, `Column`, `Card`; TaskFloww deve manter `Projeto`, `Demanda`, `Workflow` e `Etapa`.

## 7. Componentes existentes do TaskFloww que podem ser reutilizados

- `WorkspacePage`: base para Demandas, Projetos, Kanban, Dashboard e Relatórios.
- `WorkspaceStats`: KPIs e cards de resumo.
- `WorkspaceToolbar`: busca, filtros e ações primárias.
- `WorkspaceTable`: listagens operacionais antes ou ao lado do Kanban.
- `WorkspaceEmptyState`: estados vazios padronizados.
- `WorkspaceSection`: blocos de conteúdo e seções de dashboard/relatórios.
- `PageHeader`: cabeçalhos consistentes.
- `Button`: ações principais e secundárias.
- `Card`: itens repetidos e painéis pontuais.
- `Input`, `Select`, `Textarea`: formulários e filtros.
- `Badge`: status, prioridade, alerta e etapa.
- `MultiSelect`: base para responsáveis múltiplos; pode evoluir para seleção pesquisável inspirada no `SearchSelect`.
- `Modal`: cadastros e confirmações simples.
- `EntitySidePanel`: detalhes de Projeto/Demanda em painel lateral amplo.
- `Tabs`: organização de Dados, Briefing/Resumo, Workflow, Responsáveis, Equipe, Arquivos e Histórico.

## Tabela de priorização

| Elemento | Tela de origem no Flowe | Valor para o TaskFloww | Componente do TaskFloww afetado | Dependência técnica | Complexidade | Fase recomendada | Prioridade |
|---|---|---|---|---|---|---|---|
| Resumo do projeto na demanda | `ProjectPanel.tsx` + `CardModal.tsx` | Contexto operacional direto para execução da demanda | `ProjetoDetailsDrawer`, `DemandaDetailsDrawer`, `EntitySidePanel` | Projeto mock agora; backend depois | Baixa | Imediata e Projetos/Demandas V2 | Alta |
| Prioridade visual | `PRIORITIES`, `CardView.tsx` | Triagem rápida em tabela e Kanban | `Badge`, card Kanban futuro, `DemandasTable` | Campo prioridade | Baixa | Imediata/Kanban V1 | Alta |
| Estados vazios padronizados | `ColumnView.tsx`, `CardModal.tsx`, `SearchSelect.tsx`, `relatorios/page.tsx`, `calendario/page.tsx` | Clareza em telas sem dados | `WorkspaceEmptyState` | Nenhuma | Baixa | Imediata | Média |
| Feedback visual com badge/dot/contorno | `CardView.tsx`, `ColumnView.tsx`, `AppShell.tsx`, `dialog.tsx` | Escaneabilidade operacional | `Badge`, `Card`, `WorkspaceTable` | Dados de status/prazo quando existirem | Baixa | Imediata e contínua | Média |
| Seleção pesquisável | `SearchSelect.tsx` | Reduz fricção em responsáveis, clientes e filtros | `MultiSelect`, `Select`, filtros de toolbar | Nenhuma inicial; API depois | Média | Imediata incremental | Alta |
| Modal/drawer padronizado | `Modal.tsx`, `dialog.tsx`, `CardModal.tsx` | Mantém detalhe sem sair da rota | `Modal`, `EntitySidePanel`, `Tabs` | Dados do módulo | Média | Contínua/Demandas V2 | Média |
| Kanban por workflow | `KanbanBoard.tsx`, `ColumnView.tsx` | Base visual de operação | Nova view Kanban, `WorkspacePage` | Demandas + Workflow + eventos | Alta | Kanban V1 | Alta |
| Card enxuto com prazo atual | `CardView.tsx` | Mostra o essencial ao colaborador | Card Kanban futuro | Etapa atual e prazo | Média | Kanban V1 | Alta |
| Drag-and-drop acessível | `KanbanBoard.tsx`, `/api/cards/move/route.ts` | Movimentação visual por etapa | Kanban futuro | Endpoint transacional e rollback | Alta | Kanban V1 | Alta |
| Filtros no Kanban | `KanbanBoard.tsx`, `SearchSelect.tsx` | Reduz ruído e melhora foco | `WorkspaceToolbar` | API filtrável futura | Média | Kanban V1 | Alta |
| WIP visual | `ColumnView.tsx` | Indica gargalo por coluna/etapa | Coluna Kanban futura | Contagem por etapa | Média | Kanban V1.1 | Média |
| Checklist com progresso | `CardModal.tsx` (`ChecklistsSection`) | Decompõe demanda em passos | Aba futura de Demanda | Checklist backend e eventos | Média | Demandas V2 | Alta |
| Modelos de checklist | `CardModal.tsx`, `/api/checklist-templates` | Padroniza tarefas recorrentes | Demandas/Modelo Campanha | Templates persistentes | Média | Pós-checklist | Média |
| Busca global | `SidebarSearch.tsx`, `/api/search` | Encontra demandas/projetos rapidamente | Header/busca global futura | Endpoint de busca | Média | Pós-CRUD real | Alta |
| Agenda/calendário operacional | `calendario/page.tsx`, `/api/events` | Apoia prazos, reuniões e visão mensal | Agenda futura | Eventos/contatos | Média | Agenda V2 | Média |
| Dashboard rosca por projeto | `dashboard/page.tsx` | Identifica projetos que mais demandam | Dashboard gestão | Agregações de demandas | Média | Dashboard V1 | Alta |
| Barras projeto x colaborador | `dashboard/page.tsx` | Mostra carga por responsável | Dashboard gestão | Responsáveis reais | Média | Dashboard V1 | Alta |
| Linha histórica 12 semanas | `dashboard/page.tsx` | Mostra evolução do fluxo | Dashboard gestão/Central de Tráfego | Eventos e timestamps | Média | Central de Tráfego | Alta |
| Relatórios com catálogo e CSV | `relatorios/page.tsx`, `lib/reports.ts` | Organiza análises operacionais | Relatórios | Backend de relatórios | Média | Relatórios V1 | Alta |
| Múltiplos responsáveis | `cadastros/equipe/page.tsx`, `AvatarStack`, `CardDTO.assignees` | Apoia colaboração e carga de trabalho | Demandas, Workflow, `MultiSelect` | Usuários/departamentos | Média | Demandas reais | Alta |
| Alertas operacionais | `AppShell.tsx` (`AlertsBell`) | Sinaliza atraso e risco | Header/notificações futuras | Eventos, prazos e permissões | Alta | Central de Tráfego | Alta |
| Meu Dia | página inicial do Flowe citada na análise | Pauta pessoal por prioridade/prazo | Dashboard pessoal futuro | Demandas atribuídas | Alta | Central de Tráfego | Alta |
| Tempo automático por status | Síntese documentada, não recurso pronto | Base para SLA/produtividade | Central de Tráfego, Eventos | Eventos de transição | Alta | Central de Tráfego | Alta |
| Tema/glass visual | `app/globals.css` | Diferencia aparência, mas é decisão de marca | Design System | Decisão visual | Baixa | Avaliar depois | Baixa |
| Métricas financeiras | Dashboard/relatórios/custos | Fora do foco operacional atual | Nenhum no core | Financeiro/ERP | Alta | Não aplicar | Baixa |

## 5 elementos com maior retorno e menor risco

1. **Resumo do projeto na demanda**
   - Confirmado no Flowe por `ProjectPanel.tsx` + `CardModal.tsx`, já previsto nos requisitos do TaskFloww e de baixa complexidade visual.

2. **Prioridade visual alinhada ao TaskFloww**
   - A borda/badge do Flowe tem alto valor e baixo risco, desde que mantidos os três níveis oficiais do TaskFloww.

3. **Estados vazios padronizados**
   - A análise real classifica a prioridade como média, mas o custo é muito baixo e o retorno de polimento é alto; deve entrar cedo via `WorkspaceEmptyState`.

4. **Feedback visual com badges/dots/contornos**
   - Fácil de aplicar sobre componentes existentes e melhora leitura de status, prazo e prioridade sem depender de backend novo em telas mock.

5. **Seleção pesquisável para responsáveis e filtros**
   - O `SearchSelect` do Flowe é uma referência forte; no TaskFloww deve evoluir o `MultiSelect` sem criar dependência externa.

## Confirmação

Este documento é apenas planejamento visual e funcional, revisado contra `docs/referencias/flowe-para-taskfloww.md`. Nenhum frontend, backend, Docker ou banco foi alterado. Nenhum commit foi realizado.
