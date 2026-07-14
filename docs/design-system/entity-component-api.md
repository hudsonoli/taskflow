# TaskFloww V2 — Entity Component API Specification

> **Contrato oficial da API pública dos componentes `entity/`.**
> Este documento não contém implementação — apenas assinaturas, contratos, fluxos e regras. Nenhum arquivo `.tsx` foi criado ou alterado para produzi-lo.
> Baseia-se em `taskfloww-design-system.md` (inventário atual), `entity-ux-pattern.md` (decisão de UX) e `entity-architecture-plan.md` (arquitetura e roadmap) — este documento é o próximo nível de detalhe: a API que a implementação deverá seguir ao pé da letra.
> Uma vez aprovado, **este é o contrato**. Mudanças de API depois da aprovação devem ser tratadas como uma revisão deste documento, não como ajuste ad hoc durante a implementação.

---

## Sumário

1. [Convenções deste documento](#1-convenções-deste-documento)
2. [EntityDrawer](#2-entitydrawer)
3. [EntityPeek](#3-entitypeek)
4. [EntityHeader](#4-entityheader)
5. [EntityForm](#5-entityform)
6. [EntityFormNav](#6-entityformnav)
7. [EntitySection](#7-entitysection)
8. [EntityActions](#8-entityactions)
9. [EntityHistory](#9-entityhistory)
10. [EntityRelations](#10-entityrelations)
11. [Estados — visão consolidada](#11-estados--visão-consolidada)
12. [Eventos — visão consolidada](#12-eventos--visão-consolidada)
13. [Fluxos completos](#13-fluxos-completos)
14. [Tabela de responsabilidades](#14-tabela-de-responsabilidades)
15. [Padrões oficiais](#15-padrões-oficiais)
16. [Extensibilidade](#16-extensibilidade)
17. [Compatibilidade e depreciação](#17-compatibilidade-e-depreciação)
18. [Guia Administrativa — autorização e dados sensíveis](#18-guia-administrativa--autorização-e-dados-sensíveis)

---

## 1. Convenções deste documento

- Blocos `ts` descrevem **tipos e assinaturas**, como documentação de contrato — não são trechos de implementação a copiar.
- `EntityRef` é o tipo compartilhado que identifica qualquer entidade do sistema:
  ```ts
  type EntityRef = {
    type: string;   // ex.: "cliente" | "projeto" | "demanda" — string, não enum fechado,
                     // para não acoplar o pacote entity/ à lista de entidades do domínio
    id: string;
  };
  ```
- Nenhum componente deste documento importa de `src/lib/*-mock.ts`, `src/types/<entidade>.ts`, nem conhece nomes de entidades de negócio (regra herdada de `entity-architecture-plan.md`, seção 3 de `12-plano-de-migracao.md`).
- "Página" = a *View* de domínio (ex. uma futura `ClientesView` v2) — é sempre quem detém estado, dados, callbacks de mutação e decisões de permissão. Os componentes `entity/` nunca detêm esse tipo de estado.

---

## 2. EntityDrawer

### Responsabilidade

Overlay único de detalhe/edição de uma entidade. Dono de: montagem/desmontagem, backdrop, largura por modo, transição de largura, captura de foco, tratamento de `Escape`, bloqueio de scroll do `body`, e do ponto de decisão "fechar direto ou pedir confirmação" quando há alterações não salvas.

### Props

```ts
type EntityDrawerMode = "peek" | "edit";
type EntityDrawerPreset = "standard"; // único valor hoje — ver nota abaixo

type EntityDrawerProps = {
  open: boolean;
  mode: EntityDrawerMode;
  preset?: EntityDrawerPreset;          // default "standard"
  isDirty?: boolean;                     // default false
  isSaving?: boolean;                    // default false
  loading?: boolean;                     // default false — ver EntitySkeleton, seção 15
  canGoBack?: boolean;                   // default false — mostra "← Voltar" no EntityHeader
  onClose: () => void;
  onRequestModeChange: (nextMode: EntityDrawerMode) => void;
  onRequestClose?: () => void;           // chamado no lugar de onClose quando isDirty === true;
                                          // se omitido, EntityDrawer chama onClose diretamente
                                          // (comportamento idêntico a isDirty sempre false)
  onBack?: () => void;
  header: ReactNode;                     // tipicamente <EntityHeader ... />
  children: ReactNode;                   // corpo: <EntityPeek /> OU EntityFormNav+EntitySection
  footer?: ReactNode;                    // tipicamente <EntityActions ... />
};
```

**Nota sobre `preset`**: existe desde já na API (não é adicionado depois) porque a Fase 6 de `entity-architecture-plan.md` cogita entidades que "graduam" para larguras diferentes (ex. tela cheia para Projetos/Demandas). Hoje só `"standard"` existe e resolve peek/edit conforme a tabela da seção 15. Adicionar um novo preset no futuro (ex. `"workspace"`) é uma extensão aditiva da união de tipos, não uma mudança de contrato existente.

**Nota sobre `mode`/`onRequestModeChange` vs. um `onExpand`/`onCollapse` dedicado**: a API usa um único par genérico (`mode` + `onRequestModeChange`) em vez de callbacks separados por direção. Motivo: peek→edit e edit→peek são, do ponto de vista do `EntityDrawer`, a mesma operação (troca de modo com possível interceptação por `isDirty`) — modelar como dois eventos distintos obrigaria duplicar a lógica de interceptação em dois lugares. Quem consome pode nomear seus próprios handlers `handleExpand`/`handleCollapse` internamente, isso não faz parte da API pública.

### Eventos

| Evento | Assinatura | Quando dispara |
|---|---|---|
| `onClose` | `() => void` | Escape, clique no overlay, botão fechar do `EntityHeader` — **somente quando `isDirty` é `false` ou `onRequestClose` não foi fornecido** |
| `onRequestClose` | `() => void` | Mesmos gatilhos de `onClose`, mas quando `isDirty === true` — a página decide se abre `ConfirmDialog` |
| `onRequestModeChange` | `(next: EntityDrawerMode) => void` | Clique em "Editar" (`EntityActions[peek]`) ou "Cancelar"/"Salvar" bem-sucedido (`EntityActions[edit]`) |
| `onBack` | `() => void` | Clique no botão "← Voltar" do `EntityHeader`, só renderizado quando `canGoBack` é `true` |

`EntityDrawer` **nunca** dispara `onClose` sozinho ao trocar de modo — troca de modo e fechamento são eventos independentes, mesmo que na prática uma página decida fechar o drawer logo após salvar (isso é decisão da página, não comportamento embutido).

### Estados (internos ao componente, não expostos como props)

- Estado de transição de largura (`"idle" | "transitioning"`) — controla se a `transition` CSS está em andamento, usado apenas para não disparar dupla animação em cliques rápidos repetidos. Não é acessível de fora.

Todo o resto do estado (`mode`, `isDirty`, `activeSection` etc.) é **recebido via prop e/ou Context**, nunca criado internamente — reforça a regra "sem regra de negócio em componente visual".

### Slots

| Slot | Prop | Conteúdo esperado |
|---|---|---|
| Cabeçalho | `header` | `<EntityHeader />` |
| Corpo | `children` | `<EntityPeek />` (mode `peek`) **ou** `<EntityFormNav /> + <EntitySection />` (mode `edit`) |
| Rodapé | `footer` | `<EntityActions />` |

Não existem slots nomeados adicionais (`beforeHeader`, `afterFooter` etc.) — mantendo o contrato enxuto conforme o critério "não criar props genéricas demais" de `12-plano-de-migracao.md`, seção 12.

### Context

`EntityDrawer` provê um Context interno, consumido pelos demais componentes de `entity/` para evitar prop drilling de `mode`/`activeSection`/estado de navegação através de várias camadas:

```ts
type EntityDrawerContextValue = {
  mode: EntityDrawerMode;
  isDirty: boolean;
  isSaving: boolean;
  canGoBack: boolean;
  requestModeChange: (next: EntityDrawerMode) => void;
  requestClose: () => void;
  back: () => void;
};
```

Regras de uso do Context:
- É **interno ao pacote `entity/`** — não é exportado para consumo por *Views* de domínio. A página continua se comunicando com `EntityDrawer` via props, nunca lendo o Context diretamente.
- Serve só para os componentes-filhos (`EntityHeader`, `EntityFormNav`, `EntityActions`) evitarem repetir `mode`/`isDirty` como prop em cada um — mas cada um deles **também aceita as mesmas informações via prop explícita**, que tem precedência sobre o Context, para permitir uso isolado na vitrine `/design-system` sem precisar montar um `EntityDrawer` completo ao redor.

### Responsabilidades que NÃO pertencem ao Drawer

- Não sabe o que é a entidade (Cliente, Projeto...).
- Não faz fetch de dados nem decide como buscar o registro.
- Não decide o que salvar, nem chama nenhuma função de persistência — só relata a **intenção** de salvar através de `EntityActions` (ver seção 8).
- Não decide permissões (`canEdit`/`canDelete` são resolvidos pela página, que simplesmente omite a ação de `EntityActions` quando não permitida).
- Não mantém `navigationStack` — mantém só o "sabe voltar ou não" (`canGoBack`) e "dispara a intenção de voltar" (`onBack`); a pilha em si é estado da página (ver seção 11).
- Não sabe nada de validação de formulário — recebe já pronto se o botão de salvar deve estar habilitado (via `EntityActions.primaryAction.disabled`).

### Fluxo de abertura

1. Página muda `open` para `true` e define `mode` (tipicamente `"peek"`, exceto no fluxo de criação, que abre direto em `"edit"` — ver seção 13).
2. `EntityDrawer` monta o overlay (backdrop com `bg-black/25 backdrop-blur-[2px]`, conforme já validado nas fases anteriores) e o card na largura correspondente ao `mode` atual.
3. Foco move automaticamente para o primeiro elemento focável do card (mesmo comportamento hoje já implementado em `EntitySidePanel`).
4. Scroll do `body` é bloqueado enquanto `open === true`.

### Fluxo de fechamento

1. Gatilho: `Escape`, clique no overlay, ou botão fechar do `EntityHeader`.
2. Se `isDirty === false` (ou `onRequestClose` não fornecido): `EntityDrawer` chama `onClose` diretamente.
3. Se `isDirty === true` e `onRequestClose` fornecido: `EntityDrawer` chama `onRequestClose` **em vez de** `onClose` — a página decide se abre um `ConfirmDialog` ("Descartar alterações?") e só chama `onClose` de fato depois da confirmação do usuário.
4. Ao fechar de fato (`open` volta a `false`): foco retorna ao elemento que originou a abertura (mesmo comportamento hoje já implementado em `EntitySidePanel`); scroll do `body` é destravado.

### Fluxo de expansão (peek → edit)

1. Usuário aciona "Editar" em `EntityActions[peek]`.
2. Página decide (ex.: sempre aceitar) e chama a atualização de `mode` para `"edit"` — o `EntityDrawer` recebe a nova prop `mode="edit"` e:
   - anima a largura do card do valor de peek para o valor de edit (mesma instância, sem desmontar/remontar o overlay nem o backdrop);
   - troca o `children` renderizado (a página já passa o conteúdo correto para cada modo);
   - mantém o foco dentro do card durante a transição.
3. Não há, em nenhum momento do passo 2, um segundo elemento com `role="dialog"` montado — só a largura e o conteúdo interno mudam.

O caminho inverso (edit → peek, ao salvar com sucesso ou cancelar) segue o mesmo mecanismo, na direção oposta.

### Fluxo de navegação (entre entidades relacionadas)

`EntityDrawer` não implementa navegação — só expõe `canGoBack`/`onBack`. Quem implementa a troca de conteúdo (Cliente → Projeto) é a página, seguindo o mecanismo de pilha descrito em `entity-architecture-plan.md`, seção 5:

1. Página mantém `currentEntity: EntityRef` e `navigationStack: EntityRef[]`.
2. Ao navegar para uma relação, a página empilha a entidade atual e troca `currentEntity` — e, na prática, isso significa apenas trocar as props `header`/`children` passadas ao **mesmo** `EntityDrawer` já aberto (o componente nunca desmonta).
3. Página passa `canGoBack={navigationStack.length > 0}`.
4. Ao clicar em "← Voltar" (`onBack`), a página desempilha e troca `currentEntity` de volta.

### Responsividade

| Breakpoint | Comportamento |
|---|---|
| `< 640px` (mobile) | Largura `100vw` em ambos os modos — a diferença peek/edit deixa de ser de largura e passa a ser só de conteúdo interno (ver seção 15) |
| `≥ 640px` até `< 1024px` (tablet/notebook estreito) | Larguras "notebook" da tabela da seção 15 |
| `≥ 1024px` (desktop) | Larguras "desktop" |
| Telas muito largas (`≥ 2560px` aprox.) | Larguras "ultrawide" — sempre com teto absoluto, nunca crescem além do valor fixado |

A resolução de largura por breakpoint é **inteiramente CSS** (classes Tailwind responsivas), nunca uma bifurcação de componente por dispositivo — mesmo princípio já confirmado como padrão do projeto em `taskfloww-design-system.md`, seção 13.

---

## 3. EntityPeek

### Responsabilidade

Corpo do `EntityDrawer` em modo `"peek"`. Composição declarativa e **somente leitura** de: resumo de campos-chave, tags, responsáveis, contadores de relação, histórico resumido.

### Props

```ts
type EntityPeekProps = {
  summary: { label: string; value: ReactNode }[];
  tags?: ReactNode;          // slot livre — ver seção 16, hoje tipicamente omitido
  relations?: ReactNode;     // slot livre — tipicamente <EntityRelations mode="compact" />
  history?: ReactNode;       // slot livre — tipicamente <EntityHistory variant="compact" />
};
```

### Quais informações exibe

- `summary`: lista de pares label/valor, renderizados internamente via `EntityFieldRow` (já existente em `ui/EntityFieldRow.tsx`), em grade responsiva (1 coluna mobile, 2 colunas a partir de `sm`).
- `tags`, `relations`, `history`: seções opcionais, renderizadas na ordem em que aparecem nas props — se omitidas, simplesmente não aparecem (sem placeholder "em branco").

### Quais ações permite

Nenhuma ação de mutação. `EntityPeek` **não recebe `footer`/ações** — a ação "Editar" pertence ao `EntityActions` que o `EntityDrawer` renderiza como `footer`, fora do `EntityPeek` em si. Isso é deliberado: mesmo que tecnicamente fosse possível colocar um botão dentro do `summary`, a API não abre esse precedente.

### O que explicitamente NÃO pode fazer

- Não recebe nenhuma prop `onChange` de qualquer campo — contrato de tipos não permite edição inline, por construção (não é apenas uma convenção visual a ser respeitada por quem implementa).
- Não faz fetch nem sabe de onde vieram os dados de `summary`.
- Não decide quais campos aparecem por regra de permissão — se um campo não deve aparecer para o perfil atual, a página simplesmente não o inclui no array `summary`.

---

## 4. EntityHeader

### Props

```ts
type EntityHeaderProps = {
  title: string;
  description?: string;
  avatar?: ReactNode;             // tipicamente <EntityAvatar />
  statusBadge?: ReactNode;        // tipicamente <StatusPill />
  onClose: () => void;
  canGoBack?: boolean;            // default false
  onBack?: () => void;
  quickActions?: ReactNode;       // ver nota "Ações rápidas" abaixo
};
```

- **Título**: `title`, sempre `text-lg font-semibold` (valor já fixado nas fases anteriores desta sessão como padrão de título de drawer/modal — não regride para `text-base`).
- **Subtítulo**: `description`, opcional — tipicamente código interno ou uma frase de contexto (ex.: "Código interno: #1001").
- **Status**: `statusBadge`, opcional, renderizado ao lado do título (não abaixo) quando presente.
- **Avatar**: `avatar`, opcional, renderizado à esquerda do bloco título/descrição.
- **Breadcrumb interno**: não existe como conceito à parte — o par `canGoBack`/`onBack` já cobre o único caso de navegação interna previsto (voltar uma entidade na pilha). Se no futuro for necessário mostrar a pilha inteira (ex.: "Cliente > Projeto > Tarefa" como trilha clicável dentro do header), isso é uma extensão aditiva de props (`breadcrumbItems?: EntityRef[]`), não parte do contrato inicial — não construir antecipadamente.
- **Botões**: fechar (sempre presente, `onClose`) e voltar (condicional, `canGoBack`+`onBack`).
- **Ações rápidas** (`quickActions`): slot livre para ações de alta frequência específicas de uma entidade (ex.: "ligar" em um contato) que não fazem sentido dentro de `EntityActions` (que é sobre o ciclo de vida do registro, não sobre ações de contato). Uso opcional, não obrigatório.

---

## 5. EntityForm

### Responsabilidade

Container puro de layout de campos: grid de 12 colunas com gap padronizado. Nada além disso.

### Props

```ts
type EntityFormProps = {
  children: ReactNode;
};
```

Não existe prop de colunas, densidade ou variante — a grade de 12 colunas **é** o único padrão, sem parametrização que permita voltar a 2 colunas (decisão já registrada em `entity-architecture-plan.md`, seção 4, para impedir reincidência do problema original).

### Como recebe conteúdo

Cada campo é posicionado por quem o declara, envolvendo o `Input`/`Select`/`Textarea` num wrapper de span:

```tsx
<EntityForm>
  <div className="col-span-12 md:col-span-4"><Input label="Código Interno" ... /></div>
  <div className="col-span-12 md:col-span-8"><Input label="CNPJ/CPF" ... /></div>
  {/* ... */}
</EntityForm>
```

Esse wrapper de span **não é um componente `entity/`** — é uma `<div>` com classe utilitária, propositalmente não abstraído (mesma decisão já registrada em `entity-architecture-plan.md`, seção 4, "não existe `EntityFormField` de posicionamento").

### Como organiza seções

`EntityForm` não organiza seções — cada `EntitySection` (seção 7) contém um `EntityForm` próprio. A relação é: `EntityFormNav` decide qual `EntitySection` está visível; dentro da seção visível, um `EntityForm` organiza os campos daquela seção.

### Como integra com validação

`EntityForm` **não tem nenhuma integração com validação embutida**. Erros de campo continuam sendo resolvidos exatamente como hoje: cada `Input`/`Select` já aceita (via `12-plano-de-migracao.md`, melhoria de média prioridade item 10, ainda não implementada) uma prop de erro própria, controlada pela página.

O que `EntityForm`/`EntitySection` expõem para refletir validação **agregada** por seção (não por campo) é um contrato mínimo, consumido por `EntityFormNav`:

```ts
type EntitySectionStatus = "default" | "warning" | "error";
type EntitySectionsStatusMap = Record<string /* id da seção */, EntitySectionStatus>;
```

A página computa esse mapa (com a lógica de validação que já usa hoje — `canSave`/checagens de campo obrigatório, como em `NovoClienteModal.tsx` atual) e passa para `EntityFormNav` via prop `sectionsStatus` (seção 6). `EntityForm` em si nunca vê esse mapa — é responsabilidade só do par `EntityFormNav`+página.

### Como integra com React Hook Form (ou equivalente)

**Recomendação explícita: não adotar React Hook Form (ou qualquer lib de formulário) nesta fase.**

Justificativa:
1. O projeto não tem essa dependência instalada hoje (`package.json` não lista `react-hook-form` nem equivalente) — adicioná-la é uma decisão de nova dependência, categoricamente diferente de "especificar a API de um componente visual", e exigiria aprovação própria, fora do escopo deste documento.
2. O padrão atual de todo o formulário do projeto (`ClienteFormSections.tsx` e os `*FormSections.tsx` das demais entidades) é `useState` local + `onChange` manual por campo — exatamente o padrão que `frontend/AGENTS.md` reforça ("Não criar estado global se estado local resolver"). `EntityForm` é desenhado para continuar servindo esse padrão sem fricção: é agnóstico a "como o estado é gerenciado", só organiza o layout.
3. `EntityForm`/`EntitySection` não impõem nenhuma estrutura de dados, contexto ou hook — um formulário usando RHF no futuro **poderia** consumi-los sem nenhuma mudança de API (RHF cuidaria do estado por fora, os componentes de layout continuariam recebendo `children` normalmente) — ou seja, a porta fica aberta sem a decisão ser tomada agora.

---

## 6. EntityFormNav

### Responsabilidade

Menu de navegação entre as seções de um formulário em modo `edit`, substituindo `Tabs` horizontais nesse contexto específico.

### Props

```ts
type EntityFormNavSection = {
  id: string;
  label: string;
  icon?: LucideIcon;
};

type EntityFormNavProps = {
  sections: EntityFormNavSection[];
  activeSection: string;
  onSectionChange: (id: string) => void;
  sectionsStatus?: EntitySectionsStatusMap;  // ver seção 5 — default: todas "default"
};
```

### Desktop

`md:` e acima: rail vertical fixo à esquerda do conteúdo do formulário, dentro do `EntityDrawer` em modo `edit`. Cada item: ícone opcional + label + indicador de status (ponto colorido) quando `sectionsStatus[id] !== "default"`.

### Mobile

Abaixo de `md:`: vira uma tira horizontal rolável — **reaproveitando o componente `Tabs` já existente** (`ui/Tabs.tsx`, densidade `"compact"`) internamente, não uma reimplementação paralela do mesmo padrão visual de pílula ativa/inativa. `EntityFormNav` é, nessa faixa, um wrapper fino que traduz `sections`/`activeSection`/`onSectionChange` para as props de `Tabs`.

### Como navegar entre seções

Clique/toque no item correspondente dispara `onSectionChange(id)` — a troca de qual `EntitySection` está visível é responsabilidade da página (tipicamente um `useState<string>` para `activeSection`, renderizando condicionalmente a seção correspondente, exatamente como hoje `NovoClienteModal.tsx` já faz com `activeTab`).

### Como destacar seção ativa

Item correspondente a `activeSection` recebe estilo ativo (mesmo vocabulário visual já usado pela navegação da Sidebar — fundo sutil + texto de destaque) e `aria-current="page"` (ou equivalente semanticamente correto para navegação secundária, não `"true"` genérico).

### Como tratar seções inválidas

`EntityFormNav` **não valida nada** — só exibe o indicador visual que `sectionsStatus` já traz pronto da página. Seções com `status: "error"` recebem um ponto vermelho ao lado do label; `"warning"`, âmbar. Clicar numa seção com erro navega normalmente para ela (o `EntityFormNav` nunca bloqueia navegação) — é o `EntityActions` (seção 8) quem decide se o botão "Salvar" fica desabilitado com base no agregado desse mesmo `sectionsStatus`, calculado pela página.

### Navegação por teclado

Setas (↑/↓ no rail vertical, ←/→ na tira horizontal) movem o foco entre itens; `Enter`/`Espaço` ativa o item focado — mesmo padrão de um `tablist`/`tab` ARIA convencional (ver seção 15).

---

## 7. EntitySection

### Contrato

```ts
type EntitySectionProps = {
  id: string;               // deve corresponder a um id em EntityFormNavSection
  title?: string;
  description?: string;
  icon?: LucideIcon;
  children: ReactNode;      // tipicamente um <EntityForm> ou uma lista dinâmica (padrão "Contatos")
};
```

- **Título**: `title`, opcional (algumas seções — ex. uma seção de identificação/documento — podem preferir só o conteúdo, sem repetir o que o `EntityFormNav` já indica).
- **Descrição**: `description`, opcional, texto de apoio abaixo do título.
- **Ícone**: `icon`, opcional, exibido ao lado do título — mesmo ícone que `EntityFormNavSection.icon`, se fizer sentido reaproveitar (não obrigatório que sejam iguais).
- **Conteúdo**: `children`, livre — tipicamente `<EntityForm>`, mas também acomoda o padrão hoje já existente de "lista dinâmica com botão + adicionar" (ex. `ContatosSection` de Clientes), que continua sendo markup específico da entidade, apenas envolvido por `EntitySection` no lugar do `<div>` avulso de hoje.
- **Estado expandido**: `EntitySection`, em modo `edit` dentro do `EntityDrawer`, **não tem estado de expandido/colapsado** — só uma seção está visível por vez (a `activeSection`), controlada externamente. Um modo "todas as seções expandidas em accordion" é um caso de uso diferente (fallback teórico de mobile que a arquitetura já resolveu de outra forma — via `Tabs` reaproveitado em `EntityFormNav`, não via accordion) — **não implementado**, para não duplicar o mecanismo de navegação com dois comportamentos possíveis.

---

## 8. EntityActions

### Props

```ts
type EntityActionVariant = "peek" | "edit";

type EntityActionButton = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  tone?: "default" | "danger";
};

type EntityActionsProps = {
  variant: EntityActionVariant;
  primaryAction: EntityActionButton;
  secondaryActions?: EntityActionButton[];
};
```

### Salvar

`variant="edit"`, `primaryAction` — label tipicamente "Salvar"/"Salvar Alterações". `disabled` reflete a validação agregada da página (equivalente ao `canSave`/`canContinue` já usados hoje); `loading` reflete `isSaving` do `EntityDrawer` (repassado pela página).

### Cancelar

`variant="edit"`, primeiro item de `secondaryActions` — label "Cancelar", `onClick` tipicamente dispara `onRequestModeChange("peek")` (ou `onRequestClose`, se a intenção de cancelar deve verificar `isDirty` — decisão da página).

### Excluir

`variant="peek"`, item de `secondaryActions` com `tone="danger"`. `EntityActions` **não abre nenhum `ConfirmDialog` sozinho** — o `tone="danger"` é só uma sinalização visual; é responsabilidade da página, no `onClick` dessa ação, abrir o `ConfirmDialog` antes de de fato executar a exclusão. Ação só aparece se a página decidir incluí-la em `secondaryActions` (controle de permissão, ver seção 15).

### Duplicar

`variant="peek"`, item de `secondaryActions` sem `tone` especial. Mesma regra de permissão — só aparece se a página incluir.

### Fechar

Não é uma ação de `EntityActions` — pertence ao `EntityHeader` (botão fechar sempre presente ali, ver seção 4). `EntityActions` não duplica esse botão.

### Estados de loading

`primaryAction.loading` (e, por extensão, qualquer item de `secondaryActions`) desabilita o botão e troca visualmente para um indicador de carregamento (reaproveitando o mecanismo de `Button`/`LoadingState` já definidos em `12-plano-de-migracao.md`, Fase 3) — sem bloquear o resto do drawer (o usuário ainda pode navegar entre seções enquanto salva, por exemplo).

### Estados de permissão

`EntityActions` não tem nenhuma prop `canEdit`/`canDelete`/`canDuplicate`. A regra é a mesma já usada hoje por `FornecedoresView`/`GruposClientesView` (`canCreate`/`canEdit`): a página decide, e simplesmente **não inclui** a ação em `primaryAction`/`secondaryActions` quando não permitida. `EntityActions` nunca sabe o motivo de uma ação estar ausente.

---

## 9. EntityHistory

### Responsabilidade

Exibição de eventos de histórico de uma entidade, em duas variantes (compacta, dentro do `EntityPeek`; completa, dentro de uma `EntitySection` dedicada).

### Props

```ts
type EntityHistoryEvent = {
  id: string;
  usuario: string;
  dataHora: string;
  acao: string;
};

type EntityHistoryProps = {
  events: EntityHistoryEvent[];
  variant: "compact" | "full";
  hasMore?: boolean;         // default false
  loading?: boolean;         // default false — próximo lote sendo buscado
  onLoadMore?: () => void;   // presente apenas quando paginação/lazy loading está ativo
  searchValue?: string;      // só relevante em variant="full"
  onSearchChange?: (value: string) => void;
};
```

### Timeline

`variant="full"` renderiza a lista completa em ordem cronológica decrescente, reaproveitando o padrão visual de tabela/lista já usado pelas 7 implementações hoje duplicadas de `HistoricoSection` (usuário, data/hora, ação) — este componente **consolida** essas 7 implementações, não inventa um layout novo.

`variant="compact"` renderiza só `events[0]` (mais recente) + um link textual "ver histórico completo", que a página tipicamente conecta a `onRequestModeChange("edit")` + `setActiveSection("historico")`.

### Paginação / Lazy loading

Hoje, todo histórico do projeto é mock estático em memória (arrays fixos, sem paginação real — confirmado em `taskfloww-design-system.md`, seção 7: "Não existe nenhum componente ou implementação de paginação em todo o projeto"). `EntityHistory` já nasce preparado (`hasMore`/`onLoadMore`/`loading`) para quando isso mudar, mas **essas props são opcionais e, se omitidas, o componente simplesmente renderiza `events` inteiro sem nenhum controle de paginação visível** — nenhum comportamento novo é forçado sobre as entidades que ainda não têm histórico paginado.

Quando `onLoadMore` estiver presente, o padrão é "carregar mais" (botão ao final da lista), não scroll infinito automático — mais previsível e mais simples de implementar sobre o mock atual, e consistente com a ausência de qualquer scroll infinito em qualquer outro lugar do projeto hoje.

---

## 10. EntityRelations

### Responsabilidade

Lista compacta de registros relacionados a uma entidade (ex.: Projetos de um Cliente), cada item navegável para o `EntityPeek` daquele item.

> **Não construir nesta fase** (`entity-architecture-plan.md`, seção 4) — a API abaixo é especificada agora para fixar o contrato antecipadamente e evitar retrabalho quando a primeira relação navegável for de fato modelada, mas a implementação só começa quando isso acontecer.

### Props

```ts
type EntityRelationItem = {
  ref: EntityRef;
  label: string;
  description?: string;
  statusBadge?: ReactNode;
};

type EntityRelationsGroup = {
  id: string;
  title: string;             // ex.: "Projetos", "Tarefas"
  items: EntityRelationItem[];
  totalCount?: number;       // se maior que items.length, indica que a lista é truncada
};

type EntityRelationsProps = {
  groups: EntityRelationsGroup[];
  mode: "compact" | "full";
  onNavigate: (ref: EntityRef) => void;
};
```

### Relacionamentos

Agrupados por tipo (`EntityRelationsGroup`), cada grupo com título e lista de itens. `mode="compact"` (uso dentro de `EntityPeek`) mostra só contadores por grupo (`totalCount`) e, no máximo, 2–3 itens de destaque por grupo; `mode="full"` (uso dentro de uma `EntitySection` dedicada) mostra a lista completa por grupo, com o mesmo padrão de paginação opcional de `EntityHistory` se necessário no futuro.

### Como navegar

Clique em qualquer `EntityRelationItem` dispara `onNavigate(item.ref)` — `EntityRelations` **não navega sozinho**, apenas relata a intenção. Quem de fato troca o conteúdo do drawer é a página, seguindo o mecanismo de pilha já descrito na seção 2 (Fluxo de navegação) e em `entity-architecture-plan.md`, seção 5.

### Como substituir o Drawer

Não substitui — nunca abre um novo `EntityDrawer`. `onNavigate` é tratado pela página exatamente como o clique em uma linha de tabela relacionada: empilha `currentEntity` atual em `navigationStack`, troca `currentEntity` para `ref`, e repassa `header`/`children` atualizados para a **mesma instância** de `EntityDrawer` já aberta.

---

## 11. Estados — visão consolidada

Todos pertencem à **página**, nunca a um componente `entity/` (regra já fixada em `entity-architecture-plan.md`, seção 6 — este documento apenas formaliza o contrato de cada campo com o tipo exato e a prop de `EntityDrawer`/subcomponentes que o consome).

| Estado | Tipo | Por que existe | Consumido por |
|---|---|---|---|
| `selectedEntityId` | `string \| null` | Id do registro que originou a abertura do drawer (a linha clicada na tabela). Independente de navegação por relação | Não é prop direta de nenhum componente `entity/` — é usado pela página para buscar os dados a passar |
| `currentEntity` | `EntityRef \| null` | O que está de fato sendo mostrado agora — pode divergir de `selectedEntityId` após navegar por uma relação | Determina `header`/`children` passados ao `EntityDrawer` |
| `navigationStack` | `EntityRef[]` | Pilha de entidades visitadas dentro da mesma sessão de drawer, para permitir "voltar" | Determina `canGoBack` (`length > 0`) passado ao `EntityDrawer` |
| `drawerMode` | `"closed" \| "peek" \| "edit"` | Estado único e mutuamente exclusivo do que está aberto — estruturalmente impossível representar "os dois abertos ao mesmo tempo" | `open` (`!== "closed"`) e `mode` do `EntityDrawer` |
| `drawerPreset` | `EntityDrawerPreset` | Presente para simetria com a prop `preset` do `EntityDrawer` (seção 2) — hoje sempre `"standard"`, campo existe para não exigir mudança de contrato quando um segundo preset for necessário (Fase 6 de `entity-architecture-plan.md`) | `preset` do `EntityDrawer` |
| `activeSection` | `string` | Qual `EntitySection` está visível em modo `edit` | `activeSection` do `EntityFormNav`, decide qual `EntitySection` a página renderiza como filho do `EntityDrawer` |
| `isDirty` | `boolean` | Se o formulário tem alterações não salvas — decide se fechar/trocar de modo aciona confirmação | `isDirty` do `EntityDrawer` |
| `isSaving` | `boolean` | Ação de salvar em andamento — relevante assim que a persistência deixar de ser mock síncrono | `isSaving` do `EntityDrawer`, repassado a `primaryAction.loading` de `EntityActions` |
| `historyExpanded` | `boolean` | Permite expandir o teaser de histórico dentro do próprio peek (ex. mostrar 3 eventos em vez de 1) sem trocar de modo — evita forçar `"edit"` só para ver mais linhas de histórico | Controla `events.slice(...)` passado a `EntityHistory` dentro do `EntityPeek`; **não é prop de nenhum componente `entity/`**, é só um detalhe de como a página monta o array `events` |
| `sectionsStatus` | `EntitySectionsStatusMap` | Validação agregada por seção, computada pela lógica de validação já existente na página | `sectionsStatus` do `EntityFormNav` |

---

## 12. Eventos — visão consolidada

| Evento | Componente | Assinatura |
|---|---|---|
| `onClose` | `EntityDrawer` | `() => void` |
| `onRequestClose` | `EntityDrawer` | `() => void` |
| `onRequestModeChange` | `EntityDrawer` | `(next: "peek" \| "edit") => void` |
| `onBack` | `EntityDrawer`, `EntityHeader` | `() => void` |
| `onSectionChange` | `EntityFormNav` | `(id: string) => void` |
| `onNavigate` | `EntityRelations` | `(ref: EntityRef) => void` |
| `onLoadMore` | `EntityHistory` | `() => void` |
| `onSearchChange` | `EntityHistory` (variant full) | `(value: string) => void` |
| `primaryAction.onClick` / `secondaryActions[].onClick` | `EntityActions` | `() => void` — cobre Salvar/Cancelar/Excluir/Duplicar; não existem eventos nomeados `onSave`/`onDelete`/`onDuplicate` na API pública, ver nota abaixo |

**Nota sobre não existirem `onSave`/`onDelete`/`onDuplicate` como props nomeadas de `EntityActions`**: a API modela ações como uma lista genérica (`primaryAction`/`secondaryActions`), não como um conjunto fixo de callbacks nomeados. Motivo: o conjunto de ações varia por entidade e por permissão (uma entidade pode nunca ter "Duplicar"; outra pode ganhar "Arquivar" no futuro) — fixar `onSave`/`onDelete`/`onDuplicate` como props obrigatórias ou opcionais específicas tornaria a API rígida demais para esse variar, e reintroduziria exatamente o tipo de "props genéricas demais para cobrir todo caso" que `12-plano-de-migracao.md`, seção 12, já orienta a evitar. A página nomeia seus próprios handlers (`handleSave`, `handleDelete`) e os associa a `onClick` de cada botão — a nomenclatura de evento pública fica só no nível de "isto é uma ação clicável com label X".

---

## 13. Fluxos completos

### Fluxo A — Tabela → Peek → Editar → Salvar → Peek atualizado

```
1. Usuário clica numa linha da tabela.
   Página: setSelectedEntityId(id); setCurrentEntity({type, id}); setDrawerMode("peek").

2. EntityDrawer renderiza:
   open=true, mode="peek", header=<EntityHeader .../>,
   children=<EntityPeek summary=... tags=... relations=... history=.../>,
   footer=<EntityActions variant="peek" primaryAction={{label:"Editar", onClick: handleEdit}} .../>

3. Usuário clica em "Editar".
   handleEdit chama onRequestModeChange("edit") → página: setDrawerMode("edit"); setActiveSection("dados").

4. EntityDrawer re-renderiza:
   mode="edit" (largura anima peek→edit, mesma instância),
   children=<EntityFormNav sections=... activeSection="dados" onSectionChange=.../>
            + <EntitySection id="dados"><EntityForm>...</EntityForm></EntitySection>,
   footer=<EntityActions variant="edit"
            primaryAction={{label:"Salvar", onClick: handleSave, disabled: !canSave}}
            secondaryActions={[{label:"Cancelar", onClick: handleCancel}]} />

5. Usuário navega entre seções (EntityFormNav.onSectionChange) — página troca activeSection,
   troca qual EntitySection é renderizada como children. EntityDrawer não percebe diferença
   estrutural, só o conteúdo do slot children muda.

6. Usuário edita campos — estado do draft muda via useState local da página (mesmo padrão
   já usado hoje pelos *FormSections.tsx), isDirty passa a true, repassado ao EntityDrawer.

7. Usuário clica em "Salvar".
   handleSave valida, persiste (mock), e então chama onRequestModeChange("peek") →
   página: setDrawerMode("peek"); isDirty volta a false.

8. EntityDrawer re-renderiza: mode="peek" (largura anima edit→peek), children volta a
   <EntityPeek /> com os dados já atualizados (a página já tem o draft salvo em seu estado).
```

### Fluxo B — Criação (sem peek prévio)

```
1. Usuário clica em "Novo Cliente".
   Página: setCurrentEntity(null); setDrawerMode("edit") diretamente (sem passar por peek).

2. EntityDrawer abre em mode="edit" — o passo único de identificação (ex. CNPJ/CPF em
   Clientes) é o conteúdo inicial do children (uma EntitySection própria, ou um estado
   interno à página antes mesmo de haver seções — decisão de composição da página,
   não da API do EntityDrawer).

3. Usuário conclui a identificação → página avança para o formulário completo,
   mesmo mecanismo do Fluxo A a partir do passo 4.

4. Ao salvar: handleSave persiste o novo registro, chama onRequestModeChange("peek") →
   EntityDrawer mostra o EntityPeek do registro recém-criado.
```

### Fluxo C — Navegação entre entidades relacionadas (Cliente → Projeto → Tarefa)

```
1. EntityDrawer aberto: currentEntity={type:"cliente", id:"c1"}, mode="peek",
   navigationStack=[].

2. Usuário clica num Projeto dentro de EntityRelations (dentro do EntityPeek do Cliente).
   EntityRelations.onNavigate({type:"projeto", id:"p1"}) dispara.
   Página: navigationStack.push(currentEntity) → navigationStack=[{cliente,c1}];
           currentEntity={type:"projeto", id:"p1"}; drawerMode permanece "peek".

3. EntityDrawer (MESMA instância) recebe novos header/children (dados do Projeto p1),
   e canGoBack=true (porque navigationStack.length > 0) → EntityHeader mostra "← Voltar".

4. Usuário clica em "← Voltar".
   onBack dispara → página: currentEntity = navigationStack.pop() → volta a {cliente,c1};
   navigationStack=[] novamente.

5. Se, em vez de voltar, o usuário clicar em "Editar" do Projeto (passo 3), o Fluxo A se
   aplica normalmente sobre a entidade Projeto — a pilha de navegação (passo 2) e o modo
   peek/edit (Fluxo A) são dimensões independentes do mesmo estado da página.

Em nenhum passo deste fluxo um segundo EntityDrawer é montado — sempre a mesma instância,
sempre header/children trocados.
```

---

## 14. Tabela de responsabilidades

| Componente | Responsabilidade | Fora do escopo | Dependências diretas | Quem consome | Quem NÃO deve consumir |
|---|---|---|---|---|---|
| `EntityDrawer` | Overlay, largura por modo, foco, backdrop, transição | Dados, permissões, persistência, navegação entre entidades | `EntityHeader`, `EntityPeek`/`EntityFormNav`+`EntitySection`, `EntityActions` (via slots) | *Views* de domínio (`ClientesView` etc.) | Outros componentes `entity/` entre si (não há aninhamento de `EntityDrawer` dentro de `EntityDrawer`) |
| `EntityPeek` | Composição somente-leitura do resumo | Edição, navegação, persistência | `EntityFieldRow` (ui/), `EntityHistory` (compact), `EntityRelations` (compact) | `EntityDrawer.children` (modo peek) | Não deve ser usado fora de um `EntityDrawer` (não tem sentido como página avulsa) |
| `EntityHeader` | Identidade + navegação de voltar + fechar | Ações de ciclo de vida (Salvar/Excluir) | `EntityAvatar`, `StatusPill` | `EntityDrawer.header` | — |
| `EntityForm` | Grid de 12 colunas | Validação, estado, seções | `Input`/`Select`/`Textarea` (ui/) via `children` | `EntitySection.children` | Não deve ser usado para layouts fora do contexto de formulário de entidade (para isso, usar Tailwind direto) |
| `EntityFormNav` | Navegação entre seções | Validação em si (só exibe status já calculado) | `Tabs` (ui/, só no fallback mobile) | `EntityDrawer.children` (modo edit, par com `EntitySection`) | — |
| `EntitySection` | Envelope de uma seção do formulário | Navegação, grid (delega a `EntityForm`) | `EntityForm` (tipicamente) | `EntityDrawer.children` (modo edit) | — |
| `EntityActions` | Cluster de ações do rodapé | Confirmação de ações destrutivas (delega à página) | `Button` (ui/) | `EntityDrawer.footer` | — |
| `EntityHistory` | Exibição de eventos de histórico | Persistência, geração de eventos | — | `EntityPeek.history`, conteúdo de uma `EntitySection` | — |
| `EntityRelations` | Exibição/navegação de relações | Persistência, decisão de quais relações existem | — | `EntityPeek.relations`, conteúdo de uma `EntitySection` | — |

---

## 15. Padrões oficiais

### Padding

| Contexto | Valor |
|---|---|
| Cabeçalho do drawer (`EntityHeader`) | `px-4 py-3` |
| Corpo (`EntityPeek` / seção ativa do formulário) | `px-4 py-3` |
| Rodapé (`EntityActions`) | `px-4 py-3` |
| Dentro de `EntityForm` (gap, não padding) | ver "Grid" abaixo |

### Larguras

| Modo | Mobile | Notebook (~1366px) | Desktop (~1920px) | Ultrawide (≥2560px) |
|---|---|---|---|---|
| `peek` | `100vw` | `380px` | `400px` | `420px` (teto absoluto) |
| `edit` | `100vw` | `680–720px` | `760–800px` | `840px` (teto absoluto) |

Valores herdados de `entity-ux-pattern.md`, seção 5 — este documento os torna parte formal do contrato de `EntityDrawer` (seção 2), não apenas uma recomendação de UX.

### Alturas

| Elemento | Valor |
|---|---|
| Campo (`Input`/`Select` dentro de `EntityForm`) | ≈30–32px (herda o preset `"compact"` já validado nas fases anteriores) |
| Drawer, altura máxima | `100dvh` (o drawer é lateral, altura total da viewport — diferente do `Modal` centralizado, que tem teto de `vh` por ser flutuante) |

### Breakpoints

Os mesmos breakpoints Tailwind padrão já usados em todo o projeto (`sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536`), sem breakpoint customizado novo — `EntityFormNav` usa `md:` como limiar rail-vertical↔tira-horizontal.

### Grid

`grid-cols-12`, `gap-x-3` (~12px), `gap-y-2` (~8px) — valores herdados diretamente dos ajustes já validados nas fases anteriores desta sessão para o formulário de Clientes, agora promovidos a padrão oficial de `EntityForm` para todas as entidades.

### Animações

- Transição de largura peek↔edit: `transition-[width] duration-200 ease-out` — mesma duração/easing já usados hoje pela transição de largura da Sidebar (`Sidebar.tsx`), reaproveitando um valor já validado no projeto em vez de introduzir um novo.
- Abertura/fechamento do overlay: fade do backdrop + entrada lateral do card (mesmo padrão hoje implementado em `EntitySidePanel`).

### Backdrop

`bg-black/25 backdrop-blur-[2px]` — valor já aprovado nesta sessão para Clientes, promovido a padrão único de todo overlay de entidade (peek e edit).

### Focus

- Ao abrir: foco move para o primeiro elemento focável do card (mesmo padrão de `EntitySidePanel` hoje).
- Ao fechar: foco retorna ao elemento que originou a abertura.
- Durante navegação por relação (Fluxo C): foco permanece dentro do card (não sai do drawer), mas se reposiciona para o topo do novo conteúdo (mesmo tratamento de "nova página" dentro do drawer).
- Anel de foco visível (`focus-visible:ring-2`) em todos os elementos interativos novos — corrigindo a inconsistência já registrada em `taskfloww-design-system.md`, seção 12 (hoje `Input`/`Select` só mudam cor de borda no foco, sem anel).

### Keyboard

- `Escape`: fecha o drawer (ou aciona `onRequestClose` se `isDirty`).
- `Tab`/`Shift+Tab`: foco permanece preso dentro do card enquanto aberto (focus trap, mesmo comportamento já implícito em `EntitySidePanel` hoje via bloqueio de scroll + foco inicial, formalizado aqui como parte explícita do contrato).
- Setas + `Enter`/`Espaço` em `EntityFormNav`: navegação entre seções (seção 6).

### ARIA

- `EntityDrawer`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` apontando para o título do `EntityHeader`, `aria-describedby` apontando para a descrição quando presente — mesmo padrão que `EntitySidePanel` já implementa hoje (não regredir para o padrão mais fraco de `Modal`, que hoje não tem esses atributos).
- `EntityFormNav`: `role="tablist"` (desktop) com cada item `role="tab"` + `aria-selected`; na faixa mobile, herda o ARIA que `Tabs` já implementa.

### Loading

`EntityDrawer.loading` (prop, seção 2) — quando `true`, o `children` esperado é substituído por `EntitySkeleton` (silhueta do drawer no modo correspondente), no lugar de `EntityPeek`/`EntityFormNav`+`EntitySection`. É a página quem decide passar `<EntitySkeleton mode={mode} />` como `children` enquanto os dados carregam — `EntityDrawer` não troca automaticamente, só reserva a prop `loading` para eventual uso futuro de layout (ex. desabilitar interações durante o carregamento).

### Skeleton

`EntitySkeleton` (já especificado em `entity-architecture-plan.md`, seção 4) — silhueta com a mesma estrutura de `EntityHeader` (avatar+título+descrição em blocos cinza) e linhas de campo/seção, nas duas variantes `peek`/`edit`. Construído sobre o `LoadingState` genérico de `12-plano-de-migracao.md`, Fase 3.

### Empty State

Aplicável dentro de `EntityRelations`/`EntityHistory` quando não há itens: reaproveita o `EmptyState` consolidado de `12-plano-de-migracao.md` (Fase 3), nunca uma implementação própria — ex.: `EntityHistory` com `events=[]` renderiza `<EmptyState title="Nenhum evento registrado" ... />` internamente.

### Erro

Reaproveita o `ErrorState` proposto em `12-plano-de-migracao.md`, Fase 3 — hoje sem nenhum consumidor real (não há chamadas de API que falhem), mas `EntityHistory`/`EntityRelations` já preveem esse caminho (`onLoadMore` falhando, por exemplo) para quando a API real existir, sem exigir mudança de contrato.

### Permissões

Nenhum componente `entity/` tem prop de permissão (`canEdit`, `canDelete` etc.) — a regra, repetida deliberadamente em várias seções deste documento, é sempre a mesma: **a página decide e omite a ação/conteúdo**, os componentes `entity/` nunca perguntam "posso fazer isso?". Consistente com o padrão já existente (`canCreate`/`canEdit` em `FornecedoresView`/`GruposClientesView`) e com a regra explícita de `AGENTS.md`/`entity-architecture-plan.md` de que regra de negócio (inclusive permissão) nunca vive em componente compartilhado.

---

## 16. Extensibilidade

O objetivo desta seção é demonstrar que Tags, Financeiro, Histórico, Timeline, Anexos, Comentários e Projetos relacionados **já cabem na API especificada, sem exigir nenhuma mudança de contrato** quando forem implementados — apenas novo conteúdo populando slots já existentes.

| Funcionalidade futura | Onde entra, sem mudar a API |
|---|---|
| **Tags** | Novo componente `EntityTags` (não construído agora) populando o slot `tags?` de `EntityPeek` (já existe) e uma nova `EntitySection id="tags"` no array `sections` do `EntityFormNav` (que já aceita qualquer lista de seções — adicionar uma não é mudança de contrato, é uso normal da prop `sections`) |
| **Financeiro** | Nova `EntitySection id="financeiro"`, mesma mecânica de qualquer seção — `EntityFormNav`/`EntitySection` já são genéricos o suficiente para acomodar qualquer domínio de campos |
| **Histórico** | Já coberto — `EntityHistory` (seção 9) já é parte deste contrato |
| **Timeline** (histórico + comentários intercalados) | Futuro `EntityTimeline`, variante de composição que populam o mesmo slot `history?` de `EntityPeek`/mesma `EntitySection` de histórico — o slot não precisa saber se recebe um `EntityHistory` simples ou um `EntityTimeline` mais rico, ambos são só `ReactNode` |
| **Anexos** | Nova `EntitySection id="arquivos"` (já existe até um precedente: `ArquivosProjetoSection`, hoje um placeholder em Projetos) — mesma mecânica |
| **Comentários** | Populam o mesmo padrão de `EntityTimeline` acima, ou uma `EntitySection` própria, dependendo da decisão de produto quando a feature for desenhada — a API não precisa antecipar qual |
| **Projetos relacionados** (e qualquer relação) | Já coberto — `EntityRelations` (seção 10) já é parte deste contrato, incluindo o mecanismo de navegação sem empilhar drawers |

**Princípio geral que garante essa extensibilidade**: `EntityPeek` e `EntityFormNav`/`EntitySection` são compostos por **slots de `ReactNode` e listas de seções nomeadas por `id` livre (`string`)** — nunca por uma união fechada de tipos de conteúdo conhecidos de antemão. Adicionar uma nova seção ou um novo tipo de conteúdo de slot é sempre um *uso* da API existente, nunca uma alteração dela. Isso é a mesma lógica já aplicada por `PageHeader.size`/`actions?` nas fases anteriores desta sessão (props que não precisaram mudar quando um novo consumidor com necessidades diferentes apareceu).

---

## 17. Compatibilidade e depreciação

### Como coexistem até a migração completa

| Componente | Status durante a transição | Quem o usa nesse período |
|---|---|---|
| `EntitySidePanel` | **Inalterado**, continua funcionando exatamente como hoje | Todas as entidades ainda não migradas (Clientes, Fornecedores, Grupos de Clientes, Projetos, Demandas — até suas respectivas fases da seção 8 de `entity-architecture-plan.md`) |
| `Modal` | **Inalterado e não depreciado** — seu escopo de uso é dividido em dois: (a) CRUD de entidade, hoje ativo em 8 consumidores, **depreciado nesse uso específico**, migra para `EntityDrawer` por fases; (b) confirmação/bloqueio/alerta, **nunca depreciado**, é a base de `ConfirmDialog` | Entidades ainda não migradas usam `Modal` para (a); todas as entidades, migradas ou não, podem usar `Modal` para (b) |
| `CadastroPage`/`CadastroToolbar`/`CadastroTable`/`CadastroIndicators` | **Fora do escopo deste documento** — pertencem à camada de *listagem*, não de *detalhe*. Continuam existindo e sendo consolidados conforme `12-plano-de-migracao.md` (que os aposenta em favor de `PageShell`/`EntityToolbar`/`DataTable`/`MetricStrip`), processo inteiramente independente da migração de `EntityDrawer` | Todas as entidades, com ou sem `EntityDrawer` |
| `Tabs` | **Não depreciado** — continua servindo os 7 consumidores atuais sem mudança, e ganha um **novo** uso interno (fallback mobile de `EntityFormNav`, seção 6) | Todos os consumidores atuais + `EntityFormNav` |
| `EntityFieldRow`, `EntitySummaryPanel` | **Absorvidos, não removidos** — `EntityFieldRow` passa a ser usado internamente por `EntityPeek`; `EntitySummaryPanel` (hoje só em Grupos de Clientes) fica sem novo consumidor a partir da adoção de `EntityDrawer`, mas não é removido enquanto Grupos de Clientes não migrar (Fase 3 de `entity-architecture-plan.md`) | `EntityPeek` (novo) + Grupos de Clientes (antigo, até migrar) |

### Definição formal de "deprecated" neste contexto

Um componente é considerado **deprecated** quando:
1. Nenhuma entidade nova deve passar a usá-lo a partir da aprovação deste documento;
2. Continua funcionando sem alteração para as entidades que ainda não migraram;
3. Só é removido do código (`entity-architecture-plan.md`, Fase 7) quando **zero** consumidores restarem.

Com essa definição, o status de cada componente citado é:

| Componente | Deprecated? |
|---|---|
| `EntitySidePanel` (uso geral) | **Sim** — substituído por `EntityDrawer` em modo `peek` |
| `Modal` (uso para CRUD de entidade) | **Sim**, só nesse uso — substituído por `EntityDrawer` em modo `edit` |
| `Modal` (uso para confirmação/bloqueio) | **Não** |
| `Tabs` (uso geral, fora de formulário de entidade) | **Não** |
| `CadastroPage`/`CadastroToolbar`/`CadastroTable`/`CadastroIndicators` | **Não**, por este documento (têm seu próprio processo de consolidação em `12-plano-de-migracao.md`, não sobreposto aqui) |
| `EntitySummaryPanel` | **Sim, condicionalmente** — deprecated assim que a primeira entidade que o usa (Grupos de Clientes) migrar para `EntityDrawer`; até lá, ativo |

---

---

## 18. Guia Administrativa — autorização e dados sensíveis

> Primeiro consumidor: guia "Administrativa" de Clientes (`ClienteEditFormBody.tsx` + `ClienteFormSections.tsx`, seção `AdministrativoSection`). Documento de referência único para as regras abaixo — outros documentos (`taskfloww-design-system.md`, `entity-architecture-plan.md`) apenas apontam para esta seção, sem duplicar o texto.

### Componentes

Três novos componentes genéricos em `entity/`, sem nome de entidade e sem lógica de permissão própria:

```ts
type AdministrativeSectionProps = { children: ReactNode };

type FinancialValueFieldProps = {
  label: string;
  value: number | null;   // nunca string formatada com moeda
  onChange: (value: number | null) => void;
  className?: string;
};

type BankingFieldsValue = {
  chavePix: string;
  banco: string;
  agencia: string;
  conta: string;
  tipoConta: "Corrente" | "Poupança" | "Pagamento";
};

type BankingFieldsProps = {
  value: BankingFieldsValue;
  onChange: (updater: (current: BankingFieldsValue) => BankingFieldsValue) => void;
  className?: string;
};
```

`AdministrativeSection` é puramente apresentacional (aviso visual de conteúdo restrito + `children`) — **não verifica perfil, não importa `lib/access-control.ts`**. Quem decide se ela é renderizada é sempre a página/seção de domínio que a compõe.

### Perfis autorizados (`lib/access-control.ts`)

```ts
type PerfilAcesso = "Owner" | "Diretoria" | "Gestor" | "Financeiro" | "Operador" | "Cliente";

function hasAdministrativeAccess(perfil: PerfilAcesso): boolean; // true para Owner, Diretoria, Gestor, Financeiro
```

`PerfilAcesso` é a hierarquia oficial do TaskFloww V2 — não confundir com `perfis` de `lib/usuario-mock.ts` (lista legada do módulo Usuários, ainda não reconciliada; reconciliação fica para a migração de Usuários, seção "Plano de replicação" do relatório desta fase). Nesta fase, `hasAdministrativeAccess` é a única checagem de autorização existente no projeto — não é um RBAC completo, é infraestrutura mínima para esta guia.

A checagem é aplicada **duas vezes** por consumidor: (1) ao montar a lista de seções passada a `EntityFormNav` (a aba nem aparece para quem não tem acesso); (2) de novo, redundantemente, ao decidir renderizar o conteúdo (para que alterar `activeSection` programaticamente não contorne a restrição).

### Regras de dado

- **Fee Mensal** (Clientes) representa **receita**. **Salário** (Usuários, futuro) representa **despesa**. Nunca coexistem no mesmo campo/entidade, nunca são somados ou comparados diretamente.
- Todo valor financeiro é armazenado como `number | null` — nunca uma string já formatada com moeda (`FinancialValueField` força esse contrato).
- Dados bancários (`BankingFields`) são sensíveis: nunca aparecem em tabela, `EntityPeek`, resultados de busca, nem em `console.log`/logs de qualquer tipo.

### Frontend oculta, backend autoriza

Ocultar a guia/seção no frontend é apenas UI — **não substitui autorização real**. Quando existir backend, ele deverá aplicar a mesma checagem (equivalente a `hasAdministrativeAccess`) ao servir e ao gravar estes campos; um usuário sem permissão jamais deve receber esses valores na resposta da API, independentemente do que o frontend esconde.

### Reuso previsto (Usuários)

A mesma composição (`AdministrativeSection` + `FinancialValueField` + `BankingFields`) é a base prevista para Usuários: `Administrativa → Financeiro (Salário) → Dados Bancários`, sem nenhuma mudança de contrato nos três componentes — apenas uma nova composição Usuário-específica, análoga a `AdministrativoSection` em `ClienteFormSections.tsx`.

---

*Fim do documento. Esta especificação é o contrato oficial da API de `entity/` — qualquer implementação subsequente deve segui-la; qualquer necessidade de desvio deve retornar como revisão deste documento antes de ser codificada.*
