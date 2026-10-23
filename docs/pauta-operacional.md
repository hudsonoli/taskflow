# Pauta operacional por etapa

A Pauta responde "quem tem o quê, quando, em qual cliente/projeto". A unidade é a **etapa materializada** da Demanda (não a Demanda inteira), porque responsabilidade e planejamento são por etapa.
Somente leitura; sem migration.

## Endpoint — `GET /pauta/operacional`

- Autorização: a da Pauta global (`pode_visualizar_pauta_global`: Atendimento, Head de departamento ou Gestão/Admin). Operador comum: 403. Tenant sempre do token.
- Parâmetros (todos opcionais): `inicio`, `fim` (datas do calendário da empresa; padrão = segunda-feira da semana atual + 28 dias; máximo 92 dias), `usuarioIds`, `departamentoIds`, `clienteIds`, `projetoIds`
  (CSV de UUIDs), `prioridades` (CSV `baixa|media|alta`), `busca`.
- Resposta neutra: `meta` (hoje/fuso/período), `itens[]`, `pessoas[]` (id + nome só de quem aparece como responsável efetivo) e `totais`.
  O servidor **não** devolve árvore por colaborador/projeto: a interface agrupa sobre o MESMO conjunto de itens.

### Item
`etapaId/Nome/Tipo/Ordem/Status/Atual`, `demandaId/Identificador/Nome/Status`, `prioridade`, `clienteId`, `projetoId`, `prazoEtapaAtual` (só na etapa atual; informação, nunca geometria),
`planejamento { inicio, fim, estado, invalido }` e `responsabilidadeEfetiva { origem, usuarioIds, departamentoIds }`.

## Regras

- **Responsabilidade** = a regra central de `app/core/executor_etapa.py` (etapa com usuário OU departamento explícito → só a etapa; senão responsáveis gerais da Demanda; senão ninguém). Os itens usam o
  resolvedor em Python sobre vínculos carregados em lote; os filtros por colaborador/departamento usam o equivalente em SQL, coberto por teste de equivalência (16 combinações).
  Colaborador/departamento filtram a responsabilidade **efetiva** (não o responsável geral bruto nem o departamento cadastral da pessoa).
- **Geometria** = só `planejado_inicio`/`planejado_fim`. Janela completa que cruza o período → barra. `incompleto` (início sem fim) → seção "Planejamento incompleto" (entra se o início não passa do fim do período).
  `nao_planejado` (NULL/NULL) → seção "Não planejadas" (entra sempre). NULL/DATE (inválido, nunca existe por CHECK) é tratado como não planejado e marcado em `invalido`.
- **Universo**: etapas não concluídas de Demandas em `planejada`, `em_execucao`, `pausada`, `bloqueada` ou `aguardando_cliente` (a Pauta é agenda: `rascunho` ainda não é compromisso e fica fora, junto com
  `concluida`/`cancelada`/`arquivada`). A regra vale para os três baldes (planejadas, incompletas, não planejadas) e para todas as contagens; quando a Demanda sai do rascunho, as etapas passam a aparecer. Etapa atual **e** futuras.
- **Período**: cada balde (planejadas / incompletas / não planejadas) tem teto de 1000 itens e informa `{ total, devolvidos, truncado }`; a interface avisa quando há mais do que o devolvido.
  `planejadasAntes`/`planejadasDepois` contam janelas completas fora do período.
- Consultas: 11, constantes (não dependem do número de etapas); nenhum N+1.

## Interface

- Padrão **Colaborador**; alternância **Projeto** (`?visao=projeto`) e **Gantt | Lista** (`?modo=lista`); período por `?inicio=YYYY-MM-DD` (setas ±7 dias, "Hoje" limpa o parâmetro).
- Colaborador: um grupo por pessoa (por nome), depois **Sem responsável individual** (só departamento — nunca se escolhe uma pessoa) e **Sem responsável**. Etapa multi-responsável aparece no grupo de cada pessoa
  (a barra não é dividida); com o filtro Colaborador ativo só os colaboradores filtrados ganham grupo. Projeto: cada etapa aparece uma única vez, com todos os responsáveis.
- Sobreposição de barras do mesmo colaborador fica visível nas linhas vizinhas; a capacidade (sobrecarga) continua sendo da Carga.
- "Herdado da tarefa"/"Definido na etapa" aparecem no tooltip e na Lista, não em cada linha do Gantt.
