# Planejamento por etapa e capacidade alocável — Fase 11B.2B-A

Base da 11B.2B: **janela planejada por etapa** e **percentual de capacidade alocável da empresa**. Nada
disto calcula carga, ocupação ou distribuição semanal — isso é a Fase B. Sem deploy nesta fase.

## Quatro tempos que não se misturam

| Conceito | Onde vive | O que NÃO é |
| --- | --- | --- |
| Tempo **operacional** | `demanda_status_intervalos` | horas de alguém |
| Tempo **pessoal** | `sessoes_trabalho` | planejamento |
| **Estimativa** | `demanda_workflow_etapas.esforco_estimado_minutos` | prazo |
| **Planejamento** (esta fase) | `demanda_workflow_etapas.planejado_inicio/fim` | prazo, histórico, sessão |

**Prazo ≠ Planejamento.** `demandas.prazo_etapa_atual` (manual, por Demanda), `data_inicio` e
`data_fim_prevista` (período da Demanda) continuam como são. Nenhum deles é lido, escrito ou usado
como backfill pelo planejamento, e editar o planejamento não altera nenhum deles.

## Janela planejada da etapa

Migration `0051_planejamento_base.py`: revisão `e8a4c2d71f96`, anterior `d7f3b91e4a58`. Aditiva, sem
tabela nova, sem backfill.

`demanda_workflow_etapas`:

- `planejado_inicio DATE NULL`
- `planejado_fim DATE NULL` (inclusivo)
- `CHECK ck_demanda_workflow_etapas_janela_planejada`:
  `planejado_fim IS NULL OR (planejado_inicio IS NOT NULL AND planejado_fim >= planejado_inicio)`

São datas do calendário da empresa (dia, sem hora, sem fuso). O template (`workflow_modelo_etapas`) **não
recebe** janela: a estimativa nasce do template; o planejamento é contextual à execução da Demanda.

### ESTADO PLANEJAMENTO

Estado **derivado** do par (nunca persistido), em `app/core/planejamento_etapa.py`:

| início | fim | estado | entra na ocupação (Fase B) |
| --- | --- | --- | --- |
| NULL | NULL | `nao_planejado` | não |
| data | NULL | `incompleto` | **não** — não aloca carga em semana alguma |
| data | data ≥ início | `planejado` | sim |
| NULL | data | **inválido** | nunca existe (CHECK + 422) |
| data | data < início | **inválido** | nunca existe (CHECK + 422) |

Somente uma janela **completa** poderá participar da ocupação. Início sem fim **não** significa "toda a
carga na semana do início" — essa regra foi cancelada.

### Estados derivados de ALOCAÇÃO (Fase B) — não são estados da janela

`sem_dia_util` e `janela_vencida` **não são** estados da janela nem colunas persistidas. Serão estados
**derivados de alocação**, calculados pelo endpoint de Carga a partir do calendário e da data de hoje.
**Nada disso é implementado nesta fase.** As decisões congeladas:

- **sem_dia_util** — janela completa cujos dias têm todos capacidade nominal zero (ex.: sábado → domingo
  num expediente seg–sex). O PATCH **não recusa**; não vira planejamento incompleto; o esforço **não** é
  movido para segunda-feira nem colocado artificialmente na semana do início. A resposta futura terá
  `planejamento.estado = planejado` e `alocacao.estado = sem_dia_util`.
- **janela_vencida** — janela completa terminou no passado e a etapa continua aberta. O planejamento
  continua `planejado`; a alocação será `janela_vencida` ("precisa replanejar"); a carga **não** é movida
  automaticamente para a semana atual.

### API

`PATCH /demandas/{demandaId}/workflow/etapas/{etapaId}/planejamento`, corpo com `planejadoInicio` e/ou
`planejadoFim` (`YYYY-MM-DD` ou `null`; ao menos um; outros campos → 422; datetime, número ou texto
fora do formato → 422).

- **Atualização parcial**: só o que foi enviado muda; `null` limpa. A validação vale para o **par
  resultante**, não para cada campo:
  - `NULL/NULL` + `planejadoFim` → 422;
  - `20/10 → 30/10` + `planejadoInicio: null` → 422;
  - `fim < início` (no mesmo PATCH ou contra o valor já gravado) → 422;
  - `planejadoInicio: null` + `planejadoFim: null` → limpa (válido).
- **Autoridade**: a mesma do ajuste de esforço (`pode_avancar_etapa`: responsável da etapa, admin/gestor do
  tenant ou Head de departamento da etapa), sem permissão nova. O mesmo escopo-base de acesso; a leitura
  global da Pauta não concede escrita; token de plataforma não vale. Demanda arquivada → 409. Etapa
  futura ou concluída aceita planejamento (não é uma transição de workflow).
- **Leitura**: cada etapa em `DemandaRead.workflowEtapas[]` traz
  `planejamento: { planejadoInicio, planejadoFim, estado }` e `podeEditarPlanejamento` (calculado pelo
  servidor).
- **Auditoria**: uma alteração real publica `demanda.workflow_planejamento_alterado` na **mesma
  transação**, com ator, instante, etapa e os valores anterior/novo de início e fim
  (`inicioAnterior/inicioNovo/fimAnterior/fimNovo`). No-op não gera evento. Falha ao publicar desfaz a
  alteração.
- **Sem efeito colateral**: não altera status da Demanda, etapa atual, status das etapas, esforço,
  `prazo_etapa_atual`, `data_inicio`/`data_fim_prevista`, `sessoes_trabalho` nem
  `demanda_status_intervalos`.

## Percentual de capacidade alocável

`regra_expediente.percentual_capacidade_alocavel SMALLINT NOT NULL DEFAULT 100`,
`CHECK (1 <= valor <= 100)`, nível empresa. Significa o percentual do expediente **nominal** disponível
para **planejamento de tarefas**; **não é produtividade** nem eficiência de ninguém. Toda regra existente
nasce com 100 (empresa que nunca configurou não tem a capacidade reduzida em silêncio).

- API: `percentualCapacidadeAlocavel` em `GET`/`PATCH /regra-expediente` (inteiro estrito 1..100).
- **Não rearma a pausa automática**: o campo entra na lista de campos simples do
  `RegraExpedienteService.atualizar`, fora do conjunto que rearma (`pausarNoFimPeriodo`, `ativo`, `dias`,
  `timezone`). `pausa_automatica_ativada_em`, horários, fuso e dias permanecem intactos (teste explícito).
- UI: Configurações → Horário de expediente, campo "Capacidade alocável" (`[ 100 ] %`).

## Fora desta fase (Fase B e seguintes)

`GET /trafego/operacional/carga`, distribuição semanal, `sem_dia_util`, `janela_vencida`, multi-responsável
(divisão igual derivada), pool de departamento, esforço restante, aba Carga, capacidade por usuário,
férias/ausências e feriados automáticos. Nenhuma coluna ou tabela para eles existe ainda.

## UI

Detalhe da tarefa → seção do workflow, em cada etapa: "Planejado de … até …" com ícone próprio, ação
"Planejar etapa"/"Ajustar planejamento" (só com `podeEditarPlanejamento`), campos "Planejado de" e
"Planejado até" e a ajuda "Não é o prazo da tarefa". Início sem fim mostra discretamente
"Planejamento incompleto". Sem planejamento, nenhuma indicação além do atalho para quem pode editar.
O histórico da tarefa descreve o evento ("Planejamento de X: 20/10/2026 até 30/10/2026 → …").

## Testes

- Backend: `tests/test_planejamento_base.py` (regra pura, CHECK no banco, estados, PATCH parcial, 422,
  evento/no-op, efeitos colaterais, autoridade, template, percentual e não-rearme) e
  `tests/test_migration_0051_planejamento.py` (upgrade/downgrade, dados preservados, CHECKs, cabeça única).
- Frontend: `npm run test:planejamento` (`src/lib/planejamento-etapa.test.ts`).
