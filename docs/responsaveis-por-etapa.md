# Responsáveis por etapa da Demanda

Cada etapa materializada de uma Demanda pode ter **usuários** e **departamentos** próprios (tabelas `demanda_workflow_etapa_responsaveis` e `demanda_workflow_etapa_departamentos_responsaveis`).
Eles pertencem ao **snapshot da Demanda**: editar não altera o modelo de workflow, e Demandas futuras seguem o modelo original. Sem migration.

## Resolução (única fonte: `app/core/executor_etapa.py`)

1. a etapa tem responsabilidade **explícita** se possuir ao menos 1 usuário **ou** 1 departamento → vale só ela (`origem = "etapa"`). "Só departamento" já é explícita: não cai no fallback;
2. senão, os responsáveis **gerais da Demanda** são o fallback (`origem = "tarefa"`) — resolvido **em leitura**, nunca copiado para a etapa;
3. senão, ninguém (`origem = "nenhuma"`).

Leitura: cada etapa traz `usuarioResponsavelIds` / `departamentoResponsavelIds` (os vínculos **explícitos**, "configurados") e `responsabilidadeEfetiva { origem, usuarioIds, departamentoIds }`
(calculada pelo servidor; a interface não compara listas). "Iniciar trabalho" (`eh_executor_da_demanda`) consome a mesma resolução.

## Edição — `PUT /demandas/{id}/workflow/etapas/{etapaId}/responsaveis`

Substitui as duas coleções de uma vez (`usuarioResponsavelIds`, `departamentoResponsavelIds`, ambos obrigatórios; PUT porque o editor envia o estado completo).
`[]` + `[]` remove a responsabilidade explícita e a etapa volta a herdar a tarefa (não existe "sem responsável forçado").

- Autoridade: a mesma de alterar os responsáveis da Demanda — `demandas.editar` + escopo-base (fora dele, 404) + as regras de quem o ator pode atribuir (Head só departamentos que lidera,
  operador comum só o próprio contexto, Atendimento transversal). Nenhuma permissão nova.
- Etapa atual **ou futura**; etapa **concluída é somente leitura** (409) — reescrever quem era responsável depois de concluída alteraria o histórico. Tarefa arquivada: 409.
- IDs de outra empresa → 422 (sem vazar existência); etapa de outra Demanda → 404.
- Evento `demanda.workflow_responsaveis_alterados` (etapa, ator, ids antes/depois); no-op não publica; mutação + evento + encerramento de sessões na mesma transação.
- Quem deixa de ser responsável **efetivo** da etapa tem a sessão pessoal nela encerrada (`troca_responsavel`) pela regra já existente de encerramento automático.

## Criação — `workflowEtapasResponsaveis` (opcional) em `POST /demandas`

`[{ modeloEtapaId, usuarioResponsavelIds, departamentoResponsavelIds }]`, só com `workflowModeloId`. A etapa é identificada pelo **id da etapa do modelo** (inequívoco entre a tela, o modelo e a etapa
materializada — nunca por nome/ordem). As etapas listadas **substituem** o que o modelo trazia; as demais seguem copiando o modelo. Omitido = criação idêntica à legada. Tudo validado antes de qualquer
escrita e gravado na mesma transação da Demanda (falha = nenhuma Demanda parcial).

## Não coberto (de propósito)

- **Carga** lê só os vínculos explícitos da etapa (sem o fallback da tarefa) e não foi alterada; **autoridade de avançar etapa** (`pode_avancar_etapa`) também usa só os explícitos.
- **Pauta por colaborador**: fase seguinte, sobre esta mesma resolução.
