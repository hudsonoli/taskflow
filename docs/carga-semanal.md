# Carga semanal — Fase 11B.2B-B (motor e endpoint, somente backend)

`GET /trafego/operacional/carga` responde: **quanto trabalho está planejado para cada pessoa e departamento nesta
semana, contra a capacidade?** Só leitura. Sem migration, sem tabela nova, sem UI (a UI é a 11B.2B-C). Sem deploy nesta
fase.

Base: a Fase A (janela planejada por etapa e fator alocável da empresa), em [planejamento-etapa.md](planejamento-etapa.md);
decisões de roadmap em [backlog-produto-benchmark.md](backlog-produto-benchmark.md).

## O que NÃO entra (princípio)

| Conceito | Fonte | Papel na Carga |
| --- | --- | --- |
| Tempo **operacional** | `demanda_status_intervalos` | **Nunca lido.** Não reduz restante nem capacidade |
| Tempo **pessoal** | `sessoes_trabalho` | **Nunca lido.** Não reduz restante nem capacidade |
| **Estimativa** | `esforco_estimado_minutos` da etapa | É o restante de uma etapa aberta |
| **Planejamento** | `planejado_inicio`/`planejado_fim` | Diz em quais semanas a estimativa cai |
| **Capacidade** | `RegraExpediente` da empresa + fator | Denominador da ocupação |

Um teste captura o SQL do endpoint e falha se `sessoes_trabalho` ou `demanda_status_intervalos` aparecerem, e outro
prova que inserir sessão/intervalo longos não muda a resposta.

## Endpoint

`GET /trafego/operacional/carga` · prefixo `/trafego/operacional` · RBAC `require_trafego_gerenciar` (admin/gestor com a
permissão; operador 403; sem token 401). A empresa vem **sempre do token**.

| Parâmetro | Significado |
| --- | --- |
| `semana=YYYY-MM-DD` | Qualquer dia da semana; normalizado para a **segunda-feira** no **fuso da empresa** (`regra_expediente.timezone`, nunca o do navegador). Omitido = semana atual |
| `departamentoId`, `usuarioId` | Recortam o resultado **depois** do cálculo (ver "Filtros"). Outra empresa ou inexistente → 404 |
| `detalhe=usuario\|departamento` | Devolve as etapas que compõem o número; exige `usuarioId`/`departamentoId` correspondente (senão 422 `FILTRO_INVALIDO`) |
| `limite` | 1..200 (padrão 50) para listas de itens |

**Semanas suportadas:** a atual e as futuras. Semana anterior à atual → **422** `SEMANA_PASSADA_NAO_SUPORTADA` (sem
relatório histórico de capacidade).

## Calendário e capacidade

- **Capacidade nominal do dia** = soma dos períodos de `periodos_do_dia(regra, data)` (inclui dias especiais: feriado/recesso
  ativos = 0; trabalho excepcional = períodos próprios). Antecedência de acesso, bloqueio fora do expediente e pausa
  automática **não** entram.
- **Capacidade alocável** = `round(nominal × percentual_capacidade_alocavel / 100)` (meio para cima, em inteiros).
- **Semana atual recortada em hoje:** capacidade e carga contam de **hoje até domingo**. Hoje conta como **dia completo**
  (segunda às 16h continua valendo todo o dia nominal); não há precisão intradiária. `semana.recorteHoje=true`;
  `dias[].considerado=false` nos dias anteriores. Semana futura: `recorteHoje=false`, todos os dias.
- **Ponto de extensão:** `obter_capacidade_usuario(usuario, periodo, regra, percentual_alocavel)` em
  `app/core/carga_semanal.py` é o único lugar que decide a capacidade de uma pessoa. Na v1 todos os usuários elegíveis usam
  a regra da empresa; jornada individual e ausências/férias entram **aí** no futuro. Não há hierarquia de classes nem tabela.
- **Expediente desligado** (`ativo=false`) **ou ausente**: `capacidade.capacidadeIndisponivel = "expediente_desligado"`. Não
  se assume 8 h. **Comportamento escolhido (documentado):** sem calendário confiável não existe distribuição por semana, então
  `capacidadeNominalMin`, `capacidadeAlocavelMin`, **`planejadoMin`**, `saldoMin` e `ocupacaoPercentual` ficam `null`
  (nunca zero). Continuam informados o que não depende do calendário: `naoPlanejado`, `semEstimativaCount` e as janelas
  **vencidas** (dependem só de datas). Empresa sem regra: tratada como desligada e **nada é criado** numa leitura.

## Quem tem capacidade (pessoa elegível)

Usuário `status = ativo`, com `acesso_sistema`, e que **não** é conta de sistema — a mesma regra de
`DemandaService._ensure_usuario_valido` (não arquivado/inativo/bloqueado e não conta de sistema) acrescida do acesso. **Perfil
(admin/gestor/operador) não decide**: um gestor ativo recebe trabalho como qualquer pessoa.

## Restante e quais etapas participam

- Etapa **aberta** (não concluída) de Demanda em `planejada`, `em_execucao`, `pausada`, `bloqueada` ou `aguardando_cliente`:
  `restante = esforco_estimado_minutos`. Inclui etapas **futuras** ainda não iniciadas: a capacidade não se limita à etapa atual.
- Etapa concluída, e Demandas `rascunho`, `concluida`, `cancelada`, `arquivada`: **0**. O status operacional (pausada, bloqueada…)
  não zera a carga.
- **Sem estimativa** (`NULL`): não vira zero; entra em `semEstimativaCount`. Estimativa `0` explícita é uma estimativa.

## Janela e estados de alocação

| Janela | Estado do planejamento | Efeito na Carga |
| --- | --- | --- |
| NULL / NULL | `nao_planejado` | `naoPlanejado.semJanela`; fora da ocupação |
| início / NULL | `incompleto` | `naoPlanejado.janelaIncompleta`; fora da ocupação |
| início / fim | `planejado` | Pode ocupar; o **estado de alocação** abaixo é derivado |

Estados de **alocação** (derivados, nunca colunas) de uma janela completa:

- `alocada` — distribui o restante pelos dias restantes da janela.
- `janela_vencida` — `fim < hoje` com a etapa aberta: **nada é distribuído** e nada é movido para a semana atual; vai para
  `pendenciasPlanejamento.janelaVencida` ("precisa replanejar"). `fim == hoje` ainda é vigente.
- `sem_dia_util` — a janela é válida mas a soma dos minutos nominais dos dias restantes é 0 (ex.: sábado→domingo num expediente
  seg–sex): **nada é distribuído**, nada vai para segunda-feira, continua `planejado`; vai para
  `pendenciasPlanejamento.semDiaUtil`.

`naoPlanejado` e `pendenciasPlanejamento` **independem da semana** consultada: são o que ainda precisa de planejamento.

## Distribuição por semana (derivada, não persistida)

Para uma janela `alocada`, com `inicioEfetivo = max(planejado_inicio, hoje)`:

```
peso do dia   = minutos nominais do dia
denominador   = soma dos pesos de inicioEfetivo até planejado_fim
planejadoNaSemana = restante × (soma dos pesos da semana) / denominador
```

Em minutos **inteiros**, pelo **maior resto** (empate pela posição): **Σ semanas = restante, exatamente**. Exemplo: janela
19/10→06/11, 600 min, 3 semanas iguais → 200/200/200; cada semana consultada devolve a sua parte.

## Responsáveis e pools

1. **Usuários elegíveis da etapa** recebem a carga em **divisão igual**, ordem estável por `usuario_id`, maior resto
   (`241` entre 2 → `121 + 120`; `100` entre 3 → `34 + 33 + 33`). A divisão é feita sobre o valor **da semana** da etapa, então
   Σ pessoas = planejado da etapa na semana.
2. Se a etapa tem usuários **e** departamentos, a carga vai **só** para os usuários (departamento é contexto/autoridade).
3. Sem usuário elegível (inclui responsável inativo/sistema): os **departamentos da etapa** viram **POOL_DEPARTAMENTO** (1
   departamento = 100%; vários = divisão igual por id).
4. Sem usuário e sem departamento: **POOL_SEM_DEPARTAMENTO**. A carga **nunca desaparece**.

**Departamento:** capacidade = soma da capacidade das pessoas elegíveis dele; `planejadoMin` = carga das pessoas dele **+**
`planejadoPoolMin` (o pool é um **subconjunto**, não somado de novo).

## Filtros não recalculam

A alocação **completa** é calculada primeiro; `usuarioId`/`departamentoId` só escolhem o que mostrar. Etapa com A+B
(120/120) consultada com `usuarioId=A` continua mostrando 120 para A (não 240). `naoPlanejado` e `pendenciasPlanejamento`
passam a refletir as etapas daquele alvo, com os valores completos.

## Ocupação

`saldoMin = capacidadeAlocavelMin − planejadoMin`; `ocupacaoPercentual = planejadoMin / capacidadeAlocavelMin × 100`
(1 casa), **sem teto em 100**; `null` se a capacidade for 0 ou indisponível.

## Resposta (resumo)

`meta` · `semana{inicio, fim, recorteHoje, dias[{data, minutosNominais, considerado}]}` · `capacidade{capacidadeIndisponivel,
fatorAlocavelPercentual}` · `pessoas[]` · `departamentos[]` · `poolSemDepartamento` (só sem filtro) · `naoPlanejado{semJanela,
janelaIncompleta}` · `pendenciasPlanejamento{janelaVencida, semDiaUtil}` (com `itens` e `truncado`) · `detalhe` (com filtro e
`detalhe=`). Cada item de etapa explica o número: demanda, etapa, cliente/projeto, estimativa, restante, `planejadoNaSemanaMin`,
`parteMin` do alvo, janela, estado de alocação, origem, `divididoEntre` e status da Demanda. Sem dados financeiros, sem horas
trabalhadas, sem ranking.

## Desempenho

Número de consultas **constante** (regra, dias, períodos, dias especiais, pessoas, departamentos, etapas, responsáveis de
usuário e de departamento): medido em 12 com 3 etapas e 12 com 123 etapas/28 pessoas. O calendário de 7 dias é calculado em
memória. Sem cache e sem índice novo.

## Testes

`tests/test_carga_core.py` (cálculo puro, 42 casos: calendário, arredondamento, janela, responsabilidade) e
`tests/test_carga_semanal_api.py` (HTTP: RBAC, tenant, semana, fuso, fator, expediente desligado, distribuição,
filtros, status, sem estimativa, detalhe, somente leitura, sem tempo pessoal/operacional, consultas).

## Fora desta fase

UI de Carga (11B.2B-C), jornada individual, ausências/férias, feriados automáticos, histórico de semanas passadas, cache e
qualquer mudança nas colunas ou contratos da Fase A.
