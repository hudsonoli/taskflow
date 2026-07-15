# 08 — Plano de Migração da Entidade Tarefa

> Documento de planejamento. Não contém código, migration ou implementação.
> Base: [`06-diagnostico-entidade-tarefa-atual.md`](./06-diagnostico-entidade-tarefa-atual.md),
> [`07-modelo-dominio-tarefa-proposto.md`](./07-modelo-dominio-tarefa-proposto.md), e o roadmap geral já
> aprovado em [`03-roadmap-implementacao.md`](./03-roadmap-implementacao.md).
> Nenhuma subtarefa deste documento foi executada — é um plano sujeito a aprovação explícita antes de
> qualquer alteração de código, conforme `AGENTS.md` e `CLAUDE.md`.
> **Revisão 2** (esta versão): incorpora as 12 decisões funcionais oficiais aprovadas (ver `07`, seção 0.1).
> Principais mudanças em relação à revisão anterior: Subtarefa 0 deixa de ser uma escolha em aberto e vira
> uma estratégia de renomeação progressiva já decidida; a Fase A ganha autenticação real antecipada e as
> extensões de Departamento/Squad/Usuario; a Fase B ganha os campos de regra de etapa e a Revisão expandida;
> entram duas fases novas, F2 (resumo de status no Projeto) e G (experiência por papel).

## 0. Como este plano se relaciona com o roadmap de 6 fases já existente (`03`)

Este documento **não substitui** `03-roadmap-implementacao.md` — detalha, em grão menor e ordenado, a fatia "Tarefa" das Fases 1 a 4 de `03`, incorporando as decisões de `07`. As Fases 5 e 6 de `03` (Central de Tráfego real, Inteligência) não são detalhadas aqui.

Cada subtarefa é pequena o suficiente para ser entregue e validada isoladamente (`npm run lint`, `npm run build`, ou testes de backend equivalentes), seguindo o fluxo obrigatório do `CLAUDE.md` (plano → diff → aprovação → aplicar → validar → mostrar `git status`/`git diff --stat`).

---

## 1. Subtarefa 0 — Estratégia de renomeação progressiva `Demanda` → `Tarefa` (decisão 1)

**Objetivo**: a decisão de nome já está tomada — `Tarefa` é o nome oficial em produto, código novo, API e banco (decisão 1). Esta subtarefa não escolhe mais entre duas opções; define **como** a renomeação acontece sem ser uma substituição global cega, que é o segundo mandato explícito da decisão 1.

**Estratégia decidida**:
1. **Código novo nasce como `Tarefa`, sempre.** Backend (models, schemas, rotas — Subtarefa A1 em diante), banco (migrations) e qualquer tipo/entidade nova do frontend (`Squad`, extensão de `Departamento` etc.) usam `Tarefa` desde a primeira linha — nunca `Demanda`.
2. **Código existente é renomeado junto com a subtarefa que já precisa tocá-lo por outro motivo**, não em um PR isolado de "renomear tudo". Concretamente: `frontend/src/types/demanda.ts` → `types/tarefa.ts`, `components/demandas/*` → `components/tarefas/*`, `lib/demandas-mock.ts` → `lib/tarefas-mock.ts` são renomeados **na Subtarefa A8** (quando o tipo central já está sendo migrado de qualquer forma), não antes.
3. **Alias de compatibilidade durante a transição**: enquanto A8 não estiver concluída, nenhuma outra subtarefa deve depender do nome final — subtarefas que precisarem referenciar a entidade antes de A8 (nenhuma prevista neste plano) usariam um re-export temporário (`export type Tarefa = Demanda`), removido assim que A8 terminar.
4. **Rota e rótulo de produto não mudam** — `/tarefas` e o item de menu "Tarefas" já estão corretos hoje (`06`, seção 0) e não fazem parte desta renomeação.

**Critério de aceite**: esta estratégia está documentada e aprovada (este texto); a primeira ocorrência do nome `Tarefa` no código nasce em A1 (backend) e a renomeação do frontend acontece inteira dentro de A8, sem um "big bang" de renomeação prévia isolado.

**Risco de não seguir a estratégia**: renomear tudo de uma vez, fora do fluxo das subtarefas que já tocam esses arquivos, gera um diff enorme e sem valor funcional isolado — contraria a decisão 12 (entregas pequenas).

---

## 2. Fase A — Fundação da Tarefa (equivalente à Fase 1 de `03`, recorte Tarefa)

### 2.1 Subtarefa A1 — Estrutura mínima de backend

**Entregável**: `backend/app/` deixa de ter diretórios vazios; primeira migration Alembic real, cobrindo as tabelas de que a Tarefa depende diretamente para existir: `Empresa`, `Usuario`, `Departamento`, `Cliente`, `Projeto`. Nomeação já nasce como `Tarefa`-first (Subtarefa 0) — nenhum model/schema/rota deste backend usa o nome `Demanda`.

**Arquivos afetados**: `backend/app/models/`, `backend/app/schemas/`, `backend/app/api/routes/`, `backend/app/core/`, `backend/app/db/`, `backend/alembic/versions/` (todos hoje vazios, `06`, seção 1.1).

**Depende de**: Subtarefa 0.

**Critério de aceite**: `alembic upgrade head` cria as 5 tabelas; testes de integração de CRUD básico passam contra Postgres real.

### 2.2 Subtarefa A2 — Autenticação real mínima e usuário atual (decisão 11, nova)

**Entregável**: login real (usuário/senha ou equivalente simples) e sessão (JWT ou cookie de sessão), com endpoint `GET /me` retornando o usuário autenticado — substituindo `frontend/src/lib/conta-mock.ts` (`currentUser` hardcoded) como fonte de identidade.

**Arquivos afetados**: `backend/app/core/` (novo módulo de segurança/auth), nova tabela de credenciais (campo `senhaHash` em `Usuario` ou tabela separada `UsuarioCredencial`); `frontend/src/lib/conta-mock.ts`; `frontend/src/components/layout/Sidebar.tsx:144` (hoje lê `currentUser.perfil` direto do mock); componentes de login (novos, hoje inexistentes).

**Depende de**: A1.

**Nota de exceção deliberada (decisão 11 e `07`, riscos, item 4)**: esta subtarefa antecipa a autenticação em relação à regra geral de fase do projeto (`PROJECT_STATUS.md`: "Nesta fase ainda não existe autenticação"). É uma decisão explícita do usuário, aplicada **apenas à fatia Tarefa** — precisa ser comunicada às demais frentes do repositório para não gerar confusão sobre se "a fase de autenticação" já começou de forma geral (não começou; só para Tarefa).

**Critério de aceite**: login real funcional; `GET /me` retorna o usuário autenticado; nenhum componente de Tarefa/Pauta lê `conta-mock.ts` como fonte de sessão (o mock pode continuar existindo só como dado de cadastro).

### 2.3 Subtarefa A3 — Departamento como entidade real, com Head e gestores adicionais (decisões 2 e 3)

**Entregável**: módulo Departamento completo (Fase 3.14 do `PROJECT_STATUS.md`), seguindo o padrão `Page → View → Table → Modal → FormSections`, já incluindo `headUsuarioId` e a tabela `DepartamentoGestor` (`07`, seção 3/3.1). `Usuario` ganha o campo `cargo` (`07`, seção 4) na mesma subtarefa, por ser pré-requisito direto de exibir/validar "Head" no cadastro de Departamento.

**Arquivos afetados (novos)**: `frontend/src/app/configuracoes/departamentos/page.tsx`, `frontend/src/components/departamentos/*`, `frontend/src/types/departamento.ts`, `frontend/src/lib/departamento-mock.ts`.

**Arquivo afetado (existente)**: `frontend/src/types/usuario.ts` — adiciona `cargo`.

**Depende de**: A1 (quando migrar de mock para API real).

**Risco herdado de `06`, conflito #10**: unificar os IDs de departamento hoje divergentes entre `projetos-mock.ts`/`demandas-mock.ts` (`dep-atendimento`) e `trafego-mock.ts` (`departamento-atendimento`).

**Critério de aceite**: uma única fonte de Departamentos usada por Usuários, Equipes, Projetos, Tarefa e Tráfego; `headUsuarioId` só aceita usuário com `perfil = Gestor` (ou superior); cadastro permite adicionar gestores adicionais via `DepartamentoGestor`; `cargo` de Usuario é um campo de texto livre, sem gerar nenhuma checagem de permissão a partir dele (a autoridade vem de `headUsuarioId`/`DepartamentoGestor`, conforme `07`, seção 4).

### 2.4 Subtarefa A4 — Squad como entidade real (decisão 4)

**Entregável**: `Squad`/`SquadMembro` (`07`, seção 5) como módulo completo, mesmo padrão de A3. **Sem `headUsuarioId`** — Squad não tem papel de liderança estrutural (decisão 3 reserva "Head" para Departamento); liderança de squad é só `SquadMembro.papel = "líder"`.

**Arquivos afetados (novos)**: `frontend/src/app/configuracoes/squads/page.tsx`, `frontend/src/components/squads/*`, `frontend/src/types/squad.ts`, `frontend/src/lib/squad-mock.ts`.

**Arquivo afetado (existente)**: `frontend/src/types/usuario.ts:63` — campo `squad: string` removido de `UsuarioDraft`, substituído pela associação via `SquadMembro`.

**Depende de**: A1. (A ambiguidade Squad-vs-Equipe registrada na revisão anterior deste plano está resolvida pela decisão 4 — não é mais uma dependência de decisão pendente.)

**Critério de aceite**: cadastro de Squad funcional; nenhum componente restante lê `UsuarioDraft.squad` como string; a documentação/tela deixa clara a diferença entre Departamento, Equipe e Squad (`07`, seção 5, tabela comparativa) — por exemplo, um tooltip ou texto de ajuda no formulário de criação de Squad referenciando essa diferença.

### 2.5 Subtarefa A5 — `Responsavel` unificado, com papel fechado e Squad

**Entregável**: entidade `Responsavel` (`07`, seção 6) substituindo os arrays `usuarioResponsavelIds`/`departamentoResponsavelIds` hoje embutidos em `Demanda`/`DemandaWorkflowEtapa` e em `Projeto`.

**Arquivos afetados**: `frontend/src/types/demanda.ts` (remoção dos arrays — nome do arquivo só muda em A8, conforme Subtarefa 0), `frontend/src/types/projeto.ts`, `frontend/src/components/demandas/DemandaFormSections.tsx` (`ResponsaveisDemandaSection`, `WorkflowDemandaSection`), componentes equivalentes em Projetos.

**Depende de**: A3 (Departamento), A4 (Squad).

**Critério de aceite**: toda leitura de "quem é responsável por X" passa por uma função central (`getResponsaveis(entidadeTipo, entidadeId)`); existe no máximo um `Responsavel` com `papel = principal` por tarefa (validado por teste).

### 2.6 Subtarefa A6 — Elegibilidade ampla e sugestões priorizadas de atribuição (decisão 5, nova)

**Entregável**: regra de domínio "qualquer usuário ativo da empresa é elegível para ser `Responsavel`, participação no Projeto não é pré-requisito" (`07`, seção 6.1) aplicada no picker de atribuição; membros de `Projeto.equipe`/Departamento/Squad da tarefa aparecem priorizados no topo da lista, sem restringir os demais.

**Arquivos afetados**: `frontend/src/components/ui/MultiSelect.tsx` (ou variante especializada) ganha suporte a "grupos sugeridos" no topo da lista; `ResponsaveisDemandaSection`/`WorkflowDemandaSection` passam a alimentar esses grupos a partir de `Projeto.equipe`/Departamento/Squad da tarefa em edição.

**Depende de**: A5.

**Nota de escopo transitório**: nesta subtarefa, "escopo de permissão" ainda não está implementado (isso é E2) — a versão inicial libera todo usuário ativo da empresa sem filtro de escopo, o que é aceitável como estado transitório mas deve ser tratado como incompleto, não como comportamento final (`07`, seção 6.1, riscos).

**Critério de aceite**: o picker de atribuição mostra qualquer usuário ativo da empresa, com membros de Projeto/Departamento/Squad da tarefa destacados no topo; nenhum usuário fora desses grupos é bloqueado de seleção.

### 2.7 Subtarefa A7 — Motor de Eventos mínimo + Histórico unificado

**Entregável**: `Evento` (`02`, seção 6.1) capturando `entidade.criada`/`atualizada`/`excluida` para Tarefa, Projeto, Cliente, Usuário, Departamento, Squad; Histórico como projeção sobre `Evento` substituindo os 5 tipos de histórico mock hoje duplicados.

**Arquivos afetados**: `HistoricoDemandaSection` (`DemandaFormSections.tsx:522-554`) e as 4 seções equivalentes em outros módulos.

**Depende de**: A1.

**Critério de aceite**: toda operação de CRUD nos módulos migrados gera exatamente um `Evento`; nenhum tipo de histórico duplicado remanescente.

### 2.8 Subtarefa A8 — Tarefa: renomear e migrar tipo central, persistir

**Entregável**: tipo `Tarefa` (`07`, seção 8) real, com `titularidade`, sem os arrays de responsável (migrados em A5), sem `workflowEtapas` embutido (migra na Fase B). **É aqui que a renomeação `Demanda` → `Tarefa` acontece de fato** (Subtarefa 0): `types/demanda.ts` → `types/tarefa.ts`, `components/demandas/*` → `components/tarefas/*`, `lib/demandas-mock.ts` → `lib/tarefas-mock.ts`.

**Arquivos afetados**: todos os listados acima; troca de array em memória por chamada de API real, mantendo a mesma assinatura de componente sempre que possível.

**Decisão pendente a resolver nesta subtarefa** (nenhuma das 12 decisões a resolveu — ver `07`, seção 14, item 8): `Tarefa.clienteId` redundante com `Tarefa.projeto.clienteId` — este plano recomenda remover `Tarefa.clienteId` e resolver sempre via join com `Projeto`.

**Depende de**: A5, A6, A7.

**Critério de aceite**: CRUD de Tarefa 100% migrado de mock para API real, com paridade funcional; nenhuma referência restante a `Demanda`/`demanda` em nome de arquivo, tipo ou componente novo.

---

## 3. Fase B — Workflow da Tarefa (equivalente à Fase 1 tardia + Fase 4 de `03`, recorte Tarefa)

### 3.1 Subtarefa B1 — `Workflow`/`WorkflowVersao` reais (básico)

**Entregável**: substituir o array hardcoded de `frontend/src/app/configuracoes/workflows/page.tsx:11` por `Workflow` + `WorkflowVersao` (`07`, seção 7.1-7.2) persistidos, sem ainda os 10 campos avançados de etapa (isso é B2). Os 3 workflows hoje hardcoded viram seed inicial.

**Depende de**: A1.

**Critério de aceite**: `/configuracoes/workflows` deixa de ser hardcoded; criar uma nova versão de um workflow não altera etapas de tarefas já iniciadas sob a versão anterior.

### 3.2 Subtarefa B2 — `WorkflowEtapaTemplate` com os 10 campos de regra (decisão 8)

**Entregável**: `WorkflowEtapaTemplate` ganha `tipoEtapa`, `responsaveisPadrao` (via `WorkflowEtapaTemplateResponsavelPadrao`), `departamentoPadraoId`/`squadPadraoId`, `requisitosObrigatorios`, `acaoAoAprovar`, `acaoAoAjustar`, `etapaRetornoReprovacaoId`, `permissaoAvancoPerfil`, `prazoRelativoHoras`, `etapaFinal` (`07`, seção 7.3).

**Arquivos afetados**: tela de configuração de workflow (`/configuracoes/workflows`) ganha os campos, com os avançados (`requisitosObrigatorios`, `acaoAoAjustar`, `etapaRetornoReprovacaoId`, `permissaoAvancoPerfil`) recolhidos por padrão numa seção "avançado", com defaults sensatos.

**Depende de**: B1, A3 (Departamento), A4 (Squad).

**Critério de aceite**: criar uma etapa de template com todos os campos preenchidos funciona; deixar só os campos básicos preenchidos aplica os defaults documentados em `07`, seção 7.3, sem erro.

### 3.3 Subtarefa B3 — `TarefaEtapa` como tabela própria, com snapshot dos campos de B2

**Entregável**: substituir `Demanda.workflowEtapas: DemandaWorkflowEtapa[]` (array embutido) por `TarefaEtapa` (`07`, seção 7.4), com `workflowVersaoOrigemId` na Tarefa e snapshot dos 10 campos de B2 no momento da instanciação.

**Arquivos afetados**: `WorkflowDemandaSection` (`DemandaFormSections.tsx:208-460`) passa a operar sobre a nova tabela via API.

**Depende de**: B2, A8.

**Critério de aceite**: forma de dado equivalente à atual (baixo risco de migração), agora relacional; instanciar uma tarefa a partir de um template snapshota os 10 campos corretamente (mudar o template depois não altera a tarefa já criada).

### 3.4 Subtarefa B4 — `RevisaoCiclo` com 6 resultados e registro completo (decisão 7)

**Entregável**: entidade nova (`07`, seção 7.5) com `origem`, `resultado` (7 valores incluindo `pendente`), `motivo`, `comentario`, `responsavelSolicitanteId`, `responsavelExecucaoId`, `novoPrazo`, `tratamentoChecklist`. **Núcleo entregue sem depender de Anexo** — a relação `RevisaoCicloAnexo` (arquivos/versões) é uma extensão que só fica plenamente utilizável após a Subtarefa C3 (Anexos), sem bloquear esta entrega.

**Arquivos afetados (novos)**: `frontend/src/components/demandas/RevisaoCicloSection.tsx` (nova aba em `DemandaDetailsDrawer.tsx`, que hoje tem só 5 abas — `06`, seção 1.3).

**Depende de**: B3.

**Critério de aceite**: uma tarefa pode ter 2+ ciclos de revisão na mesma etapa sem mudar `etapaAtualId`; os 6 resultados (`aprovado`, `ajuste_solicitado`, `refacao_parcial`, `refacao_completa`, `reprovado`, `cancelado`) estão disponíveis e cada um aciona a consequência estrutural certa (`acaoAoAprovar`/`acaoAoAjustar`/`etapaRetornoReprovacaoId`, conforme B2); relatório simples "ajustes internos vs. cliente" funciona.

### 3.5 Subtarefa B5 — Nome de revisão configurável por empresa

**Entregável**: `NomenclaturaConfiguravel` (`07`, seção 7.6), começando só pela chave `revisao`. Reforço da decisão 7: só o rótulo muda por empresa, o conceito técnico (`RevisaoCiclo`) é fixo em todo o sistema.

**Depende de**: A1.

**Critério de aceite**: alterar o rótulo de "Revisão" para outro texto em uma empresa não afeta o rótulo padrão de outra empresa; nenhum nome de tipo/tabela/endpoint muda com essa configuração.

### 3.6 Subtarefa B6 — Reconciliar Kanban (eliminar as 3 implementações paralelas)

**Entregável**: um único Kanban, orientado por `etapaAtualId` (via `TarefaEtapa`), não por `status` — corrigindo `06`, conflito #6.

**Ações concretas**:
- Remover `frontend/src/components/kanban/*` (implementação antiga, órfã, tipo `KanbanTask` próprio).
- Reescrever `DemandasKanban.tsx`/`DemandaKanbanColumn.tsx` (renomeados em A8) para agrupar por `TarefaEtapa`.
- Adicionar drag-and-drop real (persistindo transição de etapa via API), hoje ausente na implementação nova (somente leitura).

**Depende de**: B3.

**Critério de aceite**: existe exatamente um componente de Kanban de Tarefa no repositório; mover um cartão persiste mudança de `etapaAtualId`; nenhuma coluna é definida por `status` livre.

---

## 4. Fase C — Cartão completo da Tarefa (recorte Tarefa da Fase 3 de `03`)

### 4.1 Subtarefa C1 — Checklist e Subtarefa

**Entregável**: `Checklist`/`ChecklistItem`/`Subtarefa` (`02`, seção 5) aplicados a Tarefa.

**Arquivos afetados**: nova aba em `DemandaDetailsDrawer.tsx`.

**Depende de**: A8.

### 4.2 Subtarefa C2 — Comentários

**Entregável**: `Comentario` (`02`, seção 9.2) aplicado a Tarefa, com menção disparando `Notificacao` básica.

**Depende de**: A8, A7 (Evento).

### 4.3 Subtarefa C3 — Anexos

**Entregável**: `Anexo` (`02`, seção 9.1) aplicado a Tarefa. **Conclui, por consequência, a relação `RevisaoCicloAnexo` de B4** (arquivos/versões por ciclo de revisão passam a funcionar de ponta a ponta).

**Depende de**: A8; decisão de infraestrutura de armazenamento (fora do escopo deste documento).

### 4.4 Subtarefa C4 — Timeline da Tarefa

**Entregável**: `Timeline` (`02`, seção 6.3) combinando `Evento` + `Comentario` + `Anexo` + `RevisaoCiclo`.

**Depende de**: C1, C2, C3, B4.

**Critério de aceite comum a C1-C4**: `DemandaDetailsDrawer` passa a ser o único ponto de detalhe de Tarefa, com as 4 abas novas funcionando de ponta a ponta.

---

## 5. Fase D — Pautas (decisões 6/9/10)

### 5.1 Subtarefa D1 — Consultas de pauta (backend)

**Entregável**: as 6 consultas descritas em `07`, seção 9 (Minha, Minha de Hoje, Departamento, Squad, Head, Geral), implementadas como endpoints de leitura (`GET /tarefas/pauta?tipo=minha|minha_hoje|departamento|squad|head|geral`).

**Depende de**: A3 (Departamento), A4 (Squad), A5 (Responsavel), A2 (Autenticação — **já satisfeita dentro da Fase A**, não é mais um bloqueio externo como na revisão anterior deste plano), B3 (TarefaEtapa).

**Critério de aceite**: cada consulta reflete exatamente o escopo descrito em `07`, seção 9, com usuário autenticado real (não simulado) — possível porque A2 já entrega autenticação antes desta subtarefa.

### 5.2 Subtarefa D2 — Telas de pauta (frontend)

**Entregável**: nova navegação (substituindo ou complementando o único item "Tarefas" hoje em `Sidebar.tsx:45`) com alternância entre Minha, Departamento, Squad, Head e Geral.

**Depende de**: D1.

**Critério de aceite**: cada pauta reflete o escopo correto; nenhuma pauta mostra etapa futura antecipadamente.

### 5.3 Subtarefa D3 — Dashboard: "Minha Pauta de Hoje" (decisão 10, nova)

**Entregável**: substituir o widget "Atividades Recentes" do Dashboard por "Minha Pauta de Hoje", exibindo tarefa, cliente, projeto, etapa, status e prazo com data/hora, conforme a consulta de `07`, seção 9. Métricas gerais (hoje hardcoded em `DashboardStats.tsx`: `tarefas: 128, projetos: 24, clientes: 86, sla: 97`) deixam de ser exibidas indiscriminadamente — usuário `Operador` sem escopo ampliado vê só o widget de pauta.

**Nota de contexto**: o repositório já tem, no momento deste plano, um refactor de Dashboard em andamento fora do escopo desta tarefa de documentação (arquivos novos como `DashboardRecentActivity.tsx`, `DashboardKPIs.tsx` — não tocados por este documento). Esta subtarefa deve ser coordenada com esse trabalho em andamento, não duplicá-lo; o componente mais próximo do requisito (`DashboardRecentActivity.tsx` ou equivalente vigente na hora da implementação) é o candidato natural a virar "Minha Pauta de Hoje".

**Depende de**: D1, E2 (para a regra de "não exibir métrica geral indiscriminadamente" — ver Fase E).

**Critério de aceite**: Dashboard de um usuário `Operador` mostra Minha Pauta de Hoje e não mostra métricas agregadas de outros clientes/projetos; Dashboard de um usuário com escopo ampliado (Gestor/Admin) pode mostrar ambos.

---

## 6. Fase E — Permissões de Tarefa por escopo e temporárias

### 6.1 Subtarefa E1 — Alinhar `PerfilAcesso` com a documentação

**Entregável**: resolver a divergência já registrada em `06`, seção 6.5, entre os 6 perfis documentados (`CLAUDE.md`) e os 9 valores hoje em `frontend/src/lib/access-control.ts:13-22`.

**Critério de aceite**: `CLAUDE.md`/`PROJECT_STATUS.md` e `access-control.ts` descrevem a mesma lista de perfis.

### 6.2 Subtarefa E2 — `PermissaoEscopo` aplicada a Tarefa

**Entregável**: `PermissaoEscopo` (`07`, seção 11.1) checada nos endpoints de Tarefa. **Completa a Subtarefa A6**: a partir daqui, a elegibilidade de atribuição (decisão 5) passa a respeitar escopo de fato, não só "qualquer usuário ativo".

**Depende de**: E1, A6, A8.

### 6.3 Subtarefa E3 — `PermissaoTemporaria`

**Entregável**: `PermissaoTemporaria` (`07`, seção 11.2) funcionando sobre Tarefa, com expiração automática checada em tempo de leitura.

**Depende de**: E2.

**Critério de aceite comum a E1-E3**: uma permissão temporária concedida e expirada deixa de ter efeito imediatamente após `validoAte`; toda concessão/revogação gera `Evento` auditável.

---

## 7. Fase F — Projeto: histórico agregado e resumo de status

### 7.1 Subtarefa F1 — Rollup de eventos (histórico agregado)

**Entregável**: consultas de histórico agregado descritas em `07`, seção 10, expostas nas abas "Histórico" já existentes de `ProjetoDetailsDrawer.tsx` e da tela de Cliente.

**Depende de**: A7 (Evento), A8 (Tarefa persistida).

**Critério de aceite**: a aba Histórico de um Projeto mostra, sem ação manual, eventos das Tarefas filhas; o mesmo para Cliente subindo por Projeto.

### 7.2 Subtarefa F2 — Projeto: prazo opcional e resumo de Tarefas por status (decisão 6, nova)

**Entregável**: `Projeto.dataInicio`/`dataFimPrevista` tornam-se opcionais; nova projeção `TarefaStatusResumo` (`07`, seção 8) exposta na tela de Projeto com as 5 categorias: ativas, pausadas, aguardando aprovação, concluídas, canceladas.

**Arquivos afetados**: `frontend/src/types/projeto.ts` (campos passam a `nullable`), `frontend/src/components/projetos/ProjetoDetailsDrawer.tsx` (nova seção de resumo).

**Depende de**: A8, B3 (TarefaEtapa), B4 (RevisaoCiclo — necessário para derivar `aguardando_aprovacao`).

**Critério de aceite**: criar um Projeto sem prazo não bloqueia salvamento; a tela de Projeto mostra contagem correta nas 5 categorias.

---

## 8. Fase G — Experiência por papel (decisão 9, nova)

### 8.1 Subtarefa G1 — Home/Dashboard roteado por papel e cargo

**Entregável**: Home/Dashboard prioriza conteúdo conforme `07`, seção 12: Operador vê Minha Pauta de Hoje e execução; Head/Gestor vê Departamento/Squad/carga/gargalos; Atendimento (`cargo = "Atendimento"`) vê clientes/projetos/aprovações/prazos/SLA; Admin vê configuração/permissões/visão geral. Reforça a decisão 9 de que Atendimento é cargo + experiência, não um novo valor de `PerfilAcesso`.

**Depende de**: D1-D3 (pautas), E1-E2 (permissões), F2 (SLA/aprovações), A3 (`cargo`).

**Critério de aceite**: as 4 combinações de papel/cargo descritas em `07`, seção 12, testadas manualmente, mostram Home coerente com a decisão; nenhuma delas expõe métrica geral de cliente/projeto/SLA para um usuário puramente `Operador` (reforça D3/decisão 10).

---

## 9. Ordem de dependência consolidada

```
Subtarefa 0 (estratégia de renomeação — já decidida)
   │
   ▼
A1 (backend mínimo) ──► A2 (autenticação real) ──► A3 (Departamento+Head+cargo) ──► A4 (Squad)
                                                                                          │
                                                                                          ▼
                                                                                    A5 (Responsavel)
                                                                                          │
                                              A7 (Eventos/Histórico) ◄───────────────────┤
                                                                                          ▼
                                                                                  A6 (elegibilidade)
                                                                                          │
                                                                                          ▼
                                                                                  A8 (Tarefa persistida)
                                                                                          │
        ┌─────────────────────────────────────────────────────────────────────────────────┤
        ▼                                                                                  ▼
B1 (Workflow/Versão) ──► B2 (etapa: 10 campos) ──► B3 (TarefaEtapa) ──► B4 (RevisaoCiclo)   E1 (perfis) ──► E2 (Escopo) ──► E3 (Temporária)
        │                                               │                    │
        ▼                                               ▼                    ▼
     B5 (nomenclatura)                              B6 (Kanban único)    C1-C4 (Checklist/Comentário/Anexo/Timeline)
                                                                                          │
                                                                                          ▼
                                                                          D1 (consultas de pauta) ──► D2 (telas) ──► D3 (Minha Pauta de Hoje)
                                                                                          │                              │
                                                                                          ▼                              │
                                                                          F1 (histórico agregado)   F2 (resumo de status)◄┘
                                                                                          │                              │
                                                                                          └──────────────┬───────────────┘
                                                                                                          ▼
                                                                                                   G1 (experiência por papel)
```

Fases B, C, D e E podem correr em paralelo entre si depois que A8 estiver concluída — a única serialização estrita é dentro da Fase A (A1→A2→A3→A4→A5→A7→A6→A8, na ordem indicada no diagrama) e dentro de cada fase individual.

---

## 10. Riscos de migração consolidados

1. **Maior risco do plano inteiro**: primeiro contato do backend com dado real de Tarefa — erro de modelagem na Fase A se propaga para B, C, D, E, F, G.
2. **Autenticação antecipada (A2) é uma exceção deliberada** à regra geral de fase — precisa de comunicação clara às demais frentes do projeto (`07`, riscos, item 4).
3. **Reconciliar 3 Kanbans (B6) e 4 universos de mock de Departamento (A3)** continuam sendo as subtarefas de maior risco de regressão visual perceptível — validar manualmente em navegador antes de remover componente antigo.
4. **Redundância `Tarefa.clienteId`/`Tarefa.projeto.clienteId`** (A8) segue sem decisão das 12 aprovadas — precisa de decisão explícita própria antes de A8 fechar.
5. **`RevisaoCiclo` (B4) e `EtapaSessaoTempo` (Fase 5 de `03`)** têm sobreposição conceitual — decidir o relacionamento antes de implementar B4.
6. **10 campos novos por etapa de workflow (B2)** — risco de sobrecarga de UI; mitigação de seção avançada recolhida já registrada em `07`, seção 7.3.
7. **Redundância `departamentoPadraoId`/`squadPadraoId` (etapa) vs. `Tarefa.titularidade`** — regra de precedência (etapa sobrepõe tarefa) precisa estar clara antes de B2/B3.
8. **Critério `refacao_parcial` vs. `refacao_completa` (B4)** não tem definição de negócio neste plano — validar antes de fechar como regra automática.
9. **Nenhuma subtarefa deve ser considerada concluída apenas por compilar** — critério de aceite de cada subtarefa é funcional (comportamento observável), conforme o checklist obrigatório do `CLAUDE.md`.

---

## 11. Confirmação de escopo deste documento

- Nenhum arquivo de código foi criado, alterado ou removido para produzir este plano.
- Nenhuma migration, model ou endpoint foi criado.
- Este documento não deve ser executado sem aprovação explícita, subtarefa por subtarefa, conforme `AGENTS.md`.
