# 14 — Hierarquia Oficial de Componentes Visuais

> Documento de especificação. Não altera nenhum componente — é a
> referência oficial para a implementação da **Fase 4** do refinamento
> visual em curso. Constrói sobre `13-tokens-visuais.md` (tokens de cor,
> radius, sombra, tipografia) e sobre o inventário real do código, lido
> nesta análise (`ui/Button.tsx`, `ui/Badge.tsx`, `ui/StatusPill.tsx`,
> `ui/Card.tsx`, `ui/MetricCard.tsx`, `ui/EmptyState.tsx`,
> `ui/EmptyStateIllustration.tsx`, `dashboard/DashboardWidget.tsx`,
> `layout/Sidebar.tsx`, `entity/EntityDrawer.tsx`, `entity/EntityPeek.tsx`,
> `entity/EntityActions.tsx`, `usuarios/UsuariosView.tsx`).
>
> Convenção de leitura: cada item marca **[existente]** (já implementado,
> só formalizado aqui) ou **[novo — Fase 4]** (ainda não existe, a
> construir). Nenhuma implementação é feita neste documento.

---

## 1. Botões

### 1.1 Hierarquia e prioridade visual

| Ordem | Variante | Prioridade | Quando usar |
|---|---|---|---|
| 1 | **Primary** | Máxima — no máximo 1 por tela/bloco | A ação principal do contexto (Salvar, Criar, Confirmar). Laranja de marca. |
| 2 | **Success** | Alta, contextual | Confirmação positiva de uma ação que não é "a" ação principal da tela, mas é uma conclusão (Aprovar, Concluir). |
| 2 | **Danger** | Alta, contextual | Ação destrutiva/irreversível (Excluir, Cancelar cadastro). Mesma prioridade de Success — nunca as duas competem na mesma tela. |
| 3 | **Secondary** | Média | Ação alternativa comum (Cancelar, Fechar, Voltar) ao lado de um Primary/Success/Danger. |
| 4 | **Outline** | Média-baixa | Ação secundária que ainda quer indicar afinidade com a marca no hover (ex.: "Ver detalhes" ao lado de um CTA laranja). |
| 5 | **Ghost** | Mínima | Ação terciária, botão de ícone, ação dentro de um cluster já denso (ex.: item de toolbar, ação inline em linha de tabela). |
| — | **Disabled** | — | Não é uma variante própria — é um **estado** aplicável a qualquer uma das cinco acima (seção 1.4). |

Regra fixa: **nunca dois Primary no mesmo bloco.** Success e Danger só
aparecem quando são, elas mesmas, a ação de maior prioridade daquele
bloco (ex.: rodapé de um `ConfirmDialog` de exclusão usa Danger como
ação primária daquele contexto, não como um "extra" ao lado de um
Primary laranja).

### 1.2 Cores por variante

| Variante | Classe base | Estado |
|---|---|---|
| Primary | `bg-primary text-white` (`colorScheme="brand"`) / `bg-zinc-900 text-white` (`colorScheme="neutral"`, default) | **[existente]** — único ramo que consulta `colorScheme` (regra arquitetural registrada em `ui/Button.tsx`) |
| Secondary | `border border-zinc-200 bg-white text-zinc-700` | **[existente]** — aparência fixa, não lê `colorScheme` |
| Outline | `border border-zinc-200 bg-white text-zinc-900` (hover tinge de marca) | **[implementado — Fase 4B.1, sem consumidor ainda]**. Reaproveita a combinação visual que antes só existia como `colorScheme="brand"` + `variant="secondary"` (nunca usada por nenhum consumidor real) — agora `variant="outline"` própria e fixa |
| Ghost | `bg-transparent text-zinc-600` | **[implementado — Fase 4B.1, sem consumidor ainda]**. Generaliza o padrão já usado ad hoc em `Header.tsx` (botão do tooltip) e itens de menu (`UserMenu`/`QuickCreateMenu`) |
| Danger | `border border-red-200 bg-white text-red-600` (inline) | **[implementado — Fase 4B.1, sem consumidor ainda]** — só a intensidade bordada por ora (a única já validada em produção, como *override* de className em `EntityActions`, `tone="danger"`); a intensidade preenchida (`bg-red-600 text-white`, standalone) fica para quando existir um consumidor real (ex. `ConfirmDialog`) |
| Success | `bg-emerald-600 text-white` | **[implementado — Fase 4B.1, sem consumidor ainda]**. Cor formalizada em `docs/design-system/13-tokens-visuais.md`, seção "Vocabulário semântico de ação (Button)" — mesma família de cor do tom `green` de `StatusPill` (emerald), não uma escolha independente |

Danger tem duas intensidades porque já existe um precedente real com duas
necessidades distintas: a ação "Excluir" hoje vive ao lado de uma ação
neutra no rodapé do `EntityPeek` (inline, bordada — não deve competir
visualmente com o Primary da tela) e uma futura confirmação dedicada
(`ConfirmDialog`, ainda não construído) precisa de um Danger que **é** a
ação principal daquele diálogo (preenchido, mais forte). A regra de
escolha: bordada quando Danger é secundária no bloco; preenchida quando
Danger é a única/principal ação do bloco.

### 1.3 Hover / Active / Focus

| Estado | Regra | Justificativa |
|---|---|---|
| **Hover** | Primary: `hover:bg-primary-hover`. Secondary: `hover:bg-zinc-50`. Outline: `hover:border-primary hover:text-primary`. Ghost: `hover:bg-zinc-100 hover:text-zinc-900`. Danger: `hover:bg-red-50` (bordada) / `hover:bg-red-700` (preenchida). Success: `hover:bg-emerald-700`. | Cada variante reaproveita o token de cor já existente para seu próprio hover — nenhuma cor nova é criada. |
| **Active** (pressionado) | `active:scale-[0.98]` universal, em todas as variantes, além da cor de hover já aplicada. | Microinteração única, rápida, consistente — evita seis regras de "active" diferentes. |
| **Focus** | `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2` — **sempre neutro (zinc-900), nunca laranja**, em qualquer variante. | Foco é acessibilidade, não branding. Manter neutro evita "poluir com cor" (mesmo princípio já aplicado aos inputs em `13-tokens-visuais.md`) e garante contraste consistente independentemente da cor de fundo do botão. |

### 1.4 Disabled

Estado, não variante — aplicável a qualquer uma das cinco variantes:
`disabled:cursor-not-allowed disabled:opacity-50` **[existente]**, já é a
base de `ui/Button.tsx` hoje. Nenhuma variante fica "cinza genérica" —
mantém sua cor de base com opacidade reduzida, para que o usuário ainda
reconheça qual ação estava ali.

### 1.5 Loading

**[novo — Fase 4]** `Button` ganha uma prop `loading?: boolean` nativa,
generalizando o padrão já usado manualmente em `EntityActions.tsx`
(`action.loading` → `<Loader2 className="h-3.5 w-3.5 animate-spin" />`
antes do rótulo, botão desabilitado). Regras:

- Ícone de carregamento sempre antes do texto, nunca substituindo-o
  (evita o botão "pular" de largura de forma abrupta).
- `loading` implica `disabled` (não é possível clicar duas vezes).
- A cor da variante é preservada — o spinner herda `currentColor`, não
  fica cinza sobre um botão laranja/vermelho/verde.

---

## 2. Badges

Formaliza o vocabulário que já existe em `ui/StatusPill.tsx` — nenhuma
cor nova, apenas nomes oficiais alinhados ao pedido:

| Nome oficial | Tom (`StatusPill.tone`) | Classes **[existente]** |
|---|---|---|
| Neutral | `neutral` | `bg-zinc-100 text-zinc-700 ring-zinc-200` |
| Info | `blue` | `bg-blue-50 text-blue-700 ring-blue-100` |
| Success | `green` | `bg-emerald-50 text-emerald-700 ring-emerald-100` |
| Warning | `amber` | `bg-amber-50 text-amber-700 ring-amber-100` |
| Danger | `red` | `bg-red-50 text-red-700 ring-red-100` |

Regras:

- `StatusPill` é o **único** componente de badge semântico do sistema.
  `ui/Badge.tsx` (hoje só `bg-zinc-100 text-zinc-700`, sem tom) continua
  existindo, mas só para rótulos **não semânticos** (contadores,
  categorias, "Perfil") — nunca para representar um estado real.
- `cadastros/CadastroStatusBadge.tsx`, hoje reaproveitado indevidamente
  para "Categoria" (Fornecedores) e "Perfil" (Usuários), migra para
  `Badge` genérico nesses dois usos e para `StatusPill` só quando o valor
  for de fato um estado (Ativo/Inativo/Pendente) — **[novo — Fase 4]**.
- `dot` (ponto colorido antes do texto) continua opcional, default
  `true`, igual a hoje.
- Densidade `compact` (já existente, hoje só em Clientes) generaliza para
  qualquer contexto de tabela densa — não é uma mudança de cor, só de
  padding/peso de fonte.

---

## 3. Cards

| Tipo | Componente | Borda | Radius | Sombra | Padding | Header | Footer |
|---|---|---|---|---|---|---|---|
| **Informativo** | `ui/Card.tsx` | `border border-zinc-100` **[novo — Fase 4, hoje sem borda]** | `rounded-3xl` **[existente]** | `shadow-sm` **[existente]** | `p-6` **[existente]** | nenhum (conteúdo livre) | nenhum |
| **KPI** | `ui/MetricCard.tsx` | `border border-zinc-100`, `hover:border-zinc-200` | `rounded-3xl` | `shadow-sm`, `hover:shadow-md` (+ `hover:-translate-y-0.5`) | `p-4` | eyebrow (`text-xs uppercase tracking-[0.14em]`) + valor (`text-2xl font-bold`) + ícone opcional em chip `rounded-2xl` tonal | `border-t border-zinc-100 pt-3` quando presente |
| **Lista** | padrão `ui/RankingCard.tsx` | `border border-zinc-100` | `rounded-3xl` | `shadow-sm` | `p-4`–`p-5` | título + descrição opcional | nenhum (lista de itens é o corpo) |
| **Formulário** | `entity/EntitySection.tsx` dentro de `EntityDrawer` (modo edit) | nenhuma própria — herda o chrome do Drawer | nenhum próprio | nenhuma própria | `px-4 py-3` (padrão já fixado em `entity-component-api.md`, seção 15) | título opcional + descrição opcional + ícone opcional | nenhum |
| **Dashboard** | `cadastros/CadastroIndicators.tsx` (`density="compact"`), via `dashboard/DashboardKPIs.tsx` | `border border-zinc-100` | `rounded-3xl` | `shadow-sm` | `min-h-[32px] px-2.5 py-1` (compact) | rótulo (`text-xs font-medium`) + descrição opcional | nenhum |
| **Entity** | `entity/EntityDrawer.tsx` + `EntityHeader`/`EntityPeek`/`EntityActions` | `border-zinc-200` (painel) | `sm:rounded-l-3xl` (peek) / `rounded-none sm:rounded-3xl` (edit) | `shadow-xl` (peek) / `shadow-2xl` (edit) | corpo `px-3 py-2.5` | `border-b border-zinc-100` (título + status + fechar/voltar) | `border-t border-zinc-100 px-3 py-2.5` (ações) |
| **Widget** | `dashboard/DashboardWidget.tsx` | `border border-zinc-100` | `rounded-3xl` | `shadow-sm` | `p-4` | título + descrição opcional + ação opcional (via `SectionHeader`) | nenhum — conteúdo próprio (gráfico/lista/agenda) |

> **Correção (pós-aprovação da Fase 4A):** a afirmação original desta
> seção — de que "Dashboard" e "KPI" seriam o mesmo componente
> (`MetricCard`) — **está errada** e foi corrigida acima. Por leitura
> direta de `dashboard/DashboardKPIs.tsx`, os KPIs da rota `/` usam
> `cadastros/CadastroIndicators.tsx` (`density="compact"`), não
> `MetricCard`. Hoje **coexistem duas famílias de card de indicador
> diferentes e não unificadas**:
>
> - `CadastroIndicators` — Dashboard (via `DashboardKPIs`) + as 7 telas de
>   cadastro (Clientes, Fornecedores, Grupos de Clientes, Equipes,
>   Usuários, Agências, Workflows).
> - `MetricCard` — Projetos, Demandas, Tráfego (via `ProjetosStats`,
>   `DemandasStats`, `TrafegoResumoCards`, `TempoOperacionalCard`).
>
> `DashboardWidget` ("Widget", acima) é uma terceira coisa — não é um
> indicador numérico, é a casca de seção rica (gráfico/agenda/atividade
> recente) — e não faz parte dessa duplicação.
>
> Esta é uma duplicação estrutural real, mas sua unificação **não é
> decidida nem implementada por este documento nem pela Fase 4** — já
> está registrada como decisão própria, de risco alto, em
> `12-plano-de-migracao.md` (proposta de consolidação em `MetricStrip`).
> Fica apenas registrada aqui para a referência oficial não afirmar algo
> que o código não confirma.

---

## 4. Empty States

Unifica `ui/EmptyState.tsx` (hoje sem ícone/ação) e
`ui/EmptyStateIllustration.tsx` (hoje já tem ícone + título + descrição +
1 ação) em um único padrão, com CTA secundário novo:

| Elemento | Regra |
|---|---|
| Ilustração | Chip `h-12 w-12 rounded-3xl` (ou `h-10 w-10 rounded-2xl` em `size="compact"`), `bg-white ring-1 ring-zinc-100 shadow-sm`, ícone `lucide-react` `h-5 w-5 text-zinc-500` **[existente]**. Nunca emoji — corrige a inconsistência hoje presente em `AgendaList`/`agenda/AgendaView` ("📇 Nenhum contato encontrado"). |
| Título | `text-base font-semibold text-zinc-950` (default) / `text-sm` (compact) **[existente]** |
| Descrição | `text-sm text-zinc-500` (default) / `text-xs` (compact), `max-w-md` **[existente]** |
| CTA principal | `Button variant="primary"` (laranja) — ação que resolve o vazio (ex.: "Criar primeiro Cliente") **[existente, já suportado via prop `action`]** |
| CTA secundário | `Button variant="ghost"` — ação alternativa de menor peso (ex.: "Limpar filtro", "Saiba mais") **[novo — Fase 4: `EmptyStateIllustration` ganha prop `secondaryAction?`]** |

`ui/EmptyState.tsx` (variante sem ilustração) passa a ser reservado para
contextos onde um ícone seria ruído (ex.: dentro de uma seção pequena de
formulário, como "Contatos" vazio) — continua sem ação por padrão, mas
pode receber `action`/`secondaryAction` pela mesma prop opcional, sem
quebrar os consumidores atuais.

---

## 5. Estados

| Estado | Regra padrão | Base |
|---|---|---|
| **Hover** | Linha de tabela/lista: `hover:bg-zinc-50`. Card clicável: `hover:shadow-md` (+ `hover:-translate-y-0.5` quando já suportado). Botão: ver seção 1.3. | `cadastroTableRowClassName`, `MetricCard.tsx` **[existente]** |
| **Selected** | `bg-primary-soft` + barra de destaque `bg-primary` à esquerda (`rounded-r-full`, `h-4 w-1`). | Generaliza o padrão já usado no item ativo da `Sidebar` **[existente ali; novo para tabelas/listas — Fase 4]** |
| **Active** (navegação, não pressionar botão) | Mesmo tratamento de Selected. | idem |
| **Disabled** | `opacity-50 cursor-not-allowed`. Em campo de formulário, adicionalmente `bg-zinc-50 text-zinc-400`. | **[existente]** em Button; **[novo — Fase 4]** formalizar em Input/Select/Textarea |
| **Loading** (ação) | Spinner inline (`Loader2 animate-spin`) antes do rótulo — ver seção 1.5. | **[existente]** em `EntityActions`, generaliza para `Button` |
| **Skeleton** (conteúdo) | Bloco `animate-pulse rounded-3xl border border-zinc-100 bg-zinc-100/60`, do mesmo tamanho/forma do conteúdo real. | Hoje só em `TrafegoView` (`h-32`, código inatingível) — formaliza a classe para reuso onde houver carregamento assíncrono real |
| **Error** | Reaproveita `EmptyStateIllustration` (`size="compact"`) com `title` do erro, `description` da mensagem, e `action` = `Button variant="primary" onClick={retry}` com texto "Tentar novamente". | **[existente]** — é exatamente o padrão já implementado em `UsuariosView.tsx` (`case "error"`); esta seção só o formaliza como o padrão oficial para qualquer outra tela que vier a precisar |

---

## 6. Ícones

Biblioteca única: **lucide-react** (nenhuma outra, nunca SVG customizado
solto) — regra já vigente, formalizada aqui:

| Contexto | Tamanho | Peso |
|---|---|---|
| Padrão (a maioria dos usos: botão, campo, linha de tabela) | `h-4 w-4` | `strokeWidth={2}` |
| Compacto (chevron, indicador pequeno, dentro de badge) | `h-3.5 w-3.5` | `strokeWidth={2}` |
| Grande (ação de destaque, fechar painel, ilustração de Empty State) | `h-5 w-5` | `strokeWidth={2}` |

- **Espaçamento**: `gap-1.5` entre ícone e texto quando ambos cabem numa
  linha compacta (badge, botão pequeno); `gap-2` no padrão geral.
- **Alinhamento**: sempre dentro de um contêiner `inline-flex items-center
  justify-center` (nunca `<img>`/`<svg>` solto sem wrapper de alinhamento).
- **Decorativo** (ícone ao lado de texto que já explica a ação):
  `aria-hidden="true"`, sem `aria-label` próprio.
- **Funcional** (botão só-ícone, sem texto visível): o elemento
  interativo (`<button>`) recebe `aria-label`; o ícone dentro dele
  continua `aria-hidden="true"`. Nunca depender só do `title=` nativo do
  HTML (motivo: inconsistente entre navegadores e sem estilo — ver
  `ui/Tooltip.tsx`, já unificado na Fase 3).

---

## 7. Resumo do que a Fase 4 constrói

Para rastreabilidade, tudo marcado **[novo — Fase 4]** acima, consolidado:

1. `Button`: variantes `outline`, `ghost`, `danger` (própria, não mais
   override de className), `success`; prop `loading`.
2. `EmptyStateIllustration`: prop `secondaryAction`.
3. `Card`: adicionar `border border-zinc-100`.
4. `CadastroStatusBadge`: parar de ser usado para "Categoria"/"Perfil";
   esses dois casos passam a `Badge` genérico.
5. Estado "Selected"/"Active" de linha/item (fora da Sidebar, que já o
   tem): aplicar `bg-primary-soft` + barra onde fizer sentido (tabelas
   com seleção, se/quando existirem).
6. Classe de skeleton formalizada (`animate-pulse rounded-3xl border
   border-zinc-100 bg-zinc-100/60`), para reuso onde houver carregamento
   assíncrono real.
7. `Input`/`Select`/`Textarea`: estado `disabled` visual explícito
   (`bg-zinc-50 text-zinc-400`), hoje ausente.

Nada além disso é implementado nesta etapa. Aguardando aprovação para
iniciar a Fase 4 com base neste documento.

---

## 8. Princípio arquitetural — onde vive a regra de mapeamento de estado

> Toda regra de mapeamento de estado, como status → tone, status → ícone
> ou status → descrição, pertence ao domínio da entidade. Essa lógica não
> deve ser colocada em componentes compartilhados de `ui/` nem em uma
> biblioteca genérica de status.

Registrado após a análise de deduplicação da Fase 4A: existiam, ao mesmo
tempo, `clienteStatusTone` (Cliente), `usuarioStatusTone` (Usuário) e
`statusTone` (Tipos de Tarefa, SLA, Prioridades) — mesma forma
(`status => tone`), mas domínios de valor diferentes (`"Ativo"`
capitalizado, `"ativo"` minúsculo vindo do enum real do backend,
`"Suspenso"`/`"bloqueado"` sem equivalência entre si). Avaliou-se criar um
utilitário genérico (`src/lib/status.ts`) e a conclusão foi **não
centralizar**:

- Centralizar exigiria reintroduzir heurística de texto (contradiz a
  seção 2 deste documento — "tom explícito por enum, nunca heurística de
  texto") **ou** importar os tipos de cada domínio (`ClienteStatus`,
  `Usuario["status"]` etc.) dentro de `src/lib/`, rompendo a separação já
  estabelecida em `entity-component-api.md`, seção 1: componentes/utils
  compartilhados nunca conhecem nomes de entidades de negócio.
- A única duplicação real encontrada — `clienteStatusTone` repetida
  identicamente em `ClientesView.tsx` e `GrupoClienteFormSections.tsx`,
  para o mesmo tipo `ClienteStatus` — foi corrigida por extração **dentro
  do próprio domínio**: a função agora vive em `types/cliente.ts`, ao
  lado do tipo `ClienteStatus` que ela mapeia, e é importada pelos dois
  consumidores.
- `usuarioStatusTone` (`usuarios/UsuariosView.tsx`) e as `statusTone` de
  Tipos de Tarefa/SLA/Prioridades permanecem locais a cada tela — não são
  duplicação, são regras diferentes que só parecem iguais por serem
  pequenas.

Esta decisão é definitiva para o projeto, não apenas para a Fase 4:
qualquer novo domínio (Departamentos, Cargos, Squads, ou outro) que
precisar mapear estado para aparência define sua própria função, perto do
seu próprio tipo — nunca em um utilitário genérico.
