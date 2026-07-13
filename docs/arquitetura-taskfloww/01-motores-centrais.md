# 01 — Motores Centrais do TaskFloww V2

> Documento de arquitetura conceitual. Não contém código, migration, endpoint ou implementação.
> Base: [`00-estado-atual.md`](./00-estado-atual.md).
> Objetivo: traduzir o estado atual (majoritariamente frontend + mock) em quatro motores centrais que devem sustentar o TaskFloww V2 quando o backend real for construído.

---

## 0. Visão geral dos quatro motores

O TaskFloww opera sobre quatro motores conceituais que hoje existem em graus de maturidade muito diferentes (ver `00-estado-atual.md`):

| Motor | Papel | Maturidade atual |
|---|---|---|
| **Motor de Entidades** | Fonte de verdade de cadastros e relacionamentos (quem é quem) | Parcial — modelado e funcional em mock, sem backend |
| **Motor de Workflow** | Decide em que etapa uma Demanda está e quem é responsável agora | Parcial — modelado por demanda, mas duplicado/desalinhado com a tela de Workflows |
| **Motor de Kanban** | Visualização e interação sobre o estado do Workflow | Estrutura existente, desconectada dos dados reais |
| **Motor de Eventos** | Captura toda mudança de estado e alimenta histórico, auditoria, notificação e tempo por status | Só os "efeitos" existem (telas de histórico); a "causa" (o motor em si) não existe |

Relação de dependência entre eles (leitura: A depende de B → B precisa existir antes de A funcionar de verdade):

```
Motor de Kanban  ──depende de──>  Motor de Workflow  ──depende de──>  Motor de Entidades
       │                                  │                                  │
       └──────────────emite eventos para──┴──────────────emite eventos para─┘
                                           ▼
                                  Motor de Eventos
                        (histórico, auditoria, notificação, tempo por status)
```

O **Motor de Entidades** é a base (não depende de nenhum outro). O **Motor de Workflow** depende do de Entidades (etapas referenciam usuários/departamentos/demandas que precisam existir). O **Motor de Kanban** não é uma fonte de dados própria — é uma superfície de visualização/interação do Motor de Workflow. O **Motor de Eventos** é transversal: todos os outros três emitem eventos para ele, mas ele não decide regra de negócio de nenhum — só registra, distribui e agrega.

Essa hierarquia é a principal lição do estado atual: hoje o Kanban existe **isolado** (`KanbanBoard.tsx` com dado hardcoded, sem página que o monte) e o Motor de Eventos existe apenas como **efeito colateral duplicado** (5 tipos de histórico quase idênticos, um por entidade, sem nenhuma causa real gerando esses registros).

---

## 1. Motor de Workflow

### Objetivo

Orquestrar o ciclo de vida operacional de uma Demanda (e, por extensão, de um Projeto) através de etapas configuráveis — decidir em que etapa uma demanda está, quem é responsável por ela agora, qual o prazo vigente, e sob quais regras ela pode avançar, ser pausada, bloqueada ou concluída.

### Responsabilidades

- Definir **templates de workflow** reutilizáveis (conjunto nomeado de etapas, ordem, prazos padrão).
- Instanciar um workflow em uma Demanda, permitindo customização pontual (incluir/remover/reordenar etapa, ajustar responsável, ajustar prazo) sem alterar o template original.
- Controlar transição de etapa (avançar, pausar, bloquear, concluir) e manter `etapaAtualId` consistente.
- Determinar o(s) responsável(is) vigente(s) por etapa (usuário e/ou departamento).
- Aplicar prazo por etapa (`prazoHoras`) e disponibilizar o prazo absoluto da etapa atual.
- Aplicar regras de SLA por prioridade/tipo de tarefa quando essa configuração deixar de ser mock isolado.
- Fornecer a base de dados que o Motor de Kanban usa para desenhar colunas e posicionar cards.
- Preparar o terreno para a futura Central de Tráfego (controle de tempo por etapa) e para o "prazo de retorno do cliente".

### Entidades envolvidas

- `Workflow` / `WorkflowEtapa` (templates — hoje inexistentes como entidade real).
- `Demanda` e `DemandaWorkflowEtapa` (instância aplicada a uma demanda específica).
- `Projeto` (contêiner que pode, futuramente, ter workflow ou backlog próprio).
- `Usuario`, `Departamento` (responsáveis por etapa).
- SLA / Prioridade / Tipo de Tarefa (regras de prazo hoje soltas em `/configuracoes/sla`, `/configuracoes/prioridades`, `/configuracoes/tipos-tarefa`).

### Dados de entrada

- Template de workflow selecionado (ou customização ad-hoc) ao criar uma Demanda.
- Ações de transição: avançar etapa, pausar, bloquear, concluir, reabrir.
- Edição de etapa: nome, ordem, responsáveis (usuário/departamento), prazo em horas.
- Ação futura "Enviado ao cliente" (inicia contador de retorno independente).

### Dados de saída

- `etapaAtualId` e status derivado da Demanda.
- Prazo vigente da etapa atual (para exibição no card do Kanban e nas notificações de atraso).
- Lista de responsáveis correntes (consumida pelo Motor de Eventos para notificação e pela regra de visibilidade).
- Eventos de mudança de etapa/responsável/prazo (para o Motor de Eventos).

### Regras

- Etapas de uma mesma demanda não podem ter ordens duplicadas; ao remover uma etapa, as restantes são renumeradas (já implementado como comportamento de UI em `WorkflowDemandaSection`).
- `etapaAtualId` deve sempre apontar para uma etapa existente na lista de etapas da demanda.
- Colaborador vê, na pauta principal, somente a demanda cuja etapa atual está sob sua responsabilidade — etapas futuras do fluxo não devem aparecer antecipadamente (regra documentada em `docs/requirements/projetos-demandas-dashboard.md`, seção 3.6).
- Gestor pode ter visão ampliada, conforme permissão.
- Mudança de workflow (template, etapas, responsáveis, prazo) deve ser auditável — hoje é apenas uma intenção documentada, sem geração real de evento.
- Prazo por etapa não pode ser zero/negativo (validação hoje só no `<input type="number" min={1}>` da UI, não em regra de domínio).

### Dependências

- **Motor de Entidades**: Usuário, Departamento, Demanda e Projeto precisam existir antes de o Workflow poder referenciá-los.
- **Motor de Eventos**: para transformar cada transição de etapa em evento auditável, alimentar histórico e, futuramente, calcular tempo por status.
- Configuração de SLA/Prioridade/Tipo de Tarefa (hoje telas mock isoladas em `/configuracoes/*`, sem vínculo de dado com o workflow real).

### APIs necessárias

- CRUD de templates de Workflow (`Workflow`, `WorkflowEtapa`).
- Aplicar/instanciar um template em uma Demanda nova.
- Transicionar etapa de uma Demanda (avançar/pausar/bloquear/concluir/reabrir).
- Editar etapas de uma Demanda específica (incluir, remover, reordenar, reatribuir responsável, ajustar prazo).
- Consultar "minhas demandas na etapa atual" (para a regra de visibilidade do colaborador).

### Eventos emitidos

- `workflow.etapa.iniciada`
- `workflow.etapa.concluida`
- `workflow.etapa.pausada`
- `workflow.etapa.bloqueada`
- `workflow.demanda.avancou`
- `workflow.responsavel.alterado`
- `workflow.prazo.alterado`
- `workflow.prazo.vencido` (futuro, depende de job/cron)

### Permissões

- Editar template de Workflow: Admin/Gestor (e SuperAdmin).
- Transicionar etapa de uma Demanda: responsável atual da etapa, ou Gestor com permissão ampliada.
- Ver etapas futuras do fluxo: apenas Gestor/Admin com permissão explícita — colaborador comum não deve ver.
- Aprovar avanço de etapa quando a etapa exigir aprovação (ex.: aprovação do cliente): perfil `Cliente` ou `Gestor`, a definir por etapa.

### Riscos

- **Duas fontes de verdade coexistindo hoje**: o workflow por demanda (`WorkflowDemandaSection`) e a tela `/configuracoes/workflows` (100% hardcoded, sem nenhuma relação de dado com o primeiro). Se a arquitetura real for construída sobre qualquer um dos dois sem unificar, o outro vira dívida técnica imediata.
- O modelo de Central de Tráfego (tempo por etapa) mal projetado pode gerar dados de auditoria incorretos ou custosos de corrigir depois (séries temporais são difíceis de retrofit).
- Excesso de flexibilidade (etapa 100% customizável por demanda) dificulta relatórios agregados por etapa "padrão" (ex.: "tempo médio em Revisão" deixa de fazer sentido se cada demanda tem etapas com nomes diferentes).

### O que já existe no código

- `DemandaWorkflowEtapa` (`frontend/src/types/demanda.ts`): `id, nome, ordem, usuarioResponsavelIds, departamentoResponsavelIds, prazoHoras, status`.
- `WorkflowDemandaSection` (`frontend/src/components/demandas/DemandaFormSections.tsx`): UI funcional de incluir/remover etapa, editar nome/prazo/status, definir etapa atual, atribuir responsáveis via `MultiSelect`.
- `Demanda.etapaAtualId` e `Demanda.prazoEtapaAtual`.
- `DemandaVisibilidadeConceitual` e `DemandaSessaoTrabalhoConceitual` (tipos declarados, não usados em nenhum componente — esboço do modelo futuro).
- Tela `/configuracoes/workflows` (`WorkflowsPage`): lista 3 workflows com nomes e etapas hardcoded no próprio componente, sem nenhuma relação com `DemandaWorkflowEtapa`.

### O que precisa ser criado

- Entidade real `Workflow`/`WorkflowEtapa` como template persistido e reutilizável.
- Motor de transição de etapa (validações de ordem, regras de aprovação, bloqueio).
- Vínculo real entre `etapaAtualId` e cálculo de prazo (hoje é só um campo de data manual).
- Lógica real da Central de Tráfego (sessão de trabalho por etapa, início/pausa/fim).
- Integração real com SLA/Prioridade/Tipo de Tarefa (hoje desconectados).

### O que deve ser reaproveitado

- O desenho de dado de `DemandaWorkflowEtapa` (nome, ordem, responsáveis por usuário/departamento, prazo em horas, status) — já é um contrato razoável para o modelo real.
- O padrão de `MultiSelect` para atribuição de responsáveis por etapa.
- Os tipos conceituais já escritos (`DemandaSessaoTrabalhoConceitual`, `DemandaVisibilidadeConceitual`) como ponto de partida do modelo de dados real, em vez de redesenhar do zero.

### O que deve ser refatorado

- A tela `/configuracoes/workflows` precisa deixar de ser hardcoded e passar a consumir os mesmos templates usados pelo workflow por demanda.
- Unificar o conceito "workflow" em um único modelo — hoje há dois modelos incompatíveis (template genérico da tela de configuração vs. instância por demanda).

---

## 2. Motor de Kanban

### Objetivo

Fornecer a visualização e a interação (arrastar-e-soltar) sobre o estado das Demandas, organizadas por etapa/coluna. O Motor de Kanban **não é uma fonte de dados própria** — é a camada de apresentação e interação direta do Motor de Workflow.

### Responsabilidades

- Renderizar colunas a partir das etapas configuradas pelo Motor de Workflow (não um número fixo de colunas).
- Permitir mover um card entre colunas, traduzindo esse movimento em uma transição real de etapa no Motor de Workflow — nunca uma mudança "só visual".
- Exibir card enxuto: nome da demanda, projeto vinculado, prioridade, prazo da etapa atual (regra já documentada em `docs/requirements/projetos-demandas-dashboard.md`, seção 3.5).
- Prover 3 modos de visão: por projeto, por equipe, por colaborador.
- Prover filtros: cliente, projeto, responsável, prioridade, atraso, etapa.
- Abrir o detalhe completo da demanda ao clicar em um card.

### Entidades envolvidas

- `Demanda` (principal), `Projeto`, `Equipe`, `Usuario`, `Cliente`.
- `Workflow`/`WorkflowEtapa` (para gerar as colunas — via Motor de Workflow, não diretamente).

### Dados de entrada

- Lista de demandas filtradas por escopo (projeto/equipe/colaborador) e por permissão de visibilidade.
- Configuração de colunas vinda do workflow aplicado ao escopo em exibição.
- Ação de drag-and-drop: `demandaId` de origem, coluna de destino.
- Filtros aplicados pelo usuário (cliente, projeto, responsável, prioridade, atraso, etapa).

### Dados de saída

- Solicitação de transição de etapa (delegada ao Motor de Workflow) — o Kanban não persiste a nova etapa, apenas solicita.
- Contadores agregados por coluna (quantidade de cards, indicador de atraso).
- Evento de abertura de detalhe (uso de UI).

### Regras

- Mover um card equivale a solicitar uma transição de etapa ao Motor de Workflow; se a transição não for permitida pela regra de workflow (ex.: etapa exige aprovação), o movimento deve ser recusado ou sinalizado, não aplicado silenciosamente.
- O número e a ordem das colunas seguem as etapas do workflow aplicado ao escopo (projeto/equipe/colaborador) em exibição — não um valor fixo no componente.
- Um card só aparece para quem tem permissão de visibilidade sobre aquela demanda/etapa (mesma regra de visibilidade do Motor de Workflow).
- Cards devem permanecer enxutos — evitar excesso de informação (regra documentada explicitamente no requisito de produto).

### Dependências

- **Motor de Workflow**: fonte de colunas e responsável por validar/aplicar toda transição de etapa.
- **Motor de Entidades**: dados de Demanda, Projeto, Cliente, Usuário, Equipe exibidos no card e usados nos filtros.
- **Motor de Eventos**: para registrar e notificar a mudança de etapa resultante do drag-and-drop.

### APIs necessárias

- Listar demandas por escopo (projeto/equipe/colaborador) + filtros.
- Mover demanda de etapa (delegando ao endpoint de transição do Motor de Workflow — não deve existir um endpoint de "mover card" que altere estado sem passar pela regra de workflow).
- Obter configuração de colunas do workflow ativo para o escopo em exibição.

### Eventos emitidos

- Na prática, o Kanban não emite eventos de domínio próprios — ele **aciona** eventos do Motor de Workflow (`workflow.demanda.avancou` etc.) como consequência do drag-and-drop.
- Eventos de uso de UI (abertura de card, aplicação de filtro) são internos e não precisam ser persistidos como evento de domínio.

### Permissões

- Mover um card: responsável atual da etapa, ou Gestor com permissão ampliada (mesma regra do Motor de Workflow).
- Visualizar um card/coluna: regra de visibilidade por etapa e por perfil (colaborador vê só sua etapa atual; gestor pode ter visão ampliada).

### Riscos

- **Maior risco do conjunto**: o Kanban hoje é 100% desconectado — nenhuma página o monta, e ele opera sobre um tipo de dado próprio (`KanbanTask`) diferente do tipo `Demanda` usado no resto do sistema. Se a próxima fase apenas "religar" o componente existente sem antes definir o Motor de Workflow por trás, corre-se o risco de consolidar dois modelos de dados incompatíveis.
- Risco de performance se todas as demandas de uma empresa forem carregadas no board sem paginação/filtro por escopo.
- Ausência de filtros hoje pode se tornar um card debt quando o volume de demandas crescer além do cenário de protótipo.

### O que já existe no código

- `KanbanBoard.tsx`: drag-and-drop funcional com `@dnd-kit/core` (`DndContext`, `PointerSensor`, `handleDragEnd`), 4 colunas fixas (`backlog, em-andamento, revisao, concluido`).
- `KanbanColumn.tsx`, `KanbanCard.tsx`: card visual já alinhado à regra de "card enxuto" (prioridade, tipo, cliente, projeto, responsável, SLA, prazo, refação).
- `TaskDetailModal.tsx`: modal de detalhe, hoje paralelo a `DemandaDetailsDrawer`.
- Todos os três consomem `KanbanTask`, um tipo próprio e hardcoded (`initialTasks` dentro do próprio `KanbanBoard.tsx`), não o tipo `Demanda`.
- Não existe nenhuma rota (`page.tsx`) que monte `KanbanBoard` hoje.

### O que precisa ser criado

- Ligação real entre colunas do Kanban e etapas do Motor de Workflow (hoje colunas são um array fixo de 4 strings).
- Lógica que traduza "mover card" em "solicitar transição de etapa" (hoje o `handleDragEnd` apenas atualiza estado local, sem regra nenhuma).
- Filtros por cliente/projeto/responsável/prioridade/atraso/etapa — nenhum existe hoje no Kanban.
- Os 3 modos de visão (projeto/equipe/colaborador).
- Uma rota/página real que monte o `KanbanBoard` dentro da navegação do produto.

### O que deve ser reaproveitado

- Toda a base de drag-and-drop com `dnd-kit` (`KanbanBoard`, `KanbanColumn`) — já funcional e testado visualmente.
- O formato visual do `KanbanCard` — já minimalista e alinhado ao requisito de "cards enxutos".
- A estrutura de `Modal` usada em `TaskDetailModal` como base de interação (abrir modal ao clicar em card).

### O que deve ser refatorado

- Substituir o tipo `KanbanTask` e o array `initialTasks` hardcoded por consumo real do tipo `Demanda`.
- `TaskDetailModal` deveria deixar de ser uma segunda implementação de "detalhe de tarefa" e passar a reaproveitar `DemandaDetailsDrawer` (que já tem abas Dados/Briefing/Workflow/Responsáveis/Histórico) — hoje as duas UIs de detalhe divergem em campos e em profundidade de informação.

---

## 3. Motor de Entidades

### Objetivo

Ser a camada central de cadastro e relacionamento das entidades operacionais do TaskFloww (Empresa/Agência, Usuário, Cliente, Grupo de Clientes, Fornecedor, Equipe, Departamento, Projeto, Contato de Agenda) — a fonte de verdade de "quem é quem" e "quem se relaciona com quem", sempre por ID, multiempresa, com histórico e auditoria embutidos desde a origem.

### Responsabilidades

- CRUD de cada entidade de cadastro.
- Garantir os campos obrigatórios definidos em `CLAUDE.md` para toda entidade principal: `id`, `empresaId`, `createdAt`, `updatedAt`.
- Manter relacionamentos exclusivamente por ID (nunca por nome — regra explícita do projeto).
- Isolar dados por empresa (`empresaId`) em um contexto multiempresa (SaaS).
- Gerar código interno e sigla automáticos por entidade, quando aplicável.
- Validar unicidade e formato de identificadores (ex.: CPF/CNPJ de Cliente).
- Resolver nomes a partir de IDs para exibição (hoje feito por helpers `resolveXNome` isolados em cada `lib/*-mock.ts`).

### Entidades envolvidas

Empresa/Agência, Usuário, Cliente, Grupo de Clientes, Fornecedor, Equipe, Departamento, Projeto, Contato de Agenda (visão derivada de Cliente/Fornecedor/Usuário + contatos manuais). Em suma, todas as entidades listadas hoje sob "Configurações → Cadastros" mais Projetos.

### Dados de entrada

- Formulários de cadastro (`NovoXModal` + `XFormSections`, hoje mock) com os campos específicos de cada entidade.
- IDs de relacionamento informados no formulário (`clienteId`, `equipeResponsavelId`, `departamentoId`, `responsavelComercialId` etc.).
- Ações de edição/inativação de registros existentes.

### Dados de saída

- Registro persistido com `id`, `empresaId`, `createdAt`, `updatedAt` e demais campos da entidade.
- Lista paginável/filtrável consumida pelas Views/Tables (`UsuariosView`, `ClientesView`, `ProjetosTable` etc.).
- Nomes resolvidos a partir de ID para exibição em outras telas (ex.: nome do cliente dentro do card de uma Demanda).
- Evento de criação/edição/exclusão emitido para o Motor de Eventos.

### Regras

- Toda entidade principal deve possuir `id`, `empresaId`, `createdAt`, `updatedAt` (regra explícita em `CLAUDE.md`).
- Relacionamento entre entidades sempre por ID — nunca usar nome como chave (`departamentoId`, nunca `nomeDepartamento`).
- Isolamento estrito por `empresaId` (nenhuma consulta deve vazar dados entre empresas diferentes).
- Código interno e sigla seguem um padrão de geração automática por entidade (ex.: `#0000` para Cliente, conforme fluxo descrito em `CLAUDE.md`).
- Exclusão de entidade com histórico vinculado deveria preservar o histórico (a decidir: soft delete vs. hard delete — hoje não há exclusão real implementada em nenhum módulo).

### Dependências

- **Motor de Eventos**: para registrar histórico/auditoria de toda criação, edição e exclusão.
- É, por sua vez, **dependência de todos os outros motores** — Workflow, Kanban e Eventos referenciam `usuarioId`, `clienteId`, `departamentoId`, `projetoId` etc. definidos aqui. Nenhum dos outros três motores funciona sem o Motor de Entidades primeiro.

### APIs necessárias

- CRUD REST por entidade: `/agencias`, `/usuarios`, `/clientes`, `/grupos-clientes`, `/fornecedores`, `/equipes`, `/departamentos`, `/projetos`.
- Busca e filtro por entidade (equivalente ao que hoje é feito client-side sobre mock).
- Endpoint de resolução em lote de nomes por IDs (para evitar N+1 quando o frontend precisar exibir nomes derivados de múltiplos IDs).

### Eventos emitidos

- `entidade.criada` (parametrizado por tipo: `usuario.criado`, `cliente.criado` etc.)
- `entidade.atualizada`
- `entidade.excluida` (ou `entidade.inativada`, se soft delete)
- `entidade.relacionamento.alterado` (ex.: usuário movido de departamento, cliente reatribuído a outra equipe responsável)

### Permissões

- CRUD de cada entidade deve respeitar o RBAC já descrito (`SuperAdmin, Admin, Diretoria, Gestor, Operador, Cliente`).
- Criação e gestão de Agências é exclusiva de `SuperAdmin` (regra já documentada em `docs/requirements/projetos-demandas-dashboard.md`).
- Acesso ao módulo de Configurações (onde a maioria dos cadastros vive hoje) é restrito — `Operador` e `Cliente` não devem ver.

### Riscos

- Cada entidade hoje tem seu próprio mock e seus próprios helpers isolados (`usuario-mock.ts`, `cliente-mock.ts`, `equipe-mock.ts` etc.), sem um padrão único de acesso a dado — migrar para API real sem antes unificar esse padrão tende a multiplicar retrabalho por entidade (8 implementações diferentes de "buscar por ID" e "resolver nome").
- **Departamentos** é uma dependência explícita e bloqueante hoje referenciada informalmente (`DepartamentoOption`) por Usuários, Equipes e Projetos, sem existir como entidade própria — qualquer API real de Usuário/Equipe/Projeto que dependa de `departamentoId` fica incompleta sem esse módulo.
- PII sensível já modelada em `UsuarioInformacoes` (CPF, RG, dados bancários, chave PIX) exige atenção de acesso e mascaramento assim que a persistência real existir — hoje é só mock, mas o schema já prevê esses campos.
- Ausência de exclusão real (soft/hard delete) em qualquer módulo mock deixa em aberto uma decisão que afeta diretamente o desenho do Motor de Eventos (o que acontece com o histórico de uma entidade excluída).

### O que já existe no código

- Padrão de módulo consistente e repetido: `Page → View → Table/List → Modal → FormSections`, presente em Usuários, Clientes, Fornecedores, Equipes, Grupos de Clientes e Projetos.
- Tipos completos em `frontend/src/types/*.ts` (`usuario.ts`, `cliente.ts`, `equipe.ts`, `fornecedor.ts`, `grupo-cliente.ts`, `projeto.ts`).
- Mocks e helpers de resolução de nome em `frontend/src/lib/*-mock.ts`.
- Histórico mock por entidade (`HistoricoUsuario`, `HistoricoCliente`, `HistoricoEquipe`, `ProjetoHistoricoEvento`).
- Regra de relacionamento por ID já aplicada de forma consistente (ex.: `ClienteDraft.equipeResponsavelId`, `responsavelComercialId`, `responsavelAtendimentoId`).

### O que precisa ser criado

- O módulo **Departamentos** como entidade própria (Fase 3.14 do `PROJECT_STATUS.md`, ainda não iniciada).
- Toda a camada de API real (models, schemas, rotas) para cada entidade — hoje inexistente no backend (`backend/main.py` só tem healthcheck).
- Regra real de exclusão (soft delete/hard delete) e sua relação com o histórico.
- Validação real de CPF/CNPJ (hoje só campo de texto no mock).
- Geração real de código interno/sigla (hoje presumivelmente estática nos helpers de mock).

### O que deve ser reaproveitado

- O padrão de composição `Page/View/Table/Modal/FormSections` — já é uma convenção madura, repetida em 6 módulos, e deve ser o guia para os módulos que ainda faltam (Departamentos).
- Os tipos TypeScript atuais como base direta do desenho de schema (Pydantic/SQLAlchemy) real — já seguem a regra de relacionamento por ID.
- A lógica de resolução de nome por ID (só precisa passar a consultar uma API em vez de um array em memória).

### O que deve ser refatorado

- Consolidar os helpers `resolveXNome` hoje espalhados e duplicados por `lib/*-mock.ts` em uma camada única de resolução de entidade.
- Padronizar a rota de Fornecedores (`/fornecedores`) para `/configuracoes/fornecedores`, alinhando com o padrão já adotado por Clientes e Equipes.

---

## 4. Motor de Eventos

### Objetivo

Ser o barramento central que captura toda mudança de estado relevante do sistema (criação/edição/exclusão de entidade, transição de etapa de workflow, movimentação no Kanban) e, a partir dela, alimenta Histórico, Auditoria, Notificações e, futuramente, a Central de Tráfego (tempo por status). É o motor que hoje **só existe como efeito colateral**: há telas de histórico em 5 módulos diferentes, mas nenhuma causa real (nenhum motor) gerando esses registros.

### Responsabilidades

- Receber e registrar eventos de domínio emitidos pelos demais motores (Entidades, Workflow, Kanban).
- Persistir esses eventos como trilha de auditoria imutável (não editável, não apagável).
- Distribuir eventos para os consumidores corretos: histórico por entidade, motor de notificação, futura Central de Tráfego.
- Calcular durações e tempos por status a partir de pares de eventos de início/fim de etapa (base do "controle automático de tempo por status").
- Disparar notificação (quando o canal estiver habilitado nas preferências do usuário).

### Entidades envolvidas

- `HistoricoEvento` genérico (hoje duplicado por entidade: `DemandaHistoricoEvento`, `ProjetoHistoricoEvento`, `HistoricoUsuario`, `HistoricoCliente`, `HistoricoEquipe`).
- `Auditoria` (tabela conceitual citada em `docs/database-model.md`, sem schema detalhado).
- `Notificacao` (canal: Sistema, Email, WhatsApp, Push — preferências já modeladas em `NotificacoesView`).
- `DemandaSessaoTrabalhoConceitual` (esboço de consumidor futuro de eventos de início/fim de etapa, para a Central de Tráfego).

### Dados de entrada

- Evento de domínio emitido por qualquer outro motor: tipo do evento, entidade afetada, `usuarioId`, `dataHora`, `ip`, `dispositivo`, valor anterior, valor novo.
- Preferência de canal de notificação do usuário destinatário.

### Dados de saída

- Registro de histórico por entidade (alimenta as abas "Histórico" já existentes em Clientes, Equipes, Usuários, Projetos, Demandas).
- Registro de auditoria consolidado (consulta administrativa).
- Notificação efetivamente disparada no canal habilitado.
- Duração calculada por etapa/status — insumo direto para relatórios de tempo médio, SLA e Central de Tráfego.

### Regras

- Todo evento deve registrar usuário, data/hora, IP e dispositivo — regra já explícita em `CLAUDE.md` (seção Auditoria: "Ainda não implementar. Preparar a estrutura.").
- Eventos são imutáveis: histórico e auditoria não devem ser editados ou apagados após o registro.
- Notificação só é disparada se o canal correspondente estiver habilitado nas preferências do usuário (`NotificacoesView`).
- Cálculo de tempo por status depende da existência de um evento de início e de um evento de fim/transição correspondentes — sem os dois, não há duração a calcular (risco relevante se o motor for parcialmente implementado).

### Dependências

- Depende de todos os outros três motores como **emissores**: Entidades, Workflow e Kanban (via Workflow) são as fontes de evento.
- Depende do Redis (fila/pub-sub) para processamento assíncrono — hoje Redis está provisionado na infraestrutura (`docker-compose.yml`) e citado como destino futuro (`docs/skills/database-rules.md`: "filas, cache, notificações, jobs assíncronos"), mas só é usado para `ping` de healthcheck.
- Depende de um canal de notificação real (e-mail/WhatsApp/push) ainda inexistente — sem isso, o motor pode registrar o evento mas não tem como efetivamente notificar fora do sistema.

### APIs necessárias

- Emissão de evento (endpoint interno ou barramento assíncrono — não necessariamente uma rota HTTP pública).
- Consulta de histórico por entidade (equivalente ao que hoje é renderizado a partir de mock nas abas "Histórico").
- Consulta de auditoria consolidada (restrita a Admin/SuperAdmin).
- CRUD de preferências de notificação (a tela já existe como mock; falta a API por trás).

### Eventos emitidos

Por definição, este motor é primariamente **consumidor/agregador** dos eventos emitidos pelos outros três. Ainda assim, ele próprio emite eventos derivados:

- `historico.registrado`
- `notificacao.disparada`
- `tempo.etapa.calculado` (quando o par início/fim de uma etapa é fechado)
- `auditoria.consolidada` (quando aplicável a rotinas de fechamento/relatório)

### Permissões

- Consulta de Auditoria: restrita a `SuperAdmin`/`Admin`.
- Histórico por entidade: visível conforme a permissão de leitura já existente sobre aquela entidade (quem pode ler o Cliente X pode ler o histórico do Cliente X).
- Preferências de notificação: cada usuário só edita as próprias.

### Riscos

- **Maior risco arquitetural do conjunto de motores**: hoje existem os "efeitos" (5 tipos de histórico, telas de auditoria referenciadas) sem nenhuma "causa" real. Se as APIs de negócio dos outros motores forem construídas antes de projetar este motor, cada módulo tende a reinventar sua própria gravação de histórico — o que já começou a acontecer (5 tipos de evento de histórico praticamente idênticos, um por entidade).
- Ausência de fila real (Redis hoje é só `ping`) pode forçar processamento síncrono de notificações e eventos, criando acoplamento entre a ação do usuário e o envio efetivo da notificação (lentidão, falha em cascata).
- Cálculo de tempo por status é sensível a eventos faltantes (ex.: etapa iniciada mas nunca fechada) — precisa de regra explícita de tratamento de inconsistência antes de alimentar relatórios (o requisito já assume esse dado como confiável em `docs/requirements/projetos-demandas-dashboard.md`, seções 6.1–6.3).

### O que já existe no código

- Padrão de dado de histórico repetido em 5 tipos diferentes: `id, usuarioId, usuario, dataHora, ip/ipOrigem, dispositivo, acao`.
- Seções de UI que exibem esse histórico: `HistoricoDemandaSection` (`DemandaFormSections.tsx`) e abas equivalentes em Clientes/Equipes/Usuários/Projetos.
- Tela de preferências de notificação: `NotificacoesView.tsx` (canais Sistema/Email/WhatsApp/Push, estado local via `useState`, sem persistência).
- Redis já provisionado na infraestrutura (`docker-compose.yml`, `taskfloww_redis`) e citado como destino futuro de filas/notificações (`docs/skills/database-rules.md`).
- `DemandaSessaoTrabalhoConceitual` (`types/demanda.ts`) como esboço declarativo de evento de início/pausa/fim de etapa — não usado em nenhum componente.

### O que precisa ser criado

- O barramento/motor de eventos propriamente dito (hoje inexistente — não há sequer um lugar único que centralize "algo mudou, registre").
- A tabela real de Auditoria (hoje só citada como nome em `docs/database-model.md`, sem colunas definidas).
- O mecanismo de disparo de notificação real (e-mail, WhatsApp, push) — hoje só existe a tela de preferência, sem motor de envio.
- A lógica de cálculo de tempo por status/Central de Tráfego a partir de eventos de início/fim.
- Uso real de Redis como fila de processamento assíncrono (hoje só healthcheck).

### O que deve ser reaproveitado

- O formato de dado de histórico já validado em 5 módulos diferentes — é um contrato razoável para o evento de domínio genérico, desde que generalizado.
- A tela de preferências de notificação (`NotificacoesView`) como está — só precisa passar a persistir e a alimentar um motor de envio real por trás.

### O que deve ser refatorado

- Unificar os 5 tipos de histórico (`DemandaHistoricoEvento`, `ProjetoHistoricoEvento`, `HistoricoUsuario`, `HistoricoCliente`, `HistoricoEquipe`) em um único tipo de evento de domínio genérico, parametrizado por tipo de entidade e tipo de ação, em vez de duplicar a mesma forma cinco vezes.
- Extrair a renderização de histórico (`HistoricoDemandaSection` e equivalentes) para um componente único de "linha do tempo de eventos", reutilizável por qualquer entidade, em vez de uma implementação por módulo.

---

## 5. Síntese: ordem de dependência para implementação futura

Este documento não propõe cronograma nem implementação, mas a leitura dos quatro motores deixa uma ordem de dependência técnica clara, útil para quando a fase de backend real for aprovada:

1. **Motor de Entidades** primeiro — nenhum outro motor funciona sem ele (todos referenciam IDs de entidades).
2. **Motor de Eventos** logo em seguida (ou em paralelo) — se ele nascer depois dos outros três, o retrabalho de unificar 5 implementações de histórico já duplicadas tende a se repetir para Workflow e Kanban.
3. **Motor de Workflow** depois — depende de Entidades e deveria emitir para Eventos desde o primeiro dia.
4. **Motor de Kanban** por último — é uma superfície sobre o Workflow; não deve introduzir nenhum modelo de dado próprio (o erro já cometido no protótipo atual com `KanbanTask`).

Esta ordem é uma constatação técnica, não uma recomendação de escopo ou prazo — cabe a uma etapa posterior de planejamento decidir se e quando essa reconstrução será feita.
