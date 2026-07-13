# 03 — Roadmap Técnico de Implementação

> Documento de planejamento. Não contém código, migration ou implementação.
> Base: [`00-estado-atual.md`](./00-estado-atual.md), [`01-motores-centrais.md`](./01-motores-centrais.md), [`02-modelo-dados-futuro.md`](./02-modelo-dados-futuro.md).
> Objetivo: transformar a arquitetura conceitual em 6 fases técnicas, na ordem de prioridade definida pelo usuário. Nenhuma fase deste documento foi executada — é um plano, sujeito a aprovação explícita antes de qualquer alteração de código, conforme `AGENTS.md`.

---

## 0. Como usar este documento

- A ordem das 6 fases é fixa e foi definida externamente a este documento — não é reordenada aqui, mesmo onde a arquitetura (doc `01`) sugeriria outra sequência de dependência técnica pura.
- Cada fase referencia entidades definidas em `02-modelo-dados-futuro.md` e arquivos reais hoje existentes no repositório (mapeados em `00-estado-atual.md`).
- **Entidades do modelo de dados não citadas explicitamente pelo usuário em nenhuma das 6 fases** (`SlaRegra`, `Tag`/`EntidadeTag`, `FiltroSalvo`, `Notificacao`/`PreferenciaNotificacao`) foram alocadas por aderência temática, e essa alocação é sinalizada explicitamente em cada fase — não é uma decisão silenciosa. Resumo:

| Entidade não citada explicitamente | Fase alocada | Motivo |
|---|---|---|
| `PreferenciaNotificacao` | Fase 1 | Baixo risco, independente das demais, já existe como tela mock pronta para persistir |
| `Tag` / `EntidadeTag` | Fase 2 | Uso natural como indicador/filtro de cartão |
| `FiltroSalvo` | Fase 2 | Está literalmente sob "filtros" |
| `SlaRegra` (config) | Fase 4 | Base de regra usada em automação/aprovação |
| `SlaRegra` (comparação real vs. meta) / `Notificacao` (alertas) | Fase 5 e Fase 6 | Dependem de dado real de tempo (Fase 5) e de mecanismo proativo (Fase 6, "alertas") |

- Toda fase segue a mesma estrutura de análise: objetivo, entregáveis, arquivos provavelmente afetados, entidades necessárias, APIs, frontend, backend, riscos, testes, critério de aceite, dependências da fase anterior.

---

## Fase 1 — Fundação

### Objetivo

Sair do estado atual (100% frontend + mock, backend só com healthcheck) para uma base real de persistência, cobrindo os elementos que todas as demais fases dependem: eventos, histórico, responsáveis por ID, Equipes/Departamentos como entidades reais, e a estrutura mínima de Workflow (sem regras avançadas ainda).

### Entregáveis

- Backend real com models, schemas e rotas para: `Usuario`, `Equipe`, `Departamento`, `Cliente`, `Fornecedor`, `Grupo de Clientes`, `Projeto`, `Demanda` (CRUD básico).
- Módulo **Departamentos** criado do zero (Fase 3.14 do `PROJECT_STATUS.md`, ainda não iniciada) — primeira entidade nova de verdade nesta fase.
- Entidade `Responsavel` funcionando para Demanda e Projeto (usuário e departamento; equipe pode ficar para o fim da fase, já que depende de `Equipe` estar migrada).
- Entidade `Evento` capturando `entidade.criada`/`entidade.atualizada`/`entidade.excluida` para ao menos Usuário, Cliente, Equipe, Departamento, Projeto e Demanda.
- Histórico (projeção sobre `Evento`, conforme `02`, seção 6.2) substituindo os 5 tipos de histórico mock hoje duplicados.
- `Workflow`/`WorkflowEtapaTemplate`/`DemandaEtapa` como estrutura base persistida (sem `WorkflowRegraTransicao` ainda — isso é Fase 4).
- `PreferenciaNotificacao` persistida (baixo risco, item isolado — ver tabela da seção 0).

### Arquivos provavelmente afetados

- `backend/main.py` deixa de ser um arquivo único e passa a precisar de estrutura própria (`backend/app/models/`, `backend/app/schemas/`, `backend/app/routers/`, `backend/app/core/` ou equivalente) — hoje inexistente.
- `frontend/src/lib/usuario-mock.ts`, `cliente-mock.ts`, `equipe-mock.ts`, `fornecedor-mock.ts`, `grupo-cliente-mock.ts`, `projetos-mock.ts`, `demandas-mock.ts` — todos precisam trocar array em memória por chamada real de API.
- `frontend/src/types/*.ts` — tipos já existentes tendem a se manter compatíveis (ver `02`), mas precisam de ajuste para refletir `Responsavel` como relação em vez de array simples de IDs, quando a UI passar a mostrar quem adicionou/quando.
- Novo módulo completo de Departamentos, espelhando o padrão de Equipes: `frontend/src/app/configuracoes/departamentos/page.tsx`, `frontend/src/components/departamentos/*`, `frontend/src/types/departamento.ts`.
- `frontend/src/components/demandas/DemandaFormSections.tsx` (`HistoricoDemandaSection`) e equivalentes em Cliente/Equipe/Usuário/Projeto — passam a ler de uma API de histórico unificada em vez do array `historico` embutido no mock.
- `frontend/src/components/conta/NotificacoesView.tsx` — passa a persistir via API em vez de `useState` local.
- `docker-compose.yml` **não muda de forma estrutural** (mesmos serviços), mas o comando de instalação de dependências do `taskfloww_api` provavelmente cresce (Alembic, se adotado).

### Entidades necessárias

`Responsavel`, `Evento`, `Workflow`, `WorkflowEtapaTemplate`, `DemandaEtapa`, `PreferenciaNotificacao`, além da criação da entidade **Departamento** (hoje só existe como `DepartamentoOption` informal em `types/usuario.ts`).

### APIs

- CRUD REST por entidade de cadastro: `/usuarios`, `/clientes`, `/equipes`, `/departamentos`, `/fornecedores`, `/grupos-clientes`, `/projetos`, `/demandas`.
- `/responsaveis` (associar/remover responsável de uma Demanda/Projeto/Etapa).
- `/eventos` (consulta interna/administrativa) e `/historico?entidadeTipo=...&entidadeId=...` (leitura).
- `/workflows`, `/workflows/{id}/etapas` (CRUD de template, sem endpoint de transição ainda — isso é Fase 4, mas a leitura de etapas já é necessária para a Fase 2 montar colunas).
- `/preferencias-notificacao`.

### Frontend

- Substituir chamadas a mock por chamadas de API mantendo a mesma assinatura de componente sempre que possível (para não quebrar `View`/`Table`/`Modal` já existentes).
- Adicionar módulo de Departamentos seguindo à risca o padrão `Page → View → Table → Modal → FormSections` já usado em Usuários/Clientes/Equipes.
- Ajustar seções de histórico para consumir a API unificada.

### Backend

- Primeira estrutura real de projeto FastAPI (routers, models SQLAlchemy, schemas Pydantic) — hoje inexistente.
- Primeira migration real (Alembic ou equivalente) — hoje não há nenhuma.
- Emissão de evento centralizada (ex.: um serviço/dependency único chamado por todos os routers de CRUD, para não repetir a lógica de "gravar evento" em cada endpoint individualmente).

### Riscos

- Maior risco de todo o roadmap por ser o primeiro contato do backend com dado real: qualquer erro de modelagem aqui se propaga para as 5 fases seguintes.
- Migrar 7 módulos de frontend (Usuários, Clientes, Equipes, Fornecedores, Grupos de Clientes, Projetos, Demandas) de mock para API real ao mesmo tempo é um escopo grande — recomenda-se migrar um módulo por vez e validar antes de avançar para o próximo, mesmo dentro desta fase.
- Departamentos é dependência bloqueante de Usuários/Equipes/Projetos (todos referenciam `departamentoId`) — se for deixado por último dentro da fase, os demais módulos ficam com relacionamento quebrado ou fictício até lá.
- Risco de regressão visual/funcional: `AGENTS.md`/`docs/skills/architecture.md` proíbem misturar regra de negócio com componente visual — ao trocar mock por API, garantir que a camada de dado fique isolada (hooks/serviços), não embutida nas Views.

### Testes

- Testes unitários de model/schema (validação de campos obrigatórios, `empresaId`, `createdAt`/`updatedAt`).
- Testes de integração de CRUD por entidade (criar, ler, atualizar, excluir/inativar) rodando contra banco de teste real (Postgres, não mock).
- Teste de contrato entre schema Pydantic e tipo TypeScript correspondente (mesma forma de campo) para os 7 módulos migrados.
- Teste específico de emissão de evento: toda operação de CRUD deve gerar exatamente um `Evento` correspondente.
- Teste de isolamento multiempresa (`empresaId` diferente não deve vazar dado entre consultas).

### Critério de aceite

- Departamentos existe como módulo completo, real, com CRUD funcional.
- Ao menos um módulo de cadastro (recomenda-se começar por Usuários ou Equipes) está 100% migrado de mock para API real, com histórico funcionando a partir de `Evento`.
- Toda operação de CRUD nos módulos migrados gera um evento auditável.
- `DemandaEtapa`/`Workflow` existem como tabela real, ainda que sem regra de transição (Fase 4).
- Nenhum módulo ainda migrado quebrou funcionalmente em relação ao comportamento mock anterior (paridade funcional).

### Dependências da fase anterior

Nenhuma — esta é a fase inicial. Depende apenas dos três documentos de arquitetura já produzidos (`00`, `01`, `02`).

---

## Fase 2 — Kanban

### Objetivo

Conectar o Kanban (hoje um protótipo isolado, com dado hardcoded e sem rota que o monte) ao dado real de Demandas produzido na Fase 1, com colunas derivadas do Workflow, ordenação persistida, filtros e indicadores no cartão.

### Entregáveis

- Colunas do Kanban derivadas de `WorkflowEtapaTemplate`/`DemandaEtapa` reais (não mais um array fixo de 4 strings).
- Drag-and-drop persistindo mudança de etapa via API (não apenas estado local do React).
- Ordenação manual de cartões dentro da coluna, persistida (`KanbanCartaoPosicao`).
- Filtros reais: cliente, projeto, responsável, prioridade, atraso, etapa (nenhum existe hoje no Kanban).
- Indicadores visuais no cartão: atraso, tags (`Tag`/`EntidadeTag`), prioridade — mantendo a regra de "card enxuto" já documentada.
- Filtros salvos (`FiltroSalvo`) para reuso rápido de combinações frequentes.
- Uma rota real que monte o Kanban dentro da navegação (hoje não existe nenhuma).

### Arquivos provavelmente afetados

- `frontend/src/components/kanban/KanbanBoard.tsx` — reescrita para consumir `Demanda` real via API em vez do array `initialTasks` hardcoded.
- `frontend/src/components/kanban/KanbanColumn.tsx` — colunas passam a vir de `WorkflowEtapaTemplate`, não de config fixa.
- `frontend/src/components/kanban/KanbanCard.tsx` — ajuste de props para o formato real de `Demanda` (hoje usa `KanbanTask`, com campos como `client`/`assignee` que não existem no tipo `Demanda`).
- `frontend/src/components/kanban/TaskDetailModal.tsx` — decisão a tomar nesta fase ou adiar para a Fase 3: manter como modal simplificado de visualização rápida, ou já aposentar em favor do `DemandaDetailsDrawer` (recomendado em `01`, mas o drawer completo só ganha todas as abas na Fase 3).
- `frontend/src/components/demandas/DemandasToolbar.tsx` — estendido com os filtros de Kanban (hoje só tem filtro de status).
- Nova página/rota (ex.: `frontend/src/app/tarefas/kanban/page.tsx` ou toggle de visão dentro de `/tarefas`) — nenhuma rota monta `KanbanBoard` hoje.

### Entidades necessárias

`KanbanColuna`, `KanbanCartaoPosicao`, `Tag`, `EntidadeTag`, `FiltroSalvo` — todas consumindo `Demanda`/`DemandaEtapa`/`Responsavel` já criados na Fase 1.

### APIs

- `GET /demandas?escopo=projeto|equipe|colaborador&cliente=&prioridade=&atraso=&etapa=` — listagem filtrada para o board.
- `GET /kanban/colunas?workflowId=` — configuração de colunas do workflow ativo.
- `PATCH /demandas/{id}/etapa` — transição de etapa (o "mover card" do Kanban chama este endpoint, não um endpoint próprio de Kanban).
- `PATCH /kanban/posicao` — atualizar `KanbanCartaoPosicao` (ordem dentro da coluna).
- `/tags`, `/filtros-salvos` (CRUD simples).

### Frontend

- Três modos de visão (projeto/equipe/colaborador), conforme requisito documentado em `docs/requirements/projetos-demandas-dashboard.md`.
- Reaproveitar a base de drag-and-drop já funcional (`@dnd-kit/core`) — não reescrever a mecânica, só a fonte de dado.
- Reaproveitar o visual do `KanbanCard` (já alinhado à regra de card enxuto), adicionando os novos indicadores sem poluir o card.

### Backend

- Endpoint de transição de etapa precisa, desde já, aplicar a regra de visibilidade (colaborador só vê a etapa em que está) — mesmo sem as regras avançadas de transição da Fase 4.
- Lógica de posição fracionária (ou reordenação em lote) para `KanbanCartaoPosicao`, evitando renumeração de todos os cartões a cada movimento.

### Riscos

- **O risco mais citado nos documentos anteriores**: religar o Kanban sem garantir que ele nunca introduza um modelo de dado próprio novamente. Qualquer atalho que reintroduza um tipo paralelo a `Demanda` repete o erro já diagnosticado em `01`.
- Performance ao carregar todas as demandas de uma empresa sem paginação/filtro padrão aplicado por escopo.
- Condição de corrida em reordenação simultânea por múltiplos usuários (mitigação sugerida em `02`: posição fracionária).
- Filtro por "atraso" depende de comparação de data em tempo real — se o cálculo de prazo não estiver bem definido (depende da Fase 1/Fase 4), o indicador de atraso pode ficar incorreto.

### Testes

- Teste end-to-end de arrastar um cartão entre colunas e verificar que a etapa foi persistida no backend (não apenas no estado local).
- Teste de que mover um cartão para uma transição não permitida (quando a Fase 4 não existir ainda, toda transição é permitida — testar esse comportamento explicitamente como esperado nesta fase).
- Teste de filtro combinando múltiplos critérios simultaneamente.
- Teste de carga (volume de demandas) para validar que o board não degrada com centenas de cards.
- Teste de reordenação concorrente (dois usuários movendo cartões na mesma coluna ao mesmo tempo).

### Critério de aceite

- Kanban acessível por uma rota real, exibindo demandas reais (não mock) agrupadas pelas etapas reais do Workflow aplicado.
- Mover um cartão altera a etapa da Demanda de forma persistida e refletida no `DemandaDetailsDrawer`/tabela de Demandas.
- Filtros funcionam e podem ser salvos/reaplicados.
- Cartão exibe indicadores de atraso/prioridade/tag sem violar a regra de "card enxuto".

### Dependências da fase anterior

Depende integralmente da Fase 1: sem `Workflow`/`DemandaEtapa`/`Responsavel`/`Evento` reais, o Kanban não tem de onde derivar colunas nem para onde persistir a transição de etapa.

---

## Fase 3 — Cartão completo

### Objetivo

Transformar o detalhe de uma Demanda (hoje dividido entre `DemandaDetailsDrawer`, incompleto, e `TaskDetailModal`, um paralelo simplificado dentro do Kanban) em uma experiência única e completa, incorporando Checklist, Subtarefas, Comentários, Anexos e Timeline — nenhum desses cinco existe hoje.

### Entregáveis

- `DemandaDetailsDrawer` ganha as abas **Checklist**, **Subtarefas**, **Comentários**, **Anexos** e **Timeline**, além das já existentes (Dados, Briefing, Workflow, Responsáveis, Histórico).
- `TaskDetailModal` (Kanban) é **aposentado** em favor do `DemandaDetailsDrawer` único — elimina a divergência entre as duas UIs de detalhe apontada em `01`.
- Upload real de anexo (decisão de armazenamento — local/volume Docker ou serviço externo — a ser tomada nesta fase, hoje inexistente até para Projeto além da listagem mock).
- Comentários com menção de usuário, gerando notificação básica (primeira aparição real de `Notificacao`, ainda que simples).
- Timeline funcional combinando Evento + Comentário + Anexo + Sessão de tempo (esta última só populada de fato a partir da Fase 5 — nesta fase, a Timeline já existe estruturalmente, mas com menos fontes de dado).

### Arquivos provavelmente afetados

- `frontend/src/components/demandas/DemandaDetailsDrawer.tsx` — novas abas adicionadas ao array `tabs`.
- `frontend/src/components/demandas/DemandaFormSections.tsx` — novos componentes de seção: `ChecklistDemandaSection`, `SubtarefasDemandaSection`, `ComentariosDemandaSection`, `AnexosDemandaSection`, `TimelineDemandaSection` (nomenclatura a confirmar na implementação).
- `frontend/src/components/kanban/TaskDetailModal.tsx` — remoção/substituição por reaproveitamento do `DemandaDetailsDrawer` a partir do Kanban.
- `frontend/src/types/demanda.ts` — tipo `Demanda` não precisa crescer diretamente (Checklist/Subtarefa/Comentário/Anexo são entidades filhas, carregadas à parte), mas os tipos desses novos conceitos precisam ser criados (`checklist.ts`, `subtarefa.ts`, `comentario.ts`, `anexo.ts`).
- `frontend/src/components/projetos/ProjetoDetailsDrawer.tsx` — a aba "Arquivos" já existente pode ser migrada para consumir a mesma API real de `Anexo` desta fase (hoje é mock).

### Entidades necessárias

`Checklist`, `ChecklistItem`, `Subtarefa`, `Comentario`, `Anexo`, Timeline (projeção, sem tabela própria), `Notificacao` (versão inicial, disparada por menção em comentário).

### APIs

- `/demandas/{id}/checklists`, `/checklists/{id}/itens` (CRUD).
- `/demandas/{id}/subtarefas` (CRUD).
- `/demandas/{id}/comentarios` (criar/editar/listar; menção dispara notificação).
- `/demandas/{id}/anexos` (upload/listar/remover).
- `/demandas/{id}/timeline` (leitura agregada).
- `/projetos/{id}/anexos` (migração da aba "Arquivos" já existente para a API real).

### Frontend

- Reaproveitar `EntitySidePanel`/`Tabs`/`WorkspaceSection` já existentes (componentes de UI já maduros no design system atual) para as novas abas, mantendo consistência visual.
- Componente de upload de arquivo novo (não existe nenhum hoje em nenhuma tela).
- Componente de "linha do tempo" reutilizável (mencionado como recomendação em `02`), que pode também vir a ser usado em Projeto/Cliente no futuro.

### Backend

- Serviço de armazenamento de arquivo (decisão de infraestrutura: volume local via Docker, ou serviço externo de storage — impacta `docker-compose.yml`, mas a decisão em si está fora do escopo deste documento).
- Lógica de disparo de `Notificacao` ao detectar menção em `Comentario.mencionados`.
- Agregação de Timeline (consulta combinada, conforme desenhado em `02`, seção 6.3) — avaliar performance antes de decidir por view simples vs. projeção materializada.

### Riscos

- Upload de arquivo introduz superfície de ataque nova (validação de tipo/tamanho, antivírus, controle de acesso ao arquivo) — risco de segurança real que must ser tratado explicitamente na implementação (fora do escopo deste roadmap, mas citado como ponto de atenção).
- Timeline combinando 4 fontes pode ficar lenta em demandas com muito histórico (já sinalizado como risco em `02`).
- Retirar `TaskDetailModal` do Kanban sem testar todos os fluxos de uso pode gerar regressão perceptível para quem já usa o board.
- Notificação de menção exige que `PreferenciaNotificacao` (Fase 1) já esteja funcionando corretamente — se o canal "Sistema" não estiver de fato habilitado por padrão, a funcionalidade parece "quebrada" sem estar.

### Testes

- Teste de criação/edição/remoção de item de checklist e cálculo de progresso (ex.: "3 de 5 concluídos").
- Teste de subtarefa vinculada a uma demanda, incluindo exclusão em cascata quando a demanda-pai é removida.
- Teste de upload de anexo com arquivo válido e inválido (tipo/tamanho não permitido).
- Teste de comentário com menção gerando exatamente uma notificação por usuário mencionado.
- Teste de Timeline retornando itens ordenados corretamente de múltiplas fontes.

### Critério de aceite

- `DemandaDetailsDrawer` é o único ponto de detalhe de uma Demanda (Kanban e tabela abrem o mesmo componente).
- Checklist, Subtarefas, Comentários e Anexos funcionam de ponta a ponta com persistência real.
- Timeline exibe, em ordem cronológica, ao menos eventos + comentários + anexos de uma demanda real.
- Menção em comentário gera notificação visível para o usuário mencionado (respeitando sua preferência de canal).

### Dependências da fase anterior

Depende da Fase 1 (Demanda/Evento reais) e da Fase 2 (drawer precisa ser acionável a partir do Kanban de forma unificada, sem duplicar com `TaskDetailModal`).

---

## Fase 4 — Workflow avançado

### Objetivo

Adicionar as regras de negócio que hoje não existem no Motor de Workflow: transições permitidas/negadas, campos obrigatórios por etapa, bloqueio formal (regra, não medição de tempo — isso é Fase 5), aprovações e automações simples.

> **Distinção importante**: "bloqueios" aparece tanto na Fase 4 quanto na Fase 5 do roadmap solicitado, e isso não é redundância — são duas coisas diferentes. Nesta fase, "bloqueio" é a **regra de negócio** (uma demanda pode ser marcada como bloqueada, exigindo motivo e, possivelmente, aprovação para desbloquear). Na Fase 5, "bloqueio" é a **medição real de tempo** que a demanda passou bloqueada (`EtapaSessaoTempo.tipo = bloqueio`), usada para relatórios de produtividade.

### Entregáveis

- `WorkflowRegraTransicao` funcionando: cada transição de etapa passa a ser validada contra uma matriz de regras (livre, requer aprovação, requer checklist completo).
- Campos obrigatórios por etapa: uma etapa pode exigir que determinados campos da Demanda (ou o Checklist da Fase 3) estejam preenchidos/concluídos antes de permitir avanço — **conceito novo, não coberto em `02`**, identificado como lacuna nesta fase (ver seção "riscos" abaixo).
- Fluxo de aprovação: perfil aprovador definido por regra de transição, com registro de aprovação/rejeição como evento.
- Automações simples: reação a um evento de workflow disparando uma ação (ex.: "ao concluir etapa X, notificar responsável da etapa Y") — **conceito também novo, não coberto em `02`**, exigindo uma entidade adicional (ex.: `WorkflowAutomacao`: gatilho, condição, ação) a ser desenhada em detalhe quando esta fase for de fato planejada.
- `SlaRegra` como configuração real (substituindo o array hardcoded de `/configuracoes/sla`), consumida pelas regras de transição para calcular prazo esperado.

### Arquivos provavelmente afetados

- `frontend/src/app/configuracoes/workflows/page.tsx` — deixa de ser hardcoded e passa a ser a tela real de configuração de `Workflow`/`WorkflowEtapaTemplate`/`WorkflowRegraTransicao` (unificando a divergência apontada em `01`).
- `frontend/src/app/configuracoes/sla/page.tsx` — passa a consumir `SlaRegra` real em vez do array `slaRules` hardcoded.
- `frontend/src/components/demandas/DemandaFormSections.tsx` (`WorkflowDemandaSection`) — passa a respeitar as regras de transição (ex.: desabilitar/avisar quando uma transição não é permitida, em vez de aceitar qualquer mudança de etapa atual livremente, como hoje).
- Novo componente de configuração de regra de transição e automação (não existe hoje nenhuma tela equivalente).

### Entidades necessárias

`WorkflowRegraTransicao`, `SlaRegra`; **duas entidades novas a especificar nesta fase** (fora do escopo do `02`, que não previu campos obrigatórios nem automação como conceitos): algo como `EtapaCampoObrigatorio` e `WorkflowAutomacao`.

### APIs

- `/workflows/{id}/regras-transicao` (CRUD).
- `/demandas/{id}/etapas/transicionar` — agora valida regra de transição, campos obrigatórios e aprovação antes de aplicar (o mesmo endpoint da Fase 2 ganha validação real).
- `/workflows/{id}/automacoes` (CRUD).
- `/sla-regras` (CRUD).
- `/demandas/{id}/etapas/{etapaId}/aprovar` e `/rejeitar`.

### Frontend

- Feedback visual claro quando uma transição é bloqueada por regra (mensagem explicando o motivo: aprovação pendente, campo obrigatório faltante, checklist incompleto).
- Tela de configuração de automação simples (gatilho → ação), voltada a perfis Admin/Gestor.

### Backend

- Motor de validação de transição centralizado (não espalhar a regra em múltiplos endpoints) — importante para não repetir o erro de duplicação já visto no histórico mock (5 implementações quase idênticas).
- Motor de automação precisa de cuidado especial com **idempotência** (uma automação não deve disparar a mesma ação duas vezes para o mesmo evento) e com **prevenção de loop** (automação A não deve poder disparar um evento que reative automação A indefinidamente).

### Riscos

- Regras de transição mal configuradas podem travar uma demanda sem nenhuma transição válida disponível — recomenda-se sempre existir uma transição de exceção administrativa (já registrada como recomendação em `02`).
- Campos obrigatórios e automações são conceitos **não modelados em `02-modelo-dados-futuro.md`** — esta fase precisa de uma iteração de modelagem de dados própria antes da implementação (uma extensão pontual do documento `02`, não coberta aqui).
- Automação mal desenhada (loop, cascata de reatribuição) é o maior risco técnico novo desta fase — deve ter limite de repetição/circuit breaker desde o desenho inicial.
- Aprovação sem fallback humano claro pode criar gargalo operacional (demanda presa esperando aprovador ausente).

### Testes

- Matriz de teste de transição: para cada par (etapa origem, etapa destino), validar permitido/negado conforme `WorkflowRegraTransicao`.
- Teste de bloqueio de transição por campo obrigatório ausente.
- Teste de fluxo de aprovação completo (solicitar → aprovar → transição aplicada; solicitar → rejeitar → transição não aplicada).
- Teste de automação simples ponta-a-ponta, incluindo teste de não-repetição (idempotência) e de não-loop.
- Teste de cálculo de prazo esperado a partir de `SlaRegra`.

### Critério de aceite

- Workflow real bloqueia transições não permitidas pela matriz de regras.
- Etapa com campo obrigatório não preenchido não avança.
- Aprovação é registrada como evento auditável, com aprovador identificado.
- Ao menos uma automação real funciona de ponta a ponta sem loop ou duplicação.
- `/configuracoes/workflows` e `/configuracoes/sla` deixam de ser telas hardcoded.

### Dependências da fase anterior

Depende da Fase 1 (`Workflow`/`DemandaEtapa`/`Evento`), da Fase 2 (Kanban precisa refletir visualmente uma transição negada) e da Fase 3 (regra "requer checklist completo" depende do Checklist já existir).

---

## Fase 5 — Central de Tráfego

### Objetivo

Implementar a medição real de tempo por status — sessões de trabalho, início/fim automático, pausas e bloqueios medidos (não apenas a regra de negócio da Fase 4) — e transformar isso em indicadores gerenciais reais: tempo por responsável, carga por equipe e dashboard executivo com dado real (hoje só placeholders).

### Entregáveis

- `EtapaSessaoTempo` funcionando: toda mudança de status de uma Demanda abre/fecha automaticamente um intervalo de tempo, sem intervenção manual do usuário.
- Cobertura dos 5 tipos de intervalo definidos em `02`: trabalho, pausa, bloqueio (medição), espera por cliente, espera por fornecedor.
- **Extensão do enum `DemandaStatus`** para incluir `aguardando_fornecedor` (lacuna já registrada em `02`, seção 7.1) — pré-requisito direto para "espera por fornecedor" funcionar nesta fase.
- Relatório de tempo por responsável (quanto tempo cada usuário efetivamente trabalhou em cada etapa/demanda).
- Relatório de carga por equipe (quantidade de demandas ativas e tempo agregado por equipe).
- Dashboard gerencial real, substituindo os placeholders atuais (`DashboardChart` hoje é literalmente uma área reservada com `{/* TODO: integrar Chart.js */}`; `DashboardStats` hoje usa números hardcoded).
- Job de reconciliação para sessões "penduradas" (intervalo aberto sem fechamento, por falha de sistema).

### Arquivos provavelmente afetados

- `frontend/src/components/dashboard/DashboardChart.tsx` — sai do estado de placeholder, integra biblioteca de gráfico real (ainda não instalada no `package.json`) e consome dado real.
- `frontend/src/components/dashboard/DashboardStats.tsx` — números hardcoded (`tarefas: 128, projetos: 24, clientes: 86, sla: 97`) substituídos por agregação real.
- `frontend/src/app/relatorios/page.tsx` — deixa de ser `EmptyState` e passa a ter os relatórios descritos em `docs/requirements/projetos-demandas-dashboard.md` (seções 5 e 6): status por cliente/projeto, volume por projeto/colaborador, volume histórico, análise de projeto, análise de peças, performance de colaborador.
- Backend: ponto único de transição de etapa (já centralizado desde a Fase 4) precisa, agora, também abrir/fechar `EtapaSessaoTempo` como efeito colateral automático de cada transição.
- Novo job/worker de reconciliação (fora do ciclo de request HTTP — provável consumidor assíncrono usando Redis, hoje só usado para `ping`).

### Entidades necessárias

`EtapaSessaoTempo` (todos os tipos), consultas agregadas sobre ela e sobre `SlaRegra` para os relatórios — nenhuma tabela adicional estritamente necessária além do que já foi modelado em `02`, mas pode valer a pena avaliar uma tabela de projeção/agregação para performance de dashboard (materialização, não normativa nesta fase).

### APIs

- `/relatorios/tempo-por-responsavel`
- `/relatorios/carga-por-equipe`
- `/dashboard/indicadores` (dado real para `DashboardStats`/`DashboardChart`)
- `/relatorios/analise-projeto`, `/relatorios/analise-pecas`, `/relatorios/performance-colaborador` (conforme requisitos já documentados)
- Nenhum endpoint novo de escrita para `EtapaSessaoTempo` é exposto ao frontend — a abertura/fechamento é 100% automática, disparada internamente pela transição de etapa (regra explícita em `01`/`02`).

### Frontend

- Integração de biblioteca de gráfico (Chart.js é a única já citada como intenção no próprio código, via comentário `TODO`) — decisão de manter essa escolha ou avaliar alternativa cabe à implementação, não a este roadmap.
- Painéis de carga por equipe e tempo por responsável, prováveis novos componentes em `components/dashboard/` e/ou `components/relatorios/` (pasta ainda inexistente).

### Backend

- Lógica de abertura/fechamento automático de `EtapaSessaoTempo` acoplada ao endpoint de transição de etapa (mesmo ponto criado na Fase 4) — não deve haver dois lugares no código decidindo quando uma sessão abre/fecha.
- Job de reconciliação: identificar registros com `fimEm IS NULL` abertos há mais tempo que um limite configurável e fechá-los com uma marcação de "fechamento por reconciliação" (auditável, distinto de fechamento normal).
- Agregações de relatório (tempo por responsável, carga por equipe) provavelmente precisam de índice/consulta otimizada, dado o volume potencial de linhas em `EtapaSessaoTempo`.

### Riscos

- **Risco central já sinalizado em `02`**: se a automação de abrir/fechar sessão falhar silenciosamente, todos os relatórios de tempo desta fase ficam com dado distorcido — e esse tipo de erro é difícil de perceber sem o job de reconciliação e sem alertas de monitoramento.
- Extensão do enum `DemandaStatus` (`aguardando_fornecedor`) pode quebrar qualquer código que trate esse enum como fechado (filtros, gráficos, validações) — precisa de checagem cruzada em todo o código que usa `DemandaStatus` antes de liberar esta fase.
- Dashboard e relatórios reais aumentam a carga de consulta sobre o banco — se `EtapaSessaoTempo`/`Evento` crescerem rápido, consultas de agregação sem cache/índice adequado podem degradar performance geral do sistema, não só da tela de relatório.
- Carga por equipe mal calculada nesta fase pode alimentar decisões erradas de redistribuição automática na Fase 6 — a qualidade do dado aqui tem efeito cascata direto.

### Testes

- Teste de que cada transição de status abre e fecha `EtapaSessaoTempo` corretamente, para todos os 5 tipos.
- Teste de cálculo de duração (fim - início) e de agregação (soma por responsável, por equipe).
- Teste do job de reconciliação com sessão órfã simulada.
- Teste de regressão em qualquer lógica existente que dependa de `DemandaStatus` como enum fechado, após a extensão com `aguardando_fornecedor`.
- Teste de carga/performance das consultas de relatório com volume simulado de dados.

### Critério de aceite

- Toda mudança de status de Demanda gera automaticamente o intervalo de tempo correto em `EtapaSessaoTempo`, sem ação manual do usuário.
- Dashboard (`/`) e Relatórios (`/relatorios`) exibem dado real, não mais placeholder/hardcoded.
- Relatório de tempo por responsável e carga por equipe estão disponíveis e batem com o dado bruto de `EtapaSessaoTempo` (validação cruzada).
- Job de reconciliação está ativo e testado.

### Dependências da fase anterior

Depende fortemente da Fase 4: sem regras de transição maduras (quando uma etapa realmente "conclui", quando um bloqueio realmente termina), a medição de tempo desta fase fica incoerente — medir tempo sobre um motor de workflow ainda "livre" (sem regra) produz números pouco confiáveis. Depende também da Fase 1 (`Evento` como registro auxiliar de auditoria) e da Fase 3 (Timeline já preparada para incorporar os novos dados de sessão).

---

## Fase 6 — Inteligência

### Objetivo

Usar o histórico real acumulado (Fases 1–5) para alertar proativamente, prever atraso, sugerir redistribuição de carga e oferecer recomendações — a fase mais dependente de dado histórico maduro, e a única que introduz IA/modelo preditivo.

### Entregáveis

- Alertas proativos (prazo próximo, atraso detectado, sessão de espera por cliente/fornecedor além do esperado) — primeira aparição de `Notificacao` como mecanismo **proativo** (a Fase 3 já usava `Notificacao`, mas de forma reativa/simples, disparada por menção).
- Previsão de atraso por demanda/projeto, com base em `EtapaSessaoTempo` histórico e `SlaRegra`.
- Sugestão de redistribuição de responsável/equipe com base em carga (`Responsavel` + agregações da Fase 5) — **sempre como sugestão, nunca como ação automática nesta fase inicial** (ver riscos).
- Recomendações gerais (ex.: "esta etapa costuma atrasar quando o responsável X está sobrecarregado") — item mais aberto do roadmap, dependente de decisão de produto sobre até onde a "recomendação" deve ir.
- Avaliação explícita de uso de IA externa (LLM/API de terceiros) vs. modelo estatístico simples treinado internamente — decisão em aberto, não tomada por este documento.

### Arquivos provavelmente afetados

- `frontend/src/components/layout/HeaderActions.tsx`/`Header.tsx` — provável local de um indicador de alertas/notificações (sino), hoje inexistente.
- Novo módulo de dashboard executivo (citado como "Integrações Futuras" em `CLAUDE.md`: "Dashboard Executivo", "Inteligência Artificial").
- Backend: novo serviço desacoplado do CRUD principal (idealmente um processo/worker separado, não embutido nos routers de domínio), dado que modelos preditivos têm ciclo de vida e recursos diferentes de uma API CRUD comum.

### Entidades necessárias

Nenhuma nova entidade estrutural obrigatória além do que já existe (`Evento`, `EtapaSessaoTempo`, `Notificacao`, `Responsavel`), mas é provável a necessidade de uma entidade de **registro de recomendação/sugestão** (ex.: `Recomendacao`: tipo, entidade relacionada, score de confiança, criadaEm, aplicada — a ser modelada em detalhe quando esta fase for de fato planejada, fora do escopo do `02` atual).

### APIs

- `/alertas` (consulta e configuração de regras de alerta).
- `/previsoes/atraso?demandaId=` ou `?projetoId=`.
- `/recomendacoes/redistribuicao`.
- Nenhuma API desta fase deve **executar** uma ação de negócio diretamente (redistribuir responsável, por exemplo) sem confirmação humana — a API expõe sugestão, a ação de aplicar passa pelas APIs já existentes das fases anteriores (ex.: `/responsaveis`).

### Frontend

- Indicador de alerta na navegação (sino de notificação, badge de contagem).
- Tela/painel de recomendações, sempre com ação explícita do usuário para aceitar ("aplicar sugestão") — nunca aplicação silenciosa.

### Backend

- Job assíncrono de cálculo de previsão/recomendação, rodando fora do ciclo de request (Redis como fila, finalmente saindo do uso "só healthcheck" citado desde `00-estado-atual.md`).
- Se IA externa for adotada: camada de anonimização/mascaramento de PII antes de qualquer envio de dado para fora do ambiente (`Usuario` carrega CPF, dados bancários — risco já sinalizado em `01` e `02`).

### Riscos

- **Maior risco de todo o roadmap em termos de confiança do usuário**: previsões erradas ou recomendações ruins minam a credibilidade da funcionalidade — recomenda-se lançar com métrica de acurácia visível/documentada, não como "caixa-preta".
- Redistribuição automática de responsável é uma ação sensível (afeta pessoas, carga de trabalho, remuneração indireta) — **não deve ser automática nesta fase inicial**; deve sempre exigir confirmação humana (Gestor/Admin).
- Uso de IA externa implica dado sensível (PII de `Usuario`) potencialmente trafegando para fora do ambiente — exige avaliação de segurança e, possivelmente, anonimização antes de qualquer chamada externa.
- Dependência forte de volume histórico mínimo: se as Fases 1–5 não tiverem rodado por tempo suficiente antes desta fase começar, o modelo preditivo não tem dado suficiente para ser confiável — risco de cronograma, não só técnico.

### Testes

- Teste de geração de alerta para os cenários definidos (prazo próximo, atraso, espera excedida).
- Avaliação de acurácia do modelo de previsão de atraso contra um conjunto de validação histórico, com métrica documentada (não apenas "funciona/não funciona").
- Teste garantindo que nenhuma sugestão de redistribuição é aplicada sem confirmação explícita do usuário.
- Revisão de segurança específica para qualquer integração com serviço de IA externo, cobrindo tratamento de PII.

### Critério de aceite

- Alertas de prazo próximo e atraso funcionam corretamente e respeitam a preferência de notificação do usuário.
- Previsão de atraso está disponível com métrica de acurácia documentada e aceitável (limiar a definir com o negócio).
- Sugestão de redistribuição é visível, mas só aplicada mediante ação humana explícita.
- Nenhuma chamada a serviço de IA externo (se adotado) envia PII sem tratamento documentado.

### Dependências da fase anterior

Depende diretamente da Fase 5 (dado real de tempo/carga como insumo de qualquer previsão ou recomendação) e da Fase 1 (`Evento` como fonte histórica de contexto). É a fase mais dependente de tempo de maturação de dado, não só de código pronto — mesmo que implementada tecnicamente, pode não ter dado suficiente para funcionar bem logo de início.

---

## Resumo — visão de dependência entre fases

```
Fase 1 (Fundação)
   │  Entidades, Eventos, Histórico, Responsáveis, Departamentos, Workflow base
   ▼
Fase 2 (Kanban)
   │  Colunas reais, drag-and-drop persistido, filtros
   ▼
Fase 3 (Cartão completo)
   │  Checklist, Subtarefas, Comentários, Anexos, Timeline
   ▼
Fase 4 (Workflow avançado)
   │  Regras de transição, campos obrigatórios, aprovação, automação
   ▼
Fase 5 (Central de Tráfego)
   │  Medição real de tempo, dashboards e relatórios reais
   ▼
Fase 6 (Inteligência)
      Alertas, previsão, recomendação — depende de dado maduro das fases 1–5
```

Nenhuma fase deste roadmap foi implementada. Este documento é insumo para aprovação e planejamento — qualquer execução real deve seguir o workflow obrigatório já definido em `AGENTS.md` (plano curto, lista de arquivos, aprovação explícita antes de qualquer alteração).
