# TaskFloww V2 — Padrão Oficial de UX para Entidades

> **Documento de arquitetura de UX. Nenhum código foi escrito ou alterado para produzi-lo.**
> Escopo: define o padrão de navegação/visualização/edição a ser usado por **todas** as entidades de cadastro do TaskFloww V2 (Clientes, Fornecedores, Usuários, Equipes, Agências, Grupos de Clientes, Workflows) e serve de ponto de partida para as entidades operacionais mais ricas (Projetos, Tarefas/Demandas).
> Este documento **não substitui** `taskfloww-design-system.md` (inventário do estado atual) nem `12-plano-de-migracao.md` (plano de componentes compartilhados) — ele se soma aos dois como a peça que faltava: a decisão de **fluxo**, não de pixel.

---

## 0. Por que este documento existe

Nas últimas iterações (Fase 1, 1.1 e os dois refinamentos visuais seguintes) ficou empiricamente comprovado que o problema de Clientes não era "padding grande demais". Cada correção de pixel expôs um problema estrutural mais fundo:

- Reduzir o padding do modal não resolveu a sensação de "tela grande" — porque o problema real era o **modal em si**, centralizado, sobrepondo o painel lateral que já estava aberto.
- Apertar `py-2` para `py-1.5` nos inputs não resolveu o scroll das abas Dados/Endereço — porque o problema real era uma **grade fixa de 2 colunas** desperdiçando espaço horizontal em campos curtos (UF, Sigla, Status, CEP, Número), e uma **barra de abas horizontal** consumindo o recurso mais escasso do modal: altura.
- Reduzir o overlay para "menos escuro com blur" não resolveu a sensação de "popup sobre popup" — porque o problema real era **dois paradigmas de sobreposição diferentes coexistindo** (painel lateral ancorado à direita + modal centralizado), cada um com sua própria lógica de entrada/saída.

Ou seja: **estávamos otimizando a implementação de um fluxo que estava errado na raiz.** Este documento resolve o fluxo primeiro. A implementação (que virá depois, com aprovação separada) deixa de ser uma sequência de remendos de pixel e passa a ser a construção de um padrão já certo.

---

## 1. Diagnóstico do fluxo atual

```
Tabela → clique na linha → EntitySidePanel (painel/drawer, ancorado à direita, 512–576px)
                                 │
                                 ├─ [Editar] → Modal (centralizado, overlay próprio, 660–740px)
                                 │                 └─ Abas horizontais → FormSections
                                 │
                                 └─ [Fechar]
```

Problemas estruturais (não de pixel):

1. **Dois paradigmas de overlay coexistindo.** O painel entra pela direita e permanece ancorado; o modal aparece centralizado, por cima de tudo — inclusive por cima do painel que já estava aberto. O usuário perde a referência de "estou vendo o cliente X" no instante em que clica em Editar.
2. **Perda de contexto espacial.** Ao abrir o modal, a tabela e o próprio painel desaparecem visualmente atrás de um overlay escuro. Não há mais nenhuma pista de qual linha originou aquela edição.
3. **Recurso errado sendo economizado.** Abas horizontais economizam espaço vertical raso (uma barra de ~40px) ao custo de gastar mal o espaço horizontal abundante do modal — exatamente invertido em relação ao que a tela realmente precisa (o modal tem altura limitada por viewport, não largura).
4. **Grade de formulário desacoplada do conteúdo real.** Duas colunas fixas tratam "UF" e "Nome Fantasia" como se tivessem a mesma necessidade de espaço. Isso força mais linhas do que o necessário, o que por sua vez força scroll, o que por sua vez fez a gente tentar "resolver" aumentando a altura do modal — na direção contrária à realmente necessária.
5. **Duas áreas de rolagem concorrentes** (bug já corrigido nesta fase, mas sintoma direto do problema 1: dois componentes com lógica de contenção própria, um dentro do outro).

Nenhum desses cinco pontos se resolve com mais ajuste de padding. Todos se resolvem com uma decisão de arquitetura de fluxo.

---

## 2. Comparação com referências de mercado

| Produto | Visualização | Edição | Observação relevante |
|---|---|---|---|
| **Flowe** (referência de marca do projeto) | Densidade alta, navegação enxuta, pouca decoração | Painel lateral que assume o papel de formulário | É a referência de *densidade visual* do TaskFloww — mais um alvo de "quanta informação cabe por área" do que um padrão de overlay a copiar literalmente |
| **Linear** | Ao clicar em um item, navega para uma visão de detalhe (rota própria, não modal) ou abre um painel lateral de "peek" | Não existe "modo de edição" separado — os campos são editáveis diretamente na própria visão de detalhe (edição inline) | Fluidíssimo, mas exige um modelo de dados com salvamento otimista campo a campo. Interessante como inspiração de *fluidez*, não diretamente replicável no TaskFloww hoje sem mudar o modelo de persistência mock |
| **Notion** | Página abre "peek" (expandida sobre o contexto) ou navegação completa | Mesma superfície de visualização e edição — tudo é editável no lugar | Ótimo para conteúdo livre; ruim para formulários estruturados com validação/auditoria, que é exatamente o caso do TaskFloww (CPF/CNPJ, permissões, histórico) |
| **ClickUp** | Task abre em modal central, painel lateral ("peek") ou tela cheia — **o próprio usuário escolhe o nível de imersão** | Mesma superfície do modal, com abas internas | Prova que "vários níveis de imersão" é um padrão validado de mercado — mas ClickUp também é frequentemente citado como *visualmente sobrecarregado*, justamente por empilhar abas+seções+sidebars dentro do mesmo modal |
| **Monday.com** | Item abre em modal central com abas (Updates, Files, Activity) | Mesmo modal, edição inline nos campos | Fortemente modal-cêntrico — sofre do mesmo problema estrutural que o TaskFloww tem hoje (perda de contexto da grade ao abrir o modal) |
| **Jira** | Issue abre em rota própria (ou modal dentro de um board), layout em duas colunas: conteúdo principal à esquerda, metadados/campos à direita | Os campos da coluna direita são editáveis diretamente, sem "modo de edição" — mudam de leitura para input ao clicar | Não usa abas horizontais para os campos — usa **seções verticais colapsáveis** na coluna de metadados. É a referência mais próxima do padrão que este documento recomenda para o *menu lateral* de formulário |

**Conclusão da comparação**: os produtos mais elogiados por fluidez (Linear, Notion, Jira) têm em comum **evitar modal centralizado para tarefas recorrentes de CRUD**, preferindo painel lateral, navegação para uma rota própria, ou edição inline. Os produtos mais citados como "carregados" (ClickUp, Monday) são justamente os que empilham abas+modal+seções na mesma superfície. O TaskFloww hoje está estruturalmente mais próximo do grupo Monday/ClickUp (modal central com abas) do que do grupo Linear/Notion/Jira (painel lateral, navegação fluida, seções verticais) — e isso é a causa raiz de todos os sintomas relatados nesta sessão.

---

## 3. Respostas aos 12 pontos

### 1. Visualização — qual a melhor experiência ao clicar na linha?

| Opção | Vantagens | Desvantagens |
|---|---|---|
| **A — Painel lateral (estreito)** | Mantém a tabela visível/contextualizada; leve, rápido de abrir/fechar; ótimo para "passar o olho" em vários registros seguidos | Espaço limitado — não serve para edição completa |
| **B — Modal** | Foco total, sem distração | Interrompe o fluxo por completo; some com o contexto da linha clicada; pior opção para uma ação frequente e leve como "ver um registro" |
| **C — Drawer** | Tecnicamente é a mesma família da opção A (painel ancorado à borda, com overlay) — a diferença prática está só na largura/propósito | — |
| **D — Tela inteira** | Espaço máximo, URL própria, navegação por back/forward do navegador | Custo de navegação alto para uma consulta rápida; usuário "sai" da tabela |

**Recomendação**: **Opção A/C — painel lateral estreito (peek)**, 380–420px, somente leitura. É a única opção que atende simultaneamente "consulta rápida" (a ação mais frequente, feita dezenas de vezes por sessão de trabalho) sem custo de navegação nem perda de contexto da tabela.

### 2. Edição — qual a melhor experiência ao clicar em Editar?

**Drawer largo (720–840px), não Modal, não tela inteira.**

Por quê, tecnicamente:
- **Elimina por construção** o bug de "popup sobre popup": se editar é o **mesmo componente** de visualização apenas alargado, não existe mais "um overlay em cima do outro" — existe um único overlay que muda de largura.
- **Preserva contexto**: a borda direita do drawer continua ancorada perto da linha que originou a ação; a tabela permanece parcialmente visível atrás do overlay (com o backdrop blur já aprovado), diferente do modal centralizado que cobre tudo.
- **Unifica dois componentes em um só**: hoje `EntitySidePanel` e `Modal` são implementações completamente separadas (times diferentes de overlay/foco/ARIA). Um único componente de drawer que aceita `width: "peek" | "edit"` reduz a superfície de manutenção do design system — objetivo já perseguido em `12-plano-de-migracao.md`.
- Tela inteira é descartada para CRUD simples por custo de navegação desproporcional à tarefa (editar 10 campos não justifica sair da lista).

### 3. Informações rápidas — o que o painel estreito (peek) deve mostrar

**Deve mostrar:**
- Identidade: avatar/iniciais, nome, código interno, documento
- Status (badge)
- Tags (quando existirem — até ~5 chips visíveis, com "+N")
- Responsável(is)/equipe, com avatar
- Contato principal (e-mail/telefone)
- Contadores de relação (“3 projetos ativos”, “12 tarefas”) — nunca a lista completa
- Último evento de histórico (1 item, com link "ver histórico completo")
- Ação: botão Editar (e futuramente Excluir/Inativar/Duplicar)

**Não deve mostrar:**
- Os 10+ campos do formulário completo
- Tabela de histórico inteira
- Listas completas de relações (todos os projetos, todas as tarefas)
- Qualquer conteúdo que exija sua própria paginação/scroll pesado

**Quando abrir o formulário completo**: só com ação explícita ("Editar"). Nunca automaticamente ao clicar na linha. Essa separação deliberada entre "ver" (sempre seguro, nunca modifica nada) e "editar" (ação consciente) é mais adequada a um sistema com auditoria/histórico obrigatórios (conforme `CLAUDE.md`) do que edição inline estilo Notion, onde qualquer clique já é uma mutação em potencial.

### 4. Formulário — abas horizontais ou outra estrutura?

| Padrão | Quando funciona | Por que (não) se aplica aqui |
|---|---|---|
| **Abas horizontais** (atual) | Poucas seções (2–3), largura de tela limitada | Gasta a altura (recurso escasso do drawer) para economizar largura (recurso abundante) — o problema já diagnosticado. Escala mal além de ~4 seções |
| **Menu lateral vertical** | Muitas seções, largura disponível (drawer largo) | **Recomendado.** Usa a largura abundante do drawer de 720–840px; libera 100% da altura para o conteúdo; permite indicar status por seção (ex.: ponto vermelho em "Endereço" se houver campo inválido) — algo que abas horizontais fazem pior por espaço |
| **Accordion** | Formulários curtos, ou modo "revisar tudo de uma vez" | Bom como *fallback* em mobile (menu lateral vira accordion quando não há largura para o rail), ruim como padrão principal — uma seção com 10 campos abertos ao lado de outras abertas vira uma rolagem gigante, perdendo o foco por seção |
| **Stepper** | Fluxos únicos, sequenciais, com princípio e fim (onboarding) | Adequado **só** para o passo inicial "CNPJ/CPF → identificação" (que já é, na prática, um mini-stepper de 2 passos hoje). Errado para edição de registro existente, onde o usuário quer ir direto a uma seção específica, não seguir uma sequência |
| **Cards** (grade de seções clicáveis) | Visão "cockpit" de entrada, poucas vezes por sessão | Adiciona um clique extra em relação ao menu lateral persistente — pior para edições frequentes e pequenas |

**Recomendação**: **menu lateral vertical** dentro do drawer largo, como navegação principal das seções (Dados, Endereço, Contatos, Tags, Histórico, ...). Abas horizontais deixam de ser o padrão de desktop e passam a ser **apenas o fallback responsivo** quando a largura não comporta um rail lateral (ver seção 5). Stepper continua existindo, mas restrito ao passo único de identificação inicial no fluxo de criação.

### 5. Larguras (px)

| Componente | Mobile | Notebook (~1366px) | Desktop (~1920px) | Ultrawide (≥2560px) |
|---|---|---|---|---|
| **Painel estreito (peek)** | 100vw | 380px | 400px | 420px (teto absoluto — **nunca** cresce além disso, mesmo em telas maiores) |
| **Drawer largo (edição)** | 100vw | 680–720px | 760–800px | 840px (teto absoluto) |
| **Modal** (só confirmações/micro-ações) | 100vw − margem | 420px | 440–480px | 480px (teto absoluto) |

Regra geral: **larguras sempre em pixel absoluto com teto, nunca em percentual da viewport.** É o mesmo princípio já aplicado ao painel de Clientes nesta fase (`max-w-[420px]`) — generalizado para todos os componentes de overlay. Em nenhum caso um drawer deve "ocupar metade da tela" só porque o monitor é grande.

### 6. Grade dos formulários — 2 colunas ou 12 colunas?

**Grid de 12 colunas.** Já comprovado nesta sessão que é a diferença entre precisar de scroll e não precisar: uma grade fixa de 2 colunas trata todo campo como "metade da largura do formulário", desperdiçando espaço em campos curtos (UF, Sigla, Status, Número, CEP) e forçando linhas extras. Uma grade de 12 colunas permite espelhar a largura de cada campo ao seu conteúdo real (Sigla = 3 colunas, Nome Fantasia = 6, CNPJ/CPF = 8), reduzindo o número de linhas necessárias e, por consequência, a altura total do formulário — sem reduzir nenhuma fonte. Em telas estreitas, todos os campos colapsam para `col-span-12` (uma coluna), preservando legibilidade em mobile.

### 7. Histórico — onde deve aparecer?

- **No peek**: só o último evento, como teaser ("Última atualização por Fulano, há 2h") com link "ver histórico completo".
- **No drawer de edição**: uma seção própria do menu lateral ("Histórico"), com a lista completa, pesquisável.
- **Não deve virar uma página separada** para entidades de cadastro simples (Cliente, Fornecedor, Usuário, Agência) — fragmentaria a navegação sem necessidade.
- **Exceção**: entidades operacionais ricas (Projetos, Demandas) podem evoluir para uma visão de "Atividade" que combina histórico + comentários em uma linha do tempo única (padrão Jira/Linear/GitHub) — mas isso ainda vive **dentro** da própria visão da entidade, nunca como rota/popup separado.

### 8. Tags — como deveriam aparecer (padrão para quando forem implementadas)

> Não implementar agora — só definindo o padrão para não retrabalhar quando a feature nascer.

- **Visualização (peek)**: chips coloridos logo abaixo do título/status, limitados a ~5 visíveis + contador "+N".
- **Tabela**: não merece coluna dedicada por padrão (a tabela já está no limite de densidade) — mostrar como chips compactos numa segunda linha discreta dentro da própria célula de nome, só quando a entidade realmente usa tags como dimensão primária de organização.
- **Formulário**: seção própria no menu lateral ("Tags"), com um componente de input de tags dedicado (não reaproveitar `Select`/`MultiSelect` genérico disfarçado de tag — tags têm semântica de cor/criação livre, diferente de uma lista fixa de opções).
- **Filtros**: fceta própria no toolbar (multi-seleção), como já acontece com Usuário/Departamento em Tráfego — nunca misturada com a busca textual livre.

### 9. Onde mostrar Projetos relacionados, Tarefas, Documentos, Anexos, Comentários, Links

- **No peek**: só contadores/destaques ("3 projetos ativos"), nunca listas completas.
- **No drawer de edição**: cada tipo de relação vira sua própria seção no menu lateral **quando for central para aquela entidade** (nem toda entidade precisa de todas as seções — Cliente pode ter "Projetos" e "Contatos"; Fornecedor pode ter "Pedidos"). Dentro da seção, uma lista/tabela compacta reaproveitando o mesmo padrão de linha da tabela principal — cada item clicável abre o **peek daquele item relacionado**, nunca um drawer/modal empilhado por cima do atual.
- **Comentários**: fazem sentido para entidades colaborativas (Demandas, Projetos), não para cadastros estáticos (Cliente, Fornecedor, Agência). Quando existirem, ficam ao lado do Histórico (ambos são "atividade ao longo do tempo").
- **Regra de ouro, sem exceção**: relação sempre navega para o **peek** do item relacionado — nunca abre um segundo drawer sobreposto ao primeiro. Um único drawer ativo por vez, sempre.

### 10. Design System — componentes oficiais propostos

| Componente | Status | Papel |
|---|---|---|
| `EntityPeek` | Novo (renomeia/reestrutura o atual `EntitySidePanel` em modo estreito) | Painel de leitura, 380–420px |
| `EntityDrawer` | Novo (unifica `EntitySidePanel` + `Modal` num único componente de largura variável) | Painel de edição, 680–840px, com menu lateral interno |
| `EntityForm` | Novo | Grid de 12 colunas + wrapper de seção, usado por todas as `*FormSections` |
| `EntityFormNav` | Novo — **ou** `Tabs` ganhando um `orientation="vertical"` | Menu lateral de navegação entre seções do formulário |
| `EntityHistory` | Novo (unifica as implementações de `HistoricoSection` hoje duplicadas por entidade) | Teaser (peek) + lista completa (drawer) |
| `EntityTags` | Novo, **só quando Tags for implementado** | Chips de tag + input de tag |
| `EntityRelations` | Novo, **só quando a primeira relação navegável for implementada** | Lista compacta de itens relacionados, navega para `EntityPeek` do item |
| `EntityStatusBadge` | Já existe como `StatusPill` — só formalizar como único badge de status | Badge semântico (ativo/inativo/pendente) |
| `EntityAvatar` | Já proposto em `12-plano-de-migracao.md` (promoção de `CadastroAvatar`) | Avatar/iniciais |
| `EntityActions` | Novo | Cluster de ações (Editar/Excluir/Duplicar), posição consistente no topo do peek/drawer |
| `EntityTable` | Já é o `DataTable` proposto em `12-plano-de-migracao.md` | Listagem — este documento não muda nada da tabela em si |

Regra: só construir o que já tem uso real (`EntityPeek`, `EntityDrawer`, `EntityForm`, `EntityFormNav`, `EntityHistory`, `EntityStatusBadge`, `EntityAvatar`, `EntityActions` — todos já têm uma entidade concreta, Clientes, para consumir hoje). `EntityTags` e `EntityRelations` só quando a funcionalidade correspondente for de fato implementada — não construir componente à espera de uma feature futura.

### 11. Fluxo oficial

```
Tabela (linha)
     │ clique
     ▼
EntityPeek — drawer estreito (380–420px), somente leitura
     │                                  │
     │ [Editar]                         │ [fechar / Esc / clique no overlay]
     ▼                                  ▼
EntityDrawer — MESMO drawer, alarga para 680–840px      Tabela (overlay fecha)
     │  menu lateral: Dados / Endereço / Contatos / Tags / Histórico...
     │
     │ [Salvar]                         │ [Cancelar / Esc]
     ▼                                  ▼
validação + persistência (mock)   EntityPeek (drawer volta a 380–420px, sem mudanças)
     │
     ▼
EntityPeek atualizado (mesmo drawer, volta a 380–420px, dados já refletidos)
```

Para **criação** (Novo Cliente): não existe peek prévio (nada para visualizar ainda) — abre `EntityDrawer` diretamente em modo largo, iniciando pelo passo único de identificação (CNPJ/CPF), que continua sendo um mini-stepper de 2 passos **dentro do mesmo drawer**, não mais um `Modal` separado. Ao concluir, o drawer permanece aberto e passa a exibir o registro recém-criado (equivalente a "Salvar" → peek atualizado).

`Modal` (componente centralizado) deixa de ser usado para CRUD de entidade em qualquer ponto deste fluxo. Fica reservado exclusivamente para:
- confirmações destrutivas (`ConfirmDialog`, ainda a construir);
- micro-interações de um único campo/decisão que genuinamente bloqueiam o fluxo (ex.: "tem certeza que quer sair sem salvar?").

### 12. Recomendação final — uma única arquitetura

**Drawer único e progressivo**, com as seguintes regras fixas para todas as entidades de cadastro do TaskFloww V2:

1. Visualização = mesmo componente de overlay que a edição, apenas mais estreito (peek, 380–420px).
2. Edição = o mesmo componente alargado (680–840px), nunca um modal separado.
3. Navegação interna do formulário = menu lateral vertical, não abas horizontais (abas viram só o fallback de mobile).
4. Grade de campos = 12 colunas, spans proporcionais ao conteúdo, nunca 2 colunas fixas.
5. Larguras sempre em pixel absoluto com teto — nunca percentual de viewport.
6. Um único drawer ativo por vez — relações navegam substituindo o conteúdo do peek, nunca empilhando outro overlay.
7. `Modal` centralizado reservado só para confirmação/bloqueio pontual — nunca para CRUD de entidade.
8. Tela cheia reservada só para entidades que são, por natureza, um espaço de trabalho completo (Projetos, Demandas/Tarefas com Kanban, arquivos, equipe) — não para cadastros simples.

**Justificativa técnica, sem "depende":**

- Resolve por construção, e não por ajuste posterior, os três bugs estruturais desta sessão (popup sobre popup, dupla rolagem, formulário desproporcional) — porque a causa raiz de todos os três era "dois paradigmas de overlay coexistindo", e essa causa deixa de existir quando visualização e edição são o mesmo componente.
- Reduz a superfície do design system em vez de aumentá-la: hoje `EntitySidePanel` e `Modal` são duas implementações de overlay inteiramente separadas (foco, ARIA, backdrop, cada uma com sua lógica); a proposta os funde em uma família única (`EntityPeek`/`EntityDrawer` como duas larguras do mesmo componente), continuando exatamente a direção de consolidação já definida em `12-plano-de-migracao.md`.
- Usa o recurso certo em cada situação: altura é escassa dentro de um drawer (por isso menu lateral, não abas horizontais); largura de campo deve seguir o conteúdo (por isso grid de 12 colunas, não 2 colunas fixas); largura de overlay deve ter teto absoluto (por isso pixel fixo, não percentual).
- Está alinhado às referências de mercado mais elogiadas por fluidez operacional (Linear, Notion, Jira) e deliberadamente distante do padrão mais criticado por sobrecarga visual (ClickUp/Monday), que é estruturalmente o padrão que o TaskFloww usa hoje.
- Escala para o roadmap do produto sem reinvenção: o mesmo padrão atende Clientes agora e Fornecedores/Equipes/Usuários/Agências depois; Projetos e Demandas podem nascer no mesmo padrão e "graduar" para tela cheia quando a riqueza de dados (Kanban, arquivos, comentários) justificar — uma evolução prevista, não um padrão inconsistente por página.

---

## Próximos passos (fora do escopo deste documento)

1. Aprovação explícita desta arquitetura antes de qualquer implementação.
2. Só depois: aplicar o branding BOX (preto/branco/laranja) de forma centralizada nos tokens do Design System — como você apontou, faz mais sentido aplicar identidade visual **depois** de o padrão estrutural estar fechado, evitando retrabalho.
3. Só depois: implementação do `EntityDrawer`/`EntityPeek` como piloto em Clientes, substituindo `EntitySidePanel`+`Modal`.
4. Só depois: replicação do padrão para as demais entidades de cadastro.

---

*Fim do documento. Nenhum arquivo de código foi criado, movido ou alterado para produzir esta análise.*
