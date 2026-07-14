# TaskFloww — Design System (Documentação Técnica Oficial)

> **Documento gerado por análise estática do código-fonte real.**
> Data da análise: 2026-07-13 · Branch: `feature/ui` · Commit de referência: `aad941a`
> Escopo: `/docker/taskfloww/frontend/src` (Next.js App Router)
> Este documento **não altera nenhum arquivo do projeto**. É uma fotografia do estado atual da interface, incluindo inconsistências encontradas, para servir de referência oficial ao Claude Design em trabalhos futuros.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Estrutura visual](#2-estrutura-visual)
3. [Design Tokens](#3-design-tokens)
4. [Componentes reutilizáveis](#4-componentes-reutilizáveis)
5. [Componentes de Layout](#5-componentes-de-layout)
6. [Componentes de Formulário](#6-componentes-de-formulário)
7. [Componentes de Dados](#7-componentes-de-dados)
8. [Componentes de Feedback](#8-componentes-de-feedback)
9. [Fluxo das páginas](#9-fluxo-das-páginas)
10. [Fluxo visual](#10-fluxo-visual)
11. [Consistência](#11-consistência)
12. [Acessibilidade](#12-acessibilidade)
13. [Responsividade](#13-responsividade)
14. [Melhorias sugeridas](#14-melhorias-sugeridas)
15. [Design System ideal](#15-design-system-ideal)
16. [Inventário](#16-inventário)
17. [Mapa visual](#17-mapa-visual)

---

## 1. Visão geral

### 1.1 Arquitetura do frontend

O TaskFloww v2 (frontend) é uma aplicação **Next.js 16 (App Router)** 100% client-driven nesta fase — não existe integração real com o backend FastAPI. Todos os dados são mockados em memória via `useState` e arquivos `src/lib/*-mock.ts`. Não há autenticação, não há chamadas HTTP, não há persistência além de uma única chave de `localStorage` (estado do sidebar).

```
Next.js App Router
  └─ RootLayout (src/app/layout.tsx)
       └─ Shell (sidebar + header persistentes)
            └─ page.tsx de cada rota
                 └─ *View (componente principal da tela)
                      └─ subcomponentes de feature
                           └─ componentes ui/ (primitivos)
```

### 1.2 Frameworks e bibliotecas

| Categoria | Tecnologia | Versão | Observação |
|---|---|---|---|
| Framework | Next.js | 16.2.10 | App Router, sem Pages Router |
| UI | React | 19.2.4 | Componentes funcionais apenas |
| Linguagem | TypeScript | ^5 | `strict: true` |
| Estilo | Tailwind CSS | ^4 | **CSS-first** (`@import "tailwindcss"` + `@theme inline`), **não existe `tailwind.config.js`** |
| Ícones | lucide-react | 1.23.0 | Única biblioteca de ícones do projeto |
| Drag-and-drop | @dnd-kit/core, /sortable, /utilities | 6.3.1 / 10.0.0 / 3.2.2 | `/sortable` está instalado mas **nunca importado** em nenhum arquivo — dependência morta |
| Utilitário de classes | clsx | 2.1.1 | Instalado mas **nunca usado** — todo o projeto concatena classes com template strings manuais |
| Fontes | next/font/google (Geist Sans, Geist Mono) | — | Carregadas e expostas como CSS vars, mas **o `body` força `font-family: Arial, Helvetica, sans-serif`** em `globals.css` — a fonte Geist está carregada só é aplicada onde uma classe usa `font-sans`/`font-mono` explicitamente (nenhum componente faz isso hoje) |
| Gráficos | — | — | Nenhuma biblioteca de gráficos instalada; `DashboardChart` é um placeholder ilustrativo |
| Gerenciamento de estado global | — | — | Não existe Redux/Zustand/Jotai; apenas um único React Context (`SidebarContext`) |
| Testes | — | — | Nenhum framework de teste configurado, nenhum arquivo `.test.*`/`.spec.*` encontrado |

### 1.3 Organização de pastas (conforme convenção do `CLAUDE.md`, seguida à risca)

```
frontend/src/
├── app/            → SOMENTE rotas (page.tsx), zero regra de negócio
├── components/
│   ├── ui/         → primitivos reutilizáveis (Button, Card, Input...)
│   ├── layout/      → Shell, Sidebar, Header e afins
│   ├── cadastros/   → padrão CadastroPage/Table/Toolbar/Indicators/Avatar/StatusBadge
│   ├── workspace/   → padrão WorkspacePage/Section/Stats/Table/Toolbar/EmptyState
│   ├── design-system/ → componentes da vitrine viva em /design-system
│   ├── dashboard/, clientes/, equipes/, fornecedores/, grupos-clientes/,
│   │   usuarios/, demandas/, kanban/, projetos/, trafego/, agenda/, conta/
│   │   → um subdiretório por módulo de feature (View → Table → Modal → Sections)
├── types/          → um arquivo por entidade de domínio
└── lib/            → mocks (*-mock.ts), geradores de id, helpers
```

### 1.4 Convenções observadas

- Componentes em **PascalCase**, arquivos de mock em **kebab-case** com sufixo `-mock.ts`.
- Import absoluto via alias `@/*` → `src/*`.
- Nenhum arquivo CSS além de `globals.css` (2 variáveis de cor + reset mínimo) — **100% Tailwind utility classes**, zero CSS Modules, zero styled-components.
- Todo módulo de cadastro segue (ou deveria seguir) o fluxo: `Página → View → Tabela → Modal → Sections`.
- Existe uma filosofia visual documentada internamente em `docs/skills/ui-boxx.md` e `docs/skills/frontend.md` chamada **"Boxx"**: fundo bege claro, cards brancos, bordas grandes e arredondadas, sombras suaves, pouca cor forte, sidebar fixa — inspirada em iClips (fluxos), Linear (limpeza) e ClickUp/Asana (organização), **sem nunca copiar código ou layout literalmente** dessas referências.
- Fase atual do projeto (`PROJECT_STATUS.md`): protótipo de interface — **proibido** criar migrations, banco real, APIs reais ou autenticação nesta fase.

---

## 2. Estrutura visual

### 2.1 Header

Arquivo: `src/components/layout/Header.tsx`. `border-b border-zinc-200`, fundo **igual ao da página** (`bg-[#f4f1ec]`, não branco — o header não se destaca visualmente do conteúdo), `px-6 py-2`, **não é sticky** (rola junto com a página). Contém:
- `Breadcrumb` (trilha de navegação textual, `text-xs`)
- Título dinâmico da página (`text-lg font-semibold`), resolvido por um mapa estático `pathname → título`
- `HeaderActions` (ícones de Agenda/Atividades) — **ocultado** em `/fornecedores` e em qualquer rota `/configuracoes/*`

### 2.2 Sidebar

Arquivo: `src/components/layout/Sidebar.tsx`. `sticky top-0 h-screen`, fundo branco, `border-r border-zinc-200`, `shadow-sm`. Duas larguras controladas por `SidebarContext` (persistido em `localStorage["taskflow-sidebar"]`): **expandida** `w-48` (12rem) ou **colapsada** `w-14` (3.5rem, só ícones). Botão de toggle flutuante (`-right-3 top-14`, círculo branco com borda).

Estrutura interna (topo → base):
1. Logo (`T` em quadrado `bg-zinc-900`) + nome "TaskFloww" / subtítulo "Gestão operacional"
2. `HeaderSearch` (variante `sidebar`/`icon`)
3. `QuickCreateMenu` (botão "Criar novo" com dropdown de atalhos)
4. Navegação em 4 grupos: **Principal** (Dashboard, Tarefas, Projetos, Agenda), **Operação** (Tráfego, Relatórios), **Cadastros** (submenu colapsável: Clientes, Grupos de Clientes, Fornecedores, Equipes, Workflow), **Administração** (Configurações)
5. `UserMenu` fixo na base (avatar + nome + dropdown com Perfil/Notificações/Alterar Senha/Sair)

### 2.3 Footer

**Não existe componente de Footer no projeto.** Nenhuma página renderiza rodapé.

### 2.4 Layout principal (Shell)

Arquivo: `src/components/layout/Shell.tsx`:
```tsx
<main className="min-h-screen bg-[#f4f1ec] text-zinc-900">
  <SidebarProvider>
    <div className="flex min-h-screen min-w-0">
      <Sidebar />
      <section className="min-w-0 flex-1 overflow-x-hidden">
        <Header />
        {children}
      </section>
    </div>
  </SidebarProvider>
</main>
```
Layout flexbox simples: sidebar fixa + coluna de conteúdo com `overflow-x-hidden` (proteção contra estouro horizontal).

### 2.5 Containers e espaçamentos de página

**Existem três valores de padding raiz concorrentes** (ver seção 11 — inconsistências):
- `p-4 sm:p-5` — padrão `CadastroPage` (telas de configuração/cadastro)
- `p-8` — padrão `WorkspacePage` e a maioria das páginas que não usam wrapper (Agenda, Conta, Relatórios, Equipe)
- `p-6` — usado **apenas** no Dashboard (`DashboardView`), valor único não replicado em nenhum outro lugar

### 2.6 Grid

`DashboardGrid` (`src/components/ui/DashboardGrid.tsx`) é o único componente de grid reutilizável, com 5 variantes de coluna:

| `columns` | Classes |
|---|---|
| `auto`/`four` | `grid-cols-1 sm:grid-cols-2 xl:grid-cols-4` |
| `two` | `grid-cols-1 xl:grid-cols-2` |
| `three` | `grid-cols-1 md:grid-cols-3` |
| `five` | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5` |

Fora dele, grids são montados ad hoc com classes Tailwind diretas (`grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5` em `CadastroIndicators`, `grid gap-5 md:grid-cols-3` em `WorkspaceStats`, etc.) — **nenhum reaproveita `DashboardGrid`**.

### 2.7 Responsividade (visão geral — detalhado na seção 13)

Breakpoints Tailwind padrão (`sm 640`, `md 768`, `lg 1024`, `xl 1280`, `2xl 1536`). Sidebar não colapsa automaticamente em telas pequenas (só manualmente via botão); tabelas usam `overflow-x-auto` + `minWidth` fixo em vez de layout responsivo real; toolbars empilham em coluna abaixo de `lg`.

---

## 3. Design Tokens

> Nota metodológica: a página `/design-system` (`DesignSystemColors.tsx`/`DesignSystemTypography.tsx`) documenta uma paleta **incompleta** — o inventário abaixo foi extraído do uso real em todos os componentes do projeto, não apenas do que está listado na vitrine interna.

### 3.1 Cores

#### Base (documentadas em `globals.css` e na vitrine)

| Papel | Valor | Classe Tailwind |
|---|---|---|
| Background da aplicação | `#f4f1ec` | `bg-[#f4f1ec]` |
| Surface (cards) | `#ffffff` | `bg-white` |
| Surface "soft" (headers de tabela, empty states) | `#faf8f4` | `bg-[#faf8f4]` |
| Texto principal | `#18181b` (zinc-900) | `text-zinc-900` |
| Texto secundário | zinc-500 | `text-zinc-500` |
| Texto terciário/legendas | zinc-400 | `text-zinc-400` |
| Borda padrão de superfícies | zinc-100 | `border-zinc-100` |
| Borda de inputs/botão secundário | zinc-200 | `border-zinc-200` |

Cores adicionais usadas amplamente no código mas **não documentadas** na vitrine `/design-system`: `zinc-50`, `zinc-300`, `zinc-600`, `zinc-700`, `zinc-950`.

#### Cores semânticas de estado (vocabulário oficial via `StatusPill`/`MetricCard`)

```
neutral: bg-zinc-100    text-zinc-700   ring-zinc-200
blue:    bg-blue-50     text-blue-700   ring-blue-100
green:   bg-emerald-50  text-emerald-700 ring-emerald-100   (tom chamado "green" usa a paleta emerald)
amber:   bg-amber-50    text-amber-700  ring-amber-100
red:     bg-red-50      text-red-700    ring-red-100
```
Este é o vocabulário mais consistente do sistema, reaproveitado por `StatusPill`, `MetricCard` e `ProgressBar`.

#### Cor primária / secundária

Não há um "azul de marca" nem "cor primária" explícita fora do vocabulário de status — **zinc-900 (quase preto)** funciona como cor de ação primária (botões, texto de destaque, logo), e **blue-600/blue-700** funciona como cor de destaque de navegação/interação (item ativo do menu, ícones informativos, links).

#### Cor de erro/sucesso/aviso (fora do vocabulário `StatusPill`)

- Erro textual: `text-red-600` (mensagem de senha inválida em Alterar Senha; item "Sair" do UserMenu)
- Badge de notificação: `bg-red-500` (contador no UserMenu)
- Sucesso/ativo: `emerald-50/700` (via `CadastroStatusBadge` e `StatusPill`)

#### Paletas paralelas não-oficiais (inconsistências — detalhadas na seção 11)

- **Prioridade** (Demandas/Projetos): `alta` = slate, `media` = sky, `baixa` = blue — paleta própria, não reaproveita o vocabulário `StatusPill`.
- **Tipo de contato** (Agenda): 8 cores próprias (`blue`, `amber`, `emerald`, `violet`, `fuchsia`, `sky`, `orange`, `zinc`) — únicas no sistema, incluindo tons (`violet`, `fuchsia`, `orange`) que não existem em nenhum outro componente.
- **Carga operacional** (Tráfego): função `classifyCarga()` com paleta própria de "nível de carga" (Livre/Leve/Moderada/Alta).

### 3.2 Tipografia

- **Família aplicada de fato**: `Arial, Helvetica, sans-serif` (via `body { font-family: ... }` em `globals.css`).
- **Família carregada mas não aplicada**: Geist Sans / Geist Mono (`next/font/google`), expostas como `--font-sans`/`--font-mono` no `@theme inline`, porém nenhuma classe `font-sans`/`font-mono` é usada no `body` — apenas alguns valores numéricos usam `font-mono` pontualmente (ex.: hex de cor na vitrine, tempo decorrido em Tráfego).

Escala tipográfica observada (consolidada de todo o código, não só da vitrine):

| Classe | Uso típico |
|---|---|
| `text-3xl font-bold` | Título de página (`PageHeader`), valores grandes de stat card |
| `text-xl font-semibold` | Título de seção (`Section`) |
| `text-lg font-semibold` | Título de `CadastroPage`, títulos de `EmptyState`/`WorkspaceEmptyState` |
| `text-base font-semibold` | `SectionHeader` |
| `text-sm` | Corpo de texto padrão, labels de formulário, células de tabela |
| `text-xs` | Legendas, descrições secundárias |
| `text-[11px]` | Cabeçalhos de tabela (uppercase), labels de indicadores |
| `text-[10px]` / `text-[9px]` | Micro-labels (seções da sidebar, headers de dropdown) — uppercase + `tracking-[0.12em]`–`tracking-[0.2em]` |
| `font-mono` | Valores numéricos/código (hex de cor, tempo decorrido) |
| `tabular-nums` | Alinhamento de números em tabelas/indicadores |

Pesos usados: `font-medium`, `font-semibold`, `font-bold` (não há `font-light`/`font-thin`). Não há documentação formal de `line-height` — o projeto usa os padrões do Tailwind (`leading-*` raramente explicitado, exceto `leading-5` em `SectionHeader`).

### 3.3 Ícones

Biblioteca única: **lucide-react**. Convenção: `strokeWidth={2}` explícito na maioria dos usos, tamanhos `h-4 w-4` (padrão), `h-5 w-5` (ações maiores, ex. fechar painel), `h-3.5 w-3.5` (chevrons pequenos). Todos os ícones decorativos usam `aria-hidden="true"`. ~40 ícones distintos importados no projeto todo (ex.: `LayoutDashboard`, `ListTodo`, `FolderKanban`, `BookUser`, `RadioTower`, `BarChart3`, `Building2`, `Network`, `Truck`, `Users`, `Settings`, `Search`, `Plus`, `Bell`, `CalendarDays`, `Clock3`, `Pencil`, `X`, `Inbox`, `ChevronDown`, `PanelLeftClose/Open`, `Database`).

### 3.4 Border radius

| Token | Uso |
|---|---|
| `rounded-full` | Badges/pills, avatares, `Switch` |
| `rounded-3xl` | Cards, `Modal`, `EmptyState`, componentes `Workspace*`, drawers |
| `rounded-2xl` | `Button`, componentes `Cadastro*`, itens de navegação da sidebar (alguns), dropdowns |
| `rounded-xl` | Controles de formulário (`Input`, `Select`, `Textarea`), busca do `CadastroToolbar` |
| `rounded-lg` | Itens de navegação da sidebar, botões de ícone do header |

**`rounded-2xl` (padrão Cadastro) e `rounded-3xl` (padrão Workspace) competem como "raio de card dominante"** — ver seção 11.

### 3.5 Sombras

- `shadow-sm` — sombra universal de superfície (quase todo container "cartão")
- `shadow-lg` — `Modal`
- `shadow-xl` — dropdowns (`UserMenu`, `QuickCreateMenu`), `EntitySidePanel`
- `shadow-md` — hover de `MetricCard` (`hover:shadow-md`)

### 3.6 Espaçamentos

Gaps de grid: `gap-2`, `gap-3`, `gap-4`, `gap-5`, `gap-6` (sem token nomeado — cada componente escolhe um valor). Espaçamento vertical entre seções de página: `space-y-3` (Cadastro), `space-y-5`/`space-y-6` (Workspace/Dashboard). Padding interno de card: `p-3`–`p-6` variando por componente (ver tabela na seção 2.5/11).

### 3.7 Animações e transições

- `transition` genérico (duração padrão do Tailwind, ~150ms) — usado universalmente em hover/focus.
- `transition-colors` — específico para mudanças de cor (nav links, botões).
- `duration-200 ease-out` — único uso de duração customizada, na largura da sidebar (`transition-[width]`).
- `translate-x-*` / `scale-95→100` / `opacity-0→100` — animação de abertura de dropdowns (`UserMenu`, `QuickCreateMenu`).
- `animate-pulse` — skeleton de loading em Tráfego, **nunca ativado** (`loading` está hardcoded como `false`, código morto).
- Não há biblioteca de animação (Framer Motion, etc.) — tudo via Tailwind transitions/transforms puros.

---

## 4. Componentes reutilizáveis

> Legenda de "Reutilizável?": ✅ sim (design genérico, sem acoplamento a domínio) · ⚠️ parcial (reutilizável mas com props específicas de um contexto) · ❌ não (só usado por um único módulo hoje, mesmo sendo tecnicamente genérico)

### 4.1 `src/components/ui/` (primitivos)

| Nome | Localização | Props principais | Onde é utilizado | Reutilizável? | Duplicação? | Sugestão |
|---|---|---|---|---|---|---|
| `Button` | `ui/Button.tsx` | `variant: "primary"\|"secondary"`, extends `ButtonHTMLAttributes` | Em praticamente toda tela do projeto | ✅ | Não, mas **sem variante destrutiva/ghost/tamanhos** | Adicionar `variant="danger"` e `size="sm"\|"md"` |
| `Card` | `ui/Card.tsx` | `children` | Vitrine `/design-system`, `AgendaStats`, `PerfilView`, telas soltas | ✅ | **Sem borda**, diferente de todo o resto do sistema | Adicionar `border border-zinc-100` |
| `Input` | `ui/Input.tsx` | `label`, extends `InputHTMLAttributes` | Formulários em quase todos os módulos | ✅ | Sem estado de erro/validação visual | Adicionar prop `error?: string` |
| `Select` | `ui/Select.tsx` | `label`, `options: {value,label}[]` | Todos os formulários com campo de seleção | ✅ | Mesma limitação do `Input` | idem |
| `Textarea` | `ui/Textarea.tsx` | `label`, extends `TextareaHTMLAttributes` | Descrições/observações em vários formulários | ✅ | idem | idem |
| `MultiSelect` | `ui/MultiSelect.tsx` | `options`, `values`, `onChange`, `label?`, `placeholder?`, `disabled?` | Filtro de usuário/departamento em Tráfego | ⚠️ | Não há componente de "Autocomplete" — este supre parcialmente o papel | — |
| `Switch` | `ui/Switch.tsx` | `checked`, `onCheckedChange`, `label?` | `NotificacoesView`, `AcessoSection` (Equipes) | ✅ | Não | — |
| `Modal` | `ui/Modal.tsx` | `open`, `onClose`, `children`, `maxWidthClassName?` | Todos os módulos de cadastro (Novo/Editar) | ✅ | **Sem `role="dialog"`/`aria-modal`** (diferente de `EntitySidePanel`, que tem) | Adicionar atributos ARIA |
| `Badge` | `ui/Badge.tsx` | `children` | Vitrine, `WorkspaceTable` (showcase) | ⚠️ | Cor única (cinza), não usado em produção real fora da vitrine | Avaliar se deve ser removido ou usado como badge "neutro genérico" |
| `StatusPill` | `ui/StatusPill.tsx` | `tone: neutral\|blue\|green\|amber\|red`, `dot?` | Dashboard, Demandas, Projetos, Tráfego | ✅ | É o componente de badge de status **mais consistente** do sistema | Candidato a padrão único de badge de status |
| `PageHeader` | `ui/PageHeader.tsx` | `title`, `description` | Tráfego, Agenda, Conta (3 telas), Relatórios, Equipe, vitrine | ✅ | Não | — |
| `Section` | `ui/Section.tsx` | `title`, `children` | Pouco usado fora de composições genéricas | ✅ | Sobreposição conceitual com `SectionHeader`/`WorkspaceSection` | Consolidar em um único componente de "cabeçalho de seção" |
| `SectionHeader` | `ui/SectionHeader.tsx` | `title`, `description?`, `eyebrow?`, `action?` | `DashboardAgenda`, `DashboardActivities`, `DashboardChart`, `RankingCard` | ✅ | idem acima | — |
| `ToolbarCard` | `ui/ToolbarCard.tsx` | `children`, `className?` | `DemandasToolbar`, `ProjetosToolbar`, `TrafegoFilters` | ⚠️ | Sobrepõe-se a `CadastroToolbar`/`WorkspaceToolbar` (3 formas de montar barra de filtro) | Unificar |
| `EmptyState` | `ui/EmptyState.tsx` | `title`, `description` | `WorkspaceEmptyState` (wrapper), Agenda | ✅ | Duplicado conceitualmente com `EmptyStateIllustration` | Unificar em um único componente com prop `icon?` opcional |
| `EmptyStateIllustration` | `ui/EmptyStateIllustration.tsx` | `title`, `description`, `icon?`, `action?`, `size?` | `DashboardChart`, `RankingCard`, `TrafegoAgoraTable`, colunas vazias do Kanban de Demandas | ✅ | idem acima | — |
| `MetricCard` | `ui/MetricCard.tsx` | `title`, `value`, `description?`, `icon?`, `tone?`, `badge?`, `footer?` | Dashboard, Demandas, Projetos, Tráfego (via `DashboardGrid`) | ✅ | É o card de KPI mais usado — mas convive com `CadastroIndicators` (outro padrão de indicador) | Ver seção 11 |
| `RankingCard` | `ui/RankingCard.tsx` | `title`, `description?`, `items`, `emptyTitle?`, `emptyDescription?` | `TrafegoCargaUsuarios`, `TrafegoCargaDepartamentos` | ⚠️ | Não | — |
| `ProgressBar` | `ui/ProgressBar.tsx` | `value`, `tone?`, `label?` | Usado internamente por `RankingCard` | ✅ | Não | — |
| `DashboardGrid` | `ui/DashboardGrid.tsx` | `children`, `columns?`, `className?` | Dashboard, Demandas, Projetos, Tráfego | ✅ | Coexiste com grids ad hoc (`CadastroIndicators`, `WorkspaceStats`) que não o reaproveitam | Ver seção 11 |
| `EntityFieldRow` | `ui/EntityFieldRow.tsx` | `label`, `value?`, `emptyValue?`, `variant?` | `EntitySummaryPanel` (só em Grupos de Clientes) | ⚠️❌ | Único módulo consumidor | Expandir uso para Clientes/Fornecedores (que montam `dl` manualmente) |
| `EntitySidePanel` | `ui/EntitySidePanel.tsx` | `open`, `onClose`, `onEdit?`, `title`, `description?`, `children`, `footer?` | Clientes, Fornecedores, Grupos de Clientes, Demandas, Projetos | ✅ | É o drawer de detalhe mais robusto (ARIA completo) — não usado por Equipes/Usuários (que não têm detalhe) | Padronizar uso em Equipes/Usuários |
| `EntitySummaryPanel` | `ui/EntitySummaryPanel.tsx` | `badges?`, `sections?`, `children?` | Apenas Grupos de Clientes | ❌ | Clientes/Fornecedores montam painel manualmente em vez de reusar isso | Expandir uso |

### 4.2 `src/components/cadastros/` (padrão Cadastro)

| Nome | Localização | Onde é usado | Reutilizável? | Sugestão |
|---|---|---|---|---|
| `CadastroPage` | `cadastros/CadastroPage.tsx` | Clientes, Equipes, Fornecedores, Grupos de Clientes, Usuários, Agências, Workflows | ✅ | Padrão mais adotado (7 telas reais) — candidato a "vencedor" na unificação |
| `CadastroToolbar` | `cadastros/CadastroToolbar.tsx` | idem | ✅ | idem |
| `CadastroTable` (+ 4 constantes de classe) | `cadastros/CadastroTable.tsx` | idem | ✅ | idem |
| `CadastroIndicators` | `cadastros/CadastroIndicators.tsx` | idem | ✅ | idem |
| `CadastroAvatar` | `cadastros/CadastroAvatar.tsx` | idem | ✅ | Sem equivalente em `Workspace*` — deveria ser promovido a `ui/` |
| `CadastroStatusBadge` | `cadastros/CadastroStatusBadge.tsx` | idem, mas também reaproveitado indevidamente para "Categoria" (Fornecedores) e "Perfil" (Usuários) | ⚠️ | Criar badge neutro separado para valores não-status |

### 4.3 `src/components/workspace/` (padrão Workspace)

| Nome | Localização | Onde é usado de fato | Reutilizável? | Observação |
|---|---|---|---|---|
| `WorkspacePage` | `workspace/WorkspacePage.tsx` | Demandas, Projetos, Tráfego, vitrine `/design-system` | ✅ | Único componente do grupo com uso real fora da vitrine |
| `WorkspaceEmptyState` | `workspace/WorkspaceEmptyState.tsx` | Demandas, Projetos (não Tráfego) | ⚠️ | Passthrough fino de `EmptyState` |
| `WorkspaceSection` | `workspace/WorkspaceSection.tsx` | **Somente a vitrine** `/design-system` | ❌ | Nenhuma tela de produto usa — código essencialmente morto em produção |
| `WorkspaceStats` | `workspace/WorkspaceStats.tsx` | **Somente a vitrine** | ❌ | idem — Demandas/Projetos/Tráfego usam `DashboardGrid`+`MetricCard` em vez disso |
| `WorkspaceTable` | `workspace/WorkspaceTable.tsx` | **Somente a vitrine** | ❌ | idem — Demandas/Projetos usam tabela ad hoc própria |
| `WorkspaceToolbar` | `workspace/WorkspaceToolbar.tsx` | **Somente a vitrine** | ❌ | idem — Demandas/Projetos/Tráfego usam `ToolbarCard` + markup próprio |

### 4.4 `src/components/design-system/` (vitrine viva, não reutilizável fora de si mesma)

`DesignSystemColors`, `DesignSystemTypography`, `DesignSystemButtons`, `DesignSystemInputs`, `DesignSystemBadges`, `DesignSystemCards`, `DesignSystemWorkspace` — todos são componentes de demonstração/documentação, montados especificamente para a página `/design-system`. Não devem (e não são) importados por telas de produto.

### 4.5 `src/components/layout/`

| Nome | Reutilizável? | Observação |
|---|---|---|
| `Shell`, `Sidebar`, `Header`, `Breadcrumb`, `UserMenu`, `QuickCreateMenu`, `HeaderSearch`, `HeaderActions` | ❌ (por natureza) | Singletons de aplicação — cada um é montado uma única vez no layout raiz |
| `SidebarContext` (`useSidebar`) | ✅ | Único hook customizado do projeto |

### 4.6 Componentes específicos de feature (não reutilizáveis fora do próprio módulo)

Todos os componentes em `demandas/`, `kanban/`, `projetos/`, `trafego/`, `agenda/`, `conta/`, `dashboard/`, `clientes/`, `equipes/`, `fornecedores/`, `grupos-clientes/`, `usuarios/` são acoplados ao domínio da sua respectiva tela (Views, Modals, FormSections, Tables, Toolbars, Stats específicos) — nenhum é candidato a reuso cross-módulo, exceto pelos padrões já extraídos em `ui/`, `cadastros/` e `workspace/`.

---

## 5. Componentes de Layout

### Header
Ver seção 2.1. Sem estado de loading/erro próprio — título é resolvido de forma síncrona a partir de um mapa estático `pathname → título` (`resolveTitle()` em `Header.tsx`), com fallback que transforma o último segmento de `/configuracoes/*` em Title Case automaticamente.

### Sidebar
Ver seção 2.2. Estados: **expandida** (mostra labels, seções tituladas, botão "Criar novo" com texto) e **colapsada** (só ícones, tooltips via `title`). O submenu "Cadastros" tem seu próprio estado local (`cadastrosOpen`) e se auto-expande quando a rota ativa pertence a ele (`cadastrosActive`). Indicador de rota ativa: barra azul vertical à esquerda do item (`bg-blue-600`) + fundo `bg-blue-50`/texto `text-blue-700`.

### Breadcrumb
`src/components/layout/Breadcrumb.tsx`. Puramente derivado da URL via mapa estático `breadcrumbLabels`. Lógica especial: em rotas `/configuracoes/*` mostra a trilha completa a partir de `/configuracoes`; em `/fornecedores` mostra só o próprio item (sem prefixo "Dashboard"); nas demais rotas sempre prefixa com "Dashboard" (`/`).

### Menus (User Menu)
`src/components/layout/UserMenu.tsx`. Dropdown ancorado à direita do avatar (`left-full`, abre para a direita da sidebar), fecha em clique-fora (`mousedown`) e `Escape`. Duas seções: "CONTA" (Perfil/Notificações/Alterar senha, com badge de contador fixo "3" hardcoded em Notificações) e ação isolada "Sair" (`variant: danger`, `text-red-600`). Rodapé com metadados fixos de "Último acesso"/"Último IP" (mock, não dinâmico).

### Pesquisa (Header Search)
`src/components/layout/HeaderSearch.tsx`. Três variantes: `header` (campo completo, `hidden md:flex`, só aparece em telas ≥768px — porém o `Header` real **não usa** essa variante, só existe no código para uso futuro), `sidebar` (campo decorativo sem `onChange`, é só um `<label>` visual sem `<input>` real — busca **não funcional** neste nível), `icon` (botão compacto para sidebar colapsada). Nenhuma das variantes está conectada a uma busca global real — é puramente decorativo hoje.

### Quick Actions
`src/components/layout/QuickCreateMenu.tsx`. Dropdown com 5 atalhos fixos (`+Tarefa`, `+Projeto`, `+Cliente`, `+Fornecedor`, `+Usuário`), cada um é apenas um `<Link>` para a rota de listagem correspondente (não abre modal de criação diretamente — o usuário ainda precisa clicar em "Novo X" na tela de destino).

### Cards / Painéis
- `Card` (`ui/Card.tsx`) — genérico, sem borda.
- `MetricCard` — card de KPI com ícone, tom semântico, badge e footer opcionais.
- `ToolbarCard` — invólucro neutro para barras de filtro custom.
- `RankingCard` — card de ranking com barra de progresso por item.
- `EntitySidePanel` / `EntitySummaryPanel` — painel lateral de detalhe (drawer).

---

## 6. Componentes de Formulário

| Componente | Existe? | Localização | Observações |
|---|---|---|---|
| Input (texto) | ✅ | `ui/Input.tsx` | Label obrigatória, sem estado de erro visual |
| Textarea | ✅ | `ui/Textarea.tsx` | `rows={3}` fixo, sem redimensionamento configurável via prop |
| Select | ✅ | `ui/Select.tsx` | Nativo (`<select>`), sem busca/filtro interno |
| Autocomplete | ⚠️ parcial | `ui/MultiSelect.tsx` | Não é autocomplete real (sem busca de texto), é multi-checkbox em popover fixo; busca com sugestão só existe ad hoc em `NovoGrupoClienteModal` (campo de busca de clientes a vincular) |
| Checkbox | ⚠️ | Inline (`<input type="checkbox">`) em `MultiSelect`, `PermissoesSection`, contatos com "acesso ao portal" | Não existe componente `Checkbox` dedicado — cada tela estiliza o checkbox nativo do navegador sem customização visual |
| Switch | ✅ | `ui/Switch.tsx` | Toggle customizado, usado em Notificações e Permissões de Equipe |
| Radio | ❌ | — | Não existe nenhum uso de `<input type="radio">` no projeto |
| Upload | ❌ | — | `ArquivosProjetoSection` (Projetos) é um placeholder — texto indicando "fase futura", sem input de arquivo funcional |
| Date Picker | ⚠️ | `<input type="date">` via `Input` | Não há date picker customizado — usa o seletor nativo do navegador |
| Botões | ✅ | `ui/Button.tsx` | 2 variantes (`primary`/`secondary`), sem tamanhos, sem variante destrutiva |
| Validação | ⚠️ mínima | `AlterarSenhaView` | Único formulário com validação client-side real (senha ≥ 8 caracteres + confirmação); demais formulários só desabilitam o botão "Salvar" com base em campos obrigatórios preenchidos, sem mensagens de erro |
| Máscaras | ⚠️ | `formatDocument()` (por módulo, duplicado em Clientes/Fornecedores) | Formatação de CPF/CNPJ em tempo real; CEP tem lookup mock (`mockCepLookup`, só em Usuários) que autopreenche endereço |
| Mensagens de erro | ❌ quase ausente | `AlterarSenhaView` (`text-red-600`) | Nenhum outro componente de formulário exibe mensagem de erro inline; não há padrão de `aria-invalid`/borda vermelha em `Input`/`Select`/`Textarea` |

---

## 7. Componentes de Dados

### Tabela
**Existem 3 implementações concorrentes e não compartilhadas**:
1. `CadastroTable` (+ classes `cadastroTable*`) — usado por 7 telas de cadastro. `rounded-2xl`, header `bg-[#faf8f4]` uppercase `text-[11px]`, célula `px-3 py-2`.
2. `WorkspaceTable` — usado **apenas na vitrine**. `rounded-3xl`, header `bg-[#faf8f4]` normal (sem uppercase), célula `px-6 py-4`.
3. Tabela ad hoc em `DemandasTable`/`ProjetosTable` — **não reutiliza nenhum dos dois padrões acima**. `rounded-3xl`, header `bg-zinc-50/80` uppercase `text-xs tracking-[0.12em]`, célula `px-4 py-3`. É um terceiro padrão visual só para esses 2 módulos.

`TrafegoAgoraTable` usa markup próprio mas com header `bg-[#faf8f4]` + uppercase `[11px]` — mais próximo do padrão `CadastroTable`/`WorkspaceTable` do que do padrão de Demandas/Projetos.

### Paginação
**Não existe nenhum componente ou implementação de paginação em todo o projeto.** Todas as listagens renderizam o array completo de dados mock.

### Filtros
Padrão recorrente: campo de busca textual (client-side, substring match) + `Select` de status + (em Tráfego) `MultiSelect` de usuário/departamento e toggle de período. Implementado via `CadastroToolbar`, `ToolbarCard` ou `WorkspaceToolbar`, conforme o módulo.

### Pesquisa
Sempre client-side, sobre o array em memória — nenhuma chamada assíncrona/debounce.

### Ordenação
**Não existe nenhuma tabela com cabeçalho clicável/ordenável em todo o projeto.**

### Cards (de dados)
`MetricCard` (KPI), `CadastroIndicators` (indicador compacto), `RankingCard` (ranking com barra), cards de contato em `AgendaList` (lista de cards em vez de tabela).

### Kanban
Dois Kanbans distintos e **não relacionados**:
1. **`demandas/DemandaKanban*`** — em produção (rota `/tarefas`), **somente leitura** (sem drag-and-drop, cartão é um `<button>` que abre o painel de detalhe). O próprio código sinaliza isso com um badge "Somente leitura" e um comentário explícito: *"Etapas mock por demanda. Não há motor real, Kanban ou drag-and-drop nesta fase."* 6 colunas fixas por status.
2. **`src/components/kanban/`** (`KanbanBoard`, `KanbanColumn`, `KanbanCard`, `TaskDetailModal`) — implementação **real** de drag-and-drop com `@dnd-kit/core` (`DndContext`, `useDraggable`, `useDroppable`, `PointerSensor`), mas **é código órfão**: não é importado por nenhuma rota do app. É provavelmente um protótipo anterior ao módulo de Demandas atual.

### Timeline / Histórico
Padrão `HistoricoSection` repetido em Clientes, Equipes, Fornecedores, Usuários, Grupos de Clientes, Projetos, Demandas: campo de busca (decorativo) + tabela read-only (Usuário/Data/Dispositivo/IP/Ação). Na maioria dos módulos os dados são **mock estático desconectado** do draft; **apenas Fornecedores** de fato anexa um novo evento ao array `historico` a cada salvamento real.

### Listagens
Majoritariamente tabelas; único módulo com layout de "lista de cards" é a Agenda (`AgendaList`).

---

## 8. Componentes de Feedback

| Componente | Existe? | Detalhes |
|---|---|---|
| Loading | ⚠️ quase ausente | Só existe: (a) texto "Buscando dados..." + botão desabilitado durante lookup mock de CNPJ (Clientes/Fornecedores); (b) skeleton `animate-pulse` em Tráfego, mas a flag `loading` está hardcoded em `false` — **nunca é ativado na prática** |
| Skeleton | ⚠️ código morto | Único uso é o skeleton de Tráfego citado acima |
| Spinner | ❌ | Não existe componente de spinner em nenhum lugar do projeto |
| Toast / notificação de ação | ❌ | **Não existe nenhum sistema de toast.** Ações de "Salvar" fecham o modal silenciosamente ou apenas fazem `console.log` — o usuário não recebe nenhuma confirmação visual de sucesso |
| Alertas | ❌ componente dedicado | Avisos são caixas ad hoc (ex.: box "Monitoramento — Somente leitura nesta fase" em `TrafegoHeader`) — não existe um componente `Alert`/`Banner` reutilizável |
| Modal | ✅ | `ui/Modal.tsx` — centralizado, overlay `bg-zinc-900/40`, fecha com `Escape` ou clique fora. **Sem `role="dialog"`/`aria-modal`** |
| Dialog | ✅ (mesmo componente que Modal) | Não há distinção entre "Modal" e "Dialog" no código — um único componente cobre ambos os casos |
| Drawer | ✅ | `EntitySidePanel` — painel lateral direito, com foco automático, bloqueio de scroll do body, ARIA completo (`role="dialog"`, `aria-modal`, `aria-labelledby`) |
| Empty State | ✅ (3 variações) | `EmptyState` (básico, borda tracejada), `EmptyStateIllustration` (com ícone, tamanhos `default`/`compact`), `WorkspaceEmptyState` (wrapper fino de `EmptyState`) — Agenda usa `EmptyState` com emoji no título (`"📇 Nenhum contato encontrado."`), quebrando o padrão dos demais (sem emoji) |
| Error State | ❌ quase ausente | Único exemplo real é a mensagem de senha inválida em Alterar Senha; nenhuma tela trata erro de "carregamento falhou" (não há chamadas de API para falhar nesta fase) |
| Success State | ❌ | Não existe feedback visual de sucesso em nenhuma ação de salvar/criar |

---

## 9. Fluxo das páginas

Para cada página: objetivo · rota · componentes · ações · permissões (conforme RBAC planejado em `PROJECT_STATUS.md`, **ainda não implementado tecnicamente** — nenhuma tela hoje verifica perfil de usuário) · API · loading · vazio · erro · responsividade.

### `/` — Dashboard
- **Objetivo**: visão executiva geral (saudação, KPIs, agenda do dia, atividades recentes, atalhos).
- **Componentes**: `DashboardView` → hero custom + `DashboardStats`(`MetricCard`×4) + `DashboardAgenda` + `DashboardActivities` + `DashboardChart` (placeholder) + `DashboardShortcuts`.
- **Ações**: nenhuma funcional (atalhos sem `onClick`, gráfico é ilustrativo).
- **Permissões**: planejado para todos os perfis autenticados; não implementado.
- **API**: nenhuma — dados hardcoded no próprio componente (não usa `lib/*-mock.ts`).
- **Loading/Vazio/Erro**: nenhum dos três estados existe (dados sempre presentes).
- **Responsividade**: `DashboardGrid columns="four"` → 1 coluna (mobile) → 2 (`sm`) → 4 (`xl`).

### `/tarefas` — Demandas (Lista + Kanban)
- **Objetivo**: gestão operacional de demandas/tarefas com alternância lista/kanban.
- **Componentes**: `DemandasView` (`WorkspacePage`) → hero + `DemandasStats`(5 `MetricCard`) + `DemandasToolbar` + (`DemandasKanban` **ou** `DemandasTable`) + `NovaDemandaModal` + `DemandaDetailsDrawer` (`EntitySidePanel` com 5 abas: Dados/Briefing/Workflow/Responsáveis/Histórico).
- **Ações**: buscar, filtrar status, alternar Lista/Kanban, criar, editar, ver detalhe, editar etapas de workflow.
- **Permissões**: não implementado.
- **API**: nenhuma — `lib/demandas-mock.ts`.
- **Loading**: inexistente. **Vazio**: `WorkspaceEmptyState` (lista/kanban sem resultado do filtro) e `EmptyStateIllustration` por coluna vazia do Kanban. **Erro**: inexistente.
- **Responsividade**: Kanban com colunas em scroll horizontal implícito; tabela com `overflow-x-auto`.

### `/projetos` — Projetos
- **Objetivo**: carteira de projetos/campanhas.
- **Componentes**: `ProjetosView` (`WorkspacePage`) → hero + `ProjetosStats`(4 `MetricCard`) + `ProjetosToolbar` + `ProjetosTable` + `NovoProjetoModal` + `ProjetoDetailsDrawer` (6 abas: Dados/Resumo/Modelo de Campanha/Equipe/Arquivos/Histórico).
- **Ações**: buscar, filtrar status, criar, editar, ver detalhe, gerenciar itens de modelo de campanha e membros de equipe.
- **API**: nenhuma — `lib/projetos-mock.ts`. **Vazio**: `WorkspaceEmptyState`. **Erro/Loading**: inexistente.
- **Sem Kanban** (só tabela).

### `/trafego` — Central de Tráfego
- **Objetivo**: monitoramento **somente leitura** de tempo operacional estimado, sessões ativas e carga por usuário/departamento.
- **Componentes**: `TrafegoView` (`WorkspacePage` + `PageHeader`) → `TrafegoHeader` + `TrafegoFilters` + `TrafegoResumoCards`(5 `MetricCard`) + `TempoOperacionalCard` + `TrafegoAgoraTable` + `TrafegoCargaUsuarios`/`TrafegoCargaDepartamentos` (`RankingCard`).
- **Ações**: filtrar por empresa/usuário/departamento/demanda/status/período. Botão "Atualizar" **desabilitado** (decorativo).
- **API**: nenhuma — `lib/trafego-mock.ts`. **Loading**: skeleton existe mas nunca ativa. **Vazio**: `EmptyStateIllustration`/`RankingCard` empty state.

### `/agenda` — Central de Contatos
- **Objetivo**: CRM simplificado (clientes, fornecedores, usuários, parceiros, freelancers, transportadoras, leads, outros).
- **Componentes**: `AgendaView` (`<div className="p-8">` avulso, **sem** `WorkspacePage`/`CadastroPage`) → `PageHeader` + `AgendaStats`(4 `Card`) + `AgendaToolbar` + `AgendaList` (lista de cards, não tabela).
- **Ações**: buscar, filtrar por tipo, ações de contato (telefone/email/WhatsApp/copiar) — todas mockadas via `console.log`; botão "Histórico" sempre desabilitado.
- **API**: nenhuma — `lib/agenda-mock.ts`. **Vazio**: `EmptyState` com emoji "📇".

### `/relatorios` — Relatórios (placeholder)
- **Objetivo declarado**: relatórios operacionais (futuro).
- **Estado atual**: `PageHeader` + `EmptyState` ("Relatórios ainda não disponíveis"). **Sem dados, sem componentes de negócio.**

### `/equipe` — Equipe (placeholder)
- **Estado atual**: `PageHeader` + `EmptyState` ("Módulo em construção"). Idêntico estruturalmente a `/relatorios`.

### `/fornecedores` — Fornecedores
- **Objetivo**: cadastro de fornecedores externos (gráficas, freelancers, hospedagem etc.).
- **Componentes**: `FornecedoresView` (`CadastroPage`) → `CadastroToolbar` + `CadastroIndicators` + `CadastroTable` + `NovoFornecedorModal` (2 passos: documento → 4 abas: Dados/Endereço/Contatos/Histórico) + `EntitySidePanel`.
- **Ações**: buscar, criar, visualizar, editar. Props `canCreate`/`canEdit` já preparadas para controle de permissão (não usadas hoje).
- **API**: nenhuma — `lib/fornecedor-mock.ts`. **Vazio**: `EmptyState` em Contatos/Histórico.
- Fica **fora** de `/configuracoes` (rota de primeiro nível) e **não aparece** no hub de Configurações.

### `/configuracoes` — Hub de Configurações
- **Objetivo**: navegação central para os módulos administrativos.
- **Componentes**: seções custom (`section` cards) — 3 grupos: **Cadastros** (Agências, Usuários, Clientes, Grupos de Clientes, Equipes), **Operação** (Workflows, SLA, Prioridades, Tipos de Tarefa), **Segurança** (Permissões, Auditoria — este último `disabled`, "Em breve").
- **Permissões**: conforme `CLAUDE.md`, deve ser visível apenas a SuperAdmin/Admin/Diretoria/Gestor/usuários com permissão explícita — **não implementado tecnicamente**.

### `/configuracoes/clientes` — Clientes
- **Objetivo**: cadastro fiscal completo de clientes (CNPJ/CPF, endereço, contatos, vínculo com equipe/responsáveis, histórico).
- **Componentes**: `ClientesView` (`CadastroPage`) → `CadastroToolbar`+`CadastroIndicators`+`CadastroTable` + `NovoClienteModal` (2 passos: documento com lookup mock de CNPJ → 5 abas: Dados/Endereço/Contatos/Equipe/Histórico) + `EntitySidePanel`.
- **Ações**: buscar, criar, visualizar (linha clicável), editar. Sem excluir/inativar direto.
- **API**: nenhuma — `lib/cliente-mock.ts`.

### `/configuracoes/equipes` — Equipes
- **Objetivo**: departamentos, líderes, membros e permissões internas de equipe.
- **Componentes**: `EquipesView` (`CadastroPage`) → toolbar+indicadores+tabela + `NovaEquipeModal` (2 passos → 4 abas: Dados/Membros/Permissões(Acesso)/Histórico).
- **Ações**: buscar, criar. **Sem** visualizar/editar/excluir pós-criação (único módulo, junto com Usuários, sem `EntitySidePanel`).
- **API**: nenhuma — `lib/equipe-mock.ts`.

### `/configuracoes/grupos-clientes` — Grupos de Clientes
- **Objetivo**: agrupar clientes/empresas relacionadas (matriz/filiais) para relatórios compartilhados.
- **Componentes**: `GruposClientesView` (`CadastroPage`) → toolbar+indicadores+tabela + `NovoGrupoClienteModal` (sem passo de documento → 2 abas: Dados (com busca+vínculo de clientes) e Contatos (placeholder "Integração iJob prevista para fase futura")) + `EntitySidePanel` (via `EntitySummaryPanel`/`EntityFieldRow`).
- **Ações**: buscar, criar, visualizar, editar, vincular/desvincular clientes.
- **API**: nenhuma — `lib/grupo-cliente-mock.ts`.

### `/configuracoes/usuarios` — Usuários
- **Objetivo**: colaboradores do sistema — dados pessoais, permissões granulares por módulo, múltiplos endereços, informações bancárias/documentos.
- **Componentes**: `UsuariosView` (`CadastroPage`) → toolbar+indicadores+tabela + `NovoUsuarioModal` (2 passos → 5 abas: Dados/Permissões/Endereço/Informações/Histórico).
- **Ações**: buscar, criar. **Sem** visualizar/editar/excluir pós-criação. Matriz de permissões mais granular do sistema (5 grupos × 4 ações).
- **API**: nenhuma — `lib/usuario-mock.ts`.

### `/configuracoes/agencias` — Agências
- **Objetivo**: cadastro de agências (multiempresa/franquia).
- **Estado atual**: **CRUD fake apenas leitura** — usa componentes `Cadastro*` corretamente, busca funcional, mas botão "Nova Agência" **sem handler**. Sem modal, sem tipo TS dedicado, sem mock externo (dados inline no `page.tsx`).

### `/configuracoes/workflows` — Workflows
- **Estado atual**: leitura apenas, sem `CadastroTable` (cards custom com "esteira" de etapas). Botão "Novo Workflow" sem handler. Sem tipo/mock dedicados.

### `/configuracoes/permissoes` — Permissões
- **Estado atual**: placeholder puro — `PageHeader` + `EmptyState` ("será implementado futuramente"). Nenhum dado, nenhuma tabela.

### `/configuracoes/prioridades`, `/configuracoes/sla`, `/configuracoes/tipos-tarefa`
- **Estado atual**: os três seguem um **padrão visual mais antigo** e divergente do restante — `PageHeader` + `Card` (3 cards `rounded-3xl p-6`) + tabela própria `rounded-3xl px-6 py-4` (não usa nenhum componente `Cadastro*`/`Workspace*`). Mock estático inline, sem busca, sem CRUD real, botão "Novo X" sem handler.

### `/conta/perfil`, `/conta/notificacoes`, `/conta/alterar-senha`
- **Objetivo**: dados pessoais, canais de notificação, troca de senha do usuário logado.
- **Componentes**: `<div className="p-8">` avulso + `PageHeader` + `Card`(s). Perfil: grid `xl:grid-cols-[280px_1fr]` (coluna de metadados + formulário). Notificações: lista de `Switch` (funcional em memória). Alterar Senha: validação client-side real.
- **API**: nenhuma — `lib/conta-mock.ts` (`CurrentUser`, único tipo sem `empresaId`/`agenciaId`).

### `/design-system` — Vitrine interna
- **Objetivo**: documentação viva de tokens/componentes para desenvolvimento (não é uma tela de produto).
- **Componentes**: `WorkspacePage` + `PageHeader` + todos os `DesignSystem*`.

---

## 10. Fluxo visual

Navegação primária sempre parte da **Sidebar** (persistente em todas as rotas via `Shell`):

```
Sidebar
 ├─ Principal
 │   ├─ Dashboard do Usuário (/)
 │   ├─ Tarefas (/tarefas)          → Lista ⇄ Kanban → clique no item → Drawer de detalhe (abas)
 │   ├─ Projetos (/projetos)        → Tabela          → clique no item → Drawer de detalhe (abas)
 │   └─ Agenda (/agenda)            → Lista de cards  → ação de contato (mock)
 ├─ Operação
 │   ├─ Tráfego (/trafego)          → somente leitura, filtros
 │   └─ Relatórios (/relatorios)    → placeholder
 ├─ Cadastros (submenu)
 │   ├─ Clientes                    → Tabela → linha → Painel lateral → [Editar] → Modal (5 abas)
 │   ├─ Grupos de Clientes          → Tabela → linha → Painel lateral → [Editar] → Modal (2 abas)
 │   ├─ Fornecedores (rota /fornecedores) → mesmo fluxo de Clientes (4 abas)
 │   ├─ Equipes                     → Tabela (sem detalhe) → [+ Nova Equipe] → Modal (4 abas)
 │   └─ Workflow                    → cards estáticos, sem CRUD
 └─ Administração
     └─ Configurações (/configuracoes) → Hub com 3 seções → cada card leva a um módulo acima
                                          + Usuários, Agências, SLA, Prioridades, Tipos de Tarefa, Permissões
```

Fluxo de criação típico (Clientes/Fornecedores — o mais completo):
```
Botão "Novo X" → Modal passo 1 (documento) → lookup mock (CNPJ) → passo 2 (Tabs: Dados/Endereço/Contatos/[Equipe]/Histórico)
   → preenche campos → "Salvar e fechar" ou "Salvar e continuar" → fecha modal → linha nova aparece na tabela
```

Fluxo de consulta (módulos com painel):
```
Clique na linha da tabela → EntitySidePanel abre da direita → mostra resumo (badges + seções)
   → botão [Editar] no cabeçalho do painel → reabre o Modal em modo edição, já na aba "Dados"
```

O `UserMenu` e `QuickCreateMenu` oferecem atalhos paralelos (barra lateral inferior/superior) que não substituem a navegação principal, apenas aceleram o acesso a rotas específicas.

---

## 11. Consistência

### 11.1 Componentes duplicados (mesmo problema, implementações diferentes)

| Problema | Implementações concorrentes |
|---|---|
| Shell de página com tabela | `CadastroPage`+`CadastroTable` (7 telas) vs `WorkspacePage`+`WorkspaceTable` (só vitrine) vs `WorkspacePage`+tabela ad hoc (`DemandasTable`/`ProjetosTable`) |
| Barra de filtro/busca | `CadastroToolbar` vs `WorkspaceToolbar` (só vitrine) vs `ToolbarCard`+markup próprio (Demandas/Projetos/Tráfego) vs `AgendaToolbar` (customizado, `border-zinc-200` em vez de `-100`) |
| Grid de indicadores/KPI | `CadastroIndicators` (compacto, `text-xl`) vs `WorkspaceStats` (só vitrine, `text-3xl`) vs `DashboardGrid`+`MetricCard` (Dashboard/Demandas/Projetos/Tráfego) vs grid manual de `Card` em `AgendaStats` |
| Cabeçalho de seção | `Section` vs `SectionHeader` vs `WorkspaceSection` (só vitrine) — três componentes para o mesmo conceito |
| Empty state | `EmptyState` vs `EmptyStateIllustration` vs `WorkspaceEmptyState` (wrapper de `EmptyState`) |
| Painel de detalhe | `EntitySidePanel` (Clientes/Fornecedores/Demandas/Projetos com markup manual) vs `EntitySidePanel`+`EntitySummaryPanel`+`EntityFieldRow` (só Grupos de Clientes) |
| Kanban | `demandas/DemandaKanban*` (produção, sem dnd) vs `kanban/KanbanBoard*` (órfão, com dnd-kit real) |

### 11.2 Botões diferentes fazendo a mesma função

- Botão "Novo X": componentizado (`Novo<Entidade>Button`) em Clientes/Equipes/Fornecedores/Usuários, mas **inline** (direto na prop `actions` do toolbar) em Grupos de Clientes, Agências, Workflows, Prioridades, SLA, Tipos de Tarefa.
- Botões "Nova Agência"/"Novo Workflow"/"Nova Prioridade"/"Novo SLA"/"Novo Tipo" existem visualmente mas **não têm handler** — parecem funcionais mas não fazem nada.
- Botão "Atualizar" em Tráfego é renderizado como ação mas está permanentemente `disabled`.

### 11.3 Inputs diferentes

- Campo de busca com ícone embutido (`CadastroToolbar`) vs campo de busca com `label` visível acima (`WorkspaceToolbar`, via `Input` genérico) vs campo de busca decorativo sem `onChange` (`HeaderSearch` variante `sidebar`).
- Checkbox nativo sem estilização (`MultiSelect`, `PermissoesSection`) vs `Switch` customizado (`NotificacoesView`, `AcessoSection`) para o mesmo conceito de "ligar/desligar uma opção".

### 11.4 Cards diferentes

- `Card` (sem borda) vs `MetricCard`/`CadastroIndicators`/`WorkspaceStats` (com borda) — mesma função de "container de dado", aparência diferente.
- Cards de "hero" duplicados via JSX manual (círculo decorativo `bg-blue-50` no canto) em `DashboardView` e `TrafegoHeader` — mesmo efeito visual, código copiado em vez de componentizado.

### 11.5 Ícones inconsistentes

- Uso geral é consistente (só `lucide-react`, `strokeWidth={2}`), mas `CadastroAvatar` (círculo com iniciais/ícone) não tem equivalente em `Workspace*`/Agenda (que usa `Image`/iniciais sem o wrapper padronizado).

### 11.6 Padding diferente

Três valores de padding de página raiz coexistindo sem justificativa funcional: `p-4 sm:p-5` (Cadastro), `p-6` (só Dashboard), `p-8` (Workspace e páginas soltas). Dentro de tabelas: `px-3 py-2` (Cadastro) vs `px-6 py-4` (Workspace) vs `px-4 py-3` (Demandas/Projetos).

### 11.7 Margens diferentes

Espaçamento vertical entre seções: `space-y-3` (Cadastro) vs `space-y-5`/`space-y-6` (Workspace/Dashboard) — sem token compartilhado.

### 11.8 Fontes diferentes

A fonte efetivamente renderizada é **Arial/Helvetica** (forçada em `globals.css`), apesar de Geist Sans/Mono estarem carregadas via `next/font`. Nenhum componente usa `font-sans`/`font-mono` para de fato aplicar Geist ao texto corrido — as variáveis CSS existem mas ficam sem efeito prático na tipografia do corpo.

### 11.9 Cores inconsistentes

- **Mesmo conceito de negócio, cores diferentes**: "aguardando cliente" é `amber` em Demandas mas `blue` em Tráfego (`TrafegoSessaoStatus`).
- **Prioridade "alta" usa cinza (slate)**, não vermelho/âmbar — contraintuitivo frente ao vocabulário semântico `StatusPill` (`red`/`amber` para estados críticos).
- `CadastroStatusBadge` reaproveitado para "Categoria" (Fornecedores) e "Perfil" (Usuários) — cai no fallback azul da heurística de status, misturando semântica de "estado" com "classificação".
- Paleta de chips de tipo da Agenda (8 cores, incluindo `violet`/`fuchsia`/`orange`) não tem relação com o vocabulário `StatusPill` usado no resto do sistema.
- `Card`/`AgendaStats`/`PerfilView` sem borda visível, quebrando o padrão universal `border-zinc-100`/`-200` de todo o resto do sistema.

### 11.10 Tabelas diferentes

Ver seção 7 — 3 implementações estruturalmente distintas (`CadastroTable`, `WorkspaceTable`, tabela ad hoc de Demandas/Projetos), cada uma com radius, padding e cor de cabeçalho próprios.

### 11.11 Modais diferentes

`Modal` genérico (sempre montado, controlado por `open`) é usado por Clientes/Equipes/Grupos de Clientes/Usuários/Demandas/Projetos, mas `NovoFornecedorModal` implementa um wrapper condicional próprio (`if (!open) return null` + componente interno remontado a cada abertura) — comportamento de reset de estado diferente dos demais.

---

## 12. Acessibilidade

### Contraste
Combinações de texto/fundo majoritariamente dentro de zinc-900/zinc-700 sobre branco/bege claro — boa legibilidade. Textos em `text-zinc-400`/`text-[10px]`–`text-[11px]` (labels de seção da sidebar, meta-informação) são pequenos e de baixo contraste — **candidatos a verificação formal de WCAG AA** (não medido numericamente neste documento, apenas sinalizado como área de atenção).

### Foco
- **Bom**: itens de navegação da Sidebar e botões de ícone usam `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2` de forma consistente.
- **Inconsistente**: `Input`/`Select`/`Textarea` só têm `focus:border-zinc-400` (mudança sutil de cor de borda, sem anel de foco visível) — acessibilidade de teclado mais fraca que a dos botões/nav.

### Atalhos de teclado
- `Escape` fecha `Modal`, `EntitySidePanel` e dropdowns (`UserMenu`, `QuickCreateMenu`).
- Linhas de tabela clicáveis (Clientes/Fornecedores/Grupos de Clientes) respondem a `Enter`/`Espaço` via `onKeyDown` manual (tabIndex explícito).
- Não existe atalho de busca global (`Cmd/Ctrl+K`) nem outros atalhos de produtividade.

### ARIA
- **`EntitySidePanel`** é o componente com ARIA mais completo: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`, foco automático no botão fechar ao abrir, restauração de foco ao fechar, bloqueio de scroll do `body`.
- **`Modal`** (genérico) **não tem** `role="dialog"` nem `aria-modal` — inconsistência relevante frente ao `EntitySidePanel`.
- `Switch` usa `role="switch"` + `aria-checked` corretamente.
- Navegação da Sidebar usa `aria-label="Navegação principal"`, e o submenu "Cadastros" usa `aria-expanded`/`aria-controls`.
- Botões só-ícone (Header, Sidebar, ações de contato da Agenda) majoritariamente têm `aria-label`+`title` — bom padrão, mas não 100% auditado em todos os arquivos.

### Labels
`Input`/`Select`/`Textarea` exigem `label` como prop obrigatória (bom — impede campos sem rótulo acessível). Checkboxes nativos em `MultiSelect` e `PermissoesSection` estão corretamente envolvidos por `<label>`.

### Responsividade (acessibilidade)
Ver seção 13 — ausência de navegação mobile dedicada para a Sidebar é também uma questão de usabilidade/acessibilidade em telas pequenas.

---

## 13. Responsividade

### Desktop (≥1280px, `xl`/`2xl`)
Experiência completa: sidebar expandida por padrão (ou colapsada conforme preferência salva), grids em 3–5 colunas, tabelas sem necessidade de scroll horizontal na maioria dos casos.

### Notebook (1024–1279px, `lg`)
Toolbars mudam de coluna para linha (`lg:flex-row`), `DashboardGrid columns="five"` ainda em 3 colunas (`lg:grid-cols-3`, só vira 5 em `2xl`). Sidebar comporta-se igual ao desktop.

### Tablet (768–1023px, `md`)
`HeaderSearch` variante `header` apareceria aqui (`md:flex`) mas não é usada na prática pelo `Header` real. Grids `DashboardGrid columns="auto/four"` passam de 1 para 2 colunas (`sm:grid-cols-2`), só chegando a 4 em `xl`. `EntitySidePanel` já assume largura máxima (`sm:max-w-lg`).

### Celular (<640px)
- **Sidebar**: não existe um comportamento "mobile" dedicado (sem drawer/hambúrguer) — a sidebar sempre ocupa espaço horizontal fixo (mínimo `w-14`/3.5rem mesmo colapsada), o que **reduz a área útil de conteúdo em telas muito pequenas** (problema identificado).
- **Tabelas**: `overflow-x-auto` + `minWidth` fixo (`760px` em `CadastroTable`) força scroll horizontal em qualquer tela menor que isso — **não há um layout de "cards empilhados" alternativo**, exceto na Agenda (que já usa cards por design, não como fallback responsivo).
- **Toolbars**: empilham em coluna (`flex-col` até `lg`), então funcionam bem no celular.
- **Modais**: `Modal` usa `max-w-lg` com `p-4` de margem externa — funciona, mas formulários com `Tabs` de 5 abas ficam com scroll vertical extenso em telas pequenas.
- **Drawer** (`EntitySidePanel`): assume `w-full` em mobile (bom — ocupa a tela toda), só limita largura a partir de `sm`.

### Problemas encontrados
1. Sidebar sem modo "oculto por padrão" em mobile — consome espaço horizontal mesmo colapsada.
2. Tabelas sem fallback de cartão em telas pequenas (exceto Agenda, que já nasce como lista de cards).
3. Formulários com múltiplas abas (5–6 abas em Clientes/Usuários/Projetos) não têm tratamento especial de UX para toque/mobile (abas com `overflow-x-auto`, mas sem indicador visual de mais conteúdo lateral).
4. Nenhuma página testa/documenta comportamento abaixo de 375px (mobile pequeno).

---

## 14. Melhorias sugeridas

*(Sem alterar nenhuma regra de negócio — apenas normalização visual/estrutural.)*

### Alta prioridade
1. **Unificar as 3 implementações de tabela** (`CadastroTable`, `WorkspaceTable`, tabela ad hoc de Demandas/Projetos) em um único componente parametrizável.
2. **Resolver a duplicação Cadastro\* vs Workspace\*** — decidir formalmente qual é o padrão oficial (dado o uso real, `Cadastro*` é o mais adotado em telas tabulares; `WorkspacePage` é o mais adotado como shell genérico) e aposentar os componentes `Workspace*` que só existem na vitrine (`WorkspaceSection`, `WorkspaceStats`, `WorkspaceTable`, `WorkspaceToolbar`).
3. **Migrar Prioridades/SLA/Tipos de Tarefa** para o padrão `Cadastro*` atual (hoje usam uma geração visual antiga: `Card`+`PageHeader`+tabela `rounded-3xl px-6 py-4`).
4. **Aplicar de fato a fonte Geist** ao `body` (hoje carregada mas sem efeito — `body` usa Arial/Helvetica).
5. **Adicionar `role="dialog"`/`aria-modal` ao `Modal`** genérico (hoje só `EntitySidePanel` tem ARIA completo).
6. **Padronizar a cor de "aguardando cliente"** entre Demandas (amber) e Tráfego (blue) — mesmo conceito de negócio, cores diferentes.
7. **Revisar a paleta de prioridade "alta"** (hoje cinza/slate) para usar uma cor de alerta (vermelho/âmbar), alinhada ao vocabulário semântico já existente em `StatusPill`.
8. **Decidir o destino do módulo `kanban/`** (código órfão com dnd-kit real, não usado por nenhuma rota) — remover ou integrar como motor real do Kanban de Demandas (hoje somente leitura).

### Média prioridade
9. **Criar um componente de Toast/notificação** — hoje nenhuma ação de "Salvar" dá feedback visual de sucesso.
10. **Adicionar estado de erro/validação visual** em `Input`/`Select`/`Textarea` (prop `error`, `aria-invalid`, borda vermelha) — hoje só Alterar Senha tem validação visível.
11. **Padronizar borda em `Card`** (`ui/Card.tsx`) para `border border-zinc-100`, alinhando com todos os outros containers "cartão" do sistema.
12. **Adicionar componente de paginação** — nenhuma tabela do projeto pagina resultados hoje.
13. **Padronizar o anel de foco** em campos de formulário (hoje só troca de cor de borda; botões/nav já usam `focus-visible:ring-2`).
14. **Substituir o reuso não-semântico de `CadastroStatusBadge`** (usado para "Categoria" em Fornecedores e "Perfil" em Usuários) por um badge neutro dedicado.
15. **Expandir o uso de `EntitySidePanel`** para Equipes e Usuários (hoje são os únicos módulos de cadastro sem visualização/edição pós-criação).
16. **Unificar `Section`/`SectionHeader`/`WorkspaceSection`** em um único componente de cabeçalho de seção.

### Baixa prioridade
17. Remover `clsx` do `package.json` (instalado, nunca usado) ou passar a adotá-lo para concatenar classes condicionais.
18. Remover `@dnd-kit/sortable` se não houver plano de uso, ou aplicá-lo ao Kanban real.
19. Padronizar nomenclatura de identificadores (`UsuarioDraft.id` deveria ser `usuarioId`, seguindo o padrão `<entidade>Id` das demais entidades).
20. Remover ou reintegrar os componentes órfãos `DashboardGreeting.tsx` e `StatCard.tsx` (não importados por `DashboardView`).
21. Unificar o padding de página raiz (`p-4 sm:p-5` / `p-6` / `p-8`) em um único token de espaçamento de página.
22. Ativar/testar de fato o `HeaderSearch` variante `header` (hoje só existe no código, o `Header` real nunca a renderiza) ou removê-la se não houver plano de busca global.
23. Componentizar o "hero card com círculo decorativo `bg-blue-50`" (hoje duplicado manualmente em `DashboardView` e `TrafegoHeader`).

---

## 15. Design System ideal

> Baseado exclusivamente em componentes já existentes no projeto — nenhum componente novo é inventado aqui. O objetivo é indicar, para cada categoria, **qual implementação existente deve se tornar o padrão único**, priorizando o componente já mais adotado/mais completo.

| Categoria | Estado atual | Padrão recomendado (já existe) |
|---|---|---|
| **Buttons** | `Button` (`primary`/`secondary`), sem variante destrutiva/tamanhos | Manter `ui/Button.tsx` como único componente de botão; estender com `variant="danger"` reaproveitando a cor `red-600` já usada em "Sair"/erro de senha |
| **Inputs** | `Input`/`Select`/`Textarea`/`MultiSelect`, consistentes entre si | Manter os quatro como família única; a busca do `CadastroToolbar` (com ícone embutido) deve virar a variante oficial de "campo de busca" em vez do padrão sem ícone do `WorkspaceToolbar` |
| **Cards** | `Card` (sem borda) vs demais containers (com borda) | Adotar o padrão **com borda** (`border border-zinc-100 bg-white shadow-sm`) como oficial — ajustar `Card` para incluir borda |
| **Tables** | 3 implementações | Adotar `CadastroTable` (+ constantes `cadastroTable*`) como padrão único — é o mais compacto, com header semântico (`uppercase`+`tracking`) e já usado por 7 telas reais |
| **Modals** | `Modal` (genérico) vs wrapper condicional de Fornecedores | Adotar `ui/Modal.tsx` (sempre montado, controlado por `open`) como padrão único; adicionar ARIA faltante |
| **Forms** | Fluxo em 2 passos (documento → abas) usado por Clientes/Fornecedores/Equipes/Usuários | Formalizar esse fluxo (`Modal` + `Tabs` + `FormSections` por entidade) como padrão oficial de "Novo/Editar Cadastro" |
| **Status** | `StatusPill` (vocabulário `neutral/blue/green/amber/red`) vs `CadastroStatusBadge` (heurística textual) | Adotar `StatusPill` como badge de status semântico oficial (já é usado em Dashboard/Demandas/Projetos/Tráfego); `CadastroStatusBadge` deve continuar apenas para os módulos de cadastro, mas **não deve mais ser reaproveitado para "Categoria"/"Perfil"** |
| **Badges** | `Badge` (cinza único) só usado na vitrine | Manter como badge neutro genérico (ex.: contadores, tags sem semântica de estado) |
| **Tags** | Chips de tipo da Agenda (8 cores próprias) | Extrair essa lógica de "chip colorido por categoria" para um componente `ui/CategoryTag` reutilizável, com paleta fixa documentada (em vez de reimplementar por módulo) |
| **Menus** | `UserMenu`, `QuickCreateMenu` — mesmo padrão de dropdown ancorado + fecha em clique fora/`Escape` | Já consistentes entre si; usar como referência para qualquer novo menu de contexto |
| **Dropdowns** | `Select` nativo, dropdowns custom de menu | Manter `Select` para formulários; dropdowns de ação (menus) seguem o padrão de `UserMenu`/`QuickCreateMenu` |
| **Kanban** | Kanban de produção somente-leitura (Demandas) + Kanban órfão com dnd-kit real | Migrar a implementação de drag-and-drop do módulo órfão (`src/components/kanban/`) para dentro de `DemandasKanban`, aposentando o módulo duplicado |
| **Timeline** | `HistoricoSection` repetido por módulo (mock estático na maioria, real em Fornecedores) | Formalizar `HistoricoSection` como componente genérico parametrizado por lista de eventos, conectado de fato ao draft (como já acontece em Fornecedores) |
| **Calendário** | Não existe | Fora de escopo desta fase — não inventar; aguardar módulo de Agenda evoluir |
| **Dashboard** | `DashboardGrid` + `MetricCard` já formam um padrão consistente de KPIs | Adotar como padrão oficial de "página com indicadores"; `CadastroIndicators`/`WorkspaceStats` deveriam convergir para essa mesma dupla `DashboardGrid`+`MetricCard` em vez de reimplementar grids próprios |
| **Gráficos** | Não existe (placeholder `EmptyStateIllustration`) | Fora de escopo desta fase — nenhuma biblioteca de gráficos instalada; aguardar fase correspondente do roadmap |

---

## 16. Inventário

### 16.1 Todos os componentes (por diretório)

**`src/components/ui/` (24 arquivos)**: `Badge`, `Button`, `Card`, `DashboardGrid`, `EmptyState`, `EmptyStateIllustration`, `EntityFieldRow`, `EntitySidePanel`, `EntitySummaryPanel`, `Input`, `MetricCard`, `Modal`, `MultiSelect`, `PageHeader`, `ProgressBar`, `RankingCard`, `Section`, `SectionHeader`, `Select`, `StatusPill`, `Switch`, `Tabs`, `Textarea`, `ToolbarCard`.

**`src/components/cadastros/` (6 + index)**: `CadastroAvatar`, `CadastroIndicators`, `CadastroPage`, `CadastroStatusBadge`, `CadastroTable`, `CadastroToolbar`, `index.ts` (barrel).

**`src/components/workspace/` (6)**: `WorkspaceEmptyState`, `WorkspacePage`, `WorkspaceSection`, `WorkspaceStats`, `WorkspaceTable`, `WorkspaceToolbar`.

**`src/components/design-system/` (7)**: `DesignSystemBadges`, `DesignSystemButtons`, `DesignSystemCards`, `DesignSystemColors`, `DesignSystemInputs`, `DesignSystemTypography`, `DesignSystemWorkspace`.

**`src/components/layout/` (9)**: `Breadcrumb`, `Header`, `HeaderActions`, `HeaderSearch`, `QuickCreateMenu`, `Shell`, `Sidebar`, `SidebarContext`, `UserMenu`.

**`src/components/dashboard/` (8)**: `DashboardActivities`, `DashboardAgenda`, `DashboardChart`, `DashboardGreeting` (órfão), `DashboardShortcuts`, `DashboardStats`, `DashboardView`, `StatCard` (órfão).

**`src/components/demandas/` (9)**: `DemandaDetailsDrawer`, `DemandaFormSections`, `DemandaKanbanCard`, `DemandaKanbanColumn`, `DemandasKanban`, `DemandasStats`, `DemandasTable`, `DemandasToolbar`, `DemandasView`, `NovaDemandaModal`.

**`src/components/kanban/` (4 — órfão, não roteado)**: `KanbanBoard`, `KanbanCard`, `KanbanColumn`, `TaskDetailModal`.

**`src/components/projetos/` (6)**: `NovoProjetoModal`, `ProjetoDetailsDrawer`, `ProjetoFormSections`, `ProjetosStats`, `ProjetosTable`, `ProjetosToolbar`, `ProjetosView`.

**`src/components/trafego/` (7)**: `TempoOperacionalCard`, `TrafegoAgoraTable`, `TrafegoCargaDepartamentos`, `TrafegoCargaUsuarios`, `TrafegoFilters`, `TrafegoHeader`, `TrafegoResumoCards`, `TrafegoView`.

**`src/components/agenda/` (4)**: `AgendaList`, `AgendaStats`, `AgendaToolbar`, `AgendaView`.

**`src/components/conta/` (3)**: `AlterarSenhaView`, `NotificacoesView`, `PerfilView`.

**`src/components/clientes/` (4)**: `ClienteFormSections`, `ClientesView`, `NovoClienteButton`, `NovoClienteModal`.

**`src/components/equipes/` (4)**: `EquipeFormSections`, `EquipesView`, `NovaEquipeButton`, `NovaEquipeModal`.

**`src/components/fornecedores/` (4)**: `FornecedoresView`, `FornecedorFormSections`, `NovoFornecedorButton`, `NovoFornecedorModal`.

**`src/components/grupos-clientes/` (3 + index)**: `GrupoClienteFormSections`, `GruposClientesView`, `NovoGrupoClienteModal`, `index.ts`.

**`src/components/usuarios/` (4)**: `NovoUsuarioButton`, `NovoUsuarioModal`, `UsuarioFormSections`, `UsuariosView`.

### 16.2 Todas as páginas (rotas)

`/`, `/tarefas`, `/projetos`, `/trafego`, `/agenda`, `/relatorios`, `/equipe`, `/fornecedores`, `/design-system`, `/configuracoes`, `/configuracoes/clientes`, `/configuracoes/equipes`, `/configuracoes/grupos-clientes`, `/configuracoes/usuarios`, `/configuracoes/agencias`, `/configuracoes/workflows`, `/configuracoes/permissoes`, `/configuracoes/prioridades`, `/configuracoes/sla`, `/configuracoes/tipos-tarefa`, `/conta/perfil`, `/conta/notificacoes`, `/conta/alterar-senha`.

### 16.3 Layouts

Apenas um: `src/app/layout.tsx` (`RootLayout`), que monta `Shell`. Não há layouts aninhados (`layout.tsx` por segmento) em nenhuma subrota.

### 16.4 Hooks

Apenas um hook customizado: `useSidebar()` (exportado de `src/components/layout/SidebarContext.tsx`). Não há diretório `src/hooks/`.

### 16.5 Providers / Contextos

Apenas um: `SidebarProvider` (`src/components/layout/SidebarContext.tsx`), envolvendo toda a aplicação dentro de `Shell`.

### 16.6 Estilos e arquivos CSS

- `src/app/globals.css` — único arquivo CSS do projeto (2 variáveis de cor + `@theme inline` do Tailwind v4 + reset mínimo `box-sizing`/`body`).
- **Não existe `tailwind.config.js/ts`** — Tailwind v4 configurado 100% via CSS (`@import "tailwindcss"` + diretiva `@theme inline` dentro do próprio `globals.css`).
- `postcss.config.mjs` — plugin `@tailwindcss/postcss`.
- Nenhum CSS Module, nenhum styled-components, nenhum arquivo `.scss`/`.sass`.

### 16.7 Arquivos relacionados a UI (fontes/ícones/assets)

- Fontes: `Geist`, `Geist_Mono` via `next/font/google` (declaradas em `src/app/layout.tsx`).
- Ícones: pacote `lucide-react` (sem arquivos de ícone customizados/SVG próprios para UI).
- `public/`: apenas os SVGs padrão do boilerplate Next.js (`file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg`) — **nenhum asset de marca/logo customizado**; o "logo" do TaskFloww na Sidebar é só a letra "T" em um `<div>` estilizado, sem imagem.

### 16.8 Tipos (`src/types/`)

`agenda.ts`, `cliente.ts`, `demanda.ts`, `equipe.ts`, `fornecedor.ts`, `grupo-cliente.ts`, `projeto.ts`, `trafego.ts`, `usuario.ts`. (Não existe `types/conta.ts` — o tipo `CurrentUser` é declarado direto em `lib/conta-mock.ts`; também não existem tipos dedicados para Agências/Workflows/Permissões/Prioridades/SLA/Tipos de Tarefa — todos com dados inline no `page.tsx`.)

### 16.9 Mocks (`src/lib/`)

`agenda-mock.ts`, `cliente-mock.ts`, `conta-mock.ts`, `demandas-mock.ts`, `equipe-mock.ts`, `fornecedor-mock.ts`, `grupo-cliente-mock.ts`, `projetos-mock.ts`, `trafego-mock.ts`, `usuario-mock.ts`.

`access-control.ts` (novo) — hierarquia de perfis `PerfilAcesso` e `hasAdministrativeAccess()`; regras completas em `entity-component-api.md`, seção 18 ("Guia Administrativa"), não duplicadas aqui.

---

## 17. Mapa visual

Para cada página, o caminho completo Página → Layout → Componentes → Subcomponentes → Hooks → API → Banco. **Nesta fase do projeto, API e Banco são sempre "nenhum" (dados 100% mockados em memória)** — mapeado explicitamente para deixar claro o que ainda falta implementar.

```
/  (Dashboard)
 └─ Shell (Sidebar + Header)
     └─ DashboardView
         ├─ DashboardStats → DashboardGrid → MetricCard ×4
         ├─ DashboardAgenda → SectionHeader
         ├─ DashboardActivities → SectionHeader
         ├─ DashboardChart → SectionHeader + EmptyStateIllustration + StatusPill
         └─ DashboardShortcuts → Card + Button
     Hooks: useSidebar (via Shell)
     API: nenhuma (dados hardcoded no componente)
     Banco: nenhum

/tarefas  (Demandas)
 └─ Shell
     └─ DemandasView → WorkspacePage
         ├─ DemandasStats → DashboardGrid → MetricCard ×5
         ├─ DemandasToolbar → ToolbarCard + Select + Button
         ├─ DemandasKanban → DemandaKanbanColumn ×6 → DemandaKanbanCard | EmptyStateIllustration
         ├─ DemandasTable (tabela ad hoc)
         ├─ WorkspaceEmptyState (fallback vazio)
         ├─ NovaDemandaModal → Modal + Tabs + DemandaFormSections (5 sections)
         └─ DemandaDetailsDrawer → EntitySidePanel + Tabs
     Hooks: useSidebar, useState local (filtro, viewMode, drawer)
     API: nenhuma — lib/demandas-mock.ts (resolve nomes por ID)
     Banco: nenhum (tabela `demandas` planejada, não criada)

/projetos
 └─ Shell
     └─ ProjetosView → WorkspacePage
         ├─ ProjetosStats → DashboardGrid → MetricCard ×4
         ├─ ProjetosToolbar → ToolbarCard + Select + Button
         ├─ ProjetosTable (tabela ad hoc) | WorkspaceEmptyState
         ├─ NovoProjetoModal → Modal + Tabs + ProjetoFormSections (6 sections)
         └─ ProjetoDetailsDrawer → EntitySidePanel + Tabs
     Hooks: useSidebar, useState local
     API: nenhuma — lib/projetos-mock.ts
     Banco: nenhum

/trafego
 └─ Shell
     └─ TrafegoView → WorkspacePage + PageHeader
         ├─ TrafegoHeader (hero + StatusPill + botão desabilitado)
         ├─ TrafegoFilters → ToolbarCard + Select + MultiSelect + Input
         ├─ TrafegoResumoCards → DashboardGrid → MetricCard ×5
         ├─ TempoOperacionalCard → MetricCard ×2
         ├─ TrafegoAgoraTable → EmptyStateIllustration (vazio)
         └─ TrafegoCargaUsuarios / TrafegoCargaDepartamentos → RankingCard → ProgressBar
     Hooks: useSidebar, useState local (filtros, loading nunca ativado)
     API: nenhuma — lib/trafego-mock.ts
     Banco: nenhum

/agenda
 └─ Shell
     └─ AgendaView (div solto + PageHeader)
         ├─ AgendaStats → Card ×4
         ├─ AgendaToolbar → Input + Button (toggle de tipo)
         └─ AgendaList → Card ×N | EmptyState
     Hooks: useSidebar, useState local
     API: nenhuma — lib/agenda-mock.ts
     Banco: nenhum

/relatorios
 └─ Shell → div solto → PageHeader + EmptyState
     Hooks: useSidebar apenas
     API: nenhuma · Banco: nenhum

/equipe
 └─ Shell → div solto → PageHeader + EmptyState
     Hooks: useSidebar apenas
     API: nenhuma · Banco: nenhum

/fornecedores
 └─ Shell
     └─ FornecedoresView → CadastroPage
         ├─ CadastroToolbar
         ├─ CadastroIndicators
         ├─ CadastroTable → CadastroAvatar + CadastroStatusBadge
         ├─ NovoFornecedorModal → Modal (condicional) + Tabs + FornecedorFormSections (4 sections)
         └─ EntitySidePanel
     Hooks: useSidebar, useState local
     API: nenhuma — lib/fornecedor-mock.ts
     Banco: nenhum

/configuracoes  (Hub)
 └─ Shell → sections custom (cards de navegação)
     Hooks: useSidebar apenas
     API: nenhuma · Banco: nenhum

/configuracoes/clientes
 └─ Shell
     └─ ClientesView → CadastroPage
         ├─ CadastroToolbar / CadastroIndicators / CadastroTable
         ├─ NovoClienteModal → Modal + Tabs + ClienteFormSections (5 sections, com lookup mock CNPJ)
         └─ EntitySidePanel
     API: nenhuma — lib/cliente-mock.ts · Banco: nenhum

/configuracoes/equipes
 └─ Shell
     └─ EquipesView → CadastroPage
         ├─ CadastroToolbar / CadastroIndicators / CadastroTable
         └─ NovaEquipeModal → Modal + Tabs + EquipeFormSections (4 sections)
     API: nenhuma — lib/equipe-mock.ts · Banco: nenhum

/configuracoes/grupos-clientes
 └─ Shell
     └─ GruposClientesView → CadastroPage
         ├─ CadastroToolbar / CadastroIndicators / CadastroTable
         ├─ NovoGrupoClienteModal → Modal + Tabs + GrupoClienteFormSections (2 sections)
         └─ EntitySidePanel → EntitySummaryPanel → EntityFieldRow
     API: nenhuma — lib/grupo-cliente-mock.ts · Banco: nenhum

/configuracoes/usuarios
 └─ Shell
     └─ UsuariosView → CadastroPage
         ├─ CadastroToolbar / CadastroIndicators / CadastroTable
         └─ NovoUsuarioModal → Modal + Tabs + UsuarioFormSections (5 sections)
     API: nenhuma — lib/usuario-mock.ts · Banco: nenhum

/configuracoes/agencias
 └─ Shell → CadastroPage (toolbar/indicators/table, sem modal funcional)
     API: nenhuma (dados inline) · Banco: nenhum

/configuracoes/workflows
 └─ Shell → CadastroPage (toolbar/indicators, cards custom em vez de table)
     API: nenhuma (dados inline) · Banco: nenhum

/configuracoes/permissoes
 └─ Shell → PageHeader + EmptyState (placeholder puro)
     API: nenhuma · Banco: nenhum

/configuracoes/prioridades | /sla | /tipos-tarefa
 └─ Shell → PageHeader + Card ×3 + tabela custom (padrão visual antigo)
     API: nenhuma (dados inline) · Banco: nenhum

/conta/perfil | /notificacoes | /alterar-senha
 └─ Shell → div solto → PageHeader + Card(s)
     API: nenhuma — lib/conta-mock.ts · Banco: nenhum

/design-system
 └─ Shell → WorkspacePage → PageHeader + DesignSystemTypography/Colors/Buttons/Inputs/Badges/Cards/Workspace
     API: nenhuma · Banco: nenhum
```

---

*Fim do documento. Gerado inteiramente por leitura estática do código-fonte em `/docker/taskfloww/frontend/src`, sem execução de build, lint ou testes, e sem qualquer alteração aos arquivos do projeto.*
