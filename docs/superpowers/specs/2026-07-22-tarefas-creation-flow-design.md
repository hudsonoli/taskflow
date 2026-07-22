# Reformulação do fluxo de criação e execução de Tarefas

Data: 2026-07-22
Status: aprovado para implementação (arquitetura + 7 ajustes aprovados pelo usuário)

## 1. Objetivo

O fluxo atual de criação de Tarefas não reflete a operação real de uma agência: Workflow só pode ser associado depois que a Tarefa já existe, não há responsáveis, o Cliente aparece como UUID cru na listagem, não existe visualização Kanban, e o botão "Visualizar" acumulou a responsabilidade indevida de ser o único lugar onde se configura Workflow.

Esta reformulação faz a Tarefa nascer **completamente configurada** — Workflow, Etapa inicial, Departamento (derivado), Responsável principal e Colaboradores — e separa claramente "configurar" (Criação/Edição) de "consultar e operar" (Visualizar/Kanban).

## 2. Estado atual (achados da investigação, Graphify + leitura de código)

- `TarefaCreate` (`backend/app/schemas/tarefa.py`) não aceita `workflowId`/`workflowEtapaId`. O modelo `Tarefa` já tem as duas colunas (`workflow_id`, `workflow_etapa_id`, Fase 11B, nullable) e o service já tem `_ensure_workflow_associacao_valida` — validador pronto, hoje só usado por `associar_workflow` (pós-criação, sem evento, sem regra de perfil).
- `Tarefa` não tem nenhum campo de responsável (nem principal, nem colaboradores, nem departamento próprio). Existe um doc de arquitetura especulativo (`docs/arquitetura-taskfloww/02-modelo-dados-futuro.md`) propondo uma entidade `Responsavel` polimórfica para "Demanda" — terminologia pré-Fase 10B (antes da entidade ser renomeada para Tarefa), escopo maior que o necessário aqui (cobre Projeto, Equipe como responsável). Não será adotado como está; serve só de referência.
- `WorkflowEtapa` já tem `departamento_id` (FK), `tempo_esperado_horas` (SLA — "preparado, sem cálculo/alerta associado ainda") e `icone` (idem). Não tem `checklist`.
- `TarefaResponse` só expõe `cliente_id`. Os únicos campos `clienteNome` existentes no código pertencem a `TarefaConsultaPitResponse` (preview de PIT do Publi, não-operacional) — não têm relação com a listagem real. Não é bug de mapper: a resolução do nome nunca foi implementada para o fluxo real de Tarefas.
- `frontend/src/components/kanban/{KanbanBoard,KanbanColumn,KanbanCard}.tsx` existem, mas `KanbanBoard` é 100% mock (colunas fixas, tarefas fake em `useState` local, sem props). Só `KanbanColumn`/`KanbanCard` são reaproveitáveis como peças visuais.
- `TarefaPeekDrawer.tsx` ("Visualizar") é hoje o único lugar com `TarefaWorkflowSection` — única superfície de configuração de Workflow.
- `DomainEventType` relevantes já existentes: `TAREFA_CRIADA`, `TAREFA_ATUALIZADA`, `TAREFA_STATUS_ALTERADO`, `TAREFA_INATIVADA`, `TAREFA_REATIVADA`, `TAREFA_WORKFLOW_ETAPA_ALTERADA`. **Não existe** `tarefa.workflow_associado` — é uma string referenciada em `TarefaWorkflowSection.tsx` (`eventoWorkflowLabel`) para um evento que a `associar_workflow` atual nunca publica de fato. Achado incidental, corrigido como parte deste trabalho (ver §8).
- `require_admin_or_gestor` (dependency FastAPI, `app/dependencies/authorization.py`) já existe para gates de perfil no nível de rota — mas a regra do §6 é condicionada ao **estado** da própria Tarefa, então precisa ser verificada dentro do service, não só na rota.

## 3. Arquitetura da criação

```
TarefaCreate (payload)
  título, descrição, cliente, prioridade, datas     (já existe, inalterado)
  + workflowId (opcional)
      → se workflowEtapaId omitido: service seleciona a etapa de menor `ordem` do Workflow
      → _ensure_workflow_associacao_valida (já existe) valida a referência
      → _aplicar_template_etapa (novo, ponto de extensão — ver §5) deriva departamento e expõe SLA
  + responsavelPrincipalUsuarioId (opcional)
  + colaboradoresUsuarioIds (opcional, lista)
       ↓
Tarefa criada com workflow_id + workflow_etapa_id + responsável + colaboradores já gravados
       ↓
Publica TAREFA_CRIADA (payload já inclui os campos novos — nenhum evento novo)
```

Nenhuma etapa de "associar depois" é necessária no caminho feliz. `associar_workflow` (endpoint separado) continua existindo só para correção administrativa pós-criação (ver §6).

## 4. Responsáveis (principal, colaboradores, departamento)

- **Departamento**: não é campo da Tarefa. Sempre `workflow_etapa.departamento_id` da etapa atual — somente leitura, muda sozinho quando a Tarefa muda de etapa (Kanban ou histórico).
- **Responsável principal**: novo `Tarefa.responsavel_principal_usuario_id` (FK nullable → `usuarios.id`, `ondelete="SET NULL"`), mesmo padrão de `criada_por_usuario_id`/`inativado_por_usuario_id` já existentes na própria tabela.
- **Colaboradores**: nova tabela `tarefa_colaboradores` (`id`, `empresa_id`, `tarefa_id` FK, `usuario_id` FK, `created_at`), mesmo padrão de vínculo N:N já usado por `UsuarioEquipe`/`UsuarioDepartamento`/`UsuarioCargo` (empresa_id denormalizado da Tarefa, índices em `tarefa_id` e `usuario_id`, unicidade `(tarefa_id, usuario_id)`). Repository/Service próprios, espelhando os desses vínculos existentes.
- Ambos aceitos em `TarefaCreate` (opcionais) e editáveis depois via `TarefaUpdate` (`responsavelPrincipalUsuarioId`) e um endpoint dedicado de colaboradores (mesmo padrão de `UsuarioEquipeRepository`), não um array solto dentro do PATCH genérico.

## 5. Workflow como template operacional — ponto de extensão

Ao selecionar Workflow + Etapa (automática ou manual), o service aplica um passo explícito e isolado:

```python
def _aplicar_template_etapa(self, etapa: WorkflowEtapa) -> dict:
    """
    Ponto de extensão único para tudo que uma WorkflowEtapa "empresta" à
    Tarefa na criação. Hoje aplica só o que já existe (departamento
    derivado, SLA informativo). Quando checklist/campos obrigatórios/
    regras de aprovação/documentos/automações/notificações forem
    implementados como conceitos reais de WorkflowEtapa, entram aqui —
    sem precisar redesenhar create_tarefa.
    """
    return {
        "departamento_id": etapa.departamento_id,
        "sla_horas_esperado": etapa.tempo_esperado_horas,
    }
```

- **Departamento**: já coberto por §4 (derivado, somente leitura).
- **SLA**: `workflow_etapa.tempo_esperado_horas` é exibido como informação da etapa atual na Tarefa (Peek e, se fizer sentido no layout, também no card do Kanban) — sem novo cálculo, sem alerta, sem alterar o comportamento do campo. Só passa a ser lido e mostrado.
- **Explicitamente fora de escopo nesta implementação** (arquitetura só precisa deixar o ponto de extensão pronto): Checklist, campos obrigatórios, regras de aprovação, documentos obrigatórios, automações, notificações. Nenhuma entidade, tabela, tela ou UI nova para esses itens agora.

## 6. Reatribuição de Workflow (regra por estado)

Regra aplicada em `TarefaService.update_tarefa` quando `workflow_id`/`workflow_etapa_id` estão entre os campos alterados (não na criação — lá é sempre livre):

| Status da Tarefa | Quem pode trocar Workflow/Etapa |
|---|---|
| `rascunho` | Qualquer usuário autorizado a editar a Tarefa |
| `planejada` | Qualquer usuário autorizado a editar a Tarefa |
| qualquer outro (`em_execucao`, `pausada`, `bloqueada`, `aguardando_cliente`, `concluida`, `cancelada`) | Só `admin`/`gestor` (`perfil_base`) |

**Nota de escopo**: hoje **todas** as rotas de Tarefa (`app/api/routes/tarefas.py`) já exigem `require_admin_or_gestor` — não existe perfil mais amplo com acesso a Tarefa nesta fase. Esta regra é, portanto, preparatória: não muda nenhum comportamento observável hoje (todo mundo que já pode editar Tarefa é admin/gestor), mas fica correta e pronta para quando o acesso a Tarefa for ampliado (ex.: Operador editando as próprias tarefas em rascunho/planejada). Implementar mesmo assim, como regra de negócio explícita no service — não pular por ser um no-op hoje.

Implementação: novo erro tipado `TarefaWorkflowReassociacaoNaoPermitidaError(ValueError)`, verificado dentro do service (precisa do `status` atual da Tarefa + perfil do ator — não dá para expressar só como dependency de rota). Mapeado para 403 em `handle_tarefa_error`, mesmo padrão dos demais erros do módulo.

## 7. Cliente sem UUID na interface

- `TarefaRepository.list`/`get_by_id` ganham `join` com `Cliente`.
- `TarefaResponse` ganha `cliente_nome_exibicao` (alias `clienteNomeExibicao`), resolvido no backend via `COALESCE(nome_fantasia, razao_social, nome)` — mesma regra que `nomePrincipal` já usa no domínio de Cliente. Nunca calculado no frontend.
- `types/tarefa-domain.ts`/mapper (frontend) propagam o campo; `TarefasView.tsx` e o novo Kanban exibem esse nome, nunca `clienteId` bruto. Se `clienteId` for nulo, mostra "-" (mesmo padrão já usado em outros lugares do app), nunca um UUID.

## 8. Lista + Kanban — mesma fonte de dados

- `useTarefasList` (já existe) continua sendo a única fonte. Kanban filtra client-side por `workflowId` sobre o mesmo resultado — mesmo padrão que `applyClientSideView` já aplica hoje para prioridade/ordenação em `TarefasView.tsx`.
- Toggle Lista/Kanban no `PageHeader`, mesmo estado de filtros por trás dos dois.
- Kanban é **por Workflow selecionado** (seletor no topo). Colunas = Etapas daquele Workflow (`ordem` asc). Tarefas sem Workflow não aparecem em nenhum board — continuam visíveis normalmente na Lista.
- Arrastar um card entre colunas executa a transição de Etapa correspondente, reaproveitando a mesma lógica que `WorkflowRuntimeCard.tsx`/`useWorkflowExecution.ts` já usam no Peek — publica `TAREFA_WORKFLOW_ETAPA_ALTERADA` (já existe), nenhum evento novo.
- Novo orquestrador `TarefaKanbanBoard.tsx` (em `components/tarefas/`, não em `components/kanban/`, pois os dados são específicos de Tarefa) reaproveita `KanbanColumn`/`KanbanCard` como peças visuais.
- Correção incidental: `TarefaWorkflowSection.tsx`'s `eventoWorkflowLabel()` referencia `"tarefa.workflow_associado"`, que nunca é publicado pelo backend atual — o branch morto é removido junto com a refatoração desta seção (§9).

## 9. "Visualizar" deixa de ser obrigatório para configurar Workflow

- `TarefaPeekDrawer.tsx` mantém: resumo (incluindo Workflow/Etapa atual, SLA da etapa, responsáveis, departamento derivado), histórico/timeline, inativar/reativar, e avançar etapa (`WorkflowRuntimeCard`, reaproveitado) — consulta operacional + pequenas ações, exatamente o que o nome promete.
- Configuração inicial (Workflow, Etapa, responsáveis) só existe em `TarefaCreateDrawer.tsx`.
- Reatribuição de Workflow/Etapa/responsáveis já criada passa a viver em `TarefaEditDrawer.tsx`, sujeita à regra de perfil por status (§6) — nunca mais escondida atrás de "Visualizar".

## 10. Eventos de domínio (reaproveitamento, nenhum evento novo)

| Ação | Evento publicado |
|---|---|
| Criar Tarefa (com ou sem Workflow/responsáveis) | `TAREFA_CRIADA` (payload já inclui os campos novos) |
| Editar Tarefa, incluindo reatribuir Workflow/responsáveis | `TAREFA_ATUALIZADA` (via `campos_alterados`, já existe) |
| Mover card no Kanban (executar transição de etapa) | `TAREFA_WORKFLOW_ETAPA_ALTERADA` (já existe) |
| Inativar/Reativar | `TAREFA_INATIVADA`/`TAREFA_REATIVADA` (já existem, inalterados) |

## 11. Arquivos afetados

**Backend**
- `app/models/tarefa.py` — `responsavel_principal_usuario_id`; nova classe `TarefaColaborador`
- `alembic/versions/` — nova migração (coluna + tabela `tarefa_colaboradores`)
- `app/schemas/tarefa.py` — `TarefaCreate`/`TarefaUpdate`/`TarefaResponse` (workflow, responsáveis, `clienteNomeExibicao`)
- `app/services/tarefa_service.py` — `create_tarefa` (aplica workflow/etapa/template/responsáveis), `update_tarefa` (regra §6), novo `_aplicar_template_etapa`
- `app/repositories/tarefa_repository.py` — join com Cliente na listagem/detalhe
- novo `app/repositories/tarefa_colaborador_repository.py`
- `app/api/routes/tarefas.py` — payload de criação, endpoint de colaboradores, mapeamento do novo erro de reassociação

**Frontend**
- `TarefaCreateDrawer.tsx`, `tarefa-form-value.ts`, `TarefaFormFields.tsx` — campos de Workflow/Etapa/responsáveis
- `TarefaEditDrawer.tsx` — reatribuição de Workflow/responsáveis
- `TarefaPeekDrawer.tsx`, `TarefaWorkflowSection.tsx` — reduzido a consulta + pequenas ações, remove branch morto de `eventoWorkflowLabel`
- `TarefasView.tsx` — toggle Lista/Kanban, nome do Cliente em vez de UUID
- novo `TarefaKanbanBoard.tsx` (+ card/coluna específicos de Tarefa, reaproveitando `components/kanban/KanbanColumn.tsx`/`KanbanCard.tsx`)
- `types/tarefa-api.ts`, `types/tarefa-domain.ts`, mapper de Tarefa — `clienteNomeExibicao`, workflow/etapa/responsáveis na criação
- `useTarefaCreate.ts` — payload novo
- novo hook de colaboradores (criar/listar/remover vínculo)

## 12. Fora de escopo (explicitamente adiado)

Checklist, campos obrigatórios por etapa, regras de aprovação, documentos obrigatórios, automações, notificações, qualquer tela de autoria desses conceitos em WorkflowEtapa. O ponto de extensão (§5) existe para que, quando esses recursos forem implementados, `create_tarefa` não precise ser redesenhado.

## 13. Riscos

- Maior peça greenfield: `tarefa_colaboradores` é 100% nova, sem precedente direto para Tarefa (só o padrão geral de vínculo Usuario↔entidade).
- Mudança de comportamento visível: Workflow deixa de ser "associação avançada" e passa a ser parte do cadastro — usuários acostumados ao fluxo atual percebem a mudança.
- Regra de perfil por status (§6) depende de `status` estar correto no momento da checagem — nenhuma condição de corrida esperada (mesma transação), mas vale teste explícito de cada faixa de status.
- `tempo_esperado_horas` exibido pela primeira vez em qualquer UI — checar que não há suposição implícita em algum lugar de que esse campo "nunca é mostrado".
