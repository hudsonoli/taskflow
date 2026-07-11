# 04 — Fase 1A: Motor de Eventos e Histórico

> Documento de análise arquitetural. Nenhum código foi implementado, nenhuma migration foi criada, nenhum arquivo existente (frontend, backend, Docker ou documentação) foi alterado, e o módulo Workflow não foi modificado.
> Lido integralmente antes da escrita: `00-estado-atual.md`, `00a-inventario-tecnico.md`, `00b-impacto-implementacao-eventos.md`, `01-motores-centrais.md`, `02-modelo-dados-futuro.md`, `03-roadmap-implementacao.md`, além de releitura direta do código de Demandas, Projetos, Clientes, Usuários, Workflow, backend, Docker e configuração.
> Convenção deste documento: cada afirmação é marcada como **[EXISTENTE]** (já está no código hoje), **[ALTERAÇÃO NECESSÁRIA]** (precisa mudar para a Fase 1A funcionar), **[RECOMENDAÇÃO]** (escolha de design sugerida, não obrigatória) ou **[RISCO]** (algo que pode dar errado se ignorado).
> Data da análise: 2026-07-11.

---

## 1. Estado atual

**[EXISTENTE]** O TaskFloww V2 é hoje uma aplicação frontend + mock. O backend (`backend/main.py`, 51 linhas) só expõe `GET /`, `GET /health`, `GET /status` — nenhum model, schema, router, service ou migration existe. Postgres (`taskfloww_db`, `postgres:16-alpine`) e Redis (`taskfloww_redis`, `redis:7-alpine`) estão de pé via `docker-compose.yml`, mas nenhuma tabela de negócio existe no banco e o Redis é usado apenas para `PING` de healthcheck.

**[EXISTENTE]** Desde `00-estado-atual.md`, o commit `80ba94f feat(workflow): adiciona motor de workflow mock` introduziu um motor de Workflow mock consideravelmente mais maduro: `frontend/src/components/workflows/{WorkflowEditor,WorkflowStepCard,WorkflowTemplateSelector,WorkflowTransitionControls,WorkflowHistory}.tsx`, `frontend/src/types/workflow.ts` e `frontend/src/lib/workflows-mock.ts`. Esse módulo **não é alterado neste documento** (instrução explícita), mas é analisado como fonte de conflito com o futuro Motor de Eventos (seções 4, 5, 12).

**[EXISTENTE]** Não há autenticação real. `frontend/src/lib/conta-mock.ts` define um `currentUser` fixo (`João Silva`, id `"1"`); `logout()` é `console.log("logout")`. Qualquer ator de evento hoje só pode ser um placeholder — não um usuário autenticado de verdade. Esta análise assume isso do início ao fim, conforme instruído.

**[EXISTENTE]** Nenhum teste automatizado existe (frontend ou backend) — confirmado em `00a-inventario-tecnico.md` e reconfirmado por busca direta (nenhum `jest`/`vitest`/`pytest` no repositório).

---

## 2. Modelos atuais relacionados a histórico

Levantamento direto do código, não apenas dos tipos — inclui verificação de **se o histórico é de fato escrito**, não só declarado.

| Tipo/local | Arquivo | Formato | É de fato populado ao criar/editar? |
|---|---|---|---|
| `DemandaHistoricoEvento` | `frontend/src/types/demanda.ts` | `id, usuarioId, usuario, acao, dataHora, ip, dispositivo` | **Sim** — `DemandasView.tsx`, função `createHistoricoDemanda`, chamada em `createDemandaFromDraft` e `updateDemandaFromDraft`. |
| `WorkflowTransicaoHistorico` | `frontend/src/types/workflow.ts` | `id, demandaId, etapaOrigemId, etapaDestinoId, usuarioId, dataHora, observacao?` | **Sim** — `frontend/src/lib/workflows-mock.ts`, função `createWorkflowTransitionHistory`, chamada por `WorkflowEditor.tsx` em `applyTemplate`, `transitionTo`, `blockCurrent`, `unblockCurrent`. |
| `ProjetoHistoricoEvento` | `frontend/src/types/projeto.ts` | `id, usuarioId, usuario, acao, dataHora, ip, dispositivo` | **Sim** — `ProjetosView.tsx`, função `createHistoricoProjeto`, chamada em `createProjetoFromDraft`/`updateProjetoFromDraft`. |
| `HistoricoCliente` | `frontend/src/types/cliente.ts` | `id, usuarioId, usuario, dataHora, dispositivo, ipOrigem` (nota: campo `ipOrigem`, não `ip` — divergência de nome já identificada em `00b`) | **Não.** `frontend/src/components/clientes/ClientesView.tsx` inicializa `historico: []` em toda criação (4 ocorrências, linhas 66/97/128/156) e nunca acrescenta entrada em edição. O array só é lido (linha ~380, exibição do último evento), nunca escrito além do vazio inicial. |
| `HistoricoEquipe` | `frontend/src/types/equipe.ts` | mesmo formato de `HistoricoCliente` | **Não.** `EquipesView.tsx` também só inicializa `historico: []` (6 ocorrências) e nunca acrescenta.|
| `HistoricoUsuario` | `frontend/src/types/usuario.ts` | `id, usuarioId, usuario, dataHora, dispositivo, ipOrigem, acao` | **Não, e pior: o dado é descartado.** `UsuariosView.tsx` usa um tipo **paralelo e mais simples**, `UsuarioRow` (`id, name, email, department, profile, agency, status`), definido no próprio arquivo. A função `draftToRow(draft: UsuarioDraft): UsuarioRow` (linha 94) converte o `UsuarioDraft` vindo do modal (que tem `historico`) para `UsuarioRow` **sem transportar `historico`** — o campo é descartado a cada save. `UsuarioFormSections.tsx` referencia `draft.historico` dentro do modal, mas esse dado nunca chega a ser persistido no estado da listagem. |
| `HistoricoFornecedor` (nome inferido) | `frontend/src/types/fornecedor.ts` | não lido campo a campo nesta rodada | `FornecedoresView.tsx` só lê `selectedFornecedor.historico` (linha ~307) para exibição — mesmo padrão de Cliente/Equipe (não escreve). |
| `DemandaSessaoTrabalhoConceitual` | `frontend/src/types/demanda.ts` | `id, demandaId, usuarioId, etapaId, inicioEm, pausaEm?, encerradaEm?, statusOrigem` — **formato de registro de sessão** | Não usado em nenhum componente (declarativo). |
| `WorkflowSessaoTrabalhoConceitual` | `frontend/src/types/workflow.ts` | `entradaEmEtapaAtualPodeIniciarSessao, pausaOuBloqueioPodeSuspenderSessao, saidaDaEtapaPodeEncerrarSessao` — **não é um registro, é uma política/regra booleana** | Não usado em nenhum componente. |

**[RISCO]** Os dois tipos conceituais de sessão de trabalho não são duplicatas no sentido estrito — são camadas conceituais diferentes (um é "formato de um registro de sessão", o outro é "regras sobre quando uma sessão pode existir"), mas foram criados em arquivos diferentes, em momentos diferentes, sem nenhuma referência cruzada entre si. Isso diverge da leitura de `00b`, que os trata como uma única categoria de duplicação — ver seção "divergências" no fechamento deste documento.

**[RISCO]** A tabela acima mostra que **histórico funcional hoje é muito mais inconsistente do que qualquer um dos documentos anteriores registrou explicitamente**: de 6 entidades com campo `historico`, só 2 (Demanda, Projeto) de fato escrevem uma entrada nova a cada ação do usuário; 3 (Cliente, Equipe, Fornecedor) nunca escrevem, e 1 (Usuário) tem o dado gerado no formulário mas **descartado antes de chegar ao estado da aplicação**. Isso é um achado novo desta análise, não presente em `00a` nem em `00b`.

---

## 3. Rotas e serviços atuais

**[EXISTENTE]** Backend: apenas as 3 rotas de healthcheck já citadas (`backend/main.py`). Nenhuma rota de negócio, nenhum service, nenhum router modular.

**[EXISTENTE]** Frontend: nenhuma chamada de API para nenhuma entidade — todo CRUD é local (`useState` inicializado a partir de `lib/*-mock.ts`). Não há `fetch`/`axios` em nenhum componente de módulo de negócio.

**[EXISTENTE]** "Serviço", no sentido de camada de negócio, não existe em nenhum dos dois lados. As funções mais próximas de um "service" são as funções puras dentro dos próprios componentes de View (`createDemandaFromDraft`, `createHistoricoDemanda`, `createWorkflowTransitionHistory` etc.) — todas acopladas ao componente React que as declara, não reaproveitáveis fora dele.

---

## 4. Pontos onde mudanças já são registradas

Consolidação da seção 2, organizada por "o que dispara o registro":

| Ação do usuário | Onde é capturada hoje | Isolada ou compartilhada? |
|---|---|---|
| Criar/editar Demanda | `createHistoricoDemanda` em `DemandasView.tsx` | Isolada — implementação própria, não reaproveita nada de Projeto. |
| Criar/editar Projeto | `createHistoricoProjeto` em `ProjetosView.tsx` | Isolada — mesma forma de dado que Demanda, código duplicado. |
| Aplicar/transicionar/bloquear/desbloquear Workflow | `createWorkflowTransitionHistory` em `workflows-mock.ts`, chamada por `WorkflowEditor.tsx` | Isolada — terceira implementação paralela, com campos diferentes (`etapaOrigemId`/`etapaDestinoId` em vez de `acao` livre). |
| Criar/editar Cliente, Equipe, Fornecedor | Nenhum lugar — `historico` é inicializado vazio e nunca mais escrito. | N/A — não há captura real. |
| Criar/editar Usuário | `UsuarioFormSections.tsx` popula `draft.historico` dentro do modal, mas `UsuariosView.tsx` descarta esse campo em `draftToRow`. | Capturado e depois perdido — pior caso, pois cria falsa sensação de que existe histórico. |

**[RISCO]** Três implementações independentes e incompatíveis de "registrar uma mudança" (Demanda, Projeto, Workflow) já existem hoje, cada uma com seu próprio formato e sua própria função geradora de ID (`generateId("hist-demanda")`, `generateId("hist-projeto")`, `generateId("workflow-transicao")`). Qualquer Motor de Eventos real precisa substituir as três, não apenas uma.

---

## 5. Lacunas

- **Nenhuma emissão de evento é transacional** — hoje, "registrar histórico" é só `array.push` em memória React, sem nenhuma garantia de atomicidade com a operação que o motivou (nem faria sentido ter, já que não há banco por trás).
- **Nenhum ator real** — todo `usuarioId`/`usuario` em histórico hoje é um valor mock fixo (`"user-1"`, `"Hudson Cunha"`, `"Ana Costa"` — variam por arquivo, sem relação com quem "realmente" clicou no botão, já que não há sessão).
- **Nenhuma distinção entre tipos de ator** — todo registro assume implicitamente um usuário humano; não há ator "sistema", "importação", "integração" ou "automação" em lugar nenhum do código atual.
- **Nenhuma correlação entre eventos relacionados** — não há `correlationId`/`causationId`/`requestId` em nenhum tipo atual; não é possível hoje, nem conceitualmente, saber que uma transição de workflow e uma notificação futura pertencem ao mesmo fluxo de negócio.
- **Nenhuma proteção de dado sensível** — nenhum dos tipos de histórico atuais tem qualquer mecanismo de mascaramento; o campo `acao`/`observacao` é texto livre, o que **já é, por si, um risco**: nada impede que um texto livre como "Alterou CPF de 123.456.789-00" acabe registrado hoje (não há exemplo disso no mock atual, mas o tipo permite).
- **Nenhuma tabela, nenhuma migration, nenhum model** — confirmado nas seções 1/3.
- **Nenhum consumidor de evento existe** (notificação real, timeline agregada, Central de Tráfego) — todos são apenas conceitos em documentação (`01`, `02`) ou tipos declarativos não usados (`DemandaSessaoTrabalhoConceitual`, `WorkflowSessaoTrabalhoConceitual`).

---

## 6. Modelo de dados proposto

**[ALTERAÇÃO NECESSÁRIA — mas só em documento; nenhuma migration é criada aqui]**

Uma única tabela `eventos`, **apenas para a Fase 1A** (Demandas, Projetos, Clientes, Usuários — CRUD genérico; workflow fica fora de escopo de escrita nesta fase, ver seção 12). Campos, com a proveniência de cada decisão:

| Campo | Tipo | Origem da exigência |
|---|---|---|
| `id` | `uuid`, PK | Identidade imutável do registro. |
| `event_version` | `int` | **Exigido explicitamente** pelo escopo desta fase — versão do formato do payload, para evolução futura sem quebrar consumidores antigos. |
| `entity_type` | `enum`/`text` não nulo | **Exigido explicitamente**. Valores nesta fase: `demanda`, `projeto`, `cliente`, `usuario`. |
| `entity_id` | `uuid` não nulo | **Exigido explicitamente**. |
| `action` | `text`/`enum` não nulo | **Exigido explicitamente**. Ver taxonomia na seção 11. |
| `actor_id` | `uuid`, nulo | **Exigido explicitamente**. Nulo quando `actor_type` não é `usuario`. |
| `actor_type` | `enum` não nulo | **Exigido explicitamente**. Valores: `usuario \| sistema \| importacao \| integracao \| automacao`. |
| `source` | `text` não nulo | **Exigido explicitamente**. Identifica o subsistema técnico que emitiu o evento (ex.: `api.demandas`, `worker.reconciliacao`, `import.csv`) — **diferente de `actor_type`**: `actor_type` responde "quem/o quê conceitualmente causou isso", `source` responde "qual componente técnico gravou isso". |
| `correlation_id` | `uuid`, nulo | **Exigido explicitamente**. Agrupa eventos da mesma operação de negócio. |
| `causation_id` | `uuid`, nulo | **Exigido explicitamente**. Aponta para o evento que causou diretamente este. |
| `request_id` | `uuid`, nulo | **Exigido explicitamente**. Amarra o evento a uma requisição HTTP específica (debug/tracing), distinto de `correlation_id` (que é de negócio, não técnico). |
| `occurred_at` | `timestamptz` não nulo | **Exigido explicitamente**. Quando o fato de negócio realmente ocorreu. |
| `empresa_id` | `uuid` não nulo | **[RECOMENDAÇÃO — adição além da lista literal do enunciado]**. Não foi listado explicitamente entre os campos obrigatórios pedidos, mas é uma regra transversal inegociável do projeto (`CLAUDE.md`: "Toda entidade principal deverá possuir... empresaId"). Sem isso, não há isolamento multiempresa em nenhuma consulta de evento — risco de vazamento de dado entre empresas. |
| `agencia_id` | `uuid`, nulo | **[RECOMENDAÇÃO]** — mesma lógica de `empresa_id`, seguindo o padrão já usado em `Demanda.agenciaId`/`Projeto.agenciaId`. |
| `recorded_at` | `timestamptz` não nulo, default `now()` | **[RECOMENDAÇÃO]** — quando a linha foi de fato persistida, distinto de `occurred_at` (útil para detectar backfill/reconciliação futura; não pedido explicitamente, mas de baixo custo e alto valor de diagnóstico). |
| `ip` | `text`, nulo | Requisito de auditoria já documentado em `CLAUDE.md` ("Auditoria... IP, Dispositivo"). Nulo por padrão nesta fase, pois não há request/contexto de autenticação real (ver seção 18). |
| `dispositivo` | `text`, nulo | Idem. |
| `valor_anterior` | `jsonb`, nulo | Diff mascarado — nunca dado sensível (ver seção 18). |
| `valor_novo` | `jsonb`, nulo | Idem. |
| `metadados` | `jsonb`, nulo | Contexto adicional livre (ex.: observação humana), também sujeito a mascaramento. |

**[RECOMENDAÇÃO]** `entity_type`/`action` como duas colunas separadas (em vez de um único campo composto tipo `"demanda.criada"`, como sugerido em `01-motores-centrais.md`/`02-modelo-dados-futuro.md`) — permite filtrar por entidade OU por ação de forma independente, sem parsing de string. Isso é um refinamento sobre o desenho anterior (`02`, campo único `tipo`), não uma contradição — a composição lógica `entity_type + action` continua equivalente ao `tipo` anterior.

**[EXISTENTE — reaproveitável]** O formato de campo (`usuarioId, dataHora, ip/ipOrigem, dispositivo, acao`) já usado em `DemandaHistoricoEvento`/`ProjetoHistoricoEvento` é o ponto de partida direto para `actor_id`/`occurred_at`/`ip`/`dispositivo`/`action` — não é um desenho do zero, é uma formalização do que já existe em 3 lugares diferentes.

---

## 7. Compatibilidade com banco atual

**[EXISTENTE]** Não há banco de negócio atual — `db_data/` é um volume Postgres vazio de schema de aplicação (nenhuma migration, nenhum model). Portanto "compatibilidade" aqui significa: a tabela `eventos` será a **primeira tabela de negócio** do projeto, não uma alteração de schema existente.

**[ALTERAÇÃO NECESSÁRIA]** Isso implica que a Fase 1A não é "compatível ou incompatível" com dado existente — é aditiva por definição. O ponto de atenção real de compatibilidade é: `entity_id` referencia `Demanda`/`Projeto`/`Cliente`/`Usuario`, entidades que **também não existem ainda como tabela real** (só como tipo TypeScript/mock). Ou seja, `eventos` e as tabelas das 4 entidades da Fase 1A precisam nascer **juntas**, na mesma leva de migrations — criar `eventos` isolada, sem as entidades que ela referencia, não tem utilidade prática.

**[RISCO]** Se `entity_id` for uma `FOREIGN KEY` real apontando para 4 tabelas diferentes (`demandas`, `projetos`, `clientes`, `usuarios`) — que é tecnicamente impossível com uma única coluna e uma única FK — a alternativa é **não ter FK de banco em `entity_id`**, mantendo a integridade referencial na camada de aplicação (mesmo trade-off já documentado em `02-modelo-dados-futuro.md`, seção 0, item 4, para o padrão `entidadeTipo`+`entidadeId`). Isso é assumido conscientemente aqui, não uma omissão.

---

## 8. Estratégia de migration

**[ALTERAÇÃO NECESSÁRIA — decisão a tomar, nenhuma migration criada]**

- Adotar Alembic (padrão de fato para SQLAlchemy) — decisão ainda não tomada no projeto (nenhuma ferramenta de migration está instalada ou mencionada em `docker-compose.yml`).
- Uma única migration inicial cria, na mesma transação de DDL: `empresas` (mínimo viável, já que `empresa_id` é FK obrigatória em tudo), `demandas`, `projetos`, `clientes`, `usuarios` (versões mínimas, sem todos os campos de `02-modelo-dados-futuro.md` — só o necessário para a Fase 1A existir) e `eventos`.
- Toda migration de `eventos` deve ter `downgrade()` explícito e testado (ver seção 26 — plano de rollback).
- **[RECOMENDAÇÃO]** Não usar Alembic `autogenerate` às cegas para a primeira migration — revisar manualmente o DDL gerado, dado que é a fundação de todo o schema futuro.
- **[DECISÃO PENDENTE]** Se as 4 entidades de negócio (Demanda, Projeto, Cliente, Usuário) ganham schema mínimo **nesta mesma migration** ou se são objeto de uma fase de modelagem própria antes — este documento assume que Evento não pode nascer sozinho (seção 7), mas não decide o desenho completo dessas 4 tabelas, que é escopo de um documento de modelagem próprio por entidade, não desta análise de Eventos/Histórico.

---

## 9. Serviço central de eventos

**[ALTERAÇÃO NECESSÁRIA]** Um único ponto de emissão no backend — por exemplo `backend/app/services/eventos.py` (caminho proposto, ainda não criado) — chamado por qualquer router de CRUD/transição, nunca duplicado por entidade. Responsabilidades:

1. Receber os campos de domínio (`entity_type`, `entity_id`, `action`, `actor_id`, `actor_type`, `valor_anterior`, `valor_novo`, `metadados`, `correlation_id?`, `causation_id?`).
2. Preencher automaticamente `id`, `event_version`, `occurred_at`, `recorded_at`, `request_id` (do contexto de request), `source` (do próprio router chamador).
3. **Aplicar mascaramento de campos sensíveis antes de serializar `valor_anterior`/`valor_novo`** (ver seção 18) — esta é a única porta de entrada para gravação, então é o único lugar que precisa garantir essa regra.
4. Persistir dentro da mesma transação de banco da operação que originou o evento (ver seção 16).
5. **Não** processar consumidores (notificação, timeline) de forma síncrona — apenas gravar o evento. Consumo é responsabilidade de leitura futura, não deste serviço (ver seção "preparar para notificações e Central de Tráfego", ao final da seção 9).

**[RECOMENDAÇÃO]** O serviço não deve expor um método genérico "grave qualquer coisa" para o frontend — ele é chamado internamente pelos routers de CRUD (`POST /demandas`, `PATCH /demandas/{id}` etc.), nunca por uma rota pública `POST /eventos` de uso livre (mesma conclusão de `00b`, mantida aqui: correta e reafirmada).

**Preparação para notificações e Central de Tráfego (sem implementar):** o serviço deve gravar o evento de forma que uma consulta futura (`SELECT` filtrado por `entity_type`/`action`/`occurred_at`) baste para alimentar notificação e cálculo de tempo por status — isso significa **não omitir `entity_type`/`action`/`occurred_at`/`actor_id` em nenhum evento**, mesmo quando esses consumidores ainda não existem. Nenhum consumidor é implementado nesta fase.

---

## 10. Contrato do evento

Resumo direto do modelo da seção 6, como "contrato" (o que qualquer emissor deve fornecer):

**Campos obrigatórios no momento da emissão** (fornecidos pelo código chamador): `entity_type`, `entity_id`, `action`, `actor_id` (ou nulo, se `actor_type` != `usuario`), `actor_type`, `source`, `empresa_id`.

**Campos opcionais no momento da emissão**: `correlation_id`, `causation_id`, `valor_anterior`, `valor_novo`, `metadados`, `agencia_id`.

**Campos preenchidos automaticamente pelo serviço, nunca pelo chamador**: `id`, `event_version`, `occurred_at` (a menos que a emissão seja um backfill explícito), `recorded_at`, `request_id`, `ip`, `dispositivo` (extraídos do contexto de request, quando existir).

**[DECISÃO PENDENTE]** Definir se `occurred_at` pode divergir de `recorded_at` em uso normal (ex.: emissão em lote/importação futura) ou se, na Fase 1A, os dois são sempre iguais (mais simples, recomendado para o primeiro corte).

---

## 11. Tipos de eventos iniciais

Escopo estrito da Fase 1A: CRUD genérico de Demanda, Projeto, Cliente, Usuário. **Não inclui eventos de Workflow** (fora de escopo — módulo não alterado, ver seção 12).

| `entity_type` | `action` | Dispara quando (hoje, no mock) |
|---|---|---|
| `demanda` | `criada` | Hoje: `createDemandaFromDraft` em `DemandasView.tsx`. |
| `demanda` | `atualizada` | Hoje: `updateDemandaFromDraft`. |
| `demanda` | `status_alterado` | **[RECOMENDAÇÃO]** ação específica, além de `atualizada` genérica — já que mudança de status é o dado mais relevante para relatórios futuros (SLA, Central de Tráfego). |
| `demanda` | `responsaveis_alterados` | **[RECOMENDAÇÃO]** idem, separado de `atualizada` genérica, pois "quem é responsável" é consultado com frequência isolada (regra de visibilidade). |
| `demanda` | `excluida`/`inativada` | **Não existe hoje nenhuma ação de exclusão na UI** — nenhum botão de excluir Demanda foi encontrado em `DemandasTable.tsx`/`DemandasView.tsx`. O tipo de evento é preparado, mas não tem hoje nenhum disparo real correspondente. |
| `projeto` | `criada` / `atualizada` / `status_alterado` / `responsaveis_alterados` / `excluida` | Mesmo raciocínio de Demanda; hoje só `criada`/`atualizada` têm disparo real (`ProjetosView.tsx`). |
| `cliente` | `criada` / `atualizada` / `excluida` | Hoje: nenhum disparo real de histórico (ver seção 2) — a Fase 1A precisa **introduzir** a emissão, não só migrar uma existente. |
| `usuario` | `criada` / `atualizada` / `excluida` | Hoje: histórico é gerado no formulário e descartado (`draftToRow`) — a Fase 1A corrige isso ao trocar o destino da gravação para o serviço de eventos em vez do `useState` de `UsuariosView.tsx`. |

**[DECISÃO PENDENTE]** Nomes exatos de `action` (`criada` vs. `criado`, concordância de gênero por entidade) — escolher uma convenção única (ex.: sempre particípio invariável tipo `criada`) antes de codificar, para não repetir a inconsistência de nomenclatura já vista em `HistoricoCliente.ipOrigem` vs. `DemandaHistoricoEvento.ip`.

---

## 12. Integração com demandas

**[EXISTENTE]** `Demanda.historico: DemandaHistoricoEvento[]` e `Demanda.workflow`/`Demanda.workflowHistorico: WorkflowTransicaoHistorico[]` (este último gerido inteiramente por `frontend/src/components/workflows/*`, módulo **não alterado** nesta fase).

**[ALTERAÇÃO NECESSÁRIA — futura, não agora]** Criar/editar Demanda (status, prioridade, responsáveis, briefing) deve emitir evento (`entity_type=demanda`) através do serviço central, substituindo `createHistoricoDemanda`.

**[CONFLITO IDENTIFICADO COM O WORKFLOW — análise, sem alteração]** `Demanda.workflow`/`workflowHistorico` continuam, nesta fase, **fora do Motor de Eventos**. Isso cria uma situação transitória deliberada: a aba "Histórico" de uma Demanda (dados gerais) passaria a vir de `eventos`, enquanto a aba "Workflow" (dentro da mesma `DemandaDetailsDrawer.tsx`) continua lendo `WorkflowTransicaoHistorico` diretamente do objeto `Demanda`, sem relação com `eventos`. Isso **não é um erro desta fase** — é uma decisão explícita de escopo (instrução: "não altere o módulo Workflow") — mas é um ponto de atenção real para quem for implementar: a Demanda passa a ter **duas fontes de histórico simultâneas e não relacionadas** por um período (histórico geral via evento, histórico de workflow via `WorkflowTransicaoHistorico`), até que uma fase futura (fora deste documento) decida se/como o Workflow passa a emitir eventos também.
**[DECISÃO PENDENTE]** Se, quando o Workflow for integrado (fase futura), `WorkflowTransicaoHistorico` é (a) substituído por eventos `entity_type=demanda, action=workflow_etapa_transicionada`, (b) mantido como tabela própria que também referencia `correlation_id` de um evento correspondente, ou (c) mantido intacto e apenas espelhado por um evento-sombra. Não decidir isso agora é aceitável; **decidir depois sem revisitar este documento não é** — a implementação futura do Workflow real precisa ler esta seção primeiro.

---

## 13. Integração com projetos

**[EXISTENTE]** `Projeto.historico: ProjetoHistoricoEvento[]`, hoje gerado por `createHistoricoProjeto` em `ProjetosView.tsx`.

**[ALTERAÇÃO NECESSÁRIA — futura]** Mesma substituição de Demanda: `entity_type=projeto`. Adicionalmente, `Projeto` tem campos hoje sem histórico nenhum (`resumo`, `modeloCampanha`, `equipe`, `arquivos` — abas do `ProjetoDetailsDrawer.tsx`) que, no modelo de eventos, poderiam gerar `action` mais específicas (`resumo_atualizado`, `equipe_alterada`, `arquivo_anexado`) — **fora do escopo mínimo da Fase 1A** (que cobre só `criada`/`atualizada`/`status_alterado`/`responsaveis_alterados`), mas citado aqui como extensão natural já visível no código atual.

---

## 14. Integração com clientes

**[EXISTENTE — e é o caso mais simples de corrigir]** Cliente hoje **não gera histórico nenhum** (seção 2). Não há função `createHistoricoCliente` a substituir — a Fase 1A **introduz** a emissão do zero em `ClientesView.tsx`, em vez de migrar algo que já funciona.

**[RISCO]** Por não haver nenhuma implementação de referência em Cliente hoje, há risco de a implementação futura reinventar um quarto formato de evento em vez de reaproveitar o serviço central — atenção explícita recomendada durante a implementação (não deste documento).

---

## 15. Integração com usuários

**[EXISTENTE — caso mais grave]** Usuário tem o pior estado dos quatro: o dado de histórico é produzido no formulário (`UsuarioFormSections.tsx`, via `draft.historico`) e **descartado** por `draftToRow()` em `UsuariosView.tsx` antes de chegar ao estado da aplicação (seção 2). Além disso, `UsuariosView.tsx` usa um tipo de listagem (`UsuarioRow`) diferente do tipo de formulário (`UsuarioDraft`) — a Fase 1A, ao introduzir eventos, deveria **também** parar de depender de `UsuarioRow` para não herdar essa perda de dado (nota: isso tangencia o módulo de Usuários em si, não o Motor de Eventos — citado aqui como achado relevante, não como escopo de alteração deste documento).

**[DECISÃO PENDENTE]** Se a correção do fluxo `UsuarioRow`/`UsuarioDraft` é pré-requisito da Fase 1A ou um item separado do roadmap de Usuários — recomenda-se tratar como pré-requisito, já que sem isso a emissão de evento de usuário nasce sobre uma base com bug de perda de dado já demonstrado.

---

## 16. Estratégia de transação

**[ALTERAÇÃO NECESSÁRIA]** Gravação do evento **na mesma transação de banco** da operação de negócio (`INSERT`/`UPDATE` da entidade + `INSERT` em `eventos`, um único `COMMIT`). Sem outbox, sem broker externo — Postgres local, uma transação, conforme exigido explicitamente no escopo desta análise.

**[RECOMENDAÇÃO]** Usar uma única sessão SQLAlchemy por request, com o `INSERT` de evento ocorrendo dentro do mesmo `with session.begin():` (ou equivalente) do `INSERT`/`UPDATE` da entidade — nunca em uma sessão/commit separado.

**[RISCO]** Se o evento for gravado em uma transação separada da entidade (ex.: "grave a entidade, depois tente gravar o evento"), abre-se uma janela onde a entidade muda de estado sem evento correspondente — exatamente o cenário que o Motor de Eventos existe para evitar. A recomendação é **fail-closed**: se o evento não puder ser gravado, a operação de negócio inteira deve falhar e reverter (ver seção 17).

---

## 17. Tratamento de falhas

**[RECOMENDAÇÃO — fail-closed para a escrita do evento]** Falha ao gravar o evento deve reverter a transação inteira (a mudança de entidade não se aplica). Justificativa: eventos são a única fonte de auditoria/histórico nesta arquitetura (seção 9 de `01-motores-centrais.md`) — permitir que uma entidade mude sem evento correspondente reintroduz, de forma pior, o mesmo problema que motivou esta fase (histórico incompleto, como hoje ocorre com Cliente/Equipe/Usuário).

**[DISTINÇÃO IMPORTANTE]** Isso vale para a **escrita do evento em si**, não para consumidores futuros do evento. Uma notificação (consumidor futuro) que falhe ao ser enviada **não deve** reverter a transação de negócio — o consumo de evento para notificação é assíncrono e desacoplado por natureza (não implementado nesta fase; apenas a distinção conceitual é fixada aqui para orientar o desenho futuro).

**[DECISÃO PENDENTE]** Comportamento em caso de erro de serialização do payload (`valor_anterior`/`valor_novo` não serializável em JSON) — recomenda-se falhar a operação (mesma lógica fail-closed) em vez de gravar um evento com payload nulo/corrompido silenciosamente.

---

## 18. Segurança e permissões

**[EXISTENTE]** Não há autenticação real (seção 1) — esta análise não assume nenhuma, conforme instruído.

**[ALTERAÇÃO NECESSÁRIA]** `actor_id` hoje só pode ser preenchido com um valor placeholder consistente (equivalente ao `currentUser.id` mock de `conta-mock.ts`, hoje `"1"`), com `actor_type = usuario` sempre nesta fase — **não simular múltiplos usuários reais diferentes através de eventos**, já que isso criaria uma falsa sensação de auditoria multiusuário que a aplicação não tem hoje.

**[ALTERAÇÃO NECESSÁRIA — mascaramento, exigido explicitamente]** Nenhuma senha, hash, token, dado bancário ou documento pessoal deve ser gravado em `valor_anterior`/`valor_novo`/`metadados`. Estratégia recomendada:

- **[RECOMENDAÇÃO]** Preferir **allowlist por `entity_type`** (lista explícita de quais campos daquela entidade podem entrar no diff) em vez de denylist de nomes sensíveis conhecidos. Denylist (bloquear `senha`, `cpf`, `rg`, `chavePix`, `banco`, `agencia`, `conta`, `token`, `hash` por nome) é mais simples de implementar primeiro, mas falha silenciosamente diante de um nome de campo novo não previsto — allowlist é mais seguro por padrão, ao custo de manutenção por entidade.
- **[DECISÃO PENDENTE]** Qual das duas estratégias adotar na Fase 1A. Dado que `UsuarioInformacoes` (`types/usuario.ts`) já modela CPF, RG, dados bancários e chave PIX, e que `usuario` é uma das 4 entidades desta fase, esta decisão **não pode ser adiada** para depois da primeira implementação — precisa estar definida antes do primeiro evento de `usuario` ser gravado.
- Nenhum dos tipos de histórico atuais (seção 2) tem qualquer mecanismo desse tipo — não há regressão a evitar, é uma proteção nova.

**[ALTERAÇÃO NECESSÁRIA]** Leitura de eventos/histórico deve, no futuro (quando existir permissão real), respeitar a mesma permissão de leitura da entidade associada — não implementado nesta fase (não há RBAC real), mas o desenho não deve impedir essa checagem depois (ex.: não expor `GET /eventos` sem nenhum filtro de escopo).

**[RISCO]** Sem RBAC real hoje, qualquer endpoint de consulta de evento criado nesta fase é, na prática, de acesso irrestrito dentro do ambiente — aceitável para um ambiente de desenvolvimento, mas deve ser documentado como dívida técnica explícita, não esquecido.

---

## 19. Impacto de performance

**[RISCO — moderado, aceitável na escala atual]** Toda escrita de entidade passa a gerar 2 `INSERT`s (entidade + evento) em vez de 1 — custo aceitável em volume de agência (não é um sistema de alto volume transacional), mas deve ser medido quando o volume real de Demandas/Projetos for conhecido.

**[RISCO — a médio prazo, não agora]** A tabela `eventos` cresce de forma monotônica e nunca é reduzida (imutabilidade, seção "definir imutabilidade" abaixo) — não é um problema da Fase 1A, mas uma estratégia de arquivamento/partição deve ser prevista como item de fase futura (não decidido aqui).

**[ALTERAÇÃO NECESSÁRIA]** Toda leitura de histórico por entidade (aba "Histórico" de Demanda/Projeto/Cliente/Usuário) precisa de paginação desde o primeiro dia — nenhuma tela atual pagina histórico hoje (os arrays mock são pequenos o suficiente para não precisar), mas uma tabela real cresce sem limite.

---

## 20. Índices necessários

| Índice | Motivo |
|---|---|
| `(empresa_id, entity_type, entity_id, occurred_at DESC)` | Consulta mais frequente: "histórico desta entidade, mais recente primeiro" — usada por todas as 4 integrações (seções 12–15). |
| `(empresa_id, entity_type, action, occurred_at DESC)` | Relatórios/filtros por tipo de ação dentro de uma empresa (ex.: "todas as demandas criadas este mês"). |
| `(correlation_id)` | Diagnóstico de fluxo — encontrar todos os eventos de uma mesma operação de negócio. |
| `(actor_id, occurred_at DESC)` | **[RECOMENDAÇÃO]** — não pedido explicitamente, mas necessário para uma futura consulta "minhas ações recentes" (base de dashboard pessoal). |

---

## 21. APIs necessárias

**[ALTERAÇÃO NECESSÁRIA — nenhuma implementada aqui]**

- `GET /eventos?empresaId=&entityType=&entityId=&action=&de=&ate=` — consulta administrativa/geral, paginada.
- `GET /{entityType}/{entityId}/historico` (ou `GET /eventos?entityType=&entityId=`) — alimenta diretamente as abas de histórico das 4 integrações.
- **Nenhum `POST /eventos` público.** A emissão ocorre exclusivamente dentro dos routers de CRUD de Demanda/Projeto/Cliente/Usuário, chamando o serviço central (seção 9) — conclusão de `00b` mantida e reafirmada aqui.

---

## 22. Componentes frontend afetados

**[NÃO ALTERADO NESTA FASE — apenas identificação para planejamento futuro]**

| Componente | Mudança futura esperada |
|---|---|
| `frontend/src/components/demandas/DemandasView.tsx` | `createHistoricoDemanda` seria substituído por chamada ao serviço/API de eventos. |
| `frontend/src/components/demandas/DemandaFormSections.tsx` (`HistoricoDemandaSection`) | Passaria a renderizar projeção de `eventos` filtrada por `entity_id`, em vez do array `demanda.historico`. |
| `frontend/src/components/projetos/ProjetosView.tsx` | Mesma substituição de `createHistoricoProjeto`. |
| `frontend/src/components/projetos/ProjetoFormSections.tsx` (seção de histórico) | Idem `HistoricoDemandaSection`. |
| `frontend/src/components/clientes/ClientesView.tsx` e `ClienteFormSections.tsx` | Passariam a **de fato** gravar/ler histórico, corrigindo a lacuna hoje existente (seção 14). |
| `frontend/src/components/usuarios/UsuariosView.tsx` e `UsuarioFormSections.tsx` | Precisariam parar de descartar `historico` em `draftToRow` (seção 15) — mudança tangencial ao módulo de Usuários, não só ao Motor de Eventos. |
| `frontend/src/components/workflows/*` | **Explicitamente fora desta fase** — nenhuma mudança prevista aqui (seção 12). |

Nenhum desses arquivos foi tocado nesta etapa.

---

## 23. Testes necessários

**[ALTERAÇÃO NECESSÁRIA — nenhum teste escrito aqui; projeto hoje não tem infraestrutura de teste em nenhum dos dois lados]**

- Backend (pytest, a introduzir): emissão de evento gera exatamente 1 linha; falha de gravação reverte a transação da entidade (seção 17); mascaramento nunca deixa passar campo sensível conhecido (teste de regressão fixando a lista de campos bloqueados); isolamento multiempresa (evento de uma empresa nunca aparece em consulta de outra); índice de entidade retorna em ordem cronológica correta.
- Contrato: schema Pydantic do evento equivalente ao tipo TypeScript correspondente (mesmo princípio já usado em `03-roadmap-implementacao.md`, Fase 1).
- **[DECISÃO PENDENTE]** Framework de teste backend (pytest é o candidato natural, mas não há nenhuma escolha registrada em nenhum documento do projeto até agora) e frontend (Vitest/Testing Library, se e quando o frontend também passar a consumir API real).

---

## 24. Ordem exata de implementação

Esta seção **corrige a ordem proposta em `00b`** (seção "divergências" abaixo detalha o porquê). Ordem recomendada para a Fase 1A, quando aprovada para execução (fora do escopo deste documento):

1. Decisão de nomenclatura de `action` e estratégia de mascaramento (seções 11, 18) — **decisões de produto/segurança antes de qualquer código**.
2. Modelagem mínima das 4 entidades (Demanda, Projeto, Cliente, Usuário) + tabela `eventos`, na mesma migration inicial (seção 8).
3. Estrutura backend modular mínima (`backend/app/{models,schemas,services,routers}`) — pré-requisito de qualquer código real, hoje inexistente.
4. Serviço central de eventos (seção 9), com mascaramento e transação (seções 16–18) já embutidos desde a primeira versão — não adicionados depois.
5. Router + service de uma única entidade piloto (recomendação: **Cliente**, não Demanda) — ver justificativa na seção de divergências.
6. Validar ponta a ponta: criar/editar Cliente via API real grava evento, aba de histórico lê da API.
7. Repetir para Usuário (com atenção ao bug de `draftToRow`), Projeto, Demanda (nesta ordem, dos casos mais simples aos mais acoplados a outros módulos).
8. Só então avaliar (fora desta fase) se/como o Workflow passa a emitir eventos — decisão pendente registrada na seção 12, não resolvida aqui.
9. Testes automatizados acompanhando cada etapa acima, não como item isolado ao final.

---

## 25. Critérios de aceite

- Tabela `eventos` existe, com todos os campos da seção 6, e é a única fonte de escrita de histórico para Demanda, Projeto, Cliente e Usuário.
- Toda criação/edição dessas 4 entidades grava exatamente um evento, na mesma transação, sem exceção.
- Nenhum evento contém senha, hash, token, dado bancário ou documento pessoal em `valor_anterior`/`valor_novo`/`metadados` — validado por teste automatizado, não só por revisão manual.
- Consulta de histórico por entidade responde paginada e ordenada por `occurred_at DESC`.
- Isolamento multiempresa validado por teste (evento de uma empresa nunca vaza para outra).
- O bug de descarte de `historico` em `UsuariosView.tsx` (`draftToRow`) deixa de existir — usuário passa a ter histórico real.
- Nenhuma rota pública `POST /eventos` de uso livre existe.
- O módulo Workflow continua funcionando exatamente como hoje, sem nenhuma alteração de comportamento (critério de não-regressão, já que ele está fora de escopo).

---

## 26. Plano de rollback

**[RECOMENDAÇÃO]**

- A migration da tabela `eventos` deve ter `downgrade()` que remove a tabela sem afetar `demandas`/`projetos`/`clientes`/`usuarios` — nenhuma FK de `entidade` para `eventos` (a relação é inversa: `eventos.entity_id` aponta para a entidade, nunca o contrário), então remover `eventos` nunca deveria cascatear para dado de negócio.
- Rollout aditivo: o serviço de eventos e as novas rotas de histórico devem coexistir, no primeiro momento, sem remover imediatamente os campos `historico`/`workflowHistorico` dos tipos atuais — a remoção desses campos legados é um passo posterior, só depois de validado que a leitura via API real está estável (evita quebrar build/telas que ainda referenciam o campo antigo durante a transição).
- Se o serviço de eventos precisar ser desativado temporariamente (ex.: bug crítico na gravação), a recomendação é **desativar a escrita de eventos via flag de aplicação e, nesse modo, também recusar a operação de negócio associada** — consistente com a estratégia fail-closed da seção 17 — em vez de permitir CRUD "sem auditoria temporariamente", o que reintroduziria silenciosamente o problema que esta fase resolve.
- Nenhuma migration deste documento foi criada — o plano de rollback aqui é preparatório (o que a migration real deve garantir quando escrita), não uma ação já tomada.

---

## Divergências entre `00a-inventario-tecnico.md` e `00b-impacto-implementacao-eventos.md`

Ambos os documentos concordam no diagnóstico central: há históricos paralelos incompatíveis (Demanda, Projeto, Workflow) e nenhuma infraestrutura de backend real. As divergências relevantes para a Fase 1A:

1. **Ordem de implementação.** `00b` (seção "Ordem recomendada de implementação", itens 1–7) propõe começar pelo **frontend**: taxonomia → `types/evento.ts` → `lib/eventos-mock.ts` → adaptar Demandas → adaptar `WorkflowEditor` → componente genérico de timeline → migrar Projetos/cadastros — **e só then** (itens 8–10) estruturar o backend, criar migrations e o service real. Esta análise **corrige essa ordem** (seção 24): eventos existem para garantir imutabilidade e transação atômica — propriedades que um array em memória React (`eventos-mock.ts`) **não pode oferecer**, pelo mesmo motivo já diagnosticado em `00a-inventario-tecnico.md` (seção 9, "Gargalos": o estado local hoje já se perde entre navegações). Adotar a ordem de `00b` arriscaria exatamente o que a instrução desta tarefa veta explicitamente: "não tratar os mocks atuais como persistência". A ordem correta é backend primeiro (schema + migration + service transacional), frontend depois.
2. **Duplicação de sessão de trabalho conceitual.** `00b` (seção 8, tabela "Riscos") trata `WorkflowTransicaoHistorico`, `DemandaHistoricoEvento` e "tipos conceituais de sessão" como uma única categoria de risco ("três fontes de verdade para auditoria/tempo"). Esta análise (seção 2) diferencia com mais precisão: `DemandaSessaoTrabalhoConceitual` é um **formato de registro**, enquanto `WorkflowSessaoTrabalhoConceitual` é um **conjunto de regras/política** — não competem pelo mesmo papel, apesar de ambos serem preparação não implementada para a mesma Central de Tráfego futura.
3. **Profundidade da inconsistência de histórico.** Nem `00a` nem `00b` registraram que `UsuariosView.tsx` **descarta** o campo `historico` do `UsuarioDraft` ao converter para `UsuarioRow` (`draftToRow`), nem que Cliente/Equipe/Fornecedor **nunca** escrevem uma entrada nova de histórico (apenas inicializam vazio). Esta análise (seção 2) traz esse achado, obtido por releitura direta do código, como já exigido pela tarefa.
4. **`00b` não distingue explicitamente** evento de domínio, histórico funcional, timeline técnica, auditoria e log de aplicação — trata tudo sob o guarda-chuva de "Evento". Esta análise mantém a distinção (introduzida na seção 6 de `02-modelo-dados-futuro.md` para Histórico/Timeline) e adiciona uma quinta categoria que nenhum documento anterior cobriu: **log da aplicação** (erros, stack traces, requisições técnicas) — que **não deve** ser gravado na tabela `eventos`, por ter volume, retenção e consumidores completamente diferentes de um evento de domínio de negócio. Isso não é uma correção de erro de `00b`, é uma lacuna que nenhum dos dois documentos anteriores havia coberto.
5. **`00b` está correto e é reaproveitado sem alteração** nos seguintes pontos: não propor rota pública `POST /eventos` genérica; não propor Kafka/RabbitMQ; recomendar Postgres/gravação transacional local; usar outbox apenas como opção futura condicionada a necessidade real, não como requisito imediato. Esses pontos são adotados diretamente nas seções 9, 16 e 21 deste documento.

## Conflitos identificados com o módulo Workflow (commit `80ba94f`)

1. `Demanda.workflowHistorico: WorkflowTransicaoHistorico[]` é, na prática, um proto-evento já funcional (tem `usuarioId`, `dataHora`, IDs de origem/destino, observação) — mas vive fora de qualquer contrato comum com `DemandaHistoricoEvento`. Nenhuma alteração é feita neste documento; o conflito é registrado para decisão futura (seção 12).
2. `WorkflowEtapaStatus` (`pendente|atual|concluida|bloqueada`, hoje em `types/workflow.ts`) é a terceira nomenclatura de "estado de etapa" identificada no projeto (as outras duas: o antigo formato removido de `Demanda` e o `stages: string[]` livre de `/configuracoes/workflows`) — relevante para quando (fora desta fase) o Workflow vier a emitir eventos, pois a taxonomia de `action` para transição de etapa (`workflow_etapa_avancada`, `workflow_etapa_bloqueada` etc.) precisa refletir o vocabulário **atual** (`bloqueada`/`atual`/`concluida`/`pendente`), não os anteriores.
3. `WorkflowEditor.tsx` usa `window.confirm` para uma ação destrutiva (trocar template) — não é um problema do Motor de Eventos, mas é relevante notar que, se essa ação vier a emitir evento no futuro, a confirmação visual em si é um detalhe de UI e **não deve** ser requisito do contrato do evento de domínio. O evento futuro deve registrar apenas a substituição efetiva do template — `template_anterior_id`, `template_novo_id`, `actor_id`, `source` e `correlation_id` — nunca se uma caixa de confirmação foi exibida ou confirmada, já que essa é uma decisão de apresentação, não um fato de domínio.

Nenhum desses três pontos foi alterado — são identificados e registrados para decisão em fase posterior, conforme instruído.
