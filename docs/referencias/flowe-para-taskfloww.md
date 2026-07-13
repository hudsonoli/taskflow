# Flowe para TaskFloww V2 — análise visual e funcional

> Análise somente documental. Nenhum código, banco, Docker ou arquivo do Flowe foi alterado ou copiado.
> Origem analisada: `/docker/laboratorios/flowe-lab`.
> Objetivo: identificar padrões úteis do Flowe para futura aplicação no TaskFloww V2, respeitando o Workspace Framework, o Design System e a arquitetura backend/eventos do TaskFloww.

## Premissas

- O Flowe é uma aplicação Next.js com Prisma, rotas API internas e frontend integrado ao mesmo projeto.
- O TaskFloww V2 segue outra arquitetura: frontend Next.js mock em evolução, backend FastAPI, PostgreSQL, Redis e Motor de Eventos em fase inicial.
- Nenhum arquivo do Flowe deve ser copiado diretamente. A recomendação é reaproveitar conceitos e decisões de UX, não implementação literal.
- Recursos com dependência de backend devem ser tratados como fases futuras, especialmente Kanban real, workflow persistente, RBAC e Central de Tráfego.

## 1. Navegação e layout

- **Onde está no Flowe:** shell principal com sidebar, header, seletor de agência e menu de usuário.
- **Arquivo/componente relacionado:** `/docker/laboratorios/flowe-lab/components/AppShell.tsx`, `/docker/laboratorios/flowe-lab/app/(app)/layout.tsx`.
- **Como funciona:** sidebar desktop recolhível, drawer mobile, grupos de navegação, busca na sidebar, menu de quadros, tema claro/escuro/sistema, seletor de agência no header, sino de alertas e cronômetro global.
- **Valor potencial para o TaskFloww:** alto para navegação operacional; o seletor de agência reforça multiempresa e o header com alertas/cronômetro prepara futuras operações em tempo real.
- **Riscos de copiar diretamente:** o Flowe mistura navegação, estado global, alertas, timer e criação de quadro no mesmo componente; isso conflita com a separação por módulos do TaskFloww.
- **Adaptação recomendada:** manter a ideia de shell operacional denso, mas dividir em componentes menores: `Sidebar`, `Header`, `AgencySwitcher`, `AlertsBell`, `GlobalTimer` e busca global; respeitar permissões futuras ocultando itens sem acesso.
- **Dependências de backend:** agências, sessão/autenticação, permissões, alertas, timer.
- **Fase sugerida:** Shell operacional pós-auth.
- **Prioridade:** alta.

## 2. Kanban

- **Onde está no Flowe:** quadro principal por board, com colunas e cards.
- **Arquivo/componente relacionado:** `/components/kanban/KanbanBoard.tsx`, `/components/kanban/ColumnView.tsx`, `/components/kanban/CardView.tsx`, `/app/api/boards/[id]/route.ts`.
- **Como funciona:** carrega o board completo, renderiza colunas horizontais, cards verticais, permite nova coluna, nova demanda, colunas recolhíveis, limite WIP visual e coluna de conclusão.
- **Valor potencial para o TaskFloww:** base direta para Kanban por projeto, equipe e colaborador; reforça fluxo visual de demandas.
- **Riscos de copiar diretamente:** board inteiro é carregado em memória, sem paginação/virtualização; pode não escalar. O conceito `Board/Column/Card` precisa ser reconciliado com Demandas, Workflow e Projetos do TaskFloww.
- **Adaptação recomendada:** usar Kanban como projeção de Demandas/Workflow, não como entidade paralela. Começar por colunas derivadas de etapas configuradas e prever paginação por coluna.
- **Dependências de backend:** Demandas persistentes, workflow persistente, consulta por etapa, permissões, eventos de transição.
- **Fase sugerida:** após CRUD real de Demandas e Workflow.
- **Prioridade:** alta.

## 3. Cards de demanda

- **Onde está no Flowe:** cards dentro das colunas do Kanban.
- **Arquivo/componente relacionado:** `/components/kanban/CardView.tsx`, `/lib/types.ts` (`CardDTO`, `PRIORITIES`, `checklistTotals`, `trackedSeconds`).
- **Como funciona:** exibe cliente, prioridade, título, tags, etapa atual, prazo, checklist, anexos, cronômetro e avatares dos responsáveis; prioridade aparece como borda lateral colorida e badge.
- **Valor potencial para o TaskFloww:** alto para cards enxutos com sinais operacionais fortes. Os indicadores de prazo, responsáveis e checklist reduzem abertura desnecessária de detalhes.
- **Riscos de copiar diretamente:** o card do Flowe concentra muitos indicadores e pode contrariar o requisito do TaskFloww de cards enxutos. O Flowe inclui cronômetro e anexos no card, que ainda estão fora de escopo em fases atuais.
- **Adaptação recomendada:** manter o card do TaskFloww com nome, projeto, prioridade e prazo da etapa atual; adicionar indicadores progressivamente por permissão/configuração, evitando excesso visual.
- **Dependências de backend:** Demandas, responsáveis, prioridade, prazo por etapa, checklist, anexos, timer futuro.
- **Fase sugerida:** Kanban V1 e evolução de cards.
- **Prioridade:** alta.

## 4. Drag-and-drop

- **Onde está no Flowe:** movimentação de cards e colunas no Kanban.
- **Arquivo/componente relacionado:** `/components/kanban/KanbanBoard.tsx`, `/app/api/cards/move/route.ts`, `/app/api/columns/reorder/route.ts`.
- **Como funciona:** usa `@dnd-kit/core` e `@dnd-kit/sortable`, com `PointerSensor`, `KeyboardSensor`, `activationConstraint` de 6px, atualização otimista no `onDragOver` e persistência via API no `onDragEnd`.
- **Valor potencial para o TaskFloww:** biblioteca e padrão adequados para Kanban acessível, inclusive por teclado.
- **Riscos de copiar diretamente:** ausência de rollback robusto se a confirmação falhar; atualização de posições em lote por múltiplos updates individuais pode escalar mal.
- **Adaptação recomendada:** usar `@dnd-kit`, mas implementar rollback explícito, feedback de erro, eventos de workflow e persistência transacional no backend. Desabilitar DnD com filtros ativos é uma boa regra a preservar.
- **Dependências de backend:** endpoint de transição/reordenação, eventos, controle de permissão, consistência de etapa atual.
- **Fase sugerida:** Kanban real após Workflow persistente.
- **Prioridade:** alta.

## 5. Checklist

- **Onde está no Flowe:** aba Detalhes do modal da demanda.
- **Arquivo/componente relacionado:** `/components/CardModal.tsx` (`ChecklistsSection`, `ChecklistBlock`), `/app/api/checklists/route.ts`, `/app/api/checklist/route.ts`, `/app/api/checklist-templates/route.ts`.
- **Como funciona:** permite múltiplos checklists por card, itens marcáveis, progresso visual, comentários por item, criação em branco ou por modelo, salvar checklist como modelo.
- **Valor potencial para o TaskFloww:** muito alto para decompor demandas sem transformar cada item em demanda separada.
- **Riscos de copiar diretamente:** lógica está embutida no `CardModal`, dificultando manutenção. Modelos e escopo precisam respeitar empresa/agência.
- **Adaptação recomendada:** criar componentes separados para `ChecklistSection`, `ChecklistBlock` e `ChecklistItem`; auditar alterações via Motor de Eventos; prever modelos por empresa/agência.
- **Dependências de backend:** tabela/modelo de checklist, itens, templates, eventos, permissões.
- **Fase sugerida:** Demandas V2 ou Kanban V1.1.
- **Prioridade:** alta.

## 6. Detalhes da demanda

- **Onde está no Flowe:** modal amplo de card/demanda.
- **Arquivo/componente relacionado:** `/components/CardModal.tsx`, `/components/WorkflowSection.tsx`, `/components/CatalogSection.tsx`, `/components/MediaSection.tsx`.
- **Como funciona:** modal com abas `Detalhes`, `Fluxo`, `Peças`, `Custos` e `Atividade`; inclui resumo do projeto, descrição rich text, links, anexos, checklists, mídia/PIT/OC, custos para gestores e comentários.
- **Valor potencial para o TaskFloww:** confirma a direção de drawer/modal amplo por demanda, com abas e contexto do projeto visível.
- **Riscos de copiar diretamente:** `CardModal.tsx` é monolítico e mistura múltiplos domínios; acessibilidade e foco precisam ser melhorados; custos/financeiro não fazem parte do escopo central do TaskFloww.
- **Adaptação recomendada:** manter drawer lateral grande com abas, mas quebrar por seção. No TaskFloww, priorizar `Dados`, `Briefing`, `Workflow`, `Responsáveis`, `Histórico` e depois checklist/anexos.
- **Dependências de backend:** Demandas, Projetos, Workflow, eventos/timeline, anexos futuros, permissões.
- **Fase sugerida:** Demandas V2 e Workflow/Kanban.
- **Prioridade:** alta.

## 7. Projetos

- **Onde está no Flowe:** painel de projeto ligado ao board.
- **Arquivo/componente relacionado:** `/components/kanban/ProjectPanel.tsx`, `/app/api/board-templates/route.ts`, `/app/api/boards/[id]/apply-template/route.ts`.
- **Como funciona:** botão `Projeto` abre painel com resumo rich text do projeto e modelos de projeto/backlog; pode salvar demandas atuais como modelo e aplicar modelo criando demandas.
- **Valor potencial para o TaskFloww:** muito aderente ao requisito já documentado de Resumo do Projeto e Modelo de Campanha.
- **Riscos de copiar diretamente:** Flowe acopla projeto ao board; TaskFloww já trata Projeto como entidade operacional maior, com backlog/modelo e vínculo futuro Publi/PIT/OC.
- **Adaptação recomendada:** manter o conceito, mas no TaskFloww o Projeto deve ser entidade própria; o Kanban deve ser uma visualização do projeto, não o projeto em si.
- **Dependências de backend:** Projeto persistente, modelo de campanha/backlog, geração futura de demandas, eventos.
- **Fase sugerida:** Projetos V2 e Demandas persistentes.
- **Prioridade:** alta.

## 8. Filtros

- **Onde está no Flowe:** toolbar do Kanban e seções do dashboard.
- **Arquivo/componente relacionado:** `/components/kanban/KanbanBoard.tsx`, `/components/SearchSelect.tsx`, `/app/(app)/dashboard/page.tsx`.
- **Como funciona:** busca local no quadro, filtro `Minhas demandas`, filtro por cliente, toggle para ocultar capas; filtros ativos desabilitam drag-and-drop e mostram quantos cards ficaram ocultos.
- **Valor potencial para o TaskFloww:** alto, especialmente filtros por cliente, projeto, responsável, prioridade, atraso e etapa.
- **Riscos de copiar diretamente:** filtros client-side só funcionam bem quando todo o dataset já está carregado; TaskFloww precisará server-side em produção.
- **Adaptação recomendada:** começar local/mock nas fases de UI, mas desenhar contrato de filtros no backend desde a persistência real; manter a regra de DnD desabilitado com filtros ativos.
- **Dependências de backend:** endpoints paginados/filtráveis, índices, permissões.
- **Fase sugerida:** Kanban V1 e API de Demandas.
- **Prioridade:** alta.

## 9. Busca

- **Onde está no Flowe:** busca global na sidebar e selects pesquisáveis.
- **Arquivo/componente relacionado:** `/components/SidebarSearch.tsx`, `/components/SearchSelect.tsx`, `/app/api/search/route.ts`.
- **Como funciona:** sidebar com debounce de 250ms e mínimo de 2 caracteres; agrupa resultados de quadros e demandas; `SearchSelect` reutilizável suporta single/multiple, busca com normalização de acentos e navegação por teclado.
- **Valor potencial para o TaskFloww:** alto para encontrar demandas, projetos, clientes, fornecedores e usuários rapidamente.
- **Riscos de copiar diretamente:** busca global some quando sidebar recolhida; escopo do Flowe é estreito; falta rótulo acessível em `SearchSelect`.
- **Adaptação recomendada:** criar busca global sempre acessível no header ou command palette; ampliar escopo; evoluir `MultiSelect` do TaskFloww para seleção pesquisável acessível.
- **Dependências de backend:** endpoint de busca global, índices textuais ou consultas dedicadas por módulo.
- **Fase sugerida:** pós-CRUD real de entidades principais.
- **Prioridade:** alta.

## 10. Agenda/contatos

- **Onde está no Flowe:** calendário editorial e eventos/reuniões.
- **Arquivo/componente relacionado:** `/app/(app)/calendario/page.tsx`, `/app/api/events/route.ts`, `/lib/events.ts`, `/lib/calendar-items.ts`.
- **Como funciona:** visão mensal desktop, lista mobile, cards por prazo, reuniões/eventos, veiculações de mídia, próximos eventos, modal para criar/editar reunião com cliente, participantes, link e observações.
- **Valor potencial para o TaskFloww:** bom para Agenda híbrida, mas o TaskFloww também precisa central de contatos automáticos/manuais.
- **Riscos de copiar diretamente:** Flowe foca calendário, não agenda de contatos; carrega boards para compor cards por prazo; integração mídia é específica.
- **Adaptação recomendada:** separar Agenda de Contatos e Calendário Operacional. Reaproveitar a ideia de visão mensal + lista mobile, mas manter contatos editados em módulos de origem conforme requisito TaskFloww.
- **Dependências de backend:** eventos/reuniões, contatos, clientes/fornecedores/usuários, permissões, integração calendário futura.
- **Fase sugerida:** Agenda V2 e calendário futuro.
- **Prioridade:** média.

## 11. Dashboard

- **Onde está no Flowe:** página de dashboard operacional/financeiro.
- **Arquivo/componente relacionado:** `/app/(app)/dashboard/page.tsx`, `/app/api/dashboard/route.ts`.
- **Como funciona:** KPIs por período, exportação CSV, visão por todas as agências para dono, gráficos SVG customizados, consumo de fee, rankings por cliente, equipe, quadros e fornecedores, seção `Projetos — carga e fluxo` com rosca, barras empilhadas e linha de 12 semanas.
- **Valor potencial para o TaskFloww:** alto para os requisitos de dashboard de gestão: status por cliente/projeto, volume por projeto/colaborador e volume histórico.
- **Riscos de copiar diretamente:** inclui métricas financeiras fora do foco atual do TaskFloww; algumas agregações parecem em memória; gráficos customizados podem crescer em complexidade.
- **Adaptação recomendada:** reaproveitar os três padrões visuais principais: rosca por projeto, barras empilhadas por colaborador e linha histórica. Remover financeiro no núcleo operacional e basear métricas em eventos/timeline.
- **Dependências de backend:** eventos, demandas, projetos, colaboradores, agregações SQL, permissões de gestor.
- **Fase sugerida:** Dashboard pós-Demandas/Workflow/Eventos.
- **Prioridade:** alta.

## 12. Relatórios

- **Onde está no Flowe:** tela de relatórios e exportação CSV.
- **Arquivo/componente relacionado:** `/app/(app)/relatorios/page.tsx`, `/lib/reports.ts`, `/app/api/reports/route.ts`, `/app/api/reports/export/route.ts`.
- **Como funciona:** acesso restrito a gestores, seleção de relatório por grupo, filtro de período, opção de todas as agências para dono, tabela responsiva, notas de leitura e exportação CSV.
- **Valor potencial para o TaskFloww:** alto para relatórios operacionais e análises de projeto/colaborador.
- **Riscos de copiar diretamente:** mistura relatórios financeiros e operacionais; permissões são do modelo Flowe; relatório depende de dados persistidos que TaskFloww ainda está estruturando.
- **Adaptação recomendada:** manter estrutura de catálogo de relatórios, notas explicativas e CSV; começar pelos relatórios definidos em requisitos: análise de projeto, peças por projeto e performance de colaborador.
- **Dependências de backend:** Motor de Eventos, Demandas, Workflow, Projetos, agregações, permissões.
- **Fase sugerida:** Relatórios V1 após eventos e demandas reais.
- **Prioridade:** alta.

## 13. Responsáveis e equipes

- **Onde está no Flowe:** cadastro de equipe e responsáveis por card.
- **Arquivo/componente relacionado:** `/app/(app)/cadastros/equipe/page.tsx`, `/components/ui.tsx` (`AvatarStack`), `/lib/types.ts` (`CardDTO.assignees`).
- **Como funciona:** equipe com usuários, perfis simples (`dono`, `gestor`, `equipe`), vínculo com agência, status ativo/inativo, primeiro acesso, valor/hora, cor/avatar; cards aceitam múltiplos responsáveis.
- **Valor potencial para o TaskFloww:** muito alto para múltiplos responsáveis e visualização de carga.
- **Riscos de copiar diretamente:** Flowe não tem departamento/equipe como nível intermediário completo; TaskFloww já prevê múltiplos usuários e departamentos responsáveis.
- **Adaptação recomendada:** manter múltiplos usuários por demanda e avatares, mas modelar também departamentos/equipes como IDs principais. Não importar valor/hora no núcleo inicial se for fora do escopo.
- **Dependências de backend:** usuários, departamentos/equipes, permissões, vínculo por demanda e etapa de workflow.
- **Fase sugerida:** Usuários/Equipes reais e Demandas persistentes.
- **Prioridade:** alta.

## 14. Prioridades

- **Onde está no Flowe:** tipo e visual dos cards.
- **Arquivo/componente relacionado:** `/lib/types.ts` (`PRIORITIES`), `/components/kanban/CardView.tsx`.
- **Como funciona:** quatro níveis (`urgente`, `alta`, `media`, `baixa`) com label, cor e peso; card usa borda lateral e badge.
- **Valor potencial para o TaskFloww:** alto para leitura rápida do Kanban.
- **Riscos de copiar diretamente:** TaskFloww definiu três níveis (`baixa`, `media`, `alta`) e regras visuais em tons de azul. `urgente` não está no requisito atual.
- **Adaptação recomendada:** manter o padrão visual de borda/badge, mas usar exatamente os níveis do TaskFloww e cores configuráveis futuramente.
- **Dependências de backend:** campo prioridade em demanda, configuração futura de cores.
- **Fase sugerida:** Demandas V1/V2 e Kanban.
- **Prioridade:** alta.

## 15. Feedback visual

- **Onde está no Flowe:** cards, colunas, dashboard, alertas e diálogos.
- **Arquivo/componente relacionado:** `/components/kanban/CardView.tsx`, `/components/kanban/ColumnView.tsx`, `/components/AppShell.tsx`, `/components/dialog.tsx`, `/app/globals.css`.
- **Como funciona:** badges, dots coloridos, WIP em vermelho, alerta de atraso, pulse dot para timer/cliente aguardando, estados hover, `glass-panel`, feedback de sucesso pontual e diálogos customizados.
- **Valor potencial para o TaskFloww:** alto para tornar operação escaneável e reduzir ambiguidade.
- **Riscos de copiar diretamente:** linguagem visual glass/macOS pode não combinar com TaskFloww; feedback por cor precisa de texto/ícone para acessibilidade.
- **Adaptação recomendada:** usar padrões de feedback discretos dentro do Design System do TaskFloww: badge + ícone + cor, não apenas cor. Evitar visual glass se conflitar com a identidade atual.
- **Dependências de backend:** alertas, status, prazo, timer e eventos futuros.
- **Fase sugerida:** contínua, a partir dos módulos operacionais.
- **Prioridade:** média.

## 16. Modais e drawers

- **Onde está no Flowe:** modal base, diálogo global, modal de demanda, modais de cadastro e evento.
- **Arquivo/componente relacionado:** `/components/Modal.tsx`, `/components/dialog.tsx`, `/components/CardModal.tsx`, páginas de cadastros.
- **Como funciona:** `Modal` usa overlay e cartão central; `DialogProvider` substitui `confirm/alert`; `CardModal` é um modal grande com abas; alguns painéis são popovers/drawers leves.
- **Valor potencial para o TaskFloww:** bom para confirmações consistentes e detalhes amplos.
- **Riscos de copiar diretamente:** há três padrões de overlay; modal base não tem foco preso completo; `CardModal` é monolítico.
- **Adaptação recomendada:** no TaskFloww, manter `Modal` e `EntitySidePanel` existentes como fonte única; adicionar um serviço de confirmação/toast genérico depois. Usar drawer lateral grande para detalhes de demanda/projeto.
- **Dependências de backend:** nenhuma para UI; dados reais por módulo quando conectado.
- **Fase sugerida:** UI framework contínuo.
- **Prioridade:** média.

## 17. Estados vazios

- **Onde está no Flowe:** Kanban, checklist, dashboard, relatórios, agenda, selects.
- **Arquivo/componente relacionado:** `/components/kanban/ColumnView.tsx`, `/components/CardModal.tsx`, `/components/SearchSelect.tsx`, `/app/(app)/relatorios/page.tsx`, `/app/(app)/calendario/page.tsx`.
- **Como funciona:** mensagens curtas e acionáveis: `Nenhum checklist — crie um...`, `Nada encontrado`, `Sem dados para este relatório...`, `Nenhuma demanda ou reunião...`.
- **Valor potencial para o TaskFloww:** médio/alto para reduzir sensação de tela quebrada.
- **Riscos de copiar diretamente:** mensagens ficam espalhadas, sem componente único; algumas não têm ação explícita.
- **Adaptação recomendada:** usar `WorkspaceEmptyState`/`EmptyState` do TaskFloww com título, descrição e ação opcional; padronizar tom de voz.
- **Dependências de backend:** nenhuma.
- **Fase sugerida:** imediata em todos os módulos UI.
- **Prioridade:** média.

## 18. Responsividade

- **Onde está no Flowe:** shell, Kanban e calendário.
- **Arquivo/componente relacionado:** `/components/AppShell.tsx`, `/components/kanban/KanbanBoard.tsx`, `/app/(app)/calendario/page.tsx`, `/app/(app)/dashboard/page.tsx`.
- **Como funciona:** sidebar vira drawer mobile, header compacta itens, Kanban usa scroll horizontal, calendário alterna grade desktop para lista mobile, dashboards usam grids responsivos.
- **Valor potencial para o TaskFloww:** alto para uso operacional em notebooks e consultas rápidas em celular.
- **Riscos de copiar diretamente:** Kanban horizontal em mobile pode ser pesado; modais longos em telas pequenas podem dificultar edição.
- **Adaptação recomendada:** manter drawer mobile e listas alternativas para telas pequenas; para Kanban mobile, considerar visão de lista/etapa em vez de reproduzir board completo.
- **Dependências de backend:** nenhuma direta.
- **Fase sugerida:** contínua desde UI V1.
- **Prioridade:** alta.

## Síntese de recomendações

1. **Adotar como conceito:** Kanban por colunas, `@dnd-kit`, múltiplos responsáveis, checklist com progresso, busca global, `SearchSelect`, resumo do projeto no detalhe da demanda, relatórios exportáveis e dashboard com rosca/barras/linha.
2. **Adaptar antes de implementar:** drag-and-drop com rollback, Kanban como projeção de Workflow/Demandas, modais quebrados em componentes menores, filtros server-side em produção, estados vazios componentizados e prioridades conforme requisito TaskFloww.
3. **Evitar copiar diretamente:** `CardModal` monolítico, métricas financeiras, acoplamento board=projeto, carregamento integral do board, overlays múltiplos sem padrão único e linguagem visual glass sem decisão de marca.
4. **Depender de backend futuro:** Kanban real, checklist persistente, relatórios, dashboard, busca global, timeline operacional, workflow e Central de Tráfego devem nascer sobre entidades reais e Motor de Eventos.

## Matriz final

| Elemento | Origem no Flowe | Aplicar no TaskFloww? | Adaptação | Dependências | Fase | Prioridade |
|---|---|---|---|---|---|---|
| Navegação e layout | `AppShell.tsx` | Sim | Separar shell, alertas, timer, agência e busca em componentes menores | Auth, agências, permissões, alertas | Shell pós-auth | Alta |
| Kanban | `KanbanBoard.tsx`, `ColumnView.tsx` | Sim | Usar como projeção de Demandas/Workflow, com paginação por coluna | Demandas, Workflow, eventos | Kanban real | Alta |
| Cards de demanda | `CardView.tsx` | Sim | Manter enxuto e adicionar indicadores por fase/configuração | Demandas, prioridade, prazo, responsáveis | Kanban V1 | Alta |
| Drag-and-drop | `KanbanBoard.tsx`, `/api/cards/move` | Sim | Usar `@dnd-kit` com rollback e eventos transacionais | Workflow, endpoints de transição | Kanban real | Alta |
| Checklist | `CardModal.tsx`, APIs de checklist | Sim | Componentizar e auditar por eventos | Checklist, templates, eventos | Demandas V2 | Alta |
| Detalhes da demanda | `CardModal.tsx` | Sim | Drawer amplo com abas menores e acessíveis | Demandas, Projeto, Workflow, timeline | Demandas V2 | Alta |
| Projetos | `ProjectPanel.tsx` | Sim | Projeto como entidade própria, não board | Projetos, backlog, eventos | Projetos V2 | Alta |
| Filtros | `KanbanBoard.tsx`, `SearchSelect.tsx` | Sim | Client-side no mock; server-side em produção | Índices e APIs filtráveis | Kanban/API | Alta |
| Busca | `SidebarSearch.tsx`, `/api/search` | Sim | Busca global no header/command palette e escopo ampliado | Endpoint de busca | Pós-CRUD real | Alta |
| Agenda/contatos | `calendario/page.tsx` | Parcial | Separar contatos da agenda/calendário operacional | Eventos, contatos, clientes | Agenda V2 | Média |
| Dashboard | `dashboard/page.tsx` | Sim | Usar gráficos operacionais sem financeiro inicial | Eventos, demandas, projetos | Dashboard gestão | Alta |
| Relatórios | `relatorios/page.tsx`, `lib/reports.ts` | Sim | Catálogo de relatórios operacionais e CSV | Eventos, agregações, RBAC | Relatórios V1 | Alta |
| Responsáveis e equipes | `cadastros/equipe/page.tsx`, `AvatarStack` | Sim | Acrescentar departamentos/equipes como relação por IDs | Usuários, equipes, departamentos | Demandas/Workflow | Alta |
| Prioridades | `PRIORITIES`, `CardView.tsx` | Sim | Usar 3 níveis do TaskFloww e cores configuráveis | Campo prioridade | Demandas/Kanban | Alta |
| Feedback visual | `CardView`, `ColumnView`, `dialog`, CSS | Sim | Badge + ícone + cor dentro do DS TaskFloww | Status, prazo, alertas | Contínua | Média |
| Modais e drawers | `Modal.tsx`, `dialog.tsx`, `CardModal.tsx` | Sim, com cautela | Consolidar em `Modal`/`EntitySidePanel`; evitar overlay duplicado | UI framework | Contínua | Média |
| Estados vazios | Vários componentes | Sim | Usar `WorkspaceEmptyState` padronizado | Nenhuma | Imediata | Média |
| Responsividade | `AppShell`, `calendario`, dashboard | Sim | Mobile com drawer/lista; Kanban mobile alternativo | Nenhuma direta | Contínua | Alta |

## Confirmação

Esta análise criou apenas este arquivo de documentação. Nenhum arquivo do Flowe foi copiado, nenhum código do TaskFloww foi alterado, nenhum banco/Docker foi alterado e nenhum commit foi realizado.
