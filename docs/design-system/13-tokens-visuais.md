# 13 — Tokens Visuais Oficiais (Identidade BOX)

> Documento de formalização. Não altera nenhum componente — registra o
> vocabulário visual já em uso (ou a ser generalizado) pelas fases de
> refinamento visual em curso. Consolida decisões já iniciadas de forma
> não documentada em `globals.css`, `ui/Button.tsx` e `layout/Sidebar.tsx`.

## 1. Cor

A identidade oficial do TaskFloww V2 já está definida em
`src/app/globals.css` (`@theme inline`):

| Token | Valor | Papel |
|---|---|---|
| `--color-primary` | `#fc6c00` | Laranja de marca — destaque, nunca decoração |
| `--color-primary-hover` | `#e86100` | Estado hover/active da cor de marca |
| `--color-primary-soft` | `#fff3e8` | Fundo suave para item ativo/selecionado |
| `--color-surface` | `#f7f6f3` | Superfície alternativa |
| `--color-border` | `#e5e3df` | Borda alternativa |
| `--color-text` | `#171717` | Texto alternativo |
| `--color-text-muted` | `#6b6b73` | Texto secundário alternativo |

Regra de uso do laranja: **no máximo um destaque de marca por tela/bloco**
(o botão de ação primária, ou um único indicador de item ativo). Nunca em
badge de status — status usa exclusivamente o vocabulário semântico abaixo.

### Vocabulário semântico de estado (`StatusPill`)

| Tom | Classes | Papel |
|---|---|---|
| `neutral` | `bg-zinc-100 text-zinc-700 ring-zinc-200` | Neutro/indefinido |
| `blue` | `bg-blue-50 text-blue-700 ring-blue-100` | Informação |
| `green` | `bg-emerald-50 text-emerald-700 ring-emerald-100` | Sucesso/ativo |
| `amber` | `bg-amber-50 text-amber-700 ring-amber-100` | Aviso/pendente |
| `red` | `bg-red-50 text-red-700 ring-red-100` | Erro/crítico |

Este vocabulário é a única fonte de cor de estado do sistema. Laranja de
marca e cor de estado nunca se sobrepõem.

## 2. Radius

| Camada | Classe | Aplicação |
|---|---|---|
| Controles interativos (botão, input, select, tab, dropdown, pill) | `rounded-2xl` (ou `rounded-full` para pill/avatar) | Já consistente hoje em `ui/Button.tsx` |
| Contêineres (card, painel, tabela, toolbar, modal, drawer, seção) | `rounded-3xl` | Padrão dominante em `entity/`, `workspace/`, `Modal`, `Card` — generalizado nesta fase para `cadastros/*` e `DashboardWidget` |

## 3. Sombra (elevação)

| Elevação | Classe | Quando |
|---|---|---|
| Repouso | `shadow-sm` | Cards, tabelas, toolbars na página |
| Hover de card clicável | `shadow-md` | Cards interativos (Kanban, Métricas) |
| Painel flutuante | `shadow-xl` | Dropdown, menu, peek |
| Overlay de edição | `shadow-2xl` | Drawer/Modal em modo de edição |

## 4. Tipografia (Roboto)

Fonte única do sistema: **Roboto** (`next/font/google`, variável
`--font-roboto`, mapeada em `--font-sans`). `Geist Mono` permanece restrito
a valores monoespaçados pontuais (ex.: hex de cor, contadores de tempo).

| Nome | Classe Tailwind | Uso típico |
|---|---|---|
| Display | `text-3xl font-bold` | Título de página solta |
| H1 | `text-2xl font-bold tracking-tight` | Valor numérico grande (KPI) |
| H2 | `text-xl font-semibold` | Título de seção maior |
| H3 | `text-lg font-semibold` | Título de página de cadastro, título de Drawer |
| Título de Card | `text-sm font-semibold` | Título de card/widget |
| Subtítulo | `text-sm text-zinc-500` | Descrição abaixo de título |
| Texto | `text-sm` | Corpo padrão |
| Legenda/Eyebrow | `text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400` | Rótulo acima de valor |
| Badge/Status | `text-[11px] font-medium` | Conteúdo de badge/pill |
| Tabela (cabeçalho) | `text-[11px] uppercase tracking-[0.04em] text-zinc-500` | Cabeçalho de coluna |
| Metadado mínimo | `text-[10px]` | Último recurso (ex.: e-mail truncado na Sidebar) |

Nenhum peso além de `font-medium`/`font-semibold`/`font-bold` é usado —
sem `font-light`/`font-thin`, para priorizar leitura.

## 5. Origem

Este documento formaliza decisões já presentes no código (não documentadas
anteriormente) e generaliza seu uso pelas fases descritas no plano de
refinamento visual em curso. Não substitui `taskfloww-design-system.md`
(inventário histórico) nem `12-plano-de-migracao.md`/`entity-architecture-plan.md`
(arquitetura estrutural) — é o nível de tokens de apresentação.
