# Design tokens — Taskfloww

Este documento **não define um visual novo**. Ele registra, como referência, os padrões que já estão em uso real no código de `src/components/ui/` e nas telas do app, levantados por auditoria (leitura completa dos 20 arquivos de `components/ui/` + amostragem de telas). Serve como fonte única de verdade para próximas telas e componentes — em caso de dúvida sobre "qual classe usar aqui", a resposta deve vir daqui, não de uma escolha nova.

Nenhum destes valores foi inventado nesta auditoria — todos já existem no código, em uso consistente na maioria dos casos, com poucas divergências pontuais anotadas onde relevante.

## Raio de borda

Quatro níveis, cada um com um papel fixo:

| Nível | Uso |
|---|---|
| `rounded-full` | Pills (botões, badges), avatares, toggles (Switch), chips de seleção |
| `rounded-xl` | Campos de formulário (Input/Select/Textarea/MultiSelect) e containers de popover/dropdown |
| `rounded-2xl` | Cards e modais (a unidade "container de página") |
| `rounded-lg` | Linhas/botões pequenos aninhados dentro de outro container (opção de dropdown, aba ativa, botão de toolbar) |

Não existe uso de `rounded` sem sufixo — todo raio especifica um tamanho.

## Espaçamento

A escala é a padrão do Tailwind, usada diretamente (sem extensão customizada). Valores mais frequentes, do menor ao maior:

| Valor | Uso típico |
|---|---|
| `gap-1` / `gap-1.5` | Espaçamento entre ícone e texto, itens de toolbar |
| `p-1` / `p-1.5` | Padding de containers compactos (Tabs, dropdowns) |
| `px-2 py-0.5` | Badge |
| `px-3.5 py-2` | Botão (Button) — único no sistema, não compartilhado com outro componente |
| `px-3 py-2.5` | Campo de formulário padrão (Input/Select/Textarea/campo de busca) |
| `gap-2` / `gap-2.5` | Linhas de conteúdo (cabeçalhos, opções de lista) |
| `gap-3` | Empilhamento maior (listas, cabeçalhos de modal) |
| `p-4` | Padding de card (MetricCard, RankingCard, ChartCard) |
| `p-6` | Padding de modal |
| `p-10` | Padding de EmptyState — o maior valor único do sistema |

Alguns valores arbitrários pontuais aparecem fora da escala (`min-h-[42px]` no MemberSelector, `min-h-[180px]` no RichTextEditor, `translate-x-[19px]`/`translate-x-[3px]` no thumb do Switch) — são ajustes finos intencionais, não um padrão a generalizar.

## Tipografia

Escala real usada: `text-xs` (12px) / `text-sm` (14px, o tamanho-base de quase todo o app) / `text-base` / `text-lg` / `text-xl`.

Existe um passo **de fato, não-oficial no Tailwind**: `text-[11px]`, sempre combinado com `font-semibold uppercase tracking-wide text-zinc-400` — é a legenda de campo de formulário (Input, Select, Textarea, MultiSelect, MemberSelector) e o texto de Badge. Repetido de forma idêntica em 6+ componentes — é, na prática, um token (`caption`/`text-2xs`), só não está nomeado.

`text-[10px]` aparece uma única vez (badge de overflow do AvatarStack, "+N") — não generalizar, é um caso isolado de texto muito pequeno dentro de um círculo pequeno.

Pesos: `font-medium` (labels, texto de corpo com ênfase leve), `font-semibold` (botões, badges, títulos de card, a legenda uppercase), `font-bold` (só a inicial do Avatar). `font-mono` aparece só em valores numéricos tabulares (ex. RankingCard).

## Cores semânticas (tom)

Cinco famílias Tailwind reais, usadas para transmitir estado/tom em Badge, MetricCard e ProgressBar:

| Tom (`BadgeTone`) | Família Tailwind real | Papel |
|---|---|---|
| `neutral` | `zinc` | Neutro/padrão |
| `blue` | **`indigo`** (não `blue-*`) | Marca/informação — ver nota abaixo |
| `green` | `emerald` | Sucesso/positivo |
| `amber` | `amber` | Alerta |
| `red` | `red` | Erro/perigo |

**Nota importante:** o nome do tom `"blue"` no código é enganoso — a cor renderizada é sempre `indigo`, nunca a família `blue` real do Tailwind. Isso não é um problema visual (o resultado é consistente), mas é uma armadilha de nomenclatura para quem for ler o código: não existe hoje nenhum uso de `blue-*` do Tailwind na biblioteca de UI.

`indigo` + `violet` juntos (`from-indigo-500 to-violet-600`) formam o gradiente de marca, usado no botão primário e no estado ativo do MultiSelect — `violet` nunca aparece sozinho.

`zinc` é a única família neutra usada para texto/borda/fundo em todo o sistema.

### Paletas paralelas (fora do vocabulário de tom acima)

Existem **dois outros sistemas de cor**, sem relação de nomenclatura com o de tom acima:

1. **Cor de identificação de pessoa/equipe** (`lib/cores.ts`, consumida por Avatar/AvatarStack/MemberSelector): 10 cores em hex bruto via `style` inline — `zinc, blue (#3b82f6), green (#22c55e), orange, red, purple, pink, cyan, yellow, brown`. Note que aqui "blue" e "green" são as cores Tailwind reais (diferente do tom `BadgeTone`, onde "blue" = indigo e "green" = emerald) — o mesmo nome em português significa cores diferentes dependendo de qual sistema está em uso.
2. **Grifo/cor de fonte do editor de texto rico** (`RichTextEditor.tsx`): 6 cores em hex bruto, próprias do componente (`#fef08a`, `#bbf7d0`, `#fecdd3` para grifo; `#1d4ed8`, `#b91c1c`, `#15803d` para fonte).

Estes dois sistemas existem porque servem propósitos diferentes (tag de identificação visual vs. tom semântico de estado) e não há necessidade de unificá-los — mas um desenvolvedor não deve presumir que "green" tem o mesmo valor hexadecimal nos três lugares.

## Sombras

Três níveis, mapeados por camada de elevação:

| Sombra | Uso |
|---|---|
| `shadow-sm` | Cards, botão secundário, aba ativa, estado de foco de campo (`focus:shadow-sm`), sombra colorida do botão primário (`shadow-indigo-500/25`) |
| `shadow-lg` | Painéis flutuantes (dropdown do Combobox/MemberSelector) |
| `shadow-2xl` | Modais |

Uma exceção pontual: o thumb do Switch usa uma sombra em valor arbitrário (`shadow-[0_1px_2px_rgba(0,0,0,0.25)]`) — não é um quarto nível, é um ajuste isolado do próprio thumb.

## Animações

Dois mecanismos coexistem, cada um com seu papel:

- **Transições CSS** (`transition`, `transition-colors`, `transition-all`) para micro-interação: hover, foco, press. A maioria usa a duração padrão implícita do Tailwind; só o Switch declara `duration-200` explicitamente.
- **Framer Motion** para entrada/saída estrutural e animações de valor (barra de progresso, cards entrando em lista, troca de aba). Durações usadas: `0.2s` (modais), `0.35s` (MetricCard), `0.4s` (RankingCard), `0.5s` (ProgressBar) — cada componente escolhe seu próprio valor; não há uma constante de duração compartilhada. A troca de aba usa uma mola (`spring`, `stiffness: 400, damping: 32`) em vez de duração fixa.
- Atrasos escalonados em listas usam `index * 0.05` (MetricCard) ou `index * 0.04` (RankingCard) — dois valores próximos, não idênticos.

## Como usar este documento

Ao criar um componente novo ou revisar um existente, usar os valores desta tabela em vez de escolher um novo. Se um caso genuinamente não se encaixar em nenhum papel acima, é um sinal para discutir se o token precisa crescer — não para inventar um valor isolado silenciosamente.
