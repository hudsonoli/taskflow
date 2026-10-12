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
