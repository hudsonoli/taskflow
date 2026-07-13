# TaskFloww — Plano de Migração para Arquitetura Visual Centralizada

> **Documento de planejamento.** Baseado exclusivamente em `docs/design-system/taskfloww-design-system.md`.
> Nenhum arquivo de código foi lido, movido, criado ou alterado para produzir este documento.
> Nenhum commit foi feito.

---

## 1. Diagnóstico arquitetural

Elementos de interface que se repetem entre páginas, com os arquivos onde cada implementação aparece (conforme catalogado no documento de Design System, seções 2, 4–8, 11).

### Breadcrumb
**Já centralizado — não é um problema.** Única implementação: `src/components/layout/Breadcrumb.tsx`, renderizada uma vez dentro de `Header.tsx`, que por sua vez é montado uma única vez em `Shell.tsx`. Nenhuma página monta seu próprio breadcrumb. Este é o único elemento da lista que **já** está no estado desejado — serve de referência para os demais.

### Header de página (título + descrição)
Três implementações concorrentes:
- `ui/PageHeader.tsx` (título `text-3xl font-bold` + descrição) — usado por `TrafegoView` (combinado com hero custom), `AgendaView`, `PerfilView`, `NotificacoesView`, `AlterarSenhaView`, `app/relatorios/page.tsx`, `app/equipe/page.tsx`, `app/design-system/page.tsx`.
- Título/descrição inline dentro de `cadastros/CadastroPage.tsx` (`h2 text-lg font-semibold` + `p text-sm`, **não reutiliza `PageHeader`**) — usado por `ClientesView`, `EquipesView`, `FornecedoresView`, `GruposClientesView`, `UsuariosView`, `app/configuracoes/agencias/page.tsx`, `app/configuracoes/workflows/page.tsx`.
- "Hero card" com título/descrição montado manualmente em JSX duplicado (círculo decorativo, ícone, `StatusPill`) — em `DashboardView`, `DemandasView`, `ProjetosView`, `trafego/TrafegoHeader.tsx`.
- `app/configuracoes/prioridades|sla|tipos-tarefa/page.tsx` também usam `PageHeader`, mas dentro de um layout visual antigo (`Card`+tabela `rounded-3xl px-6 py-4`).

### Título / Descrição (isolado do header)
Mesma fragmentação acima — hierarquia tipográfica **inconsistente**: `PageHeader` usa `text-3xl`, `CadastroPage` usa `text-lg`, hero cards usam variações próprias. Não há um único componente que decida "qual o tamanho do título de uma página".

### Ações (botão "Novo X" e afins)
- Componentizado (`Novo<Entidade>Button`, com `useState` de abertura embutido): `clientes/NovoClienteButton.tsx`, `equipes/NovaEquipeButton.tsx`, `fornecedores/NovoFornecedorButton.tsx`, `usuarios/NovoUsuarioButton.tsx`.
- Inline, direto na prop `actions` do toolbar, sem componente dedicado: `GruposClientesView` (grupos-clientes), `app/configuracoes/agencias/page.tsx`, `app/configuracoes/workflows/page.tsx`, `app/configuracoes/prioridades|sla|tipos-tarefa/page.tsx` (estes últimos com botão **sem handler**, decorativo).

### Indicadores (KPIs de topo de página)
- `cadastros/CadastroIndicators.tsx` — `ClientesView`, `EquipesView`, `FornecedoresView`, `GruposClientesView`, `UsuariosView`, `agencias/page.tsx`, `workflows/page.tsx`.
- `ui/DashboardGrid.tsx` + `ui/MetricCard.tsx` — `DashboardStats` (Dashboard), `DemandasStats`, `ProjetosStats`, `TrafegoResumoCards`, `TempoOperacionalCard`.
- `workspace/WorkspaceStats.tsx` — **somente** `design-system/DesignSystemWorkspace.tsx` (vitrine, sem uso em produção).
- Grid manual de `Card` (sem componente de indicador dedicado) — `agenda/AgendaStats.tsx`.
- Nenhum indicador — `prioridades|sla|tipos-tarefa/page.tsx` (usam `Card` genérico em grid `md:grid-cols-3`, papel diferente de indicador de KPI).

### Toolbar / Busca / Filtros
- `cadastros/CadastroToolbar.tsx` (busca com ícone embutido + slot de filtros + slot de ações) — 7 telas de cadastro.
- `ui/ToolbarCard.tsx` + markup próprio de busca/filtro montado por página — `demandas/DemandasToolbar.tsx`, `projetos/ProjetosToolbar.tsx`, `trafego/TrafegoFilters.tsx`.
- `workspace/WorkspaceToolbar.tsx` — só vitrine.
- `agenda/AgendaToolbar.tsx` — implementação própria, `border-zinc-200` (diferente do `border-zinc-100` universal).

### Tabelas
- `cadastros/CadastroTable.tsx` (+ 4 constantes de classe exportadas) — 7 telas de cadastro.
- `workspace/WorkspaceTable.tsx` — só vitrine.
- Tabela ad hoc duplicada entre `demandas/DemandasTable.tsx` e `projetos/ProjetosTable.tsx` (terceiro padrão visual, não reutiliza os dois anteriores).
- `trafego/TrafegoAgoraTable.tsx` — markup próprio, mas visualmente mais próximo de `CadastroTable`/`WorkspaceTable`.
- Tabela antiga custom em `prioridades|sla|tipos-tarefa/page.tsx` (`rounded-3xl px-6 py-4`, sem reaproveitar nenhuma das constantes `cadastroTable*`).

### Paginação
**Não existe em nenhum arquivo do projeto.** Gap total — toda listagem renderiza o array completo. Precisa ser desenhada do zero como parte deste plano, e não apenas "extraída" de código existente.

### Status
- `cadastros/CadastroStatusBadge.tsx` (heurística por texto) — 7 telas de cadastro, e também reaproveitado **indevidamente** para "Categoria" (`fornecedores/FornecedoresView.tsx`) e "Perfil" (`usuarios/UsuariosView.tsx`).
- `ui/StatusPill.tsx` (mapa de tom explícito por enum) — `DashboardView`, `DemandaKanbanCard`/`DemandasTable`, `ProjetosTable`, `TrafegoAgoraTable`/`TrafegoHeader`.
- Paleta própria não reaproveitando nenhum dos dois acima: prioridade em Demandas/Projetos (`slate`/`sky`/`blue`), chips de tipo na Agenda (8 cores próprias em `agenda/AgendaList.tsx`).

### Estados vazios
- `ui/EmptyState.tsx` — seções de "Contatos" nos formulários (`ClienteFormSections`, `FornecedorFormSections`, `EquipeFormSections`), `agenda/AgendaList.tsx` (com emoji), `app/relatorios/page.tsx`, `app/equipe/page.tsx`, `app/configuracoes/permissoes/page.tsx`.
- `ui/EmptyStateIllustration.tsx` — `dashboard/DashboardChart.tsx`, `ui/RankingCard.tsx`, `trafego/TrafegoAgoraTable.tsx`, colunas vazias de `demandas/DemandaKanbanColumn.tsx`.
- `workspace/WorkspaceEmptyState.tsx` (wrapper fino de `EmptyState`) — `demandas/DemandasView.tsx`, `projetos/ProjetosView.tsx` (não usado por `trafego/TrafegoView.tsx`, que renderiza vazio sem esse wrapper).

### Loading
Praticamente inexistente: texto "Buscando dados..." + botão desabilitado durante lookup mock de CNPJ (`clientes/NovoClienteModal.tsx`, `fornecedores/NovoFornecedorModal.tsx`); skeleton `animate-pulse` em `trafego/TrafegoView.tsx`, mas a flag `loading` está hardcoded em `false` — nunca ativa. **Não existe um componente `LoadingState`/spinner reutilizável em lugar nenhum.**

### Erros
Praticamente inexistente: única implementação real é a mensagem `text-red-600` de senha inválida em `conta/AlterarSenhaView.tsx`. Nenhuma outra tela trata "carregamento falhou" ou "salvamento falhou" (coerente com a fase de mock, mas é uma lacuna estrutural a fechar antes de existir API real).

### Modais
- `ui/Modal.tsx` (sempre montado, controlado por `open`, **sem `role="dialog"`/`aria-modal`**) — `NovoClienteModal`, `NovaEquipeModal`, `NovoGrupoClienteModal`, `NovoUsuarioModal`, `NovaDemandaModal`, `NovoProjetoModal`.
- Wrapper condicional próprio (`if (!open) return null`, remonta o formulário do zero a cada abertura) — `fornecedores/NovoFornecedorModal.tsx`, comportamento de reset diferente dos demais.

### Drawers (painel lateral de detalhe)
`ui/EntitySidePanel.tsx` (ARIA completo, foco automático, bloqueio de scroll) — `ClientesView`, `FornecedoresView`, `GruposClientesView` (combinado com `EntitySummaryPanel`+`EntityFieldRow`), `DemandaDetailsDrawer`, `ProjetoDetailsDrawer`. **Ausente** em `EquipesView` e `UsuariosView` — únicos módulos de cadastro sem visualização/edição pós-criação.

### Formulários (padrão `*FormSections`)
`clientes/ClienteFormSections.tsx`, `equipes/EquipeFormSections.tsx`, `fornecedores/FornecedorFormSections.tsx`, `grupos-clientes/GrupoClienteFormSections.tsx`, `usuarios/UsuarioFormSections.tsx`, `demandas/DemandaFormSections.tsx`, `projetos/ProjetoFormSections.tsx` — todos seguem a mesma estrutura conceitual (seção "Dados", seção de relacionamento/endereço, seção de listas dinâmicas tipo "Contatos"/"Membros", seção "Histórico"), mas cada arquivo reimplementa o wrapper de seção e o padrão "lista dinâmica com botão + adicionar" do zero, sem componente compartilhado.

### Confirmações
**Não existe nenhum `ConfirmDialog` ou fluxo de confirmação em todo o projeto.** Não há hoje nenhuma ação destrutiva real (excluir, inativar em massa) implementada — mas isso significa que, quando essas ações forem adicionadas, corre-se o risco de cada módulo inventar sua própria confirmação (ou pior, nenhuma).

---

## 2. Componentes oficiais propostos

Critério de inclusão: só é proposto abaixo um componente para o qual **já existem 2+ implementações divergentes do mesmo problema** no código atual, ou uma lacuna estrutural comprovada (paginação, erro, confirmação). Nenhum componente é proposto "por precaução".

### `PageShell`
- **Responsabilidade**: wrapper único de página — padding e espaçamento vertical raiz. Substitui a decisão "qual padding esta página usa" por uma única fonte de verdade.
- **Localização sugerida**: `src/components/layout/PageShell.tsx` (é infraestrutura de layout, não um componente de domínio).
- **Props**: `children: ReactNode`, `density?: "compact" | "default"` (ver seção 7 — variantes).
- **Substituiria**: `cadastros/CadastroPage.tsx` (a parte de wrapper/padding — o título/descrição migra para `PageHeader`), `workspace/WorkspacePage.tsx`, os `<div className="p-8">`/`<div className="p-6">` soltos em `AgendaView`, `PerfilView`, `NotificacoesView`, `AlterarSenhaView`, `DashboardView`, `app/relatorios/page.tsx`, `app/equipe/page.tsx`.
- **Páginas que usariam**: todas as 23 rotas, sem exceção — é o único componente deste plano com adoção universal.
- **Riscos**: baixo — é puramente estrutural (padding/espaçamento), não contém lógica.
- **Dependências**: nenhuma (não depende de outro componente novo).
- **Dificuldade de migração**: **baixa**. É trocar um `<div className="p-X space-y-Y">` por `<PageShell>`, sem tocar no conteúdo interno.

### `PageHeader` (evolução do componente já existente)
- **Responsabilidade**: título + descrição + ações de página, em um único lugar, com hierarquia tipográfica fixa.
- **Localização sugerida**: manter em `ui/PageHeader.tsx` (já existe, só precisa de props novas).
- **Props adicionais necessárias**: `actions?: ReactNode` (hoje `PageHeader` não tem slot de ação — o botão "Novo X" fica sempre fora dele), `size?: "page" | "section"` (para absorver o caso `CadastroPage`, que hoje usa um título menor `text-lg` em vez de `text-3xl`).
- **Substituiria**: o `h2`/`p` inline de `cadastros/CadastroPage.tsx`, e os "hero cards" duplicados de `DashboardView`, `DemandasView`, `ProjetosView`, `TrafegoHeader.tsx` (a parte de título/descrição/ação — o elemento decorativo do hero, se mantido, vira um `variant` do próprio `PageHeader`, não um componente à parte).
- **Páginas que usariam**: as mesmas 23 rotas (via `PageShell`).
- **Riscos**: **médio** — unificar `text-3xl` (padrão atual do `PageHeader`) com `text-lg` (padrão atual do `CadastroPage`) é uma decisão visual, não só técnica; muda a hierarquia visual de 7 telas de cadastro se a escolha for `text-3xl`. Recomenda-se manter o tamanho `text-lg` como padrão de página de cadastro (mais compacto, já validado em produção em 7 telas) e reservar `text-3xl` para o `size="page"` usado hoje pela vitrine/telas soltas.
- **Dependências**: nenhuma.
- **Dificuldade de migração**: **média** (decisão de tamanho de fonte precisa ser tomada antes da Fase 1, ver seção 10).

### `Breadcrumb`
- **Já existe e já está correto.** `src/components/layout/Breadcrumb.tsx` não precisa de mudança estrutural — é citado aqui apenas para registrar que **nenhuma migração é necessária** neste elemento.

### `PageActions`
- **Responsabilidade**: slot padronizado para o botão principal de criação de uma página ("Novo Cliente", "Novo Fornecedor" etc.), incluindo o estado de abertura do modal associado.
- **Localização sugerida**: não é um componente visual novo — é um **padrão de composição**: o botão de ação vive dentro do `actions` do `PageHeader` (ou do `EntityToolbar`, ver abaixo), e cada módulo continua definindo seu próprio `Novo<Entidade>Button` (que já é o padrão correto hoje em 4 dos 7 módulos).
- **Substituiria**: os botões inline sem componente dedicado em `GruposClientesView`, `agencias/page.tsx`, `workflows/page.tsx`, `prioridades|sla|tipos-tarefa/page.tsx` — cada um passa a ter seu próprio `Novo<Entidade>Button` seguindo o padrão já usado por `NovoClienteButton`.
- **Páginas que usariam**: `GruposClientesView`, `agencias`, `workflows`, `prioridades`, `sla`, `tipos-tarefa`.
- **Riscos**: baixo — é replicar um padrão já validado, não inventar um novo.
- **Dependências**: `PageHeader`/`EntityToolbar` (para ter onde encaixar o slot).
- **Dificuldade de migração**: **baixa**.

### `EntityToolbar`
- **Responsabilidade**: barra de busca + filtros + ações de uma listagem, com busca sempre com ícone embutido.
- **Localização sugerida**: `src/components/data-display/EntityToolbar.tsx`.
- **Props**: `searchValue`, `onSearchChange`, `searchPlaceholder?`, `filters?: ReactNode`, `actions?: ReactNode`.
- **Substituiria**: `cadastros/CadastroToolbar.tsx`, `workspace/WorkspaceToolbar.tsx` (dead), o uso de `ToolbarCard`+markup próprio em `DemandasToolbar`/`ProjetosToolbar`/`TrafegoFilters`, e `agenda/AgendaToolbar.tsx`.
- **Páginas que usariam**: as 7 telas de cadastro + Demandas + Projetos + Tráfego + Agenda (11 telas no total).
- **Riscos**: **médio** — `TrafegoFilters` tem filtros mais ricos (`MultiSelect`, toggle de período) que precisam caber no slot `filters` sem que o componente vire genérico demais (ver seção 12 — não generalizar acima do necessário).
- **Dependências**: `ui/Input.tsx` (busca), `ui/Select.tsx`/`ui/MultiSelect.tsx` (filtros ficam de responsabilidade de quem preenche o slot, não do `EntityToolbar` em si).
- **Dificuldade de migração**: **média**.

### `MetricStrip`
- **Responsabilidade**: faixa de indicadores/KPIs no topo de uma página.
- **Localização sugerida**: `src/components/data-display/MetricStrip.tsx`, internamente composto por `DashboardGrid` (já existente) + `MetricCard` (já existente) — ou seja, este item é mais uma **formalização de composição** do que um componente novo do zero.
- **Props**: `items: MetricCardProps[]`, `columns?: "three" | "four" | "five"` (delegado ao `DashboardGrid` já existente).
- **Substituiria**: `cadastros/CadastroIndicators.tsx`, `workspace/WorkspaceStats.tsx` (dead), o grid manual de `Card` em `agenda/AgendaStats.tsx`.
- **Páginas que usariam**: as mesmas que hoje usam `CadastroIndicators` (7 telas) + `DashboardGrid`/`MetricCard` (Dashboard, Demandas, Projetos, Tráfego) + Agenda = 12 telas.
- **Riscos**: **médio-alto** — é a unificação mais visível do plano, porque `CadastroIndicators` (`text-xl`, compacto, `min-h-[58px]`) e `MetricCard` (`text-2xl`/`text-3xl`, mais espaçoso, com ícone/tom/badge/footer) têm densidades visuais diferentes hoje. Escolher `MetricCard` como base (mais completo — já suporta ícone, tom semântico, badge, footer) significa que as 7 telas de cadastro ganham cards visualmente maiores do que têm hoje.
- **Dependências**: `ui/DashboardGrid.tsx`, `ui/MetricCard.tsx` (nenhuma dependência nova).
- **Dificuldade de migração**: **alta** (é uma mudança visual perceptível, não só estrutural — precisa de aprovação visual explícita antes de aplicar em massa).

### `DataTable`
- **Responsabilidade**: tabela de listagem única, com cabeçalho, linhas, e (novo) slot de paginação.
- **Localização sugerida**: `src/components/data-display/DataTable.tsx`.
- **Props**: `columns: { key, label, align? }[]`, `children` (linhas, mantendo o padrão atual de render-prop por linha em vez de um `rows`/`renderRow` genérico — ver seção 12), `minWidth?`, `emptyState?: ReactNode`.
- **Substituiria**: `cadastros/CadastroTable.tsx` (+ as 4 constantes de classe), `workspace/WorkspaceTable.tsx` (dead), a tabela ad hoc duplicada entre `DemandasTable`/`ProjetosTable`, e a tabela antiga de `prioridades|sla|tipos-tarefa`. `TrafegoAgoraTable` também migra, por já ser o mais próximo visualmente do padrão escolhido.
- **Páginas que usariam**: 7 telas de cadastro + Demandas + Projetos + Tráfego + Prioridades/SLA/Tipos de Tarefa = 12 telas.
- **Riscos**: **alto** — é o componente com maior número de variações concorrentes hoje (3 implementações distintas). Precisa decidir um único radius (`2xl` vs `3xl`), um único padding de célula (`px-3 py-2` vs `px-6 py-4` vs `px-4 py-3`) e uma única cor/estilo de cabeçalho (uppercase+tracking vs normal). Recomenda-se adotar o padrão de `CadastroTable` como base (mais compacto, já usado por 7 telas, já exporta constantes reaproveitáveis).
- **Dependências**: nenhuma nova; ganha uma dependência de **Pagination** (novo) quando essa parte for implementada.
- **Dificuldade de migração**: **alta**.

### `Pagination` (novo — não existe hoje em nenhuma forma)
- **Responsabilidade**: navegação entre páginas de resultado de uma listagem.
- **Localização sugerida**: `src/components/data-display/Pagination.tsx`.
- **Props**: `page`, `pageSize`, `totalItems`, `onPageChange`.
- **Substituiria**: nada (gap total) — mas deve nascer já acoplada ao contrato de `DataTable` para não repetir o erro de cada módulo inventar sua própria paginação depois.
- **Páginas que usariam**: inicialmente nenhuma (não há paginação hoje); é infraestrutura para ativação futura conforme o volume de dados mock crescer ou a API real chegar.
- **Riscos**: baixo (não substitui nada existente, então não há regressão possível na primeira versão).
- **Dependências**: `DataTable`.
- **Dificuldade de migração**: **baixa** (é adição pura, não substituição).

### `StatusBadge` (consolidação de `StatusPill` + `CadastroStatusBadge`)
- **Responsabilidade**: badge de status com tom semântico fixo por enum (não por heurística de texto).
- **Localização sugerida**: manter em `ui/StatusPill.tsx`, renomeando o papel para "badge de status oficial" (não precisa necessariamente trocar o nome do arquivo — trocar o nome é opcional e de baixo valor).
- **Props**: já existentes (`tone`, `dot?`) são suficientes.
- **Substituiria**: `cadastros/CadastroStatusBadge.tsx` **enquanto usado para status real** (Ativo/Inativo/Pendente). **Não deve** substituir os usos indevidos de `CadastroStatusBadge` para "Categoria" (Fornecedores) e "Perfil" (Usuários) — esses casos precisam de um badge neutro à parte (ver `EntityTag` abaixo, opcional).
- **Páginas que usariam**: todas as que hoje usam `CadastroStatusBadge` ou `StatusPill` (praticamente todas as 12 telas com dado tabular).
- **Riscos**: **médio** — a lógica de tom por status precisa de um mapa explícito por módulo (`ativo→green`, `inativo→neutral`, `pendente→amber`), substituindo a heurística de texto (`contém "ativo"`) hoje usada em `CadastroStatusBadge`. Isso é mais seguro (não quebra com valores inesperados) mas exige que cada módulo declare seu próprio mapa, em vez de "funcionar sozinho" com qualquer string.
- **Dependências**: nenhuma.
- **Dificuldade de migração**: **média**.

### `EntityAvatar`
- **Responsabilidade**: círculo com iniciais ou ícone, usado como avatar de linha de tabela/card.
- **Localização sugerida**: promover `cadastros/CadastroAvatar.tsx` para `ui/EntityAvatar.tsx` (é genérico o suficiente para sair de `cadastros/`).
- **Props**: já existentes (`label`, `icon?`) são suficientes.
- **Substituiria**: `cadastros/CadastroAvatar.tsx` (mesma implementação, novo endereço) e o avatar montado manualmente em `agenda/AgendaList.tsx` (hoje usa `Image`/iniciais sem wrapper padronizado).
- **Páginas que usariam**: as 7 telas de cadastro + Agenda.
- **Riscos**: baixo.
- **Dependências**: nenhuma.
- **Dificuldade de migração**: **baixa**.

### `EmptyState` (consolidação de `EmptyState` + `EmptyStateIllustration` + `WorkspaceEmptyState`)
- **Responsabilidade**: estado vazio de lista/seção, com ou sem ícone.
- **Localização sugerida**: manter em `ui/EmptyState.tsx`, absorvendo a prop `icon?`/`size?` que hoje só existe em `EmptyStateIllustration`.
- **Props**: `title`, `description`, `icon?`, `action?`, `size?: "default" | "compact"`.
- **Substituiria**: `ui/EmptyStateIllustration.tsx` (mesmo componente, unificado) e `workspace/WorkspaceEmptyState.tsx` (que hoje é só um passthrough).
- **Páginas que usariam**: todas as que já usam qualquer uma das três variantes hoje.
- **Riscos**: baixo — é uma fusão de props, não uma mudança de comportamento.
- **Dependências**: nenhuma.
- **Dificuldade de migração**: **baixa**.

### `ErrorState` (novo)
- **Responsabilidade**: comunicar falha de carregamento/salvamento de forma visual consistente.
- **Localização sugerida**: `src/components/feedback/ErrorState.tsx`.
- **Props**: `title`, `description`, `action?` (ex.: "Tentar novamente").
- **Substituiria**: a mensagem `text-red-600` ad hoc de `AlterarSenhaView` (que passaria a usar o componente, mesmo sendo o único caso hoje) — mas o objetivo real é existir **antes** de qualquer integração real com API, para não repetir o erro de cada módulo inventar sua própria tela de erro quando isso passar a ser necessário.
- **Páginas que usariam**: nenhuma obrigatoriamente hoje; recomenda-se adotar já em `AlterarSenhaView` como primeiro caso de uso real.
- **Riscos**: baixo.
- **Dependências**: nenhuma.
- **Dificuldade de migração**: **baixa**.

### `LoadingState` (novo, formalizando o skeleton hoje morto)
- **Responsabilidade**: indicar carregamento assíncrono de forma consistente (skeleton de card/tabela, ou spinner inline em botão).
- **Localização sugerida**: `src/components/feedback/LoadingState.tsx` (skeleton de bloco) + um estado `loading?` opcional em `Button` (para os casos de "Salvando...", "Buscando dados...").
- **Props**: `variant?: "card" | "table-row"`, `count?: number`.
- **Substituiria**: o skeleton `animate-pulse` hoje hardcoded em `TrafegoView.tsx` (nunca ativado), e o padrão de texto "Buscando dados..." + botão desabilitado hoje reimplementado independentemente em `NovoClienteModal`/`NovoFornecedorModal`.
- **Páginas que usariam**: Tráfego (ativando o loading que hoje é morto), Clientes/Fornecedores (lookup de CNPJ).
- **Riscos**: baixo — não há comportamento de produção para regredir (o loading de Tráfego nunca roda).
- **Dependências**: `ui/Button.tsx` (para o estado `loading` do botão).
- **Dificuldade de migração**: **baixa**.

### `FormField` (extração do wrapper label+controle já implícito em `Input`/`Select`/`Textarea`)
- **Responsabilidade**: layout comum de "label acima + controle abaixo + mensagem de erro opcional", hoje duplicado dentro de `Input.tsx`, `Select.tsx` e `Textarea.tsx` de forma quase idêntica.
- **Localização sugerida**: `src/components/forms/FormField.tsx`, usado **internamente** por `Input`/`Select`/`Textarea` (que continuam em `ui/`, pois são os componentes que o resto do app importa — `FormField` é um detalhe de implementação compartilhado entre eles, não um novo componente público de primeira classe).
- **Props**: `label`, `error?`, `children`.
- **Substituiria**: o markup `<label className="block text-sm">...<span>...</span>` repetido em `Input.tsx`, `Select.tsx`, `Textarea.tsx`.
- **Páginas que usariam**: indiretamente, todas — é refatoração interna, não muda a API pública de `Input`/`Select`/`Textarea`.
- **Riscos**: baixo (mudança interna, sem efeito colateral se a extração for fiel ao markup atual).
- **Dependências**: nenhuma.
- **Dificuldade de migração**: **baixa**, mas de **baixa prioridade** também — não resolve nenhuma inconsistência visível hoje, só reduz duplicação de código-fonte.

### `FormSection` (generalização do padrão "Dados/Endereço/Contatos" repetido nos `*FormSections.tsx`)
- **Responsabilidade**: card de seção dentro de um formulário em abas (título + grid de campos + eventualmente lista dinâmica "+ Adicionar").
- **Localização sugerida**: `src/components/forms/FormSection.tsx`.
- **Props**: `title?`, `children`; para o sub-padrão de lista dinâmica, um componente irmão `FormRepeatableList` com `items`, `onAdd`, `onRemove`, `renderItem`.
- **Substituiria**: o wrapper de seção repetido dentro de `ClienteFormSections.tsx`, `EquipeFormSections.tsx`, `FornecedorFormSections.tsx`, `GrupoClienteFormSections.tsx`, `UsuarioFormSections.tsx`, `DemandaFormSections.tsx`, `ProjetoFormSections.tsx` — **não** substitui os campos específicos de cada seção (que são regra de negócio de cada entidade, ver seção 3).
- **Páginas que usariam**: os 7 módulos com `*FormSections.tsx`.
- **Riscos**: **médio** — o padrão de "lista dinâmica" (Contatos, Membros, Modelo de Campanha) tem pequenas variações de campos entre módulos; o componente compartilhado precisa ficar restrito ao *layout* (card + botão + grid), nunca aos campos em si.
- **Dependências**: nenhuma.
- **Dificuldade de migração**: **média**.

### `Modal` (evolução do componente já existente)
- **Responsabilidade**: diálogo centralizado modal.
- **Localização sugerida**: manter em `ui/Modal.tsx`.
- **Mudança necessária**: adicionar `role="dialog"`, `aria-modal="true"`, `aria-labelledby` (hoje ausentes, ao contrário de `EntitySidePanel`, que já tem).
- **Substituiria**: o wrapper condicional próprio de `fornecedores/NovoFornecedorModal.tsx` (que hoje remonta o formulário do zero a cada abertura — comportamento a preservar via prop, não a eliminar silenciosamente, ver riscos).
- **Páginas que usariam**: os 6 módulos que já usam `Modal` + Fornecedores (após migração).
- **Riscos**: **médio** — o comportamento de "reset ao abrir" de Fornecedores pode ser intencional (evita estado de formulário obsoleto entre uma edição e outra); ao unificar para o `Modal` padrão (sempre montado), é preciso garantir que o reset de estado do draft aconteça explicitamente no `onOpen`, não deixar de existir.
- **Dependências**: nenhuma.
- **Dificuldade de migração**: **média**.

### `Drawer` (formalização de `EntitySidePanel` como componente oficial de detalhe)
- **Responsabilidade**: painel lateral de detalhe/edição.
- **Localização sugerida**: manter em `ui/EntitySidePanel.tsx` (já é o mais completo em acessibilidade — não precisa de reescrita, só de mais adoção).
- **Substituiria**: nada estruturalmente — a mudança é de **adoção**, não de implementação: `EquipesView` e `UsuariosView` passam a ganhar visualização/edição pós-criação via este componente, alinhando-se aos demais 5 módulos.
- **Páginas que usariam**: as 5 atuais + Equipes + Usuários.
- **Riscos**: **médio** — Equipes/Usuários hoje não têm esse fluxo; adicioná-lo é uma mudança de comportamento visível para o usuário (não é só reorganização visual), precisa ser tratado como uma pequena feature nova, não uma refatoração pura.
- **Dependências**: `EntitySummaryPanel`/`EntityFieldRow` (opcional — ver abaixo).
- **Dificuldade de migração**: **média-alta** (Equipes/Usuários), **baixa** (demais, que só continuam como estão).

### `EntitySummaryPanel` + `EntityFieldRow` (expansão de uso)
- **Responsabilidade**: já existem e já resolvem bem o problema de estruturar o conteúdo interno de um `Drawer` em seções nomeadas — hoje só usados por Grupos de Clientes.
- **Substituiria**: o `<dl>`/`<section>` montado manualmente dentro do `EntitySidePanel` de `ClientesView` e `FornecedoresView`.
- **Páginas que usariam**: Clientes, Fornecedores (além de Grupos de Clientes, que já usa).
- **Riscos**: baixo.
- **Dependências**: `EntitySidePanel`.
- **Dificuldade de migração**: **baixa**.

### `ConfirmDialog` (novo — não existe hoje)
- **Responsabilidade**: confirmação antes de uma ação destrutiva ou irreversível (excluir, inativar em massa).
- **Localização sugerida**: `src/components/feedback/ConfirmDialog.tsx`, implementado como uma composição fina sobre `Modal` (não um componente do zero).
- **Props**: `open`, `onConfirm`, `onCancel`, `title`, `description`, `confirmLabel?`, `tone?: "default" | "danger"`.
- **Substituiria**: nada hoje (não existe ação destrutiva implementada no projeto) — é infraestrutura preparatória.
- **Páginas que usariam**: nenhuma hoje; deve ser adotado no momento em que a primeira ação de "excluir"/"inativar" for implementada em qualquer módulo de cadastro.
- **Riscos**: baixo (adição pura).
- **Dependências**: `Modal`.
- **Dificuldade de migração**: **baixa**.

### Componentes deliberadamente **não** propostos

- **`AppShell`**: já existe e já está correto (`layout/Shell.tsx`) — não precisa de um componente novo com esse nome, evitando confusão com `PageShell`.
- **Um componente de "Filtro" genérico separado de `EntityToolbar`**: os filtros variam demais entre módulos (Select simples em Cadastros, `MultiSelect`+período em Tráfego) para justificar uma abstração própria além do slot já previsto em `EntityToolbar`.

---

## 3. Separação entre UI e regra de negócio

Regra geral: **um componente compartilhado nunca importa de `src/lib/*-mock.ts`, nunca decide "o que fazer" com um clique, e nunca sabe o que é um "Cliente" ou uma "Equipe".** Ele recebe dados já resolvidos e devolve eventos.

O que fica **dentro das Views/páginas de domínio** (`ClientesView`, `EquipesView`, `DemandasView` etc.) e não migra para componentes compartilhados:

- **Estado do draft** de criação/edição (`useState<ClienteDraft>`, `useState<EquipeDraft>` etc.) — cada entidade continua dona do seu próprio shape de dados.
- **Resolução de IDs para nomes** (ex.: `resolveEquipeNome(equipeResponsavelId)`) — é lógica de domínio, os componentes compartilhados só recebem a string já resolvida.
- **Chamadas a `lib/*-mock.ts`** (hoje `useState(initialX)`; no futuro, chamadas de API/hooks de dados) — nenhum componente em `ui/`, `data-display/`, `forms/`, `feedback/` deve importar um `*-mock.ts` diretamente.
- **Callbacks de salvar/criar/editar** (`handleSave`, `handleCreate`) — a lógica de "o que acontece ao salvar" (fechar modal, atualizar lista, gerar novo `codigoInterno`) fica na View; o `Modal`/`FormSection` só expõe `onSubmit`/`onClose` como props vazias de significado de negócio.
- **Validação de campos obrigatórios** (`canSave`, `nome && email && departamentoId`) — cada `*FormSections.tsx` continua validando os próprios campos; `FormField`/`FormSection` só sabem exibir um erro que recebem como prop, não decidem quando ele existe.
- **Permissões (RBAC)** — verificações de perfil (`SuperAdmin`/`Admin`/`Gestor`/`Operador`/`Cliente`, quando implementadas) devem ficar em um nível acima dos componentes compartilhados: na página (`page.tsx`) decidindo se renderiza a View, ou na View decidindo se passa `canCreate`/`canEdit` para baixo — nunca dentro de `EntityToolbar`/`DataTable`/`Modal` verificando `perfil === "Admin"` diretamente. O padrão já existe parcialmente (`FornecedoresView` já recebe `canCreate`/`canEdit` como props) e deve ser o modelo a seguir: **o componente compartilhado recebe um booleano já decidido, nunca decide sozinho**.
- **Mutations futuras** (quando a API real existir) — hooks de dados (`useClientes()`, `useSaveCliente()` ou equivalente) devem viver perto do domínio (ex.: `src/components/domains/clientes/` ou um futuro `src/hooks/`), nunca dentro de `ui/`/`data-display/`.

O que fica **dentro dos componentes compartilhados** (e nada além disso):

- Apresentação visual (classes Tailwind, estrutura de DOM).
- Estado de UI puramente local e sem significado de negócio (aberto/fechado de um dropdown dentro do próprio componente, por exemplo o `open` interno de um tooltip — não o `open` de um modal de edição, que é decidido pela View).
- Formatação neutra (ex.: `StatusBadge` decide **como pintar** um tom, não decide **qual tom** um status de Cliente deveria ter — esse mapa `ativo→green` é passado como prop/config pela View, não fica hardcoded dentro do badge para todas as entidades).

**Regra prática de checagem**: se ao ler o código de um componente em `ui/`, `data-display/`, `forms/` ou `feedback/` for possível responder "isso é sobre Clientes" ou "isso é sobre Demandas", o componente está errado de lugar — regra de negócio vazou para a camada visual.

---

## 4. Estrutura de pastas proposta

Mudança **mínima e pragmática** — a estrutura atual já segue bem a convenção do `CLAUDE.md` (rotas em `app/`, componentes por módulo em `components/`, tipos em `types/`, mocks em `lib/`). Não há justificativa para mover os ~60 arquivos de componentes de domínio para dentro de um novo `domains/` — o custo (diffs grandes, risco de quebrar imports) não se paga frente ao ganho (nenhuma ambiguidade real existe hoje entre "isso é layout" e "isso é domínio", já que cada pasta tem nome de entidade).

```
frontend/src/components/
├── ui/                  → MANTIDO. Primitivos atômicos: Button, Input, Select, Textarea,
│                          MultiSelect, Switch, Tabs, PageHeader, EmptyState, ErrorState (novo),
│                          StatusPill (StatusBadge oficial), EntityAvatar (promovido de cadastros/),
│                          ProgressBar, DashboardGrid, MetricCard, Modal, EntitySidePanel,
│                          EntitySummaryPanel, EntityFieldRow
│
├── layout/              → MANTIDO. Shell, Sidebar, Header, Breadcrumb, UserMenu, QuickCreateMenu,
│                          HeaderSearch, HeaderActions, SidebarContext + PageShell (novo, único
│                          arquivo novo nesta pasta)
│
├── data-display/        → NOVO. Concentra o que hoje está espalhado entre cadastros/ e workspace/:
│                          EntityToolbar, MetricStrip, DataTable, Pagination (novo)
│
├── forms/                → NOVO. FormField, FormSection, FormRepeatableList — primitivos internos
│                          de formulário reaproveitados pelos *FormSections.tsx de cada domínio
│
├── feedback/             → NOVO. LoadingState (novo), ConfirmDialog (novo) — os demais estados
│                          de feedback (EmptyState, Modal) permanecem em ui/ por já serem usados
│                          amplamente fora do contexto estrito de "feedback de ação"
│
├── cadastros/            → APOSENTADO GRADUALMENTE. Durante a transição (Fases 1–4, seção 10),
│                          continua existindo com os componentes ainda não migrados; ao final da
│                          Fase 4 fica vazio e é removido
│
├── workspace/            → APOSENTADO. WorkspaceSection/Stats/Table/Toolbar são removidos assim
│                          que MetricStrip/EntityToolbar/DataTable existirem (não têm uso em
│                          produção hoje — baixo risco). WorkspacePage é substituído por PageShell.
│                          WorkspaceEmptyState é absorvido por EmptyState
│
├── design-system/        → MANTIDO sem alteração estrutural — é a vitrine, deve ser atualizada
│                          conteúdo a conteúdo conforme cada componente migra (fora do escopo
│                          deste plano de arquitetura, é responsabilidade de manutenção contínua)
│
└── (módulos de domínio, mantidos na raiz de components/, SEM mover para domains/)
    clientes/, equipes/, fornecedores/, grupos-clientes/, usuarios/, demandas/, kanban/,
    projetos/, trafego/, agenda/, conta/, dashboard/
```

**Decisão explícita de não fazer**: não criar `navigation/` separado de `layout/` — `Breadcrumb`/`UserMenu`/`QuickCreateMenu` já vivem bem dentro de `layout/` por serem elementos fixos do shell, não elementos de navegação reaproveitáveis em outros contextos. Criar uma pasta nova para eles seria mover por estética, não por necessidade.

---

## 5. Padrão oficial de página (telas de cadastro)

```
PageShell (density="default")
├── PageHeader
│     title, description
│     actions?  → <Novo<Entidade>Button />
├── MetricStrip?          (opcional)
├── EntityToolbar
│     searchValue, onSearchChange
│     filters?            (opcional)
│     actions?            (raramente usado aqui — normalmente a ação principal já está no PageHeader)
├── DataTable
│     columns
│     linhas (renderizadas pela View, usando EntityAvatar/StatusBadge conforme a coluna)
│     emptyState → <EmptyState />
└── Pagination?           (opcional hoje, obrigatório assim que existir volume real de dados)
```

**O que é opcional e por quê:**
- `MetricStrip` — opcional porque nem toda entidade tem indicadores relevantes (ex.: `Permissões`, hoje placeholder, provavelmente nunca precisará de KPIs de topo).
- `Pagination` — opcional **por ora**, porque os mocks atuais são pequenos; deve deixar de ser opcional (tornar-se padrão) assim que qualquer listagem passar de ~50 itens ou quando a API real substituir o mock.
- `filters` dentro de `EntityToolbar` — opcional; a maioria dos módulos de cadastro hoje só tem busca textual, sem filtro adicional (só Tráfego usa filtros ricos).
- `actions` dentro de `PageHeader` — sempre presente quando a entidade permite criação; ausente em telas somente-leitura (ex.: `Tráfego`, `Permissões` enquanto placeholder).

O `Modal` (criação/edição) e o `Drawer` (visualização/edição de detalhe) **não fazem parte da composição vertical da página** — são camadas sobrepostas, acionadas por eventos (clique em "Novo X" ou clique em uma linha), e continuam vivendo como filhos condicionais da View, não como slots do `PageShell`.

---

## 6. Padrão para páginas especiais

Estas páginas **não devem** ser forçadas ao padrão de cadastro da seção 5 — teriam a identidade descaracterizada:

- **Kanban (`/tarefas`, visão Kanban)**: o corpo da página (colunas + cards) é estruturalmente incompatível com `DataTable`/`Pagination` — um Kanban não pagina, ele rola horizontalmente por coluna. **Reutiliza**: `PageShell`, `PageHeader`, `MetricStrip` (já usa `DemandasStats`), `EntityToolbar` (já usa toggle Lista/Kanban dentro do toolbar). **Não reutiliza**: `DataTable`, `Pagination`.
- **Workflow (`/configuracoes/workflows`)**: hoje renderiza cards com "esteira" de etapas, não uma tabela — a natureza do dado (sequência de etapas, não uma lista tabular de registros) não se encaixa em `DataTable`. **Reutiliza**: `PageShell`, `PageHeader`, `EntityToolbar` (para o botão "Novo Workflow" e busca). **Não reutiliza**: `DataTable`/`MetricStrip` (hoje já não usa indicadores).
- **Dashboard (`/`)**: página de composição livre (hero, KPIs, agenda do dia, atividades, gráfico placeholder, atalhos) — não é uma listagem de entidade, não tem toolbar de busca nem tabela. **Reutiliza**: `PageShell`, `PageHeader` (para o hero, adaptado), `MetricStrip` (já usa `DashboardGrid`+`MetricCard`). **Não reutiliza**: `EntityToolbar`, `DataTable`, `Pagination`, `Drawer`.
- **Agenda (`/agenda`)**: layout de lista de cards, não de tabela — é uma decisão de produto (CRM de contatos), não uma inconsistência a "corrigir" forçando para `DataTable`. **Reutiliza**: `PageShell`, `PageHeader`, `MetricStrip` (adaptando `AgendaStats` para usar `MetricCard`), `EntityToolbar` (busca + filtro por tipo). **Não reutiliza**: `DataTable` (mantém o layout de cards, que é correto para o caso de uso, apenas os cards individuais poderiam evoluir para usar `EntityAvatar`+`StatusBadge` em vez de implementação própria).
- **Projetos (`/projetos`)**: é o módulo mais próximo do padrão de cadastro (já usa tabela, toolbar, stats, drawer com abas) — **deve** migrar para o padrão completo da seção 5, incluindo `DataTable`/`Pagination`. Não é uma página especial, é citada aqui só para reforçar que, apesar de estar hoje sob `WorkspacePage`, seu destino é o padrão de cadastro, não o de página especial.
- **Histórico** (não é uma página própria — é uma aba dentro dos drawers/modais de cada entidade): continua como uma seção de formulário (`HistoricoSection`), candidata a usar `DataTable` internamente (para a tabela de eventos) mas sem `PageShell`/`PageHeader` próprios, pois vive dentro de um `Modal`/`Drawer` já existente.
- **Relatórios (`/relatorios`)**: hoje é um placeholder puro. Quando implementado, provavelmente será mais parecido com Dashboard (composição livre de gráficos/indicadores) do que com uma tela de cadastro — **não** deve ser pré-planejado para `DataTable`.

---

## 7. Variantes

Variantes propostas **somente onde o código atual já demonstra a necessidade** (não são inventadas):

| Variante | Onde se aplica | Justificativa no código atual |
|---|---|---|
| `density: "compact" \| "default"` | `PageShell`, `EntityToolbar` | Já existe divergência real entre o padding `p-4 sm:p-5` (Cadastro) e `p-8` (Workspace) — formalizar como uma variante evita reintroduzir um terceiro valor (como aconteceu com o `p-6` do Dashboard) |
| `size: "default" \| "compact"` | `EmptyState` (unificado) | Já existe hoje em `EmptyStateIllustration` (`default`/`compact`) — só se estende ao componente consolidado |
| `size: "page" \| "section"` | `PageHeader` | Reflete a diferença real hoje existente entre o título `text-3xl` (páginas soltas) e `text-lg` (dentro de `CadastroPage`) |
| `withMetrics` / sem essa prop | `PageShell`/composição de página | Não é uma variante formal (enum) — é simplesmente a **presença ou ausência** do slot `MetricStrip` na composição da página. Não modelar como prop booleana redundante quando a composição JSX já resolve isso. |
| `withFilters` | idem — **não é variante**, é a presença do slot `filters` em `EntityToolbar` |
| `readOnly` | `EntityToolbar`, `DataTable` | Já existe um caso real: Tráfego é 100% somente-leitura (botão "Atualizar" desabilitado, sem ações de escrita) e o Kanban de Demandas é somente-leitura hoje. Faz sentido como prop booleana explícita (`readOnly?: boolean`) que desabilita ações/edição, em vez de a View precisar ocultar manualmente cada botão |
| `desktop` / `mobile` | **Não propor como variante controlada por JS.** | Toda a responsividade atual do projeto é resolvida via classes Tailwind responsivas (`sm:`/`md:`/`lg:`/`xl:`), sem nenhuma bifurcação de componente por dispositivo. Introduzir uma variante JS `desktop`/`mobile` seria inventar um mecanismo que o código atual não usa e não precisa — mantém-se CSS puro. |
| `comfortable` | **Não propor.** | Não há evidência no código atual de um terceiro nível de densidade além dos dois já observados (`p-4 sm:p-5` e `p-8`) — criar `compact`/`default`/`comfortable` (3 níveis) seria inventar um nível sem uso real. Ficar em 2 (`compact`/`default`) já resolve a divergência existente. |

**Regra geral adotada**: uma variante só é criada quando o código atual já expressa aquele eixo de variação em produção (mesmo que de forma inconsistente); presença/ausência de conteúdo opcional é resolvida por composição JSX (renderização condicional), nunca por uma prop booleana redundante do tipo `showMetrics`.

---

## 8. Design tokens centralizados

Já que o Tailwind está configurado no modo CSS-first do v4 (`@import "tailwindcss"` + `@theme inline` dentro de `globals.css`, **sem `tailwind.config.js`**), há duas vias possíveis para tokens — recomenda-se a combinação das duas, cada uma no seu nível de responsabilidade:

1. **`@theme inline` em `globals.css`** — para tokens que o Tailwind precisa conhecer nativamente (cores, se algum dia saírem do vocabulário `zinc`/`blue`/`emerald`/`amber`/`red` padrão; a fonte, quando `font-sans`/`font-mono` passarem a ser de fato aplicadas ao invés do Arial/Helvetica hardcoded hoje).
2. **Um arquivo de constantes TypeScript** (`src/lib/design-tokens.ts`, novo) — para strings de classes Tailwind reaproveitadas por múltiplos componentes compartilhados, evitando a necessidade de expandir o `@theme` do Tailwind para cada decisão de espaçamento/raio. É a via de menor risco e menor custo de adoção, dado que não exige reconfigurar o pipeline CSS.

| Token | Estado atual (inconsistente) | Token proposto | Onde definir |
|---|---|---|---|
| Radius de card/superfície | `rounded-2xl` (Cadastro) vs `rounded-3xl` (Workspace, Modal, EmptyState) | `RADIUS_SURFACE = "rounded-3xl"` (adotar o maior, já dominante em mais contextos) | `lib/design-tokens.ts` |
| Radius de controle de formulário | `rounded-xl` (já consistente) | manter | — |
| Padding de página raiz | `p-4 sm:p-5` / `p-6` / `p-8` | `PAGE_PADDING = { compact: "p-4 sm:p-5", default: "p-8" }` (eliminar o `p-6` único do Dashboard) | `lib/design-tokens.ts`, consumido por `PageShell` |
| Altura de toolbar | `p-2.5` (Cadastro, ~h-9 do campo interno) vs `p-4` (Workspace/Demandas) vs `p-5` (Agenda) | `TOOLBAR_PADDING = "p-3"` (valor intermediário único) | `lib/design-tokens.ts`, consumido por `EntityToolbar` |
| Padding de célula de tabela | `px-3 py-2` (Cadastro) vs `px-6 py-4` (Workspace) vs `px-4 py-3` (Demandas/Projetos) | `TABLE_CELL_PADDING = "px-3 py-2"` (adotar o padrão Cadastro, já mais compacto e mais adotado) | `lib/design-tokens.ts`, consumido por `DataTable` |
| Cor de fundo de cabeçalho de tabela | `bg-[#faf8f4]` (Cadastro/Workspace/Tráfego) vs `bg-zinc-50/80` (Demandas/Projetos) | `TABLE_HEADER_BG = "bg-[#faf8f4]"` | `lib/design-tokens.ts` |
| Largura de drawer | já consistente (`sm:max-w-lg lg:max-w-xl` em `EntitySidePanel`) | manter | — |
| Largura de modal | já parametrizável (`maxWidthClassName`, default `max-w-lg`) | manter, apenas documentar os valores usados hoje (`max-w-lg` maioria, verificar se algum módulo já usa um valor maior) | — |
| Tamanho de ícone | `h-4 w-4` (padrão) / `h-3.5 w-3.5` (chevrons) / `h-5 w-5` (fechar painel) | `ICON_SIZE = { sm: "h-3.5 w-3.5", md: "h-4 w-4", lg: "h-5 w-5" }` | `lib/design-tokens.ts` |
| Sombra de superfície | já consistente (`shadow-sm` quase universal) | manter | — |
| Sombra de modal/dropdown | já consistente (`shadow-lg` Modal, `shadow-xl` dropdowns/drawer) | manter | — |
| Transições | `transition` genérico + um único `duration-200 ease-out` (largura da sidebar) | manter como está — não há inconsistência real a resolver, apenas documentar os dois casos existentes | — |
| Fonte aplicada | Arial/Helvetica hardcoded no `body`, Geist carregada mas não usada | `@theme inline` já define `--font-sans`; falta aplicar `font-sans` ao `body` em `globals.css` | `globals.css` (`@theme inline`, já existe — falta uma linha em `body { font-family: var(--font-sans) }`) |
| Cor de badge de status | vocabulário `neutral/blue/green/amber/red` já centralizado em `StatusPill` | manter como token de referência único; `StatusBadge` (seção 2) reaproveita este vocabulário em vez de duplicar | `ui/StatusPill.tsx` (já é a fonte da verdade, só precisa virar a única) |

---

## 9. Matriz página × componente

Legenda de "Estado atual": ✅ já usa um padrão consolidado · ⚠️ usa um padrão paralelo/divergente · ❌ implementação totalmente ad hoc · — não se aplica.
Legenda de "Estado desejado": mesma escala, projetada após a migração completa (Fase 5).

| Página | PageShell | PageHeader | MetricStrip | Toolbar | DataTable | Modal | Drawer | Estado atual | Estado desejado |
|---|---|---|---|---|---|---|---|---|---|
| `/` Dashboard | — (`p-6` próprio) | ⚠️ (hero custom) | ✅ (`DashboardGrid`+`MetricCard`) | — | — | — | — | ⚠️ | ✅ (via `PageShell`+`PageHeader` adaptado) |
| `/tarefas` Demandas | ✅ (`WorkspacePage`) | ⚠️ (hero custom) | ✅ | ⚠️ (`ToolbarCard` custom) | ❌ (tabela ad hoc) | ✅ | ✅ (`EntitySidePanel`) | ⚠️ | ✅ (exceto Kanban, ver seção 6) |
| `/projetos` Projetos | ✅ (`WorkspacePage`) | ⚠️ (hero custom) | ✅ | ⚠️ (`ToolbarCard` custom) | ❌ (tabela ad hoc) | ✅ | ✅ | ⚠️ | ✅ |
| `/trafego` Tráfego | ✅ (`WorkspacePage`) | ✅ (+ hero custom) | ✅ | ⚠️ (`ToolbarCard` custom) | ⚠️ (tabela custom, próxima do padrão) | — | — | ⚠️ | ✅ |
| `/agenda` Agenda | ❌ (`div` solto) | ✅ | ⚠️ (grid manual de `Card`) | ⚠️ (custom) | — (lista de cards, mantido — ver seção 6) | — | — | ❌ | ✅ (exceto DataTable, por design) |
| `/relatorios` Relatórios | ❌ (`div` solto) | ✅ | — | — | — | — | — | ❌ (placeholder) | ✅ (quando implementado) |
| `/equipe` Equipe | ❌ (`div` solto) | ✅ | — | — | — | — | — | ❌ (placeholder) | ✅ (quando implementado) |
| `/fornecedores` Fornecedores | ✅ (`CadastroPage`) | ❌ (título inline) | ✅ (`CadastroIndicators`) | ✅ (`CadastroToolbar`) | ✅ (`CadastroTable`) | ⚠️ (wrapper custom) | ✅ | ⚠️ | ✅ |
| `/configuracoes` Hub | — | — | — | — | — | — | — | ❌ (custom, não é listagem) | manter como está (é navegação, não cadastro) |
| `/configuracoes/clientes` | ✅ | ❌ (título inline) | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ **(página piloto — ver seção 11)** |
| `/configuracoes/equipes` | ✅ | ❌ (título inline) | ✅ | ✅ | ✅ | ✅ | ❌ (ausente) | ⚠️ | ✅ |
| `/configuracoes/grupos-clientes` | ✅ | ❌ (título inline) | ✅ | ✅ | ✅ | ✅ | ✅ (+ `EntitySummaryPanel`) | ⚠️ | ✅ |
| `/configuracoes/usuarios` | ✅ | ❌ (título inline) | ✅ | ✅ | ✅ | ✅ | ❌ (ausente) | ⚠️ | ✅ |
| `/configuracoes/agencias` | ✅ | ❌ (título inline) | ✅ | ✅ (ação sem handler) | ✅ | ❌ (ausente) | ❌ (ausente) | ⚠️ (CRUD incompleto) | ✅ (após completar CRUD) |
| `/configuracoes/workflows` | ✅ | ❌ (título inline) | — | ✅ (ação sem handler) | ❌ (cards custom, mantido — ver seção 6) | ❌ (ausente) | — | ⚠️ | ✅ (exceto DataTable, por design) |
| `/configuracoes/permissoes` | ❌ (`div` solto) | ✅ | — | — | — | — | — | ❌ (placeholder) | ✅ (quando implementado) |
| `/configuracoes/prioridades` | ❌ (layout antigo) | ✅ | ❌ (grid de `Card`, não é `MetricStrip`) | ❌ (sem busca) | ❌ (tabela antiga) | ❌ (ausente) | — | ❌ | ✅ |
| `/configuracoes/sla` | ❌ (layout antigo) | ✅ | ❌ | ❌ | ❌ (tabela antiga) | ❌ (ausente) | — | ❌ | ✅ |
| `/configuracoes/tipos-tarefa` | ❌ (layout antigo) | ✅ | ❌ | ❌ | ❌ (tabela antiga) | ❌ (ausente) | — | ❌ | ✅ |
| `/conta/perfil` | ❌ (`div` solto) | ✅ | — | — | — | — | — | ⚠️ | ✅ (via `PageShell`) |
| `/conta/notificacoes` | ❌ (`div` solto) | ✅ | — | — | — | — | — | ⚠️ | ✅ |
| `/conta/alterar-senha` | ❌ (`div` solto) | ✅ | — | — | — | — | — | ⚠️ | ✅ |
| `/design-system` | ✅ (`WorkspacePage`) | ✅ | — | — | — | — | — | ✅ (é a vitrine) | manter, mas atualizar conteúdo conforme migração |

---

## 10. Plano de migração incremental

Princípio geral: cada fase deve ser **mergeável isoladamente**, sem depender da fase seguinte já estar pronta, e sem quebrar nenhuma tela existente durante a transição (os componentes antigos de `cadastros/`/`workspace/` continuam funcionando até serem explicitamente aposentados).

### Fase 1 — Fundação: tokens, `PageShell`, `PageHeader`, `Breadcrumb`
- **Escopo**: criar `lib/design-tokens.ts`; criar `layout/PageShell.tsx`; estender `ui/PageHeader.tsx` com `actions?`/`size?`; **decidir e registrar** (nesta fase, sem aplicar ainda em massa) o tamanho de título padrão de cadastro (`text-lg`, mantendo o atual). `Breadcrumb` não precisa de nenhuma mudança — só é revalidado.
- **Arquivos candidatos**: `src/lib/design-tokens.ts` (novo), `src/components/layout/PageShell.tsx` (novo), `src/components/ui/PageHeader.tsx` (editado).
- **Dependências**: nenhuma (fase raiz).
- **Riscos**: baixíssimo — nenhum arquivo de página é tocado nesta fase; é só a criação da fundação.
- **Critérios de aceite**: `PageShell`/`PageHeader` renderizam corretamente em isolamento (testável na própria vitrine `/design-system`, adicionando um exemplo novo); `npm run typecheck` e `npm run lint` passam.
- **Validações**: revisão visual manual comparando o novo `PageHeader` com `size="page"` e `size="section"` contra os usos atuais de `PageHeader`/`CadastroPage`.

### Fase 2 — `MetricStrip`, `EntityToolbar`, `StatusBadge`, `EntityAvatar`
- **Escopo**: criar `data-display/MetricStrip.tsx`, `data-display/EntityToolbar.tsx`; promover `cadastros/CadastroAvatar.tsx` → `ui/EntityAvatar.tsx`; formalizar `ui/StatusPill.tsx` como badge de status oficial (sem remover `CadastroStatusBadge` ainda — isso só acontece quando a última tela que o usa migrar, na Fase 5).
- **Arquivos candidatos**: `src/components/data-display/MetricStrip.tsx` (novo), `src/components/data-display/EntityToolbar.tsx` (novo), `src/components/ui/EntityAvatar.tsx` (novo, movido de `cadastros/`).
- **Dependências**: Fase 1 (`PageShell`/tokens já definem padding a ser reaproveitado pelo `EntityToolbar`).
- **Riscos**: **médio** — decisão de densidade visual do `MetricStrip` (ver seção 2, `MetricCard` é mais espaçoso que `CadastroIndicators`) precisa de validação visual antes de aplicar; recomenda-se aprovação explícita com print/comparação lado a lado antes de seguir para a Fase 5.
- **Critérios de aceite**: os dois componentes novos existem e têm exemplo de uso na vitrine `/design-system`; nenhuma tela de produto foi alterada ainda nesta fase.
- **Validações**: comparação visual `CadastroIndicators` vs `MetricStrip` proposto; `npm run typecheck`/`lint`.

### Fase 3 — `DataTable`, `Pagination`, `EmptyState` (consolidado), `LoadingState`
- **Escopo**: criar `data-display/DataTable.tsx` unificando os 3 padrões de tabela hoje existentes; criar `data-display/Pagination.tsx`; consolidar `EmptyState`/`EmptyStateIllustration`/`WorkspaceEmptyState` em `ui/EmptyState.tsx`; criar `feedback/LoadingState.tsx`.
- **Arquivos candidatos**: `src/components/data-display/DataTable.tsx` (novo), `src/components/data-display/Pagination.tsx` (novo), `src/components/ui/EmptyState.tsx` (editado, absorve `EmptyStateIllustration`), `src/components/feedback/LoadingState.tsx` (novo).
- **Dependências**: Fase 1 (tokens de padding de célula/radius).
- **Riscos**: **alto** — `DataTable` é o componente com mais decisões visuais concentradas (radius, padding de célula, cor de header — ver seção 8). É o item de maior risco de todo o plano; recomenda-se implementá-lo primeiro **sem** ainda trocar nenhuma tela, validando visualmente contra os 3 padrões atuais lado a lado.
- **Critérios de aceite**: `DataTable` renderiza de forma equivalente (visualmente) ao padrão `CadastroTable` quando usado com as mesmas colunas/dados de exemplo; `Pagination` funciona isoladamente com dados mock na vitrine.
- **Validações**: comparação visual pixel-a-pixel (ou próxima disso) entre `CadastroTable` atual e `DataTable` novo usando o mesmo dataset de Clientes; `npm run typecheck`/`lint`/`build`.

### Fase 4 — Formulários, modais, drawers
- **Escopo**: criar `forms/FormField.tsx` (refatoração interna de `Input`/`Select`/`Textarea`), `forms/FormSection.tsx`, `forms/FormRepeatableList.tsx`; adicionar ARIA ao `Modal`; criar `feedback/ConfirmDialog.tsx`; expandir uso de `EntitySummaryPanel`/`EntityFieldRow`.
- **Arquivos candidatos**: `src/components/forms/FormField.tsx` (novo), `src/components/forms/FormSection.tsx` (novo), `src/components/forms/FormRepeatableList.tsx` (novo), `src/components/ui/Modal.tsx` (editado — ARIA), `src/components/feedback/ConfirmDialog.tsx` (novo).
- **Dependências**: Fase 1 (`PageShell`, para o `Modal`/`Drawer` decidirem largura consistente com os tokens definidos).
- **Riscos**: **médio** — mudar `Input`/`Select`/`Textarea` internamente (extraindo `FormField`) tem risco de regressão sutil de estilo se a extração não for fiel; adicionar ARIA ao `Modal` pode expor testes/comportamentos de foco não antes verificados manualmente.
- **Critérios de aceite**: `Input`/`Select`/`Textarea` continuam renderizando pixel-idênticos após a extração de `FormField` (comparação antes/depois); `Modal` com ARIA não quebra nenhum modal existente (teste manual de abrir/fechar/Escape em pelo menos 2 módulos).
- **Validações**: `npm run typecheck`/`lint`/`build`; teste manual de teclado (Tab, Escape) em pelo menos um `Modal` migrado.

### Fase 5 — Migração das páginas restantes
- **Escopo**: aplicar `PageShell`+`PageHeader`+`MetricStrip`+`EntityToolbar`+`DataTable`+`Pagination` em cada página da matriz da seção 9, uma de cada vez, começando pela página piloto (seção 11). Ao final, remover `cadastros/` e `workspace/` (exceto o que ainda for necessário) e atualizar a vitrine `/design-system`.
- **Arquivos candidatos**: cada `*View.tsx` da matriz da seção 9, em ordem de menor para maior risco (ver ordem sugerida abaixo).
- **Ordem sugerida dentro da Fase 5** (do menor para o maior risco, não da lista completa de uma vez):
  1. `ClientesView` (página piloto, ver seção 11)
  2. `FornecedoresView`, `GruposClientesView` (mesma família de padrão, risco similar ao piloto)
  3. `EquipesView`, `UsuariosView` (ganham `Drawer` pela primeira vez — mudança de comportamento, não só visual)
  4. `agencias/page.tsx`, `workflows/page.tsx` (completar handlers ausentes é trabalho adicional além da migração visual)
  5. `prioridades/sla/tipos-tarefa` (migração do layout mais antigo — maior salto visual)
  6. `DemandasView`, `ProjetosView` (envolvem `DataTable` com Kanban coexistindo, ver seção 6)
  7. `TrafegoView`, `AgendaView`, `DashboardView`, `conta/*`, `relatorios`, `equipe` (páginas especiais/soltas, aplicam só `PageShell`+`PageHeader`+`MetricStrip` onde fizer sentido)
- **Dependências**: Fases 1–4 completas.
- **Riscos**: variam por página (detalhados na ordem acima); risco agregado alto pelo volume de páginas, mitigado por migrar uma de cada vez.
- **Critérios de aceite**: cada página migrada preserva 100% das funcionalidades atuais (nenhuma ação, campo ou fluxo removido sem ser explicitamente uma decisão registrada); `git diff --stat` de cada página mostra troca de wrapper/imports, não reescrita de lógica de negócio.
- **Validações**: `npm run lint`, `npm run typecheck`, `npm run build` após cada página migrada (não em lote); `git status`/`git diff --stat` mostrados antes de considerar a página concluída, conforme o fluxo de trabalho do `CLAUDE.md`.

---

## 11. Página piloto

### Escolha: **Clientes** (`/configuracoes/clientes`, `ClientesView.tsx`)

**Por que deve ser a primeira:**
1. É o módulo **mais completo** entre os 7 de cadastro — usa todos os elementos do padrão da seção 5 (`CadastroPage`, `CadastroToolbar`, `CadastroIndicators`, `CadastroTable`, `CadastroAvatar`, `CadastroStatusBadge`, `EntitySidePanel`, `Modal` em fluxo de 2 passos com 5 abas). Migrar Clientes valida **todos** os componentes novos de uma vez, em vez de validar cada um isoladamente em páginas parciais.
2. É a **família de padrão mais replicada** — 6 outras telas (Equipes, Fornecedores, Grupos de Clientes, Usuários, Agências, Workflows) seguem a mesma estrutura de base; validar em Clientes primeiro reduz o risco de descobrir um problema estrutural só depois de já ter migrado várias páginas.
3. Ao contrário de Agências/Workflows (que têm handlers ausentes e CRUD incompleto), Clientes é uma tela **funcionalmente completa e estável** hoje — a migração fica isolada à camada visual, sem misturar "consertar bug" com "trocar componente", o que tornaria difícil isolar a causa de uma eventual regressão.
4. Tem o fluxo de formulário mais rico (lookup mock de CNPJ, 5 abas, lista dinâmica de contatos) — se `FormSection`/`FormRepeatableList` (Fase 4) funcionarem bem aqui, funcionam nos demais módulos, que são subconjuntos deste em complexidade.

### Componentes atuais (o que `ClientesView`/`NovoClienteModal` usam hoje)
`CadastroPage`, `CadastroToolbar`, `CadastroIndicators`, `CadastroTable` (+ constantes `cadastroTable*`), `CadastroAvatar`, `CadastroStatusBadge`, `EntitySidePanel` (com `<dl>` manual dentro, não usa `EntitySummaryPanel`/`EntityFieldRow`), `Modal`, `Tabs`, `Badge` (para mostrar tipo de documento no modal), `ClienteFormSections` (`DadosSection`, `EnderecoSection`, `EquipeSection`, `ContatosSection`, `HistoricoSection`), `NovoClienteButton`.

### Componentes compartilhados que passaria a usar (pós-migração)
`PageShell` (no lugar do wrapper de `CadastroPage`), `PageHeader` com `size="section"` (no lugar do `h2`/`p` inline de `CadastroPage`), `MetricStrip` (no lugar de `CadastroIndicators`), `EntityToolbar` (no lugar de `CadastroToolbar`), `DataTable` (no lugar de `CadastroTable`), `EntityAvatar` (no lugar de `CadastroAvatar`, mesma implementação em novo endereço), `StatusBadge`/`StatusPill` (no lugar de `CadastroStatusBadge`, com mapa de tom explícito para `Ativo`/`Inativo`), `EntitySummaryPanel`+`EntityFieldRow` (no lugar do `<dl>` manual dentro do `EntitySidePanel`), `FormSection`+`FormRepeatableList` (dentro de `ClienteFormSections`, para o wrapper de seção e a lista dinâmica de contatos). `Modal`, `Tabs`, `EntitySidePanel`, `NovoClienteButton` permanecem os mesmos (já corretos).

### O que permaneceria local (não migra para componente compartilhado)
- Todo o estado do draft (`useState<ClienteDraft>`), incluindo os dois passos do modal (`documento`/`cadastro`).
- A lógica de lookup mock de CNPJ (`mockCnpjLookup`, `setTimeout`) e a formatação de documento (`formatDocument`).
- As funções de resolução de nome por ID (`resolveEquipeNome`, `resolveResponsavelNome`, etc.).
- Os campos específicos de cada aba do formulário (`ClienteFormSections` continua definindo *quais* campos existem — só o *wrapper visual* de cada seção migra).
- A constante `EMPRESA_PADRAO_ID` e a geração de `codigoInterno`.
- O array/estado da tabela de clientes e a lógica de filtro por busca.

### O que seria removido
- O `<dl>` manual dentro do `EntitySidePanel` (substituído por `EntitySummaryPanel`+`EntityFieldRow`, mesma informação, menos código próprio).
- O import de `cadastros/CadastroPage`, `CadastroToolbar`, `CadastroIndicators`, `CadastroTable`, `CadastroAvatar`, `CadastroStatusBadge` (substituídos pelos equivalentes novos — **não removidos do repositório** nesta fase, só deixam de ser importados por Clientes; a remoção definitiva dos arquivos antigos só acontece ao final da Fase 5, quando nenhuma tela mais os usa).

### Riscos de regressão
- **Título visualmente diferente** se a decisão de tamanho de `PageHeader` (Fase 1) não preservar o `text-lg` atual — risco de a página parecer "maior"/diferente das demais que ainda não migraram, gerando inconsistência temporária proposital (aceitável durante a transição, mas deve ser comunicado).
- **Comportamento de foco do `EntitySidePanel`** pode mudar sutilmente se `EntitySummaryPanel` alterar a ordem de elementos focáveis dentro do painel.
- **`aria-label` da busca**: `EntityToolbar` precisa preservar exatamente o `aria-label={searchPlaceholder}` que `CadastroToolbar` já tem hoje, para não regredir acessibilidade.
- **`minWidth` da tabela**: `DataTable` precisa preservar o comportamento de `overflow-x-auto` + largura mínima que `CadastroTable` já tem, para não quebrar o scroll horizontal em mobile.
- **Linha clicável com `tabIndex`/`onKeyDown`**: `ClientesView` implementa esse comportamento manualmente hoje (não é parte de `CadastroTable`) — precisa ser preservado exatamente como está ao trocar para `DataTable`, já que esse padrão de acessibilidade (Enter/Espaço abrindo o painel) não está documentado como parte do componente de tabela em si.

---

## 12. Critérios para evitar abstração excessiva

- **Não criar componente usado por uma única página sem justificativa.** Todo componente proposto na seção 2 já tem 2+ usos reais mapeados na seção 1, exceto `ConfirmDialog`/`ErrorState`/`Pagination` — que são lacunas estruturais comprovadas (não abstrações antecipadas de recurso hipotético), justificadas por já serem necessárias para fechar o gap identificado no diagnóstico, não por "pode ser útil algum dia".
- **Não colocar regra de negócio em componente visual.** Reforça a seção 3: se um componente em `ui/`, `data-display/`, `forms/` ou `feedback/` precisar saber o nome de uma entidade (Cliente, Demanda, Projeto) ou importar um `*-mock.ts`, a proposta está errada e deve ser revista antes da implementação.
- **Não criar props genéricas demais.** Exemplo concreto de risco já identificado neste plano: `EntityToolbar` não deve ganhar uma prop `filterConfig: FilterDefinition[]` que tente descrever todos os filtros possíveis de todos os módulos (incluindo o caso rico de Tráfego) — o `filters` continua sendo um slot `ReactNode` livre, preenchido por cada View com os próprios `Select`/`MultiSelect`, não uma configuração declarativa genérica.
- **Não transformar todas as telas em uma única configuração gigante.** Não propor, por exemplo, um único componente `CadastroPageConfig` que receba um objeto JSON descrevendo colunas, campos de formulário, abas e validações de todas as 7 entidades de cadastro. Cada `*View.tsx` continua sendo um componente React explícito que compõe `PageShell`+`PageHeader`+`MetricStrip`+`EntityToolbar`+`DataTable` diretamente em JSX — mais fácil de ler, depurar e divergir pontualmente quando necessário (como já acontece hoje entre Clientes com 5 abas e Grupos de Clientes com 2).
- **Não criar abstrações mais complexas que os componentes atuais.** `DataTable`, por exemplo, deve continuar recebendo linhas via `children` (como `CadastroTable` já faz hoje), não migrar para um padrão `rows`+`renderRow`/`columns.render` genérico ao estilo de bibliotecas de grid corporativas — isso adicionaria uma camada de indireção que o projeto não usa em nenhum lugar hoje e que o `CLAUDE.md` explicitamente desencoraja ("não criar abstrações além do necessário").
- **Preferir composição em vez de componentes monolíticos.** `PageShell` não deve, por exemplo, aceitar props `title`/`metrics`/`toolbarProps`/`tableColumns` todas de uma vez e montar a página inteira internamente — a View continua compondo `<PageShell><PageHeader/><MetricStrip/><EntityToolbar/><DataTable/></PageShell>` explicitamente. Isso preserva a capacidade de cada página omitir/reordenar partes (como as páginas especiais da seção 6 já precisam fazer).

---

## 13. Definition of Done

A arquitetura visual só deve ser considerada padronizada quando, **de forma verificável**:

- [ ] **Alterações de espaçamento feitas em um único lugar** — mudar o padding padrão de página, o radius de card ou o padding de célula de tabela exige editar apenas `src/lib/design-tokens.ts` (e, quando aplicável, o `@theme inline` de `globals.css`), nunca múltiplos arquivos `*View.tsx`.
- [ ] **Header igual entre páginas compatíveis** — todas as páginas da categoria "cadastro" (linha "Estado desejado ✅" da matriz da seção 9) usam `PageHeader` com o mesmo `size`, sem título/descrição montado inline.
- [ ] **Tabela com comportamento consistente** — todas as tabelas de listagem (exceto Kanban/Agenda/Workflow, por design conforme seção 6) usam `DataTable`, com o mesmo radius, padding de célula e cor de cabeçalho, e nenhuma reimplementa `overflow-x-auto`/`minWidth` por conta própria.
- [ ] **Estados de loading, erro e vazio padronizados** — `LoadingState`, `ErrorState` e `EmptyState` (consolidado) são os únicos componentes usados para esses três estados em toda a base; nenhum módulo implementa skeleton/mensagem de erro/estado vazio ad hoc.
- [ ] **Acessibilidade preservada** — `Modal` com `role="dialog"`/`aria-modal`; `EntitySidePanel` mantém o comportamento de foco/`aria-*` já existente; nenhuma regressão de `aria-label`/`tabIndex` identificada nos testes manuais de cada fase.
- [ ] **Páginas especiais não descaracterizadas** — Kanban, Workflow, Dashboard, Agenda e Relatórios (quando implementado) preservam seu layout de corpo específico (seção 6), usando apenas `PageShell`/`PageHeader`/`MetricStrip` onde fizer sentido.
- [ ] **Lint, typecheck e build passando** — `npm run lint`, `npm run typecheck` e `npm run build` executados e aprovados após cada fase (não só ao final do plano), conforme o fluxo de trabalho descrito em `CLAUDE.md`.
- [ ] **Documentação atualizada** — `docs/design-system/taskfloww-design-system.md` reflete o estado pós-migração (as seções 4, 9 e 11 daquele documento, sobre componentes reutilizáveis, consistência e inventário, precisam ser reescritas para refletir a nova realidade, não descrever mais as duplicações que motivaram este plano).

---

*Fim do documento. Este plano não altera, move ou remove nenhum arquivo do projeto — é exclusivamente um documento de planejamento derivado de `docs/design-system/taskfloww-design-system.md`.*
