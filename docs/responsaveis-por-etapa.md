# Responsáveis por etapa da Demanda

Cada etapa materializada de uma Demanda pode ter **usuários** e **departamentos** próprios (tabelas `demanda_workflow_etapa_responsaveis` e `demanda_workflow_etapa_departamentos_responsaveis`).
Eles pertencem ao **snapshot da Demanda**: editar não altera o modelo de workflow, e Demandas futuras seguem o modelo original. Sem migration.

## Resolução (única fonte: `app/core/executor_etapa.py`)

1. a etapa tem responsabilidade **explícita** se possuir ao menos 1 usuário **ou** 1 departamento → vale só ela (`origem = "etapa"`). "Só departamento" já é explícita: não cai no fallback;
2. senão, os responsáveis **gerais da Demanda** são o fallback (`origem = "tarefa"`) — resolvido **em leitura**, nunca copiado para a etapa;
3. senão, ninguém (`origem = "nenhuma"`).

Leitura: cada etapa traz `usuarioResponsavelIds` / `departamentoResponsavelIds` (os vínculos **explícitos**, "configurados") e `responsabilidadeEfetiva { origem, usuarioIds, departamentoIds }`
(calculada pelo servidor; a interface não compara listas).

### Consumidores da responsabilidade efetiva

Todo consumidor operacional usa a MESMA resolução (`resolver_responsabilidade_etapa`; no banco, `DemandaRepository.responsabilidade_efetiva_da_etapa` e, em SQL agregado, a UNION "vínculos explícitos
+ geral só para etapa sem nenhum vínculo"). Não existe resolvedor por consumidor.

| Consumidor | Usa |
|---|---|
| Leitura da Demanda (`responsabilidadeEfetiva`, `podeAvancar`, `podeRejeitar`) | efetiva |
| Autoridade de concluir / aprovar / rejeitar (`_preparar_etapa_atual`) | efetiva (admin/gestor seguem com a autoridade de gestão; Head só do que lidera) |
| Iniciar trabalho / sessão pessoal (`eh_executor_da_demanda`) | efetiva |
| Carga semanal (`usuarios_das_etapas`, `departamentos_das_etapas`) | efetiva (a matemática de planejamento não mudou) |
| Tráfego: KPI "sem responsável", responsáveis/departamentos exibidos | efetiva |
| Notificação da próxima etapa (`destinatarios_da_etapa`) | efetiva |
| Encerramento de sessões ao trocar responsáveis (da etapa **ou** gerais) | efetiva, antes × depois |
| Meu Dia / Meu Departamento | escopo da DEMANDA (`demanda_responsaveis` / `demanda_departamentos`), que já contém o fallback |
| Edição de responsáveis da etapa, "Restaurar padrão do modelo", template/materialização | **explícita** (configuração) |
| Esforço e planejamento da etapa (`_etapa_para_ajuste`) | **explícita**: o fallback NÃO concede ajuste de esforço/planejamento nem gestão da Demanda |
| Relatórios de participação, histórico e auditoria | vínculos reais/históricos (inalterados) |

Quem tem apenas o fallback avança a etapa e inicia trabalho, mas não ganha `demandas.editar`, gestão de workflow, esforço, planejamento nem troca de responsáveis.

## Edição — `PUT /demandas/{id}/workflow/etapas/{etapaId}/responsaveis`

Substitui as duas coleções de uma vez (`usuarioResponsavelIds`, `departamentoResponsavelIds`, ambos obrigatórios; PUT porque o editor envia o estado completo).
`[]` + `[]` remove a responsabilidade explícita e a etapa volta a herdar a tarefa (não existe "sem responsável forçado").

- Autoridade: a mesma de alterar os responsáveis da Demanda — `demandas.editar` + escopo-base (fora dele, 404) + as regras de quem o ator pode atribuir (Head só departamentos que lidera,
  operador comum só o próprio contexto, Atendimento transversal). Nenhuma permissão nova.
- Etapa atual **ou futura**; etapa **concluída é somente leitura** (409) — reescrever quem era responsável depois de concluída alteraria o histórico. Tarefa arquivada: 409.
- IDs de outra empresa → 422 (sem vazar existência); etapa de outra Demanda → 404.
- Evento `demanda.workflow_responsaveis_alterados` (etapa, ator, ids antes/depois); no-op não publica; mutação + evento + encerramento de sessões na mesma transação.
- Quem deixa de ser responsável **efetivo** da etapa tem a sessão pessoal nela encerrada (`troca_responsavel`): vale para a troca dos responsáveis da etapa **e** para a troca dos responsáveis/departamentos
  GERAIS da Demanda enquanto a etapa atual herda (quem era executor efetivo antes e não é depois). Nunca se cria sessão automaticamente para o novo responsável.

## Criação — `workflowEtapasResponsaveis` (opcional) em `POST /demandas`

`[{ modeloEtapaId, usuarioResponsavelIds, departamentoResponsavelIds }]`, só com `workflowModeloId`. A etapa é identificada pelo **id da etapa do modelo** (inequívoco entre a tela, o modelo e a etapa
materializada — nunca por nome/ordem). As etapas listadas **substituem** o que o modelo trazia; as demais seguem copiando o modelo. Omitido = criação idêntica à legada. Tudo validado antes de qualquer
escrita e gravado na mesma transação da Demanda (falha = nenhuma Demanda parcial).

## Não coberto (de propósito)

- **Pauta por colaborador**: fase seguinte, sobre esta mesma resolução.
- Esforço/planejamento continuam exigindo vínculo explícito (ou gestão); estender o fallback a eles é decisão de produto.
- Rótulo "Usuário indisponível" para responsável inativo/removido: P2 (`P2_STAGE_ASSIGNEE_UNAVAILABLE_USER_LABEL`).
