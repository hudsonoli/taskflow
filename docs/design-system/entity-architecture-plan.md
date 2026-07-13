# TaskFloww V2 — Entity Architecture Plan

> **Especificação técnica. Nenhum código foi escrito, nenhum arquivo além deste foi criado ou alterado.**
> Este documento projeta a infraestrutura reutilizável do novo padrão de UX definido em `entity-ux-pattern.md`, com base no inventário de `taskfloww-design-system.md` e na disciplina de migração incremental de `12-plano-de-migracao.md`.
> **Não migra Clientes.** Não migra nenhuma página. É a planta baixa dos componentes que tornarão a migração possível depois, com aprovação própria.

---

## Sumário

1. [Diagnóstico da arquitetura atual](#1-diagnóstico-da-arquitetura-atual)
2. [Problemas encontrados](#2-problemas-encontrados)
3. [Objetivos da nova arquitetura](#3-objetivos-da-nova-arquitetura)
4. [Componentes oficiais](#4-componentes-oficiais)
5. [Fluxos](#5-fluxos)
6. [Estados](#6-estados)
7. [Estrutura de pastas](#7-estrutura-de-pastas)
8. [Estratégia de migração](#8-estratégia-de-migração)
9. [Compatibilidade](#9-compatibilidade)
10. [Riscos](#10-riscos)
11. [Roadmap](#11-roadmap)
12. [Ordem exata de implementação](#12-ordem-exata-de-implementação)
13. [Critérios de aceite](#13-critérios-de-aceite)
14. [Dívidas técnicas](#14-dívidas-técnicas)
15. [Recomendações futuras](#15-recomendações-futuras)

---

## 1. Diagnóstico da arquitetura atual

Relendo `EntitySidePanel.tsx`, `Modal.tsx`, `PageShell.tsx`, `ui/PageHeader.tsx`, `ClientesView.tsx`, `NovoClienteModal.tsx`, `ClienteFormSections.tsx`, `cadastros/CadastroTable.tsx`, `cadastros/CadastroToolbar.tsx` e `cadastros/CadastroIndicators.tsx` no estado atual (pós Fase 1/1.1), a arquitetura de detalhe/edição de entidade hoje é composta por **duas famílias de overlay independentes**, sem nenhum contrato em comum:

| | `EntitySidePanel` | `Modal` |
|---|---|---|
| Ancoragem | Direita, `fixed inset-y-0 right-0` | Centro, `fixed inset-0 flex items-center justify-center` |
| Largura | `sm:max-w-lg lg:max-w-xl` (512–576px) | `maxWidthClassName` por consumidor (hoje `740px` em Clientes) |
| Overlay | `bg-zinc-900/40` (ou `overlayClassName` opt-in) | idem |
| Foco/ARIA | `role="dialog"`, `aria-modal`, foco automático, restauração de foco | nenhum `role`/`aria-modal` |
| Navegação interna | Nenhuma (conteúdo livre) | `Tabs` horizontais |
| Consumidores | 5 (Clientes, Fornecedores, Grupos de Clientes, Projetos, Demandas) | 8 (os 5 acima + Equipes, Usuários, Kanban) |

Essas duas famílias **coexistem na mesma tela**: hoje, ao clicar em "Editar" dentro do `EntitySidePanel` de Clientes, o `Modal` abre **por cima** do painel já aberto — dois overlays simultâneos, cada um com sua própria lógica de fechamento, foco e escape. Esse é o diagnóstico já registrado em `entity-ux-pattern.md` seção 1, e é a causa raiz de todos os sintomas visuais corrigidos nas fases anteriores (dupla rolagem, "popup sobre popup", grade desproporcional).

Além disso, o formulário interno usa `Tabs` horizontais + grade fixa `md:grid-cols-2`, ambos já identificados como estruturalmente ruins para o recurso realmente escasso (altura) dentro de um overlay de largura limitada.

## 2. Problemas encontrados

1. **Dois paradigmas de overlay sem contrato comum** — `EntitySidePanel` e `Modal` não compartilham nenhuma interface, nenhum hook de foco, nenhuma convenção de largura. Cada novo consumidor decide do zero como compor os dois.
2. **Nenhum estado único de "o que está aberto"** — cada `*View.tsx` mantém dois `useState` paralelos (`selectedClienteId` para o painel, `editingClienteId` para o modal), que **podem** ficar ambos preenchidos ao mesmo tempo (o código de `ClientesView` hoje zera um ao abrir o outro manualmente — `openEdit` faz `setSelectedClienteId(null)` antes de `setEditingClienteId`, mas isso é uma convenção seguida por disciplina, não impedida pela estrutura de dados).
3. **Navegação entre abas horizontais degrada com o número de seções** — 5 abas já ocupam toda a largura útil em telas menores e competem por espaço vertical com o conteúdo.
4. **Grade fixa de 2 colunas não reflete o conteúdo real dos campos** — já mensurado em fases anteriores: força linhas extras e, por consequência, rolagem desnecessária.
5. **Nenhuma convenção de navegação entre entidades relacionadas** — não existe hoje nenhum caso de "abrir Projeto a partir de Cliente", mas se fosse implementado ingenuamente sobre a arquitetura atual, o caminho óbvio (abrir outro `EntitySidePanel`/`Modal` por cima) replicaria o mesmo bug do item 1, em cascata.
6. **Cores e larguras espalhadas por consumidor** — `overlayClassName`, `maxWidthClassName`, `maxHeightClassName` viraram props "escape hatch" introduzidas nas últimas fases para não quebrar os outros consumidores; funcionam, mas cada nova tela precisaria redescobrir os mesmos valores (`bg-black/25 backdrop-blur-[2px]`, `max-w-[660px]`, `max-h-[80vh]`...) em vez de herdar um padrão já oficial.
7. **Nenhum ponto de extensão para relações/tags/histórico rico** — o `EntitySidePanel` de hoje recebe `children` livre; cada `*View.tsx` reimplementa manualmente `<dl>`/`<section>` para mostrar os mesmos tipos de informação (nome, código, status, histórico), sem nenhum componente compartilhado (diagnóstico já feito em `12-plano-de-migracao.md`, seção 1, para `EntitySummaryPanel`/`EntityFieldRow`, hoje usados só por Grupos de Clientes).

## 3. Objetivos da nova arquitetura

1. **Uma única família de overlay para CRUD de entidade** — substituindo `EntitySidePanel` (nesse uso) e `Modal` (nesse uso) por `EntityDrawer`, com dois modos (`peek`/`edit`) da mesma instância, nunca dois overlays simultâneos.
2. **Estado de UI centralizado e mutuamente exclusivo** — um único `drawerMode` (`"closed" | "peek" | "edit"`) por página, estruturalmente impossível de representar "os dois abertos ao mesmo tempo".
3. **Navegação vertical no formulário**, substituindo abas horizontais, escalável a qualquer número de seções sem perder espaço vertical.
4. **Grid de 12 colunas** como único padrão de layout de campos, span proporcional ao conteúdo.
5. **Navegação entre entidades relacionadas sem empilhar overlays** — clicar em um Projeto relacionado dentro do Cliente troca o conteúdo do mesmo `EntityDrawer`, nunca abre um segundo.
6. **Zero cor hardcoded nos componentes novos** — todos os componentes de `entity/` usam exclusivamente classes Tailwind já existentes no vocabulário do projeto (`zinc-*`, `blue-*`, os tons semânticos de `StatusPill`) hoje, preparados para uma futura substituição mecânica por tokens de marca (sem antecipar a marca BOX agora, conforme instrução explícita).
7. **Adoção incremental sem quebrar nada** — os componentes antigos (`EntitySidePanel`, `Modal`, `Tabs`, `CadastroPage`, `CadastroToolbar`, `CadastroTable`, `CadastroIndicators`) continuam funcionando, inalterados, durante toda a transição.

## 4. Componentes oficiais

Convenção de leitura: **Responsabilidade** · **Props principais** (tabela) · **Não faz** (limites explícitos) · **Substitui/relaciona-se com**.

### `EntityDrawer`

**Responsabilidade**: overlay único de detalhe/edição de entidade. Dono do backdrop, da largura por modo, da transição de largura, do foco/Escape, e do ponto de decisão "fechar direto ou confirmar perda de alterações".

| Prop | Tipo | Descrição |
|---|---|---|
| `open` | `boolean` | controla montagem |
| `mode` | `"peek" \| "edit"` | decide largura, e se o rodapé usa `EntityActions` variante peek ou edit |
| `onClose` | `() => void` | fechar (Escape, clique no overlay, botão fechar) |
| `onRequestModeChange` | `(mode: "peek" \| "edit") => void` | pedido de troca de modo (ex.: clique em "Editar") — quem decide se aceita é a página, não o `EntityDrawer` |
| `isDirty` | `boolean` | se `true` e o usuário tentar fechar/trocar de modo, o `EntityDrawer` aciona `onRequestClose` em vez de fechar direto, para a página decidir se abre um `ConfirmDialog` |
| `title` / `description` | `string` | delegados ao `EntityHeader` interno |
| `statusBadge` | `ReactNode` | idem |
| `children` | `ReactNode` | conteúdo do corpo (o `EntityPeek` **ou** o par `EntityFormNav`+`EntityForm`, decidido por quem usa) |
| `footer` | `ReactNode` | tipicamente um `EntityActions` |

**Larguras** (ver seção detalhada mais abaixo) são resolvidas **internamente** por `mode` + breakpoint — não existe mais uma prop `maxWidthClassName` livre por consumidor. Isso é uma mudança deliberada em relação ao padrão `overlayClassName`/`maxWidthClassName` introduzido nas fases anteriores: aquele padrão era necessário **durante a transição**, mas o objetivo final é que a largura pare de ser uma decisão de cada tela.

**Não faz**: não sabe o que é um Cliente/Projeto/Fornecedor; não decide o que salvar; não faz fetch; não decide permissão.

**Relaciona-se com**: substitui o uso de `EntitySidePanel` + `Modal` para CRUD de entidade. `Modal` (`ui/Modal.tsx`) continua existindo, inalterado, para o seu escopo reservado (confirmação, exclusão, alertas, bloqueios, conflitos) — inclusive é literalmente o que resolve o caso `isDirty` acima.

### `EntityHeader`

**Responsabilidade**: bloco de identidade, constante entre os dois modos — avatar/ícone, título, descrição/código, badge de status, botão fechar, e (só em `peek`) botão de navegação "voltar" quando houver uma entidade anterior na pilha de navegação (ver seção 6).

| Prop | Tipo |
|---|---|
| `title` | `string` |
| `description?` | `string` |
| `avatar?` | `ReactNode` (tipicamente `EntityAvatar`, já proposto em `12-plano-de-migracao.md`) |
| `statusBadge?` | `ReactNode` |
| `onClose` | `() => void` |
| `onBack?` | `() => void` — presente só quando existe histórico de navegação para voltar |

**Não faz**: não decide o texto do título (recebe pronto) — quem resolve "nome fantasia ou razão social" continua sendo a *View* da entidade.

### `EntityPeek`

**Responsabilidade**: corpo do modo somente-leitura. Composição declarativa de: resumo (campos-chave), status, tags (quando existirem), responsáveis, contadores de relação, histórico resumido.

| Prop | Tipo |
|---|---|
| `summary` | `{ label: string; value: ReactNode }[]` — os campos-chave, renderizados via `EntityFieldRow` (já existe, `ui/EntityFieldRow.tsx`) |
| `tags?` | `ReactNode` (placeholder até `EntityTags` existir) |
| `relations?` | `ReactNode` (tipicamente `EntityRelations` em modo compacto) |
| `history?` | `ReactNode` (tipicamente `EntityHistory` em modo `compact`) |

**Nunca permite edição inline** — não recebe `onChange` de nenhum campo; isso é reforçado por contrato de props (não existe nenhuma prop de mutação na sua assinatura), não apenas por convenção visual.

**Relaciona-se com**: absorve o papel que hoje `EntitySummaryPanel`+`EntityFieldRow` cumprem parcialmente (usados hoje só por Grupos de Clientes) — passam a ser peças internas do `EntityPeek`, não algo que cada View monta à mão.

### `EntityForm`

**Responsabilidade**: container puro de layout de campos — grid de 12 colunas, gap padronizado. Nada além disso.

| Prop | Tipo |
|---|---|
| `children` | `ReactNode` |

Não existe prop de densidade/variante — a grade de 12 colunas **é** o único padrão, sem alternativa configurável (evita reabrir a discussão de 2 colunas por engano). Cada campo é posicionado por quem o declara, com um `<div className="col-span-12 md:col-span-N">` ao redor do `Input`/`Select` — **deliberadamente não existe** um componente `EntityFormField` de posicionamento: o wrapper é trivial (uma classe utilitária) e não justifica uma nova abstração, seguindo a mesma régua já aplicada a `FormField` em `12-plano-de-migracao.md` (que é interno a `Input`/`Select`, não um componente público).

**Não faz**: não conhece nomes de campos, não valida nada, não conhece Cliente/Projeto.

### `EntitySection`

**Responsabilidade**: cartão de seção dentro do `EntityForm` — título opcional + conteúdo. Consolida o papel que `12-plano-de-migracao.md` havia reservado para `forms/FormSection.tsx`.

> **Nota de reconciliação com `12-plano-de-migracao.md`**: aquele plano propunha `forms/FormSection.tsx` assumindo que as seções continuariam navegadas por abas horizontais. Como o padrão de navegação mudou para `EntityFormNav` (menu lateral), o papel de "seção dentro do formulário" muda de dono — passa a viver em `entity/EntitySection.tsx`, não em `forms/`. `forms/FormField.tsx` (o wrapper interno de `Input`/`Select`, já citado ali) **continua válido e sem mudança** — é ortogonal a esta decisão.

| Prop | Tipo |
|---|---|
| `id` | `string` — corresponde ao `id` usado por `EntityFormNav` |
| `title?` | `string` |
| `children` | `ReactNode` (tipicamente um `EntityForm`) |

### `EntityFormNav`

**Responsabilidade**: menu de navegação entre seções do formulário, substituindo `Tabs` horizontais nesse contexto.

| Prop | Tipo |
|---|---|
| `sections` | `{ id: string; label: string; icon?: LucideIcon; status?: "default" \| "warning" \| "error" }[]` |
| `activeSection` | `string` |
| `onChange` | `(id: string) => void` |

Comportamento responsivo (sem prop nova, resolvido só por CSS, seguindo a convenção já confirmada em todo o projeto de "responsividade via Tailwind, nunca bifurcação de componente por dispositivo" — `taskfloww-design-system.md`, seção 13):
- **Desktop/tablet largo** (`md:` e acima): rail vertical fixo à esquerda do `EntityForm`, dentro do `EntityDrawer` em modo `edit`.
- **Mobile** (abaixo de `md:`): vira uma tira horizontal roláve, visualmente idêntica ao `Tabs` compacto que já existe hoje — reaproveita a implementação de `Tabs.tsx` internamente para essa faixa, em vez de duplicar o markup de "pílula ativa/inativa".

`status` por seção (`"warning"`/`"error"`) é o que abas horizontais fazem mal por falta de espaço — aqui vira um ponto colorido ao lado do label, útil para indicar "esta seção tem um campo obrigatório vazio" sem o usuário precisar clicar em cada aba para descobrir.

### `EntityActions`

**Responsabilidade**: cluster de ações do rodapé, com duas variantes.

| Prop | Tipo |
|---|---|
| `variant` | `"peek" \| "edit"` |
| `primaryAction` | `{ label: string; onClick: () => void; disabled?: boolean }` |
| `secondaryActions?` | `{ label: string; onClick: () => void; tone?: "default" \| "danger" }[]` |

Em `variant="peek"`: ação primária tipicamente "Editar"; secundárias futuras "Duplicar"/"Excluir" (excluir sempre com `tone="danger"`, o que sinaliza para quem monta a página que aquela ação **deve** passar por um `ConfirmDialog` antes de chamar o callback — governança de UX embutida na própria tipagem).
Em `variant="edit"`: ação primária "Salvar", secundária "Cancelar".

**Não faz**: não sabe se deve mostrar "Excluir" (isso é decisão de permissão da *View*, que só passa a ação se o usuário tiver permissão — mesmo padrão já usado hoje por `canCreate`/`canEdit` em `FornecedoresView`/`GruposClientesView`).

### `EntityHistory`

**Responsabilidade**: histórico de eventos da entidade, em duas variantes.

| Prop | Tipo |
|---|---|
| `events` | `{ id: string; usuario: string; dataHora: string; acao: string }[]` |
| `variant` | `"compact" \| "full"` |

`"compact"`: só o evento mais recente + link "ver histórico completo" (usado dentro de `EntityPeek`). `"full"`: lista completa, pesquisável (usado como conteúdo de uma `EntitySection` dedicada em modo `edit`). Consolida as ~7 implementações hoje duplicadas de `HistoricoSection` (uma por entidade, cada uma reescrevendo a mesma tabela).

### `EntitySkeleton`

**Responsabilidade**: placeholder de carregamento com a silhueta do `EntityDrawer` (cabeçalho + linhas de campo), para quando a busca de dados deixar de ser síncrona (mock em memória) e passar a ser assíncrona (API real).

| Prop | Tipo |
|---|---|
| `mode` | `"peek" \| "edit"` |

**Relaciona-se com**: constrói-se **sobre** o `LoadingState` genérico já proposto em `12-plano-de-migracao.md` (Fase 3) — `EntitySkeleton` é a forma "silhueta de entidade" desse primitivo genérico, não uma implementação paralela.

### `EntityRelations` (futuro — não construir agora)

**Responsabilidade**: lista compacta de registros relacionados (Projetos de um Cliente, Tarefas de um Projeto etc.), cada item navegando para o `EntityPeek` daquele item (nunca abrindo um segundo `EntityDrawer`).

Só deve ser construído **quando a primeira relação navegável real for implementada** — hoje nenhuma entidade tem esse dado modelado além de contagens estáticas (`totalContatos` em Clientes, por exemplo, que nem é uma relação navegável, é uma contagem local).

### `EntityTags` (futuro — não construir agora)

**Responsabilidade**: chips de tag na visualização + input de tags no formulário. Só constrói quando a feature de Tags for de fato aprovada e modelada (`docs/design-system/entity-ux-pattern.md`, seção 8, já define o padrão de UX; este documento só reserva o nome do componente).

### `EntityTimeline` (futuro — não construir agora)

**Responsabilidade**: variante do `EntityHistory` que intercala histórico de sistema **e** comentários numa única linha do tempo cronológica — só faz sentido para entidades colaborativas (Projetos, Demandas), quando Comentários existir. Para todas as entidades de cadastro simples, `EntityHistory` sozinho é suficiente — não construir `EntityTimeline` como abstração antecipada.

---

## 5. Fluxos

### Fluxo principal (view → edit → save)

```
Tabela (linha)
   │ clique
   ▼
EntityDrawer aberto, mode="peek"
   corpo: EntityPeek (EntityHeader + resumo + status + tags + relations + history compact + EntityActions[peek])
   │
   ├─ [Editar] → onRequestModeChange("edit")
   │        │
   │        ▼
   │   EntityDrawer, mode="edit" (MESMA instância, larguras diferentes)
   │        corpo: EntityFormNav + EntitySection ativa (EntityForm dentro)
   │        rodapé: EntityActions[edit]
   │        │
   │        ├─ [Salvar] → validação → persistência (mock) → onRequestModeChange("peek")
   │        │                                                        ▼
   │        │                                              EntityDrawer, mode="peek" (dados atualizados)
   │        │
   │        └─ [Cancelar] / [Esc] / [clique no overlay]
   │                 │
   │                 ├─ isDirty === false → fecha direto para "peek" (ou fecha o drawer inteiro, se veio do fechamento)
   │                 └─ isDirty === true  → abre `ConfirmDialog` ("Descartar alterações?") — usa o `Modal` já existente,
   │                                          dentro do seu escopo reservado (confirmação/bloqueio)
   │
   └─ [fechar / Esc / clique no overlay] (em modo peek) → EntityDrawer fecha, drawerMode="closed"
```

### Fluxo de criação (sem peek prévio)

```
Botão "Novo X" → EntityDrawer abre direto em mode="edit"
   (o passo único de identificação, ex. CNPJ/CPF em Clientes, continua existindo como
    conteúdo inicial do corpo do EntityDrawer — não é mais um Modal separado)
   │
   [Salvar] → persistência → EntityDrawer troca para mode="peek" mostrando o registro recém-criado
```

### Fluxo de navegação entre entidades relacionadas (Cliente → Projeto → Tarefa)

**Regra fixa**: nunca empilhar `EntityDrawer`. Sempre substituir o conteúdo do drawer atual.

```
EntityDrawer aberto (Cliente, peek)
   │ clique em um Projeto dentro de EntityRelations
   ▼
navigationStack.push({ type: "cliente", id: clienteId })
currentEntity = { type: "projeto", id: projetoId }
   │
   ▼
EntityDrawer (MESMA instância) troca o conteúdo para o Peek do Projeto
   (título, descrição, resumo, status — tudo re-renderizado; a instância do
    componente e o overlay/backdrop não desmontam, só o conteúdo interno muda)
   │
   ├─ EntityHeader agora mostra botão "← Voltar" (porque navigationStack não está vazio)
   │      │ clique
   │      ▼
   │   currentEntity = navigationStack.pop() → volta para o Peek do Cliente
   │
   └─ [Editar] no Projeto → mode="edit" do Projeto, na mesma instância, mesma regra de largura por modo
```

**Como implementar tecnicamente** (sem escrever código agora, só a decisão de arquitetura): o `EntityDrawer` não sabe nada disso — ele é `open`/`mode`/`children` puro. Quem sabe é a camada que o invoca, que precisa manter um estado do tipo:
```
type EntityRef = { type: string; id: string };

currentEntity: EntityRef | null;
navigationStack: EntityRef[];
```
Ao "abrir" uma entidade relacionada, a página empilha a atual (`navigationStack.push(currentEntity)`) e troca `currentEntity`. Ao "voltar", desempilha. Isso é uma pilha de navegação **dentro de uma única instância de overlay** — nada a ver com empilhar componentes de overlay, que continua proibido. É o mesmo princípio de uma SPA com histórico de rota, sem de fato usar rotas — o `EntityDrawer` funciona como uma "mini-rota" local.

Esse mecanismo só precisa existir de fato quando a primeira relação navegável for implementada (junto com `EntityRelations`) — hoje é só a decisão de design que evita reabrir essa discussão depois.

---

## 6. Estados

O estado pertence à **página** (a *View* de cada entidade, ex. uma futura `ClientesView` v2), nunca aos componentes de `entity/`. Isso segue a regra de separação UI/negócio já fixada em `12-plano-de-migracao.md`, seção 3.

```
selectedEntityId: string | null      // id do registro cujo drawer está aberto (null = fechado)
drawerMode: "closed" | "peek" | "edit"
activeSection: string                // id da seção ativa no EntityFormNav (só relevante em "edit")
isDirty: boolean                     // formulário tem alterações não salvas (drives o ConfirmDialog ao fechar/trocar de modo)
isSaving: boolean                    // ação de salvar em andamento (relevante quando a API deixar de ser mock síncrono)
navigationStack: EntityRef[]         // pilha de navegação entre entidades relacionadas (vazio na maioria das sessões de uso)
currentEntity: EntityRef | null      // qual entidade (tipo+id) está de fato sendo mostrada — pode divergir de selectedEntityId
                                      // quando o usuário navegou para uma relação
historyExpanded: boolean             // (opcional) permite expandir o teaser de histórico dentro do próprio peek,
                                      // sem trocar de modo — evita forçar "edit" só para ver mais 2 linhas de histórico
```

Regras derivadas (não são estado, são calculadas):
- `open = drawerMode !== "closed"`
- Largura do drawer = função pura de `drawerMode` (ver tabela da seção 4/`EntityDrawer`) — nunca armazenada como estado próprio.
- `EntityFormNav` só é renderizado quando `drawerMode === "edit"`.

**Por que `selectedEntityId` e `drawerMode` são dois campos, não um só**: porque o `id` precisa sobreviver à troca de modo (ao clicar "Editar", o registro continua sendo o mesmo, só o modo muda) — combiná-los em um único enum (`"closed" | "peek:123" | "edit:123"`) funcionaria, mas tornaria a leitura do id mais indireta (precisaria fazer parsing da string) sem ganho real. Mantê-los separados é mais simples de ler e testar.

**Por que existe `currentEntity` além de `selectedEntityId`**: `selectedEntityId` responde "qual linha da tabela originou a abertura do drawer"; `currentEntity` responde "o que está sendo mostrado agora", que pode ser outra entidade após uma navegação por relação. Nas telas que ainda não têm relações navegáveis (hoje, todas), os dois sempre coincidem e `navigationStack` fica sempre vazio — a distinção só passa a importar quando `EntityRelations` for implementado.

---

## 7. Estrutura de pastas

```
frontend/src/components/
├── ui/                  → MANTIDO. Primitivos atômicos (Button, Input, Select, StatusPill,
│                          EntityFieldRow, EntityAvatar quando promovido, Modal — inalterado)
├── layout/               → MANTIDO. Shell, Sidebar, Header, PageShell
├── data-display/         → conforme 12-plano-de-migracao.md (EntityToolbar, MetricStrip, DataTable,
│                          Pagination) — este documento não altera nada ali
├── feedback/             → conforme 12-plano-de-migracao.md (EmptyState, ErrorState, LoadingState,
│                          ConfirmDialog) — ConfirmDialog ganha aqui seu primeiro consumidor concreto
│                          (fechar EntityDrawer com alterações não salvas)
├── forms/                → conforme 12-plano-de-migracao.md, só FormField (interno a Input/Select/Textarea)
│                          — FormSection é removido dessa proposta e substituído por entity/EntitySection
├── entity/               → NOVO, escopo deste documento
│   ├── EntityDrawer.tsx
│   ├── EntityHeader.tsx
│   ├── EntityPeek.tsx
│   ├── EntityForm.tsx
│   ├── EntitySection.tsx
│   ├── EntityFormNav.tsx
│   ├── EntityActions.tsx
│   ├── EntityHistory.tsx
│   ├── EntitySkeleton.tsx
│   ├── EntityRelations.tsx     (futuro — arquivo só criado quando implementado)
│   ├── EntityTags.tsx          (futuro — idem)
│   ├── EntityTimeline.tsx      (futuro — idem)
│   └── index.ts                 (barrel export, mesmo padrão de cadastros/index.ts)
├── cadastros/             → MANTIDO durante a transição (ver seção 9)
├── workspace/              → MANTIDO durante a transição, partes mortas já identificadas em
│                          12-plano-de-migracao.md continuam candidatas a remoção, sem relação com este documento
└── <domínios>/            → clientes/, fornecedores/, equipes/, usuarios/, grupos-clientes/,
                           projetos/, demandas/, agencias, workflows — mantidos; cada um passa a
                           montar EntityDrawer em vez de EntitySidePanel+Modal quando migrado (Fase N)
```

**Por que uma pasta nova (`entity/`) em vez de encaixar em `data-display/` ou `cadastros/`**: esses componentes não exibem listas/tabelas (isso é `data-display/`) nem são específicos do padrão de cadastro tabular antigo (`cadastros/`) — eles resolvem um problema diferente e mais amplo: o ciclo de vida de visualização/edição de **um único registro**, reaproveitável por entidades que nem usam tabela como listagem principal (ex.: um futuro Kanban de Demandas também abriria um `EntityDrawer` ao clicar num card). Merecem vocabulário e pasta próprios, alinhados ao nome já cunhado em `entity-ux-pattern.md`.

---

## 8. Estratégia de migração

Migração **por entidade**, nunca em lote. Cada fase é aprovável e revertível isoladamente.

| Fase | Escopo | Critério de saída |
|---|---|---|
| **Fase 0** (este documento) | Especificação, sem código | Aprovação da arquitetura |
| **Fase 1** | Construir `entity/` (todos os componentes da seção 4, exceto os 3 marcados "futuro") — sem nenhum consumidor real ainda, validados só na vitrine `/design-system` | `typecheck`/`lint`/`build` passam; exemplo funcional na vitrine; nenhuma página de produto importa `entity/` ainda |
| **Fase 2** | Piloto: Clientes migra de `EntitySidePanel`+`Modal` para `EntityDrawer` | Clientes com paridade funcional total (nada removido, nada quebrado); aprovação visual explícita |
| **Fase 3** | Fornecedores e Grupos de Clientes migram (mesma família de padrão do piloto) | idem, por entidade |
| **Fase 4** | Equipes e Usuários migram (ganham `EntityPeek` pela primeira vez — hoje não têm painel de detalhe nenhum) | idem |
| **Fase 5** | Agências e Workflows migram (hoje são CRUD incompletos — a migração inclui completar os handlers que faltam, fora do escopo deste documento) | idem |
| **Fase 6** | Projetos e Demandas avaliam se migram para `EntityDrawer` ou "graduam" para tela cheia (`entity-ux-pattern.md`, seção 12, ponto 8) — decisão própria, não assumida aqui | decisão registrada em documento específico |
| **Fase 7** | Remoção de `EntitySidePanel` e do uso de `Modal` para CRUD, uma vez que nenhuma tela mais os use dessa forma | `grep` confirma zero uso de `EntitySidePanel` para CRUD e zero `Modal` fora do escopo de confirmação/bloqueio |

---

## 9. Compatibilidade

- **Nada em `ui/`, `cadastros/`, `layout/` é alterado por este documento.** `EntitySidePanel.tsx` e `Modal.tsx` continuam exatamente como estão hoje (isso é uma restrição explícita desta tarefa, e também a postura correta: são usados por 5 e 8 consumidores respectivamente, nenhum deles tocado).
- `Tabs.tsx` continua existindo e sendo usado pelos 7 consumidores atuais sem nenhuma mudança — `EntityFormNav` **reaproveita** `Tabs` internamente só na faixa mobile (conforme seção 4), não o substitui, não o depreca.
- `CadastroPage`, `CadastroToolbar`, `CadastroTable`, `CadastroIndicators` seguem exatamente como propôs `12-plano-de-migracao.md` — este documento não muda nada da camada de listagem/tabela, só da camada de detalhe/edição de um registro.
- Enquanto uma entidade não migrar (fases 3 a 6), ela continua 100% funcional no padrão atual — a existência de `entity/` na árvore de componentes não afeta nenhuma tela até que a própria tela decida importar de lá.
- `ConfirmDialog` (proposto em `12-plano-de-migracao.md`, ainda não construído) passa a ter, com este documento, seu **primeiro caso de uso concreto e obrigatório** (fechar `EntityDrawer` com alterações não salvas) — o que justifica priorizá-lo dentro da Fase 1 de construção da infraestrutura (seção 12).

---

## 10. Riscos

| Risco | Fase | Mitigação |
|---|---|---|
| `EntityDrawer` tentar abstrair demais (virar um "component gigante configurável") | Fase 1 | Contrato de props enxuto (ver seção 4); larguras resolvidas internamente por `mode`, não expostas como prop livre |
| `EntityFormNav` responsivo (rail↔abas) ficar inconsistente visualmente com o `Tabs` que reaproveita | Fase 1 | Reutilizar o componente `Tabs` de fato (import, não reimplementação) na faixa mobile |
| Migração de Equipes/Usuários (Fase 4) introduzir comportamento novo (eles hoje não têm `EntityPeek`) e ser confundida com "só troca de componente" | Fase 4 | Tratar explicitamente como pequena feature nova na aprovação daquela fase, não como refatoração pura |
| `navigationStack`/`currentEntity` serem construídos antes de qualquer relação real existir, virando código morto | Fase 1 | A pilha de navegação só é **codificada de fato** quando `EntityRelations` for implementado (fase futura); nesta fase é só decisão de forma, não implementação |
| Regressão de acessibilidade ao consolidar `EntitySidePanel`+`Modal` em `EntityDrawer` | Fase 1 | `EntityDrawer` herda o padrão de ARIA mais completo já validado hoje em `EntitySidePanel` (`role="dialog"`, `aria-modal`, foco automático, restauração de foco) — nunca o padrão mais fraco do `Modal` atual |
| Times futuros reintroduzirem `md:grid-cols-2` por hábito | Fases 2+ | `EntityForm` não expõe nenhuma prop que permita voltar a 2 colunas — a única forma de "voltar ao padrão antigo" seria não usar `EntityForm` |

---

## 11. Roadmap

```
Fase 0  ── este documento (aprovação de arquitetura)
Fase 1  ── construção de entity/ (sem consumidores reais)
Fase 2  ── piloto Clientes
Fase 3  ── Fornecedores, Grupos de Clientes
Fase 4  ── Equipes, Usuários
Fase 5  ── Agências, Workflows
Fase 6  ── decisão Projetos/Demandas (EntityDrawer vs tela cheia)
Fase 7  ── remoção de EntitySidePanel/Modal-para-CRUD
─────────────────────────────────────────────
(paralelo, sem bloquear o roadmap acima)
Branding BOX ── só depois da Fase 2 aprovada visualmente, aplicado nos tokens
                 centralizados (globals.css), nunca antes — conforme já
                 combinado ao final de entity-ux-pattern.md
Tags          ── EntityTags construído só quando a feature for aprovada
Relações      ── EntityRelations construído só quando a primeira relação
                 navegável real for modelada
```

---

## 12. Ordem exata de implementação (Fase 1 — construção de `entity/`)

Ordem de dependência, não de prioridade de negócio — cada item só pode ser construído depois do anterior:

1. `EntityDrawer` (casca: `open`/`mode`/backdrop/largura por modo/transição/Escape/foco) — nada mais existe sem isso.
2. `EntityHeader` — primeiro conteúdo real dentro da casca, permite um smoke test visual na vitrine.
3. `EntityActions` (as duas variantes) — pequeno, fecha o "esqueleto" ponta a ponta (cabeçalho + corpo vazio + rodapé) para validação visual.
4. `EntityPeek` — primeiro modo completo e funcional.
5. `EntityForm` (grid de 12 colunas) — primitivo de layout, sem depender de navegação ainda.
6. `EntitySection` — depende de `EntityForm` existir para ter o que envolver.
7. `EntityFormNav` — depende de `EntitySection` existir (precisa ter `id`s de seção reais para navegar entre).
8. Composição do modo `edit` do `EntityDrawer` = `EntityHeader` + `EntityFormNav` + `EntitySection`/`EntityForm` + `EntityActions[edit]`.
9. `EntityHistory` (`compact` + `full`) — primeiro tipo de conteúdo "real" de seção, valida o padrão ponta a ponta com um caso de uso concreto (todas as entidades têm histórico hoje).
10. `EntitySkeleton` — construído sobre o `LoadingState` genérico (que precisa existir antes; se `12-plano-de-migracao.md` Fase 3 ainda não tiver sido implementada, `EntitySkeleton` pode nascer com um placeholder simples próprio e ser refatorado depois, sem bloquear).
11. `ConfirmDialog` (de `feedback/`, não de `entity/`) — construído/priorizado aqui porque é o que resolve `isDirty` no fechamento do `EntityDrawer`.
12. Atualização da vitrine `/design-system` com exemplos de `EntityDrawer` (peek e edit) usando dados fictícios — validação final da Fase 1, sem tocar em nenhuma entidade real.

**Fora desta lista, propositalmente**: `EntityRelations`, `EntityTags`, `EntityTimeline` (aguardam suas respectivas features) e qualquer migração de entidade real (Fase 2 em diante, cada uma com sua própria aprovação).

---

## 13. Critérios de aceite

Da Fase 1 (construção de `entity/`) especificamente:

- [ ] `EntityDrawer` nunca renderiza dois overlays — validável inspecionando que só existe **um** elemento com `role="dialog"` montado por vez, mesmo durante a transição de largura peek→edit.
- [ ] Nenhum componente em `entity/` importa de `src/lib/*-mock.ts` ou de qualquer `types/<entidade>.ts`.
- [ ] Nenhuma cor hardcoded (hex) em nenhum arquivo novo de `entity/` — só classes Tailwind do vocabulário já existente.
- [ ] `EntityForm` não expõe nenhuma forma de renderizar menos de 12 colunas de base.
- [ ] `EntityFormNav` funciona por teclado (setas ou Tab entre itens, `Enter`/`Espaço` para ativar) e expõe `aria-current`/equivalente no item ativo.
- [ ] `EntityDrawer` reproduz, no mínimo, o mesmo nível de ARIA que `EntitySidePanel` tem hoje (`role="dialog"`, `aria-modal`, `aria-labelledby`, foco automático, restauração de foco, bloqueio de scroll do body).
- [ ] `npm run typecheck`, `npm run lint`, `npm run build` passam com os novos arquivos, sem nenhuma página de produto alterada.
- [ ] `git status`/`git diff --stat` mostram só arquivos novos dentro de `frontend/src/components/entity/` (e `feedback/ConfirmDialog.tsx`, se construído junto) — zero linha alterada em `EntitySidePanel.tsx`, `Modal.tsx`, `Tabs.tsx`, `cadastros/*`, ou qualquer `*View.tsx` de entidade.

Das fases de migração (2 em diante, critério geral repetido por entidade):

- [ ] Paridade funcional 100% com o padrão antigo (nenhum campo, ação ou fluxo removido sem decisão explícita).
- [ ] Nunca dois overlays simultâneos, em nenhum ponto do fluxo (incluindo o instante de transição peek→edit).
- [ ] Aprovação visual explícita antes de considerar a fase concluída.

---

## 14. Dívidas técnicas

Herdadas dos documentos anteriores e ainda não resolvidas por este plano (propositalmente — não é escopo desta tarefa):

- Duplicação do título entre `Header.tsx` (chrome global) e o conteúdo da página (`taskfloww-design-system.md`, seção 11) — não tocado, pois exigiria alterar `Header.tsx`, explicitamente fora de escopo.
- Fonte Geist carregada mas não aplicada ao `body` (`globals.css`) — não tocado nesta fase.
- `CadastroStatusBadge` ainda reaproveitado indevidamente para "Categoria"/"Perfil" em Fornecedores/Usuários — não tocado; quando essas entidades migrarem para `EntityPeek`/`EntityDrawer`, é o momento natural de corrigir, usando `StatusPill` para status real e um badge neutro (a definir) para valores não-semânticos.
- Ausência de paginação em qualquer tabela — inalterado, é escopo de `data-display/DataTable` (`12-plano-de-migracao.md`), não deste documento.
- Ausência de toast/feedback de sucesso ao salvar — este documento **não resolve isso**; `EntityActions`/`EntityDrawer` preveem o ponto de extensão (`onSave` retornando uma Promise, por exemplo) mas o componente de toast em si é do escopo de `feedback/` e não foi incluído na Fase 1 aqui definida — registrar como próxima dívida a fechar assim que uma entidade migrar de verdade e o "silêncio pós-salvar" ficar visível de novo.
- `@dnd-kit/sortable` instalado e nunca usado; módulo `kanban/` órfão com drag-and-drop real não conectado — sem relação com este documento, seguem como dívidas já registradas.

Nova dívida introduzida conscientemente por este plano:

- `navigationStack`/`currentEntity` são especificados (seção 6) mas **não implementados** até `EntityRelations` existir — ou seja, por um período, a arquitetura "sabe" como deveria funcionar a navegação entre entidades, mas nenhum código a exercita. Risco aceito: é preferível decidir a forma agora (evitando um redesenho de estado depois) a implementar um mecanismo sem nenhum consumidor real hoje.

---

## 15. Recomendações futuras

1. **Branding BOX** deve ser aplicado **depois** da Fase 2 (piloto Clientes) estar visualmente aprovada — nessa ordem, os tokens de marca são aplicados uma única vez sobre uma arquitetura já estável, em vez de retrabalhados a cada ajuste de fluxo (exatamente a ordem que você já indicou ao final de `entity-ux-pattern.md`).
2. Quando a API real substituir os mocks (`PROJECT_STATUS.md`, "Fases Futuras → Backend"), `isSaving`/`EntitySkeleton` passam de "preparados mas ociosos" para efetivamente exercitados — vale revisitar o contrato de `EntityActions.primaryAction` para suportar um estado de carregamento (`disabled` + label alternativo, ex. "Salvando...") nesse momento, não antes.
3. Ao implementar `EntityRelations`, revisitar se `navigationStack` deveria refletir na URL (deep link para "Cliente X → Projeto Y aberto") — hoje o app não usa nenhuma rota dinâmica para estado de UI; isso é uma decisão maior de arquitetura de roteamento, fora do escopo deste documento, mas vale registrar como pergunta em aberto.
4. Ao migrar Projetos/Demandas (Fase 6), reavaliar com dados reais de uso se a "graduação" para tela cheia é necessária de fato ou se `EntityDrawer` em modo `edit` (840px) já é suficiente — a decisão de `entity-ux-pattern.md` foi uma previsão, não uma certeza, e deve ser revalidada com o produto já rodando no novo padrão.
5. Considerar, só depois de pelo menos 3 entidades migradas (Fase 4 concluída), extrair um guia de "como migrar uma entidade" a partir dos padrões repetidos observados nas Fases 2–4 — não escrever esse guia antecipadamente, para não prescrever regras antes de ter casos reais suficientes.

---

*Fim do documento. Nenhum arquivo de código foi criado, movido ou alterado para produzir esta especificação.*
