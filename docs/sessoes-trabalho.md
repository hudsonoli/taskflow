# Sessões de trabalho — integridade (Fase 11B.2A)

`SessaoTrabalho` é a fonte de **tempo realizado** do TaskFlow. Esta fase corrige a fundação (integridade, simultaneidade, encerramento, agregação básica) **antes** de
qualquer capacidade semanal. Não há planejamento semanal, rateio, capacidade nem tela nova aqui.

## Regras de abertura — `POST /sessoes-trabalho/abrir`

O servidor valida tudo; nada que o cliente manda é confiável. Ordem: responsável → demanda → etapa → usuário/departamento → sessão ativa.

| Caso | Resposta |
|---|---|
| sem `usuarioId` nem `departamentoId`, ou os dois | 422 |
| demanda inexistente **ou de outra empresa** | 404 (mesma resposta nos dois: não confirma existência cross-tenant) |
| demanda `arquivada`, `concluida`, `cancelada`, `pausada`, `bloqueada`, `aguardando_cliente` | 409 `DEMANDA_NAO_EXECUTAVEL` |
| `workflowEtapaId` inexistente, de outra demanda ou de outra empresa | 422 (mensagem única) |
| usuário/departamento de outra empresa ou inválido | 422 |
| a pessoa já tem uma sessão ativa (qualquer demanda) | 409 `SESSAO_ATIVA_EXISTENTE` — a anterior **não** é encerrada |

O 409 vem como `detail: { code, message }`; a UI não depende do texto. Não expõe a outra sessão nem dados de outra empresa.
`rascunho`, `planejada` e `em_execucao` aceitam sessão.

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
| status → `rascunho`/`planejada` | todas | `pausa` |
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

- **P1 de produto — etapa obrigatória:** `workflowEtapaId` ainda é opcional. O único chamador atual (Tráfego → "Iniciar sessão de teste") não envia a etapa, e deduzir a
  etapa seria arbitrário. Sessão sem etapa em demanda com workflow não é encerrada por mudança de etapa (só pelas transições da demanda). Decidir antes do tempo realizado
  por etapa.
- **P2 — departamento histórico:** a sessão de pessoa não persiste o departamento do momento da execução; `horas_departamento` usa a lotação **atual**. Mudar a lotação
  altera a leitura histórica. Resolver quando houver snapshot de lotação/capacidade.
- **P2 — FKs:** `demanda_id`/`workflow_etapa_id` seguem sem FK (colunas `varchar(128)`); a validação é do service. A auditoria não achou órfãos no DEV nem em produção.
- **P2 — sessão esquecida:** não há timeout nem watchdog. Sessão antiga aberta (no DEV há uma departamental de ~1400 h) é dado inconsistente a tratar com regra de produto
  (qual limite? 8 h, 12 h, 24 h?) — nenhum limite foi inventado.
- **P3 — relógio:** `indicadores/carga/agora/resumo` do Tráfego continuam usando `NOW()` por consulta (consistente dentro de cada consulta).

## Testes

`tests/test_sessao_trabalho_integridade.py` (abertura, uma sessão por pessoa, banco, auto-encerramento, workflow, agregação), `tests/test_sessao_trabalho_concorrencia.py`
(corrida real e SAVEPOINT), `tests/test_migration_0046_sessao_unica.py` (up/down e guarda de legado), frontend `npm run test:sessao-trabalho`.
Os testes de agregação do Tráfego (`test_trafego_carga.py`) derrubam o índice só dentro da transação do teste para continuar exercitando o SQL sobre várias sessões por pessoa.
