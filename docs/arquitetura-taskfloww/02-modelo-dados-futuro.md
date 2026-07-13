# 02 — Modelo de Dados Futuro

> Documento conceitual de modelagem de dados. Não é migration, não é DDL, não altera o schema atual (que, conforme `00-estado-atual.md`, hoje não possui nenhuma tabela de negócio).
> Base: [`00-estado-atual.md`](./00-estado-atual.md) e [`01-motores-centrais.md`](./01-motores-centrais.md).
> Objetivo: propor as entidades necessárias para sustentar os quatro motores centrais (Entidades, Workflow, Kanban, Eventos), cobrindo obrigatoriamente os 27 conceitos solicitados.
> "Campos principais" é descrito em prosa (`nome (tipo) — finalidade`), não em `CREATE TABLE`. Tipos são indicativos (ex.: `uuid`, `texto`, `inteiro`, `jsonb`, `enum`, `timestamp`), a serem confirmados na fase de implementação.

---

## 0. Convenções gerais (valem para todas as entidades abaixo)

Estas regras já são exigidas hoje em `CLAUDE.md`/`docs/skills/architecture.md` para o frontend mock, e devem valer também para o schema real:

1. **Multiempresa obrigatório**: toda entidade principal carrega `empresaId`. Entidades de associação (join tables) também carregam `empresaId` de forma redundante para permitir index/particionamento por empresa sem depender de join.
2. **Relacionamento sempre por ID**: nenhuma entidade nova abaixo referencia outra por nome/label — apenas por `*Id`.
3. **Auditoria mínima de linha**: toda entidade principal tem `createdAt`/`updatedAt`; quem cria/edita é rastreado via Evento (seção 6), não necessariamente como coluna própria em cada tabela.
4. **Padrão polimórfico controlado**: várias entidades novas (Responsavel, Anexo, Comentario, EntidadeTag, Evento) precisam se associar a "qualquer entidade principal" (Demanda, Projeto, Cliente, Subtarefa...). Em vez de criar uma tabela de associação por combinação (o que explodiria em dezenas de tabelas quase idênticas), este documento usa o par `entidadeTipo` (enum fechado) + `entidadeId` (uuid) repetido nessas tabelas.
   - **Risco assumido de forma consciente**: esse padrão não permite `FOREIGN KEY` real de banco apontando para "a tabela certa conforme o tipo" — a integridade referencial de `entidadeId` precisa ser garantida pela aplicação (ou por trigger/constraint por tipo, se o banco final optar por isso). Esse risco é citado uma vez aqui e não repetido em cada entidade que usa o padrão, mas se aplica a todas elas.
5. **Enums fechados são preferíveis a texto livre** sempre que o conjunto de valores é conhecido (status, tipo de evento, canal de notificação) — reduz risco de dado inconsistente, mas exige migração de schema a cada novo valor (trade-off a decidir na implementação).

---

## 1. Entidades de referência já cobertas (não redetalhadas aqui)

As entidades abaixo já foram tratadas em profundidade no **Motor de Entidades** (`01-motores-centrais.md`, seção 3) e possuem hoje um tipo TypeScript equivalente em `frontend/src/types/`. Este documento assume sua existência (com `id`/`empresaId`) como pré-requisito e não repete os 8 campos de análise para elas: **Empresa/Agência**, **Usuário**, **Departamento**, **Equipe**, **Cliente**, **Fornecedor**, **Grupo de Clientes**, **Projeto**, **Demanda**.

Uma exceção pontual: a **Demanda** ganha uma entidade filha nova nesta etapa (`DemandaEtapa`, seção 3.4) que substitui o array embutido `Demanda.workflowEtapas` por uma tabela própria — isso está detalhado abaixo porque é parte direta do Motor de Workflow.

---

## 2. Responsabilidade (múltiplos usuários, departamentos e equipes responsáveis)

### 2.1 `Responsavel`

- **Nome**: `Responsavel`
- **Finalidade**: registrar, de forma genérica e relacional, quais usuários, departamentos e/ou equipes respondem por uma Demanda, um Projeto ou uma Etapa de workflow — substituindo os arrays `usuarioResponsavelIds: string[]` / `departamentoResponsavelIds: string[]` hoje embutidos diretamente nos objetos mock. **Também introduz "equipe responsável"**, que hoje não existe em nenhum tipo atual (`Demanda`, `Projeto` e `DemandaWorkflowEtapa` só têm usuário e departamento) — é uma extensão de requisito desta etapa, não algo já existente no código.
- **Campos principais**:
  - `id (uuid)` — identificador.
  - `empresaId (uuid)` — isolamento multiempresa.
  - `entidadeTipo (enum: demanda | projeto | workflow_etapa)` — o que está recebendo o responsável.
  - `entidadeId (uuid)` — id da Demanda/Projeto/Etapa.
  - `tipoResponsavel (enum: usuario | departamento | equipe)`.
  - `usuarioId (uuid, nullable)`, `departamentoId (uuid, nullable)`, `equipeId (uuid, nullable)` — exatamente um preenchido, de acordo com `tipoResponsavel`.
  - `papel (texto, nullable)` — ex.: "principal", "apoio" (campo aberto para uso futuro, não obrigatório na primeira versão).
  - `adicionadoEm (timestamp)`, `adicionadoPor (uuid → Usuario)`.
- **Relacionamentos**: N:1 com `Usuario`, `Departamento` ou `Equipe` (conforme `tipoResponsavel`); associação polimórfica com `Demanda`, `Projeto` ou `DemandaEtapa` via `entidadeTipo`+`entidadeId`.
- **Índices**: `(entidadeTipo, entidadeId)` para listar responsáveis de uma entidade; `(usuarioId)`, `(departamentoId)`, `(equipeId)` para a consulta inversa ("quais demandas este usuário/departamento/equipe responde"), essencial para a regra de visibilidade do Motor de Workflow.
- **Restrições**: `CHECK` garantindo que só a coluna correspondente a `tipoResponsavel` esteja preenchida; `UNIQUE (entidadeTipo, entidadeId, tipoResponsavel, usuarioId, departamentoId, equipeId)` para impedir atribuição duplicada.
- **Riscos de migração**: os arrays atuais (`usuarioResponsavelIds`, `departamentoResponsavelIds`) precisam ser "explodidos" — cada elemento do array vira uma linha nova nesta tabela. Isso é reinterpretação de dado mock para seed, não uma migração automática de banco real (hoje não há banco real com esse dado).
- **Compatibilidade com o banco atual**: nenhuma — o banco atual (`db_data`) não tem nenhuma tabela de negócio. A compatibilidade é com a **estrutura de tipo do frontend** (`Demanda.usuarioResponsavelIds`, `Projeto.responsavelIds`, `DemandaWorkflowEtapa.usuarioResponsavelIds`), que mapeiam diretamente para linhas desta tabela filtradas por `tipoResponsavel = usuario`. Não há equivalente atual para `tipoResponsavel = equipe` — é 100% novo.

---

## 3. Workflows configuráveis e etapas

### 3.1 `Workflow`

- **Finalidade**: template reutilizável de fluxo operacional (nome, descrição), aplicável a múltiplas Demandas.
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `nome (texto)`, `descricao (texto, nullable)`, `ativo (booleano, default true)`, `createdAt`, `updatedAt`.
- **Relacionamentos**: 1:N com `WorkflowEtapaTemplate`; referenciado opcionalmente por `Demanda.workflowOrigemId` (rastreabilidade — de qual template a demanda partiu, mesmo após customização).
- **Índices**: `(empresaId, nome)` — não necessariamente único, agências podem ter workflows com nomes repetidos por área.
- **Restrições**: `nome` obrigatório; `ativo` não pode ser removido, só desativado (evita quebrar Demandas que já referenciam o template).
- **Riscos de migração**: nenhum dado real hoje — a tela `/configuracoes/workflows` é 100% hardcoded (`WorkflowsPage`), sem persistência. Os 3 workflows de exemplo ali (`Marketing Padrão`, `Produção Gráfica`, `Clínica Clare`) podem virar **seed inicial**, não migração.
- **Compatibilidade com o banco atual**: nenhuma tabela existente. O objeto `workflows` hardcoded em `WorkflowsPage.tsx` é a única referência de forma (nome, agência, status, lista de etapas).

### 3.2 `WorkflowEtapaTemplate`

- **Finalidade**: etapa pertencente a um template de Workflow — a "receita" que será copiada (não referenciada em tempo real) para cada Demanda que adotar o template.
- **Campos principais**: `id (uuid)`, `workflowId (uuid, FK)`, `nome (texto)`, `ordem (inteiro)`, `prazoHorasPadrao (inteiro)`, `exigeAprovacao (booleano, default false)`, `createdAt`, `updatedAt`.
- **Relacionamentos**: N:1 `Workflow`; referenciada opcionalmente por `DemandaEtapa.origemTemplateId` (rastreabilidade de origem, não fonte de verdade em tempo real).
- **Índices**: `UNIQUE (workflowId, ordem)`.
- **Restrições**: `ordem >= 1`; `prazoHorasPadrao > 0`.
- **Riscos de migração**: se uma etapa de template for renomeada ou removida depois que Demandas já a usaram, isso **não pode** afetar etapas já instanciadas — por isso `DemandaEtapa` (3.4) sempre guarda seu próprio `nome`/`prazoHoras` (snapshot), igual ao comportamento já presente no mock atual (`DemandaWorkflowEtapa` já tem campos próprios, independentes de qualquer template).
- **Compatibilidade com o banco atual**: nenhuma tabela existente; corresponde conceitualmente ao array `stages: string[]` hardcoded em `WorkflowsPage.tsx`, hoje sem prazo nem aprovação — esses dois campos são novos requisitos desta etapa.

### 3.3 `WorkflowRegraTransicao`

- **Finalidade**: formalizar quais transições entre etapas são permitidas e sob quais condições — hoje **inexistente**: a UI mock atual (`WorkflowDemandaSection`) permite marcar qualquer etapa como "etapa atual" livremente, sem nenhuma regra de transição.
- **Campos principais**: `id (uuid)`, `workflowId (uuid, FK)`, `etapaOrigemId (uuid, FK → WorkflowEtapaTemplate)`, `etapaDestinoId (uuid, FK → WorkflowEtapaTemplate)`, `condicao (enum: livre | requer_aprovacao | requer_checklist_completo)`, `perfilAprovador (enum de perfil RBAC, nullable)`.
- **Relacionamentos**: N:1 com duas etapas do mesmo `Workflow` (origem e destino).
- **Índices**: `UNIQUE (etapaOrigemId, etapaDestinoId)`.
- **Restrições**: `etapaOrigemId <> etapaDestinoId`; ambas as etapas devem pertencer ao mesmo `workflowId` (checado na aplicação, já que é uma regra entre duas FKs da mesma tabela-pai).
- **Riscos de migração**: nenhum dado a migrar (conceito novo). Risco de **design**: se a matriz de transições não cobrir um caso necessário (ex.: reabrir uma demanda concluída), o Motor de Workflow trava — recomenda-se sempre existir uma transição de exceção administrativa (perfil Admin/Gestor pode forçar qualquer transição, registrando evento com justificativa).
- **Compatibilidade com o banco atual**: nenhuma — conceito não presente em nenhum tipo ou tela hoje.

### 3.4 `DemandaEtapa`

- **Finalidade**: instância real de uma etapa de workflow aplicada a uma Demanda específica — substitui o array `Demanda.workflowEtapas: DemandaWorkflowEtapa[]` hoje embutido no objeto mock por uma tabela própria e relacional.
- **Campos principais**: `id (uuid)`, `demandaId (uuid, FK)`, `origemTemplateId (uuid, FK → WorkflowEtapaTemplate, nullable — nulo se a etapa foi criada ad-hoc, sem template)`, `nome (texto)`, `ordem (inteiro)`, `prazoHoras (inteiro)`, `status (enum: pendente | em_execucao | pausada | bloqueada | concluida)`, `createdAt`, `updatedAt`.
- **Relacionamentos**: N:1 `Demanda`; N:1 opcional `WorkflowEtapaTemplate`; 1:N `Responsavel` (via `entidadeTipo = workflow_etapa`); 1:N `EtapaSessaoTempo` (seção 7).
- **Índices**: `UNIQUE (demandaId, ordem)`; `INDEX (status)` para consultas de carga de trabalho por status de etapa.
- **Restrições**: `status` deve ser um dos 4 valores enum (já usados hoje em `DemandaWorkflowEtapaStatus`); `ordem` sequencial sem duplicidade dentro da mesma demanda (garantido pela aplicação ao reordenar, como já ocorre hoje no `removeEtapa` de `WorkflowDemandaSection`).
- **Riscos de migração**: **baixo** — o formato de campo já é praticamente idêntico ao tipo TypeScript atual (`types/demanda.ts`, `DemandaWorkflowEtapa`); a mudança é estrutural (de "array embutido no objeto Demanda" para "tabela própria relacional com FK"), não de forma de dado.
- **Compatibilidade com o banco atual**: alta com o **tipo do frontend** (`DemandaWorkflowEtapa`); nula com qualquer tabela real (não existe nenhuma).

---

## 4. Kanban (colunas e posição de cartões)

### 4.1 `KanbanColuna`

- **Finalidade**: representar visualmente as colunas de um board — **deve sempre derivar do Workflow aplicado** (nunca ser editável de forma independente), para não repetir o erro já presente no protótipo atual, em que o Kanban tem 4 colunas fixas (`backlog, em-andamento, revisao, concluido`) totalmente desconectadas de qualquer etapa real de Demanda.
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `workflowId (uuid, FK)`, `origemTemplateId (uuid, FK → WorkflowEtapaTemplate)`, `nome (texto — espelha o nome da etapa)`, `ordem (inteiro)`, `cor (texto, nullable)`.
- **Relacionamentos**: N:1 `Workflow`; N:1 `WorkflowEtapaTemplate` (a coluna nasce sempre de uma etapa de template); referenciada por `KanbanCartaoPosicao`.
- **Índices**: `UNIQUE (workflowId, ordem)`.
- **Restrições**: `nome` deve ser mantido sincronizado com `WorkflowEtapaTemplate.nome` (regra de aplicação — se a etapa do template for renomeada, a coluna acompanha; não é um valor livre editável na tela de Kanban).
- **Riscos de migração**: nenhum dado hoje — as 4 colunas atuais são um array `KanbanColumnConfig[]` hardcoded dentro do próprio `KanbanBoard.tsx`, sem persistência nem relação com Workflow.
- **Compatibilidade com o banco atual**: nenhuma. **Risco de design a registrar**: se a implementação futura permitir coluna 100% customizada (fora de qualquer `WorkflowEtapaTemplate`), o Kanban volta a divergir do Workflow — recomenda-se **não** oferecer essa opção.

### 4.2 `KanbanCartaoPosicao`

- **Finalidade**: permitir ordenação manual dos cartões dentro de uma mesma coluna (arrastar verticalmente), algo que hoje **não existe** — `handleDragEnd` em `KanbanBoard.tsx` só troca a coluna (`columnId`) da tarefa no estado local do React, sem persistir nenhuma posição.
- **Campos principais**: `id (uuid)`, `demandaId (uuid, FK)`, `kanbanColunaId (uuid, FK)`, `posicao (numérico — recomenda-se valor fracionário, ex.: `double precision`, para permitir inserir um cartão entre dois outros sem renumerar todos)`, `atualizadoEm (timestamp)`, `atualizadoPor (uuid → Usuario)`.
- **Relacionamentos**: N:1 `Demanda`; N:1 `KanbanColuna`.
- **Índices**: `UNIQUE (demandaId, kanbanColunaId)` — uma demanda tem no máximo uma posição por coluna em que está presente; `INDEX (kanbanColunaId, posicao)` para renderizar o board ordenado.
- **Restrições**: `posicao >= 0`. Ao mover um cartão de coluna, a mudança de `kanbanColunaId` **deve** disparar uma solicitação de transição de etapa ao Motor de Workflow (regra de aplicação, não de banco) — nunca deve ser possível só atualizar a posição sem passar pela regra de workflow.
- **Riscos de migração**: nenhum dado a migrar (conceito novo). Risco de **concorrência**: dois usuários reordenando o mesmo board ao mesmo tempo podem gerar posições conflitantes — mitigado pelo uso de posição fracionária (recalcular só localmente, sem lock de tabela inteira) ou por reordenação em lote no backend.
- **Compatibilidade com o banco atual**: nenhuma.

---

## 5. Checklists e subtarefas

### 5.1 `Checklist`

- **Finalidade**: agrupar itens de verificação dentro de uma Demanda (ou de uma Subtarefa) — conceito **totalmente inexistente** hoje (confirmado em `00-estado-atual.md`, seção 22: nenhuma ocorrência funcional de "checklist" no produto).
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `entidadeTipo (enum: demanda | subtarefa)`, `entidadeId (uuid)`, `titulo (texto)`, `createdAt`, `createdBy (uuid → Usuario)`.
- **Relacionamentos**: 1:N `ChecklistItem`; polimórfico com `Demanda`/`Subtarefa`.
- **Índices**: `INDEX (entidadeTipo, entidadeId)`.
- **Restrições**: `titulo` obrigatório.
- **Riscos de migração**: nenhum — não há dado hoje, apenas risco de design (decidir se uma Demanda pode ter mais de um Checklist ou só um; este desenho permite múltiplos, por flexibilidade).
- **Compatibilidade com o banco atual**: nenhuma. Nenhum campo, tipo ou tela equivalente existe.

### 5.2 `ChecklistItem`

- **Finalidade**: item individual dentro de um Checklist.
- **Campos principais**: `id (uuid)`, `checklistId (uuid, FK)`, `descricao (texto)`, `concluido (booleano, default false)`, `ordem (inteiro)`, `concluidoEm (timestamp, nullable)`, `concluidoPor (uuid → Usuario, nullable)`.
- **Relacionamentos**: N:1 `Checklist`.
- **Índices**: `INDEX (checklistId, ordem)`.
- **Restrições**: `descricao` obrigatória e não vazia.
- **Riscos de migração**: nenhum.
- **Compatibilidade com o banco atual**: nenhuma.

### 5.3 `Subtarefa`

- **Finalidade**: quebrar uma Demanda em unidades menores de execução, mais leves que criar uma nova Demanda completa (sem workflow próprio) — conceito também **inexistente** hoje.
- **Campos principais**: `id (uuid)`, `demandaId (uuid, FK — sempre pertence a uma demanda "pai")`, `titulo (texto)`, `concluida (booleano, default false)`, `responsavelUsuarioId (uuid, nullable)`, `ordem (inteiro)`, `prazoEm (timestamp, nullable)`, `createdAt`.
- **Relacionamentos**: N:1 `Demanda`; N:1 opcional `Usuario` (responsável); pode ter seu próprio `Checklist` (`entidadeTipo = subtarefa`).
- **Índices**: `INDEX (demandaId, ordem)`.
- **Restrições**: `titulo` obrigatório.
- **Riscos de migração**: nenhum dado a migrar. **Risco de design a registrar**: existe sobreposição conceitual entre "Subtarefa" (sem workflow) e "Demanda" (com workflow completo) — se o produto evoluir para exigir que subtarefas também tenham etapas, revisar se não deveria ser apenas "Demanda filha" reaproveitando o mesmo Motor de Workflow, em vez de uma entidade paralela com regras próprias.
- **Compatibilidade com o banco atual**: nenhuma — não presente no tipo `Demanda` atual.

---

## 6. Eventos, histórico e timeline

### 6.1 `Evento`

- **Finalidade**: registro atômico e imutável de toda mudança de estado relevante no sistema — é a fonte de verdade única do Motor de Eventos (`01-motores-centrais.md`, seção 4), hoje **inexistente**: o que existe são apenas os "efeitos" (5 tipos de histórico mock duplicados), sem nenhuma causa real gerando esses registros.
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `tipo (texto/enum extensível — ex.: workflow.etapa.iniciada, entidade.criada, comentario.criado)`, `entidadeTipo (enum)`, `entidadeId (uuid)`, `usuarioId (uuid, FK, nullable — nulo para eventos de sistema)`, `dataHora (timestamp)`, `ip (texto, nullable)`, `dispositivo (texto, nullable)`, `valorAnterior (jsonb, nullable)`, `valorNovo (jsonb, nullable)`.
- **Relacionamentos**: N:1 `Usuario`; polimórfico com qualquer entidade (`entidadeTipo`+`entidadeId`).
- **Índices**: `INDEX (entidadeTipo, entidadeId, dataHora)` — consulta de histórico por entidade; `INDEX (tipo)`; `INDEX (empresaId, dataHora)` — consulta de auditoria consolidada.
- **Restrições**: tabela deve ser tratada como **append-only** — nenhum `UPDATE`/`DELETE` a nível de aplicação (idealmente reforçado por permissão de banco restringindo essas operações ao usuário da aplicação).
- **Riscos de migração**: os "eventos" que existem hoje são, na verdade, os arrays mock de histórico (`DemandaHistoricoEvento`, `ProjetoHistoricoEvento`, `HistoricoUsuario`, `HistoricoCliente`, `HistoricoEquipe`) — migrá-los não é uma cópia direta, é uma **reinterpretação de conceito** (cada entrada de histórico mock vira um `Evento` com `tipo` inferido a partir do campo livre `acao`, hoje um texto não padronizado).
- **Compatibilidade com o banco atual**: parcial — o **formato de campo** (`usuarioId, dataHora, ip/ipOrigem, dispositivo, acao`) já é usado de forma consistente nos 5 tipos mock atuais; o que é novo é o conceito de tabela única e polimórfica reunindo todos eles.

### 6.2 Histórico (projeção sobre `Evento`, não é uma tabela própria)

- **Finalidade**: alimentar as abas "Histórico" já existentes em Cliente, Equipe, Usuário, Projeto e Demanda — **decisão de design**: não criar uma tabela `Historico` separada, e sim tratá-la como uma **consulta filtrada sobre `Evento`** (`WHERE entidadeTipo = X AND entidadeId = Y ORDER BY dataHora DESC`), evitando duplicar o mesmo dado em duas tabelas.
- **Campos principais**: os mesmos de `Evento`, apenas filtrados por entidade — nenhum campo adicional.
- **Relacionamentos**: nenhum além do já descrito em `Evento`.
- **Índices**: reaproveita `INDEX (entidadeTipo, entidadeId, dataHora)` de `Evento` — nenhum índice adicional necessário.
- **Restrições**: somente leitura; nenhuma escrita direta (toda escrita passa por `Evento`).
- **Riscos de migração**: nenhum adicional além do já descrito para `Evento`.
- **Compatibilidade com o banco atual**: substitui diretamente os 5 tipos de histórico hoje duplicados no mock, unificando-os em uma única consulta reutilizável.

### 6.3 Timeline (view agregada, não é uma tabela própria)

- **Finalidade**: compor, para uma entidade (tipicamente uma Demanda), uma linha do tempo cronológica combinando `Evento` + `Comentario` (9.2) + `Anexo` (9.1) + `EtapaSessaoTempo` (7.1) — algo que hoje **não existe em nenhuma forma** (nem como conceito documentado, nem como campo de tipo, nem como componente de UI — confirmado em `00-estado-atual.md`, seção 24).
- **Campos principais**: não é uma tabela; é uma composição de consulta que retorna, ordenados por timestamp, itens heterogêneos com um discriminador (`origem: evento | comentario | anexo | sessao_tempo`) e a referência ao registro de origem.
- **Relacionamentos**: consome `Evento`, `Comentario`, `Anexo`, `EtapaSessaoTempo`, todos filtrados pela mesma `entidadeId`.
- **Índices**: depende dos índices já definidos em cada tabela-fonte; se o volume por entidade crescer muito, considerar uma tabela de projeção materializada dedicada (fora de escopo desta etapa conceitual).
- **Restrições**: somente leitura.
- **Riscos de migração**: nenhum dado a migrar (conceito novo). Risco de **performance**: uma timeline calculada por `UNION` de 4 fontes em tempo real pode ficar lenta em demandas com muito volume de eventos — se isso se confirmar na implementação, avaliar materialização assíncrona (consumidor do Motor de Eventos escrevendo em uma tabela de projeção).
- **Compatibilidade com o banco atual**: nenhuma.

---

## 7. Sessões de trabalho e tempo por status

### 7.1 `EtapaSessaoTempo`

- **Finalidade**: registrar, de forma **uniforme**, todo intervalo de tempo relevante pelo qual uma Demanda passa — é a entidade que sustenta simultaneamente: sessões de trabalho, início/fim automático por mudança de status, pausas, bloqueios, espera por cliente e espera por fornecedor. Em vez de criar 5 tabelas quase idênticas (uma por tipo de intervalo), este desenho usa **um tipo discriminador** (`tipo`), o que mantém o cálculo de "tempo por status" uniforme para relatórios, independentemente do tipo de intervalo.
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `demandaId (uuid, FK)`, `etapaId (uuid, FK → DemandaEtapa, nullable)`, `tipo (enum: trabalho | pausa | bloqueio | espera_cliente | espera_fornecedor)`, `usuarioId (uuid, FK, nullable — nulo para tipos de espera sem ator direto)`, `inicioEm (timestamp)`, `fimEm (timestamp, nullable — nulo enquanto o intervalo está aberto)`, `origem (enum: automatico | manual)`, `motivo (texto, nullable — usado em pausa/bloqueio/espera)`, `metadados (jsonb, nullable — ex.: para `espera_cliente`, guardar `aprovadoOuAjuste`)`.
- **Relacionamentos**: N:1 `Demanda`; N:1 opcional `DemandaEtapa`; N:1 opcional `Usuario`.
- **Índices**: `INDEX (demandaId, inicioEm)`; `INDEX (etapaId)`; `PARTIAL INDEX WHERE fimEm IS NULL` — para localizar rapidamente intervalos ainda abertos (essencial para o mecanismo de fechamento automático).
- **Restrições**: no máximo **um** registro com `fimEm IS NULL` por `demandaId` simultaneamente (regra de aplicação — idealmente reforçada por constraint/trigger de banco, já que é uma invariante crítica para o cálculo de tempo); `fimEm >= inicioEm` quando preenchido.
- **Riscos de migração**: nenhum dado hoje — só existe o tipo conceitual `DemandaSessaoTrabalhoConceitual` (`types/demanda.ts:40-49`), nunca usado em nenhum componente. Maior risco é de **design/operação**: se a automação de "abrir/fechar intervalo por mudança de status" falhar (bug, deploy, timeout), intervalos ficam "pendurados" sem `fimEm`, distorcendo todos os relatórios de tempo (médio de entrega, SLA, produtividade) que dependem desta tabela.
- **Compatibilidade com o banco atual**: parcial. `DemandaSessaoTrabalhoConceitual` já antecipa quase os mesmos campos (`demandaId, usuarioId, etapaId, inicioEm, pausaEm?, encerradaEm?, statusOrigem`), mas **não tem** o campo `tipo` (trabalho/pausa/bloqueio/espera) nem cobre `espera_fornecedor`.
  - **Lacuna a registrar explicitamente**: `espera_fornecedor` não corresponde a nenhum valor hoje existente em `DemandaStatus` (`rascunho, planejada, em_execucao, pausada, bloqueada, aguardando_cliente, concluida, cancelada` — ver `types/demanda.ts`). Para que "início/fim automático por status" cubra espera por fornecedor, será necessário **um novo status** (ex.: `aguardando_fornecedor`) no enum `DemandaStatus` quando a implementação real for desenhada — este documento não altera esse enum, apenas registra a lacuna.

---

## 8. SLA

### 8.1 `SlaRegra`

- **Finalidade**: substituir a lista hardcoded de `/configuracoes/sla` (`slaRules` dentro de `SlaPage.tsx`) por uma regra real, associável a prioridade e usada pelo Motor de Workflow/Eventos para calcular prazo esperado e comparar com o tempo real registrado em `EtapaSessaoTempo`.
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `nome (texto)`, `prioridade (enum: baixa | media | alta)`, `tempoRespostaMinutos (inteiro)`, `tempoResolucaoMinutos (inteiro)`, `ativo (booleano, default true)`, `createdAt`, `updatedAt`.
- **Relacionamentos**: referenciada indiretamente por `Demanda` (via `prioridade`) para calcular o prazo esperado; consumida pelo Motor de Eventos/`EtapaSessaoTempo` para comparar tempo real vs. meta (base dos relatórios de SLA descritos em `docs/requirements/projetos-demandas-dashboard.md`).
- **Índices**: `INDEX (empresaId, prioridade)`.
- **Restrições**: `tempoRespostaMinutos > 0`; `tempoResolucaoMinutos > 0`; `tempoResolucaoMinutos >= tempoRespostaMinutos` (regra de bom senso, a confirmar com o negócio).
- **Riscos de migração**: nenhum dado real — `slaRules` é puro array de exemplo de UI (`Urgente, Alta, Normal, Baixa`), pode virar seed inicial, não migração.
- **Compatibilidade com o banco atual**: nenhuma tabela existente; não há sequer um tipo TypeScript dedicado a SLA hoje (`frontend/src/types/` não tem `sla.ts`) — os dados vivem só como array local do componente de página.

---

## 9. Anexos e comentários

### 9.1 `Anexo`

- **Finalidade**: generalizar o conceito hoje restrito a Projeto (`ProjetoArquivo`) para qualquer entidade — especialmente Demanda, onde anexos hoje **não existem** (confirmado em `00-estado-atual.md`, seção 21).
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `entidadeTipo (enum: demanda | projeto | cliente | ...)`, `entidadeId (uuid)`, `nomeArquivo (texto)`, `tipoArquivo (texto — mime type)`, `tamanhoBytes (inteiro)`, `urlArmazenamento (texto)`, `uploadedBy (uuid → Usuario)`, `createdAt`.
- **Relacionamentos**: polimórfico com a entidade de origem; N:1 `Usuario` (quem fez upload).
- **Índices**: `INDEX (entidadeTipo, entidadeId)`.
- **Restrições**: `tamanhoBytes > 0`; validação de tipo de arquivo permitido é regra de aplicação/infraestrutura, não de banco.
- **Riscos de migração**: `ProjetoArquivo` (`types/projeto.ts`) já existe como mock, com campos praticamente equivalentes (`nome, tipo, tamanho, criadoEm, usuarioId, usuarioNome`) — esse dado mock pode virar seed para Projeto; para Demanda, não há nenhum dado a reaproveitar (é criação do zero).
- **Compatibilidade com o banco atual**: parcial — alta com o tipo mock de Projeto, nula para Demanda e para as demais entidades.

### 9.2 `Comentario`

- **Finalidade**: permitir discussão/anotação contextual em qualquer entidade — conceito **totalmente inexistente** hoje, citado apenas como nome de tabela em `docs/database-model.md` e `docs/skills/database-rules.md`, sem nenhum campo definido antes deste documento.
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `entidadeTipo (enum)`, `entidadeId (uuid)`, `autorId (uuid → Usuario)`, `texto (texto)`, `mencionados (array de uuid, nullable — usuários citados no comentário)`, `editadoEm (timestamp, nullable)`, `createdAt`.
- **Relacionamentos**: polimórfico; N:1 `Usuario` (autor); gera `Evento` (`comentario.criado`) e potencialmente `Notificacao` para cada usuário em `mencionados`.
- **Índices**: `INDEX (entidadeTipo, entidadeId, createdAt)`.
- **Restrições**: `texto` obrigatório e não vazio.
- **Riscos de migração**: nenhum dado hoje — entidade 100% nova.
- **Compatibilidade com o banco atual**: nenhuma.

---

## 10. Tags

### 10.1 `Tag`

- **Finalidade**: rotular livremente entidades para busca/filtro rápido — conceito novo, sem menção anterior em nenhum documento ou tipo do projeto.
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `nome (texto)`, `cor (texto, nullable)`, `createdAt`.
- **Relacionamentos**: 1:N `EntidadeTag`.
- **Índices**: `UNIQUE (empresaId, nome)`.
- **Restrições**: `nome` obrigatório e único por empresa.
- **Riscos de migração**: nenhum dado hoje.
- **Compatibilidade com o banco atual**: nenhuma.

### 10.2 `EntidadeTag`

- **Finalidade**: associar uma `Tag` a qualquer entidade (Demanda, Projeto, Cliente etc.).
- **Campos principais**: `id (uuid)`, `tagId (uuid, FK)`, `entidadeTipo (enum)`, `entidadeId (uuid)`, `adicionadoEm (timestamp)`, `adicionadoPor (uuid → Usuario)`.
- **Relacionamentos**: N:1 `Tag`; polimórfico com a entidade marcada.
- **Índices**: `UNIQUE (tagId, entidadeTipo, entidadeId)`; `INDEX (entidadeTipo, entidadeId)` (para listar tags de uma entidade).
- **Restrições**: sem duplicidade de associação (garantida pelo índice único).
- **Riscos de migração**: nenhum.
- **Compatibilidade com o banco atual**: nenhuma.

---

## 11. Filtros salvos

### 11.1 `FiltroSalvo`

- **Finalidade**: persistir combinações de filtros que hoje são recriadas manualmente a cada acesso (estado React efêmero, nunca salvo) — ex.: "Demandas do Cliente X, prioridade Alta, atrasadas".
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `usuarioId (uuid, FK — dono do filtro)`, `modulo (enum: demandas | projetos | kanban | agenda | ...)`, `nome (texto)`, `criterios (jsonb — os valores de filtro serializados)`, `compartilhadoComEquipeId (uuid, FK → Equipe, nullable)`, `createdAt`.
- **Relacionamentos**: N:1 `Usuario`; N:1 opcional `Equipe` (quando compartilhado).
- **Índices**: `INDEX (usuarioId, modulo)`.
- **Restrições**: `nome` obrigatório; validação de que `criterios` é um JSON bem-formado é responsabilidade da aplicação, não do banco.
- **Riscos de migração**: nenhum dado hoje — os filtros atuais (`DemandasToolbar`, `AgendaToolbar`) vivem apenas como `useState` local, nunca persistidos.
- **Compatibilidade com o banco atual**: nenhuma — não existe estrutura equivalente em nenhum tipo atual.

---

## 12. Notificações

### 12.1 `Notificacao`

- **Finalidade**: registrar cada notificação efetivamente disparada, permitindo uma futura "central de notificações" e status de leitura — hoje só existe a **preferência de canal** (seção 12.2), nenhuma notificação real é gerada ou armazenada.
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `destinatarioId (uuid, FK → Usuario)`, `tipo (enum — ex.: prazo_proximo, mencao, demanda_atribuida, etapa_concluida)`, `canal (enum: sistema | email | whatsapp | push)`, `entidadeTipo (enum, nullable)`, `entidadeId (uuid, nullable)`, `titulo (texto)`, `corpo (texto)`, `lida (booleano, default false)`, `lidaEm (timestamp, nullable)`, `createdAt`.
- **Relacionamentos**: N:1 `Usuario` (destinatário); polimórfico com a entidade de origem (quando aplicável).
- **Índices**: `INDEX (destinatarioId, lida, createdAt)` — consulta típica de "minhas notificações não lidas, mais recentes primeiro".
- **Restrições**: o `canal` usado deve estar habilitado em `PreferenciaNotificacao` do destinatário no momento do disparo (regra de aplicação, checada antes do `INSERT`, não uma constraint de banco).
- **Riscos de migração**: nenhum dado hoje — apenas a intenção de canal existe na UI (`NotificacoesView`), sem nenhum histórico de notificação real armazenado em lugar nenhum.
- **Compatibilidade com o banco atual**: nenhuma.

### 12.2 `PreferenciaNotificacao`

- **Finalidade**: versão persistida da tela `NotificacoesView.tsx`, hoje mantida apenas em `useState` local (perdida a cada reload de página).
- **Campos principais**: `id (uuid)`, `usuarioId (uuid, FK)`, `canal (enum: sistema | email | whatsapp | push)`, `habilitado (booleano)`, `updatedAt`.
- **Relacionamentos**: N:1 `Usuario`.
- **Índices**: `UNIQUE (usuarioId, canal)`.
- **Restrições**: `canal` deve ser um dos 4 valores já usados na UI.
- **Riscos de migração**: nenhum dado real hoje (estado local nunca persistido); a migração é, na prática, **criar a tabela e usar como seed os mesmos valores-padrão já definidos** em `NotificacoesView.tsx` (`initialChannels`: `Sistema: true, Email: true, WhatsApp: false, Push: false`).
- **Compatibilidade com o banco atual**: alta com a **UI atual** (mesmos 4 canais, mesmos valores-padrão), nula com qualquer tabela (não existe nenhuma).

---

## 13. Mapa entidade → motor central

| Entidade | Motor principal |
|---|---|
| `Responsavel` | Motor de Entidades (associação) + consumido por Workflow e Kanban |
| `Workflow`, `WorkflowEtapaTemplate`, `WorkflowRegraTransicao`, `DemandaEtapa` | Motor de Workflow |
| `KanbanColuna`, `KanbanCartaoPosicao` | Motor de Kanban |
| `Checklist`, `ChecklistItem`, `Subtarefa` | Motor de Entidades (composição de Demanda) |
| `Evento`, Histórico (view), Timeline (view) | Motor de Eventos |
| `EtapaSessaoTempo` | Motor de Eventos (consumido pelo Motor de Workflow para SLA/prazo) |
| `SlaRegra` | Motor de Workflow (regra) + Motor de Eventos (comparação real vs. meta) |
| `Anexo`, `Comentario` | Motor de Entidades (conteúdo associado) + gera evento no Motor de Eventos |
| `Tag`, `EntidadeTag` | Motor de Entidades (metadado transversal) |
| `FiltroSalvo` | Motor de Kanban / Motor de Entidades (camada de consulta, não de domínio) |
| `Notificacao`, `PreferenciaNotificacao` | Motor de Eventos (efeito colateral de evento) |

---

## 14. Lacunas e novidades identificadas nesta etapa

Conceitos que **não existiam** em nenhuma forma (tipo, mock, tela ou documento) antes deste levantamento, e que passam a existir apenas como proposta neste documento:

- **Equipe responsável** (`Responsavel.tipoResponsavel = equipe`) — hoje só usuário e departamento são responsáveis em Demanda/Projeto/Etapa.
- **Espera por fornecedor** (`EtapaSessaoTempo.tipo = espera_fornecedor`) — não corresponde a nenhum valor hoje existente em `DemandaStatus`; exige extensão futura desse enum.
- **Checklist**, **ChecklistItem**, **Subtarefa** — nenhuma menção anterior.
- **Comentario**, **Tag**/**EntidadeTag**, **FiltroSalvo** — nenhuma menção anterior (Comentário e Anexo já eram citados como nomes de tabela em `docs/database-model.md`, mas sem nenhum campo definido).
- **Timeline** como composição de múltiplas fontes — nenhuma menção anterior em nenhum documento.
- **KanbanCartaoPosicao** (ordem manual dentro da coluna) — hoje o drag-and-drop só troca de coluna, não guarda ordem.
- **WorkflowRegraTransicao** — hoje qualquer etapa pode virar "etapa atual" livremente, sem regra de transição.

---

## 15. Riscos transversais de migração

Riscos que não são de uma entidade específica, mas do modelo como um todo:

1. **Não há dado real a migrar** — todo o levantamento acima parte de mocks e tipos de UI, não de um banco de produção. "Migração", neste contexto, significa principalmente **reinterpretar conceito de mock para schema relacional**, não transportar linhas de um banco antigo.
2. **Padrão polimórfico (`entidadeTipo`+`entidadeId`) repetido em 6 entidades** (`Responsavel`, `Anexo`, `Comentario`, `EntidadeTag`, `Evento`, e a Timeline derivada) — se a implementação real preferir integridade referencial forte (FK de banco), a alternativa é uma tabela de associação dedicada por combinação entidade×conceito, o que multiplica o número de tabelas. Essa escolha de trade-off (flexibilidade polimórfica vs. integridade referencial forte) deve ser decidida explicitamente antes da implementação, não assumida por omissão.
3. **`DemandaStatus` precisará crescer** para acomodar `aguardando_fornecedor` (seção 7.1) — qualquer código futuro que trate `DemandaStatus` como enum fechado (validações, gráficos, filtros) precisa considerar essa extensão desde o desenho.
4. **Dependência de Departamentos como entidade real** (já registrada em `01-motores-centrais.md`) se propaga para `Responsavel.departamentoId` — nenhuma linha de `Responsavel` com `tipoResponsavel = departamento` pode existir sem o módulo de Departamentos (ainda não iniciado, Fase 3.14 do `PROJECT_STATUS.md`).
5. **PII em `Usuario`** (CPF, dados bancários, PIX, já mapeados em `01-motores-centrais.md`) se propaga por referência (`usuarioId`) para praticamente todas as entidades novas deste documento (`Responsavel`, `Evento`, `Comentario`, `Anexo`, `Notificacao`) — nenhuma dessas entidades duplica PII diretamente, mas todas permitem, por join, expor esse dado; controle de acesso deve ser pensado na camada de API, não apenas no schema.
