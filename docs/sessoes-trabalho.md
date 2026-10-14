# Sessões de trabalho — integridade (Fase 11B.2A)

`SessaoTrabalho` é a fonte de **tempo realizado** do TaskFlow. Esta fase corrige a fundação (integridade, simultaneidade, encerramento, agregação básica) **antes** de
qualquer capacidade semanal. Não há planejamento semanal, rateio, capacidade nem tela nova aqui.

## Regras de abertura — `POST /sessoes-trabalho/abrir`

O servidor valida tudo; nada que o cliente manda é confiável. Ordem: responsável → demanda → etapa → usuário/departamento → sessão ativa.

| Caso | Resposta |
|---|---|
| sem `usuarioId` nem `departamentoId`, ou os dois | 422 |
| demanda inexistente **ou de outra empresa** | 404 (mesma resposta nos dois: não confirma existência cross-tenant) |
| demanda fora de `em_execucao` (`rascunho`, `planejada`, `pausada`, `bloqueada`, `aguardando_cliente`, `concluida`, `cancelada`, `arquivada`) | 409 `DEMANDA_NAO_EXECUTAVEL` |
| demanda **com workflow**, sem `workflowEtapaId` | a sessão é ligada à **etapa atual**, resolvida no servidor |
| `workflowEtapaId` enviado inexistente, de outra demanda ou de outra empresa | 422 (mensagem única) |
| `workflowEtapaId` enviado de etapa da demanda que **não é a atual** (já concluída ou futura) | 409 `ETAPA_NAO_ATUAL` |
| demanda com workflow mas **sem etapa atual executável** (workflow todo concluído, etapa atual `pausada`, workflow sem etapas materializadas) | 409 `ETAPA_ATUAL_INDISPONIVEL` — nunca abre sessão sem etapa |
| demanda **sem workflow** | `workflow_etapa_id` fica NULL (nenhuma etapa fictícia) |
| usuário/departamento de outra empresa ou inválido | 422 |
| a pessoa já tem uma sessão ativa (qualquer demanda) | 409 `SESSAO_ATIVA_EXISTENTE` — a anterior **não** é encerrada |

O 409 vem como `detail: { code, message }`; a UI não depende do texto. Não expõe a outra sessão nem dados de outra empresa.
Sessão de trabalho representa **execução ativa**: só `em_execucao` aceita abertura. A abertura trava a Demanda (`FOR UPDATE`, o mesmo lock do avanço de etapa e do UPDATE de
status), então a etapa/estado lidos não mudam até o commit e uma transição concorrente já encontra (e encerra) a sessão nova.

### Etapa atual (autoridade do servidor)
"Etapa atual" = a de **menor `ordem` com `status != 'concluida'`** — a mesma regra de `etapaAtualId` da API de Demanda e do avanço de workflow; `UNIQUE (demanda_id, ordem)` a
torna inequívoca. O chamador atual (Tráfego → "Iniciar sessão de teste") continua omitindo o campo, e o servidor associa a etapa. O tempo realizado por etapa passa a ser
rastreável (base de estimado × realizado, capacidade e relatórios). Nunca se escolhe "primeira/última/por responsável".

### Uma sessão ativa por pessoa
Antes da 11B.2A, abrir de novo na **mesma** demanda substituía a sessão em silêncio e a mesma pessoa podia ter sessões ativas em demandas diferentes. Agora há **uma**
sessão ativa por pessoa, e a barreira contra a corrida é o índice parcial único `uq_sessoes_trabalho_ativa_empresa_usuario (empresa_id, usuario_id) WHERE
usuario_id IS NOT NULL AND status = 'ativa'` (migration `0046`, revisão `f2c6a9d41b87`). Quem perde a corrida recebe o mesmo 409 de uma abertura sequencial.

Sessão **puramente departamental** (sem usuário) fica fora do índice e mantém a semântica anterior (reabrir o mesmo departamento na mesma demanda substitui). Ela é uma
linha só: nunca é multiplicada pelos membros do departamento.

## Encerramento automático (idempotente, na mesma transação)

`SessaoTrabalhoService.encerrar_ativas_da_demanda` fecha só sessões **ativas** da **demanda** em questão, trava as linhas (`FOR UPDATE`), grava um evento
`sessao_trabalho_encerrada` por sessão (`motivoEncerramento`, `automatico: true`) e usa a duração `fim − início` (nunca negativa). Sessão já encerrada/cancelada nem é
selecionada: nada de segundo evento, duração ou carimbo alterado.

| Transição | Quem fecha | Motivo |
|---|---|---|
| status → `pausada` | todas da demanda | `pausa` |
| status → `bloqueada` | todas | `bloqueio` |
| status → `aguardando_cliente` | todas | `aguardando_cliente` |
| status → `concluida` | todas | `conclusao` |
| status → `cancelada` | todas | `cancelamento` |
| arquivar | todas | `arquivamento` (novo) |
| status → `rascunho`/`planejada` | todas | `pausa` (só `em_execucao` mantém sessão) |
| status → `em_execucao` | ninguém | — |
| responsável/departamento **removido** da demanda | só a sessão dele(a) naquela demanda | `troca_responsavel` |
| concluir/aprovar etapa | sessões ligadas **àquela etapa** | `mudanca_etapa` (última etapa: `conclusao`) |
| rejeitar etapa de aprovação | sessões ligadas à etapa rejeitada | `mudanca_etapa` |

Rejeição **não** abre sessão: a etapa reaberta volta sem sessão e quem vai trabalhar precisa iniciar a sua. O novo responsável começa com zero realizado próprio. As
transições de aprovação/rejeição e o portal externo não mudaram de lógica; o fechamento acontece dentro da mesma transação (rollback conjunto).

## Agregação

- `horas_departamento` **não conta sessão `cancelada`** (antes entrava; sem duração persistida seria tempo ao vivo crescendo para sempre).
- Sessão ativa é medida até **um único `as_of` por resposta**; encerrada usa a duração persistida.
- Uma sessão conta **uma vez** mesmo sendo pertinente ao departamento pelas duas regras (pessoa lotada ou vínculo direto).

## Auditoria do legado (somente leitura, antes da migration)

| | DEV | Produção |
|---|---|---|
| sessões / ativas | 3 / 1 | 0 / 0 |
| conflitos de sessão ativa por pessoa | 0 | 0 |
| demanda órfã, etapa órfã, etapa de outra demanda, demanda de outra empresa | 0 | 0 |
| ativa sem usuário (departamental) | 1 | 0 |
| sobreposição de sessões da mesma pessoa | 0 | 0 |

Nada foi corrigido automaticamente. A migration confere os conflitos antes de criar o índice e **para** (só contagem, sem ids) se houver algum.

## Limitações conhecidas (fora do escopo desta fase)

- **Resolvido (decisão de produto):** demanda com workflow sempre tem sessão ligada à etapa atual (ver acima). Linhas **legadas** sem etapa em demanda com workflow (não há em
  produção; no DEV a auditoria não achou) não são encerradas por mudança de etapa, só pelas transições da demanda.
- **P2_SESSION_DEPARTMENT_HISTORY — departamento histórico:** a sessão de pessoa não persiste o departamento do momento da execução; `horas_departamento` usa a lotação **atual**. Mudar a lotação
  altera a leitura histórica. Resolver quando houver snapshot de lotação/capacidade.
- **P2 — FKs:** `demanda_id`/`workflow_etapa_id` seguem sem FK (colunas `varchar(128)`); a validação é do service. A auditoria não achou órfãos no DEV nem em produção.
- **P2_SESSION_STALE_POLICY — sessão esquecida:** não há timeout nem watchdog. Sessão antiga aberta (no DEV há uma departamental de ~1400 h) é dado inconsistente a tratar com regra de produto
  (qual limite? 8 h, 12 h, 24 h?) — nenhum limite foi inventado.
- **P3 — relógio:** `indicadores/carga/agora/resumo` do Tráfego continuam usando `NOW()` por consulta (consistente dentro de cada consulta).

## Testes

`tests/test_sessao_trabalho_integridade.py` (abertura, uma sessão por pessoa, banco, auto-encerramento, workflow, agregação), `tests/test_sessao_trabalho_concorrencia.py`
(corrida real e SAVEPOINT), `tests/test_migration_0046_sessao_unica.py` (up/down e guarda de legado), frontend `npm run test:sessao-trabalho`.
Os testes de agregação do Tráfego (`test_trafego_carga.py`) derrubam o índice só dentro da transação do teste para continuar exercitando o SQL sobre várias sessões por pessoa.

## Direção: Tráfego V2 — tempo operacional automático (decisões aprovadas; NADA implementado)

Registrado após a auditoria de 2026-10-14. Esta fase (11B.2A) e a tabela `sessoes_trabalho` **não mudam**.

- **Tempo operacional automático ≠ tempo pessoal.** O tempo da **tarefa/etapa** (quanto ficou em cada estado) é automático e vem da mudança de status; o tempo de uma **pessoa** só existe com evidência real (hoje, a sessão aberta pelo botão). Nunca se divide por responsáveis (3 responsáveis × 2 h ≠ 6 h pessoais) e quem **move** a tarefa (gestor/admin/atendimento) **não** é, por isso, executor: `executor_usuario_id` não é inferido pelo simples ato de mover.
- **Modelo futuro (opção B): `demanda_status_intervalos`** — uma **linha do tempo dos estados operacionais** (não só `em_execucao`): um intervalo por estado, com etapa do workflow no instante, motivo/ator de início e fim e `evento_inicio_id`/`evento_fim_id` únicos. Um intervalo aberto por Demanda (índice único parcial), fechamento e abertura na mesma transação da mudança de status/etapa, sempre pelo `DemandaService` e pelo `DemandaWorkflowService`. Tempo pausado, bloqueado e **aguardando cliente (bucket próprio)** saem da mesma tabela. Aprovação interna conta como **tempo na etapa / tempo operacional decorrido**, não como hora trabalhada por pessoa.
- **`sessoes_trabalho` permanece o TEMPO PESSOAL** (e a regra de uma sessão ativa por pessoa). Não é fonte das métricas automáticas do Tráfego.
- **Tráfego V2** = painel de **observação para gestores**. "Iniciar sessão de teste" fica temporariamente só para diagnóstico/admin e depois sai da experiência normal.
- **Workflow:** quando todas as etapas materializadas estiverem concluídas e não houver aprovação pendente, a Demanda deve terminar como `concluida` (será implementado na fase do Tráfego V2, não antes).
- **As métricas automáticas de DURAÇÃO NÃO serão expostas em produção antes da Fase Expediente 3** (pausa automática nos fins de período). Sem ela, uma tarefa esquecida em `em_execucao` acumularia tempo noturno falso. Contagens por status "agora" não dependem disso.
- **Migração:** não inventar horas pessoais retroativas; a medição automática começa na migration, com marcador explícito de início (`medicao_automatica_desde`) e um intervalo aberto para cada Demanda que já estiver `em_execucao`.
- **Pré-requisito já resolvido (hardening do gate, branch `fix/expediente-work-gate-entrypoints`):** as três portas para `em_execucao` — `PATCH /demandas/{id}`, `POST /demandas` com `status=em_execucao` e `POST /demandas/{id}/restaurar` de uma Demanda arquivada que estava em execução — passam pela **mesma** autoridade de horário (`DemandaService._ensure_dentro_expediente`); ver `docs/expediente.md`.

## Fase Expediente 3 — encerramento por fim de período

Motivo novo `fim_expediente` (ver `docs/expediente.md`): o tick de pausa automática encerra as sessões de usuários sujeitos ao fim de cada período, com `fim_em` = o corte configurado e evento sem usuário ator.
Abrir sessão pessoal passou a respeitar o gate de TRABALHO (`FORA_DE_EXPEDIENTE`, 409). `close_session` nunca grava fim anterior ao início (limita ao início e registra warning).

## Status da Fase 11B.2A — ENCERRADA (2026-10-14)

`FASE_11B2A=CLOSED`, `AUTO_CLOSE_ON_PAUSE=OK`. Teste C humano em produção (main `46cccde`): PATCH em_execucao 200 → `POST /sessoes-trabalho/abrir` 201 (etapa atual) → PATCH pausada 200, sem fechamento manual; a sessão foi encerrada
na mesma transação da pausa (`motivo_encerramento=pausa`, evento `sessao_trabalho_encerrada` único com `automatico=true`), `pausaOrigem=manual`, 0 sessões ativas, 0 erros. Evidências anteriores mantidas: segunda sessão ativa
protegida, índice único parcial, vínculo com a etapa atual autoritativa, origem manual da pausa.

## Tráfego V2 — Fase 1: motor de intervalos operacionais (`demanda_status_intervalos`) — implementado em branch

> **Estado:** branch `feature/trafego-v2-intervalos`, migration `0050` (`d7f3b91e4a58`, down `c6e1a38d5b92`), **sem merge e sem deploy**. Sem frontend e sem endpoints novos: o painel do Tráfego e as
> métricas vêm em fases seguintes. Esta seção substitui o "modelo futuro" descrito acima.

### TEMPO OPERACIONAL ≠ TEMPO PESSOAL (regra de ouro)

- **Intervalo de status** (`demanda_status_intervalos`) = tempo **decorrido da Demanda/etapa** num estado (ex.: `em_execucao` 09:12 → 10:47 = 1h35 operacionais).
- **Sessão** (`sessoes_trabalho`) = tempo **atribuível a uma pessoa**, com evidência explícita. Continua exatamente como está (inclusive o botão manual do Tráfego).
- **Nunca** converter um no outro: não existe `executor`, `horas por usuário` nem função que some intervalos "por pessoa" neste modelo. `iniciado_por_usuario_id` é **auditoria** ("quem provocou a abertura");
  um gestor que move a tarefa para `em_execucao` aparece ali e **nenhuma hora pessoal** é atribuída a ele. Os eventos seguem como auditoria; métricas de duração consultam a tabela, não JSON de evento.

### Modelo

Uma linha por **estado** (e por **etapa atual do workflow**): `empresa_id`, `demanda_id` (FK), `status`, `workflow_etapa_id` (NULL sem workflow ou com o workflow já concluído), `inicio_em`, `fim_em`/`duracao_segundos`
(só fechado), `motivo_fim`, `iniciado_por_usuario_id`, `origem`, `evento_inicio_id`/`evento_fim_id` (liga ao evento de domínio que causou a mudança), `created_at`/`updated_at`.
Estados com intervalo: `rascunho`, `planejada`, `em_execucao`, `pausada`, `bloqueada`, `aguardando_cliente` (**bucket próprio** — nunca se mistura com execução).

**Estados terminais** (`concluida`, `cancelada`, `arquivada`) **não têm intervalo**: entrar neles só **fecha** o anterior (`conclusao`/`cancelamento`/`arquivamento`). Decisão: uma Demanda concluída não acumula "tempo concluída"
por meses; o fim do último intervalo já marca o fechamento da linha do tempo. Reabrir (concluída → em execução) abre um intervalo novo; o buraco entre os dois é real.

**Invariantes no banco:** no máximo **1 intervalo aberto por Demanda** (índice único parcial `WHERE fim_em IS NULL`); aberto ⇒ sem fim/duração/motivo; fechado ⇒ `fim_em ≥ inicio_em`, `duracao_segundos ≥ 0`, motivo; status/origem/motivo enumerados;
`evento_inicio_id` único (o mesmo evento nunca abre dois intervalos). `duracao_segundos` é o **piso** em segundos (4500 = 1h15).

### Mecanismo único (`DemandaIntervaloService.sincronizar`)

Toda mudança de estado operacional chama `sincronizar` **dentro da transação** que a causou. Ele não recebe "o que aconteceu": compara o estado ATUAL da Demanda (status + etapa atual) com o intervalo aberto —
igual → **no-op** (mesmo status ou retry nunca duplicam tempo); diferente → fecha o aberto e abre o novo. Trava a linha da Demanda (`FOR UPDATE`) antes; o índice único é a segunda barreira. Pontos de entrada (todos no domínio, nenhuma rota):
criar (`create_demanda`), mudar status (`update_demanda`), arquivar, restaurar, **progressão de workflow** (concluir/aprovar/rejeitar → a ETAPA atual mudou, mesmo status → fecha e reabre) e a **pausa automática do expediente**.
A "etapa atual" é a **autoridade existente** (`get_etapa_atual`: menor `ordem` não concluída) — nenhuma definição nova.

### Instante efetivo (`quando`)

Parâmetro explícito, nunca `datetime.now()` escondido: ação manual = o instante da operação; **pausa automática = o CORTE configurado** (12:00:00), não o do tick (12:00:07) — o scheduler não tem integração especial, só passa `quando=corte`.
Se `quando` for anterior ao início do aberto, usa-se o início (sem fim < início, sem sobreposição, com aviso `demanda_intervalo_instante_anterior_ao_inicio`).

### Histórico e início da medição

Nada é reconstruído. A migration abre **um intervalo por Demanda NÃO terminal** com `inicio_em = now()` da migration e `origem='migracao'` — esse é o marcador do início da medição. "Dados disponíveis a partir de…" = o **menor `inicio_em`** da
empresa (modelo mínimo: sem coluna genérica nova). Terminais não ganham nada. Downgrade remove só a tabela.

### O que o modelo já suporta (consultas futuras, sem ambiguidade)

Tempo em execução / pausado / bloqueado / aguardando cliente por **Demanda, Projeto, etapa, departamento da etapa e período**; duração total, média e maior tempo **por etapa** — sempre como **tempo operacional decorrido**.
Métricas de duração só serão expostas em produção depois da Fase Expediente 3 em uso (acumulação noturna) — agora publicada, com a pausa automática já encerrando o intervalo no corte.

### Pendente (decisão separada): conclusão automática do workflow

Hoje **concluir o último passo encerra o workflow e NÃO conclui a Demanda** (decisão do 8A, coberta por testes). A decisão de produto aprovada diz que, com todas as etapas concluídas e sem aprovação pendente, a Demanda deve convergir para `concluida`. Não foi implementado aqui
(`WORKFLOW_FINAL_AUTO_COMPLETE_PENDING=SIM`): mexe num contrato existente e tem efeitos colaterais (resolução de SLA, notificações, `status_alterado` com ator, aprovação externa em aberto, e o `workflow_etapa_id` NULL do último intervalo). Desenho: no fim de
`_avancar_etapa`, se `proxima is None` e nenhuma `aprovacao_externa` aberta, chamar o MESMO caminho de `update_demanda` para `concluida` (um único ponto, com o ator da ação) — o motor de intervalos já o trataria como terminal. Até lá, o último intervalo fica `em_execucao` com etapa NULL.
