# Changelog — Refinamento Visual TaskFloww V2

> Registro cronológico das fases já aprovadas do refinamento visual em
> curso. Cobre Fase 0 a Fase 4A. Não é um documento de arquitetura (isso
> vive em `13-tokens-visuais.md` e `14-component-hierarchy.md`) — é o
> histórico do que foi decidido e por quê, para consulta rápida sem
> precisar reconstruir o raciocínio a partir da conversa original.

---

## Fase 0 — Fundação de tokens

**Objetivo:** formalizar, em documento, o vocabulário visual que já
existia de forma implícita/espalhada no código (radius, sombra, escala
tipográfica) — sem tocar em nenhum componente.

**Componentes afetados:** nenhum.

**Decisões arquiteturais:**
- Radius: `rounded-2xl` para controles interativos (botão, input) vs.
  `rounded-3xl` para contêineres (card, painel, tabela, toolbar, modal,
  drawer).
- Sombra por elevação: `shadow-sm` (repouso) → `shadow-md` (hover de card
  clicável) → `shadow-xl` (painel flutuante) → `shadow-2xl` (overlay de
  edição).
- Escala tipográfica nomeada (Display/H1/H2/H3/Título de Card/Subtítulo/
  Texto/Legenda/Badge/Tabela), mapeada a classes Tailwind já usadas no
  código — nenhum tamanho novo inventado.
- Cor de marca (laranja `#fc6c00`) e fonte (Roboto) **já existiam** no
  código antes desta fase, de forma não documentada — este documento só
  as formaliza.

**Decisões descartadas:** nenhuma — é a fase de fundação, sem alternativa
avaliada.

**Documentos criados:** `docs/design-system/13-tokens-visuais.md`.

**Impacto visual:** nenhum (documentação pura).

---

## Fase 1 — Alinhamento de radius (Cadastro* / Dashboard)

**Objetivo:** aplicar a regra de radius de contêiner definida na Fase 0
aos únicos componentes que ainda estavam em `rounded-2xl`.

**Componentes afetados:** `cadastros/CadastroTable.tsx`,
`cadastros/CadastroToolbar.tsx`, `cadastros/CadastroIndicators.tsx`,
`dashboard/DashboardWidget.tsx`.

**Decisões arquiteturais:** nenhuma nova — aplicação direta da regra já
definida na Fase 0.

**Decisões descartadas:** nenhuma.

**Documentos criados:** nenhum.

**Impacto visual:** baixo — bordas mais arredondadas (`2xl`→`3xl`) nas 7
telas de cadastro (via `CadastroTable`/`CadastroToolbar`/
`CadastroIndicators`) e na Dashboard (via `DashboardWidget`).

---

## Fase 2 — Hierarquia de botões (implementada e depois revertida)

**Objetivo original:** generalizar o laranja de marca
(`colorScheme="brand"`) como default de toda ação primária do sistema,
substituindo o default `"neutral"` (preto) em `ui/Button.tsx` e
`entity/EntityActions.tsx` — até então o laranja era opt-in, usado só por
Clientes.

**Componentes afetados:** `ui/Button.tsx`, `entity/EntityActions.tsx`.

**Decisões arquiteturais:**
- Implementada inicialmente (default `colorScheme` trocado para
  `"brand"` nos dois arquivos).
- **Revertida** a pedido explícito do usuário antes de seguir para a
  Fase 3: o default volta a `"neutral"`; `colorScheme="brand"` permanece
  disponível e continua em uso explícito por Clientes e Usuários (via
  `EntityActions`), sem nenhum consumidor alterado pela reversão.
- A definição formal de qual variante de botão é a "principal" do
  sistema foi adiada para uma decisão própria — que veio a ser resolvida
  depois, na hierarquia de botões documentada em
  `14-component-hierarchy.md` (seção 1), a ser implementada na Fase 4B.

**Decisões descartadas:** generalização automática do laranja como
default global de ação primária, sem uma hierarquia visual formalmente
definida antes — descartada nesta fase; a hierarquia completa (Primary/
Secondary/Outline/Ghost/Danger/Success) só foi definida depois, com
aprovação própria, e sua implementação fica para a Fase 4B.

**Documentos criados:** nenhum nesta fase (o resultado da reversão
motivou, mais tarde, a criação de `14-component-hierarchy.md`).

**Impacto visual:** líquido zero — a mudança foi implementada e revertida
dentro da mesma fase; nenhuma alteração visual desta fase permanece no
código hoje.

---

## Fase 3 — Tooltip único + refinamento de primitivos `ui/`

**Objetivo:** consolidar as duas implementações divergentes de tooltip
que existiam no projeto; padronizar o anel de foco visível em campos de
formulário e navegação; alinhar o radius dos painéis de dropdown.

**Componentes afetados:** novo `ui/Tooltip.tsx`; `layout/Header.tsx`;
`agenda/AgendaList.tsx`; `ui/Input.tsx`; `ui/Select.tsx`;
`ui/Textarea.tsx`; `ui/Tabs.tsx`; `ui/MultiSelect.tsx`;
`layout/UserMenu.tsx`; `layout/QuickCreateMenu.tsx`.

**Decisões arquiteturais:**
- `Tooltip` único do sistema: `role="tooltip"` + `aria-describedby` via
  `useId()`, com dois posicionamentos (`bottom-start`/`right`) cobrindo
  os dois usos reais existentes — substitui a marcação manual duplicada
  em `Header.tsx` (que já tinha ARIA) e `AgendaList.tsx` (que não tinha,
  e duplicava com `title=` nativo).
- Anel de foco (`focus-visible:ring-2`) sempre neutro (`zinc-900`), nunca
  laranja, em qualquer componente — "foco é acessibilidade, não
  branding", princípio que evita usar a cor de marca fora do que é
  destaque intencional.
- Painéis de dropdown (`UserMenu`, `QuickCreateMenu`) alinhados a
  `rounded-3xl`, mesma regra de contêiner da Fase 0/1.

**Decisões descartadas:** nenhuma registrada explicitamente nesta fase —
execução direta sem pontos de decisão em aberto.

**Documentos criados:** nenhum novo (aplicação das regras já definidas em
`13-tokens-visuais.md`).

**Impacto visual:** baixo e discreto — tooltip com aparência unificada
nos dois pontos onde já existia; campos de formulário e abas passam a
mostrar um anel de foco visível ao navegar por teclado (antes só mudavam
de cor de borda); dropdowns com cantos mais arredondados.

---

## Fase 4A — Normalização de componentes existentes

**Objetivo:** consolidar o vocabulário entre `Badge` e `StatusPill`;
revisar `Card`/`MetricCard`/`DashboardWidget`; alinhar hover/active/
selected/disabled/error/focus; padronizar `EmptyState`/
`EmptyStateIllustration`; revisar tamanho e acessibilidade de ícones;
remover duplicações visuais evidentes — sem criar APIs novas nem alterar
comportamento, a partir da hierarquia definida em
`14-component-hierarchy.md`.

**Componentes afetados:** `ui/Card.tsx` (borda), `ui/EmptyState.tsx`
(cor de borda), `agenda/AgendaList.tsx` (emoji removido do empty state),
`ui/Input.tsx`/`ui/Select.tsx`/`ui/Textarea.tsx` (estado `disabled`
visual), `fornecedores/FornecedoresView.tsx` (Categoria:
`CadastroStatusBadge`→`Badge`), `usuarios/UsuariosView.tsx` (Perfil:
`StatusPill`→`Badge`), `grupos-clientes/GrupoClienteFormSections.tsx`
(status do Cliente vinculado: `Badge`→`StatusPill`),
`app/configuracoes/{tipos-tarefa,sla,prioridades}/page.tsx` (status:
`Badge`→`StatusPill`), `types/cliente.ts` (nova função
`clienteStatusTone`, centralizada), `clientes/ClientesView.tsx` (passa a
importar a função em vez de defini-la localmente).

**Decisões arquiteturais:**
- `Badge` representa informação não semântica (categoria, perfil,
  classificação); `StatusPill` representa estado real do sistema — essa
  distinção passa a valer em todo o projeto, não só nos casos corrigidos
  nesta fase.
- Toda regra de mapeamento de estado (status → tone, status → ícone,
  status → descrição) pertence ao domínio da entidade — nunca a um
  componente compartilhado de `ui/` nem a uma biblioteca genérica de
  status. Registrado formalmente em `14-component-hierarchy.md`, seção 8,
  como decisão definitiva do projeto (não só desta fase).
- `Tabs` (navegação local) mantém hierarquia visual deliberadamente
  diferente da `Sidebar` (navegação global) — a distinção entre os dois
  níveis é intencional, não uma inconsistência a corrigir.
- Correção de registro: `14-component-hierarchy.md` originalmente
  afirmava que os KPIs da Dashboard usavam `MetricCard` — por leitura do
  código, na verdade usam `CadastroIndicators`. Documento corrigido para
  registrar que **duas famílias de indicador coexistem** hoje
  (`CadastroIndicators` e `MetricCard`), sem unificá-las.

**Decisões descartadas:**
- Adicionar `className`/densidade a `Badge.tsx` — descartada; a API do
  componente permanece simples, revisitada apenas se o mesmo problema
  aparecer em múltiplos lugares no futuro.
- Aplicar o tratamento laranja da Sidebar (`bg-primary-soft`/barra) à aba
  ativa de `Tabs` — descartada; é a mesma decisão acima sobre hierarquia
  Tabs vs. Sidebar.
- Normalizar o tamanho dos ícones "hero" (`h-6 w-6`) de cabeçalho de
  página (Projetos, Demandas, Tráfego) — descartada por ora; fica para
  uma futura documentação própria de Page Layout/Page Header, para não
  reduzir a presença visual desses ícones sem esse contexto mais amplo.
- Utilitário genérico `src/lib/status.ts`/`status-tone.ts` cobrindo
  Cliente, Usuário, SLA, Prioridades, Tipos de Tarefa e Workflows —
  descartado após análise de impacto; a única duplicação real encontrada
  (`clienteStatusTone` repetida) foi resolvida dentro do próprio domínio
  Cliente, não por um utilitário genérico.
- Unificar `CadastroIndicators` e `MetricCard` numa família única de
  indicador — fora de escopo desta fase; já registrado como decisão
  estrutural separada, de risco alto, em `12-plano-de-migracao.md`.

**Documentos criados:** `docs/design-system/14-component-hierarchy.md`
(hierarquia de Botões/Badges/Cards/Empty States/Estados/Ícones), depois
atualizado com a correção sobre KPI/Widget (seção 3) e com o princípio
arquitetural sobre mapeamento de estado por domínio (seção 8).

**Impacto visual:** pequeno e espalhado — borda adicionada a `Card`;
badges de categoria/perfil corrigidos de status para informação neutra
(Fornecedores, Usuários); status reais corrigidos de badge neutro para
`StatusPill` com cor semântica (Grupos de Clientes, Tipos de Tarefa, SLA,
Prioridades); campos de formulário desabilitados agora visivelmente
acinzentados; empty state da Agenda sem emoji.

---

## Resumo — o que está pendente

**Fase 4B** (novas capacidades: variantes `Outline`/`Ghost`/`Success`/
`Danger` formalizada, `loading` em `Button`, CTA secundário em
`EmptyState`, skeleton padronizado) ainda não foi iniciada — aguarda
aprovação própria.

Nenhuma das fases documentadas aqui foi commitada ou enviada ao remoto.
