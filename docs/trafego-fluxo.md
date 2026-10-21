# Tráfego — Fluxo por etapa (contrato backend, Fase A)

`GET /trafego/operacional/fluxo` responde: **onde está o trabalho aberto agora, agrupado pela etapa em que ele está?** Só leitura,
sem migration, sem UI (a UI é a fase seguinte). Resolve a lacuna de contrato que bloqueou o `P1_KANBAN_METRICA_ETAPA` (ver
[backlog-produto-benchmark.md](backlog-produto-benchmark.md): `P1_TRAFEGO_FLUXO_POR_ETAPA`).

## Por que um endpoint próprio

Gargalos só devolve **agregados** por definição de etapa (sem Demandas), e o Agora lista **só** as Demandas em execução e identifica a etapa
por `etapaAtual.id` (etapa materializada), sem a chave da definição. O cliente não pode (e não deve) reconstruir a chave — um SHA-1 do
servidor sobre `nome normalizado + tipo + ids de departamentos ordenados`. O Fluxo faz o agrupamento **no servidor**.

## Identidade e universo (reuso, nenhuma regra nova)

- **Identidade:** a mesma função `_definicao` de Gargalos (`definicaoEtapa.chave`). Mesmo nome com departamentos diferentes = colunas
  diferentes. Um teste fixa o formato da chave com um oráculo independente e compara com Gargalos.
- **Universo:** o mesmo de `fila[]`/WIP de Gargalos — intervalo aberto em `demanda_status_intervalos`, com a Demanda **e** o intervalo em
  `planejada | em_execucao | pausada | bloqueada | aguardando_cliente`. **Fora:** `rascunho`, `concluida`, `cancelada`, `arquivada`.
- **Etapa atual:** a do intervalo aberto (`workflow_etapa_id`), a mesma que define o WIP em Gargalos e que o motor mantém em sincronia com a
  etapa atual do workflow. Um teste confirma que coincide com a etapa que o Agora deriva do workflow.
- **Sem etapa atual:** Demanda aberta cujo workflow já concluiu (pendência conhecida) ou que nunca teve workflow não vira coluna nem some:
  entra em `semEtapa` (só contagens) e no `atual`.
- Uma Demanda aparece **no máximo uma vez**.

## Parâmetros

| Parâmetro | Padrão / limites | Efeito |
| --- | --- | --- |
| `periodoDias` | 30 · 1..90 | Janela (até agora) das métricas de **tempo**. WIP e itens são sempre o estado atual |
| `departamentoId` | — | Só definições cujo conjunto de departamentos inclui este. **Métricas, itens, `atual` e totais** respeitam o filtro (igual ao de Gargalos) |
| `limiteDefinicoes` | 100 · 1..200 | Quantas colunas voltam |
| `limiteItensPorDefinicao` | 20 · 1..100 | Quantos cards voltam por coluna |

Não há filtro de cliente/projeto/responsável nesta v1.

## Resposta (resumo)

`agoraServidor` · `fusoEmpresa` · `periodo{inicio,fim,fimEfetivo}` · `medicaoDesde` · `coberturaParcial` · `filtros` ·
`atual{wip,planejadas,emExecucao,pausadas,bloqueadas,aguardandoCliente}` · `semEtapa{workflowConcluido,semWorkflow}` ·
`definicoes[]` · `definicoesTotal` · `definicoesRetornadas` · `truncado` · `limiteDefinicoes` · `limiteItensPorDefinicao`.

Cada definição: `definicaoEtapa{chave,nome,tipo,departamentos}` · `metricas{wip, planejadas, emExecucao, pausadas, bloqueadas,
aguardandoCliente, maisAntigaSegundos, maisAntigaTruncadaPelaMedicao, tempoExecucaoMedioSegundos, nExecucao}` · `itensTotal` ·
`itensRetornados` · `truncado` · `itens[]`.

Cada item: Demanda (`demandaId`, `codigoReferencia`, `numeroOperacional`, `identificador`, `titulo`, `status`), `cliente`, `projeto`
(nulos quando não há), `etapaAtual`, **`definicaoChave`** (gerada pelo servidor, **igual** a `definicaoEtapa.chave` da coluna),
`responsaveis` (atribuição atual da etapa — não é executor), `inicioEstadoAtual`, `idadeEstadoSegundos`, `prazo`, `atrasada`.
Sem financeiro, sem sessões, sem tokens.

## Garantias

- `metricas.wip == itensTotal` por definição (contagens independentes: a de WIP vem de `fila_atual`; `itensTotal` de uma janela SQL sobre os
  itens). Os limites cortam só cards/colunas — **nunca os totais**: 27 cards com limite 20 ⇒ `wip=27`, `itensTotal=27`, `itensRetornados=20`,
  `truncado=true`; 60 definições com limite 50 ⇒ `definicoesTotal=60`, `definicoesRetornadas=50`, e `atual.wip` continua o total real.
- **Métricas = as de Gargalos** (mesmas consultas): contagens por estado, idade na etapa, `tempoExecucaoMedioSegundos` e `nExecucao`.
  `tempoExecucaoMedioSegundos` é o tempo **operacional** médio em execução por ocorrência (Demanda × etapa) — nunca horas trabalhadas.
  `null` = sem amostra (nunca zero inventado). Definição com tempo no período mas sem WIP agora aparece com `wip=0` e sem itens.
- **Ordem das colunas** (sem sequência global entre workflows): sem departamento por último; depois nomes dos departamentos → nome da
  etapa → tipo → chave. Determinística.
- **Cobertura:** `coberturaParcial`/`medicaoDesde` como em Gargalos (o passado não é estimado).
- **Ordem dos cards:** atrasadas primeiro; depois a mais antiga no estado atual; depois o maior número.
- **Somente leitura, sem tempo pessoal:** nenhuma consulta a `sessoes_trabalho`; fonte do tempo = `demanda_status_intervalos` (a mesma de
  Gargalos). Nenhum INSERT/UPDATE/DELETE/evento.
- **Consultas:** constantes (9 com 3 ou com 120 definições/520 Demandas, incluindo autenticação). Sem cache, sem índice novo.
- **RBAC:** `require_trafego_gerenciar` (admin/gestor), como Agora e Gargalos; operador 403; sem token 401; empresa sempre do token.

## Contratos que não mudaram

`GET /trafego/operacional/gargalos` e `GET /trafego/operacional/agora` seguem com o mesmo schema, valores, chaves, ordenação, filtros e
RBAC (nenhuma linha de código deles foi alterada; testes de regressão do schema e das chaves).
