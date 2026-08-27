import type { ModeloCampanhaItemFormDraft, PrioridadePadrao } from "@/types/modelo-campanha";

/**
 * Snapshot relacional de Modelo de Campanha aplicado a um Projeto (Fase 2G.5C). Distinto do
 * tipo `ModeloCampanha` da biblioteca (`types/modelo-campanha.ts`) de propósito: aqui os
 * `*NomeSnapshot` são dado HISTÓRICO, escrito uma vez no momento da aplicação/troca — nunca
 * recalculado. Reutilizar o tipo da biblioteca teria misturado as duas semânticas (entidade
 * viva vs. fotografia) sob o mesmo nome de campo.
 */
export type ProjetoModeloCampanhaSnapshotItem = {
  id: string;
  ordem: number;
  nome: string;
  briefingPadrao: string | null;
  prioridadePadrao: PrioridadePadrao;
  pecaId: string | null;
  pecaNomeSnapshot: string | null;
  tipoTarefaId: string | null;
  tipoTarefaNomeSnapshot: string | null;
  workflowModeloId: string | null;
  workflowModeloNomeSnapshot: string | null;
  responsavelUsuarioId: string | null;
  responsavelUsuarioNomeSnapshot: string | null;
  responsavelDepartamentoId: string | null;
  responsavelDepartamentoNomeSnapshot: string | null;
};

export type ProjetoModeloCampanhaSnapshot = {
  id: string;
  modeloCampanhaOrigemId: string | null;
  modeloCampanhaNomeSnapshot: string | null;
  aplicadoAt: string | null;
  aplicadoPorUsuarioId: string | null;
  itens: ProjetoModeloCampanhaSnapshotItem[];
  createdAt: string;
  updatedAt: string;
};

/**
 * Payload de `PATCH /projetos/{id}/modelo-campanha` — reaproveita a MESMA forma de item da
 * biblioteca (`ModeloCampanhaItemFormDraft`, com `clientKey` local e `*Nome` genérico, não
 * `*NomeSnapshot`) porque é o que `ModeloCampanhaItensEditor` edita nos dois contextos. A
 * conversão de/para o formato do snapshot (`pecaNomeSnapshot` etc.) acontece na borda, em
 * `lib/api-backend.ts`.
 */
export type ProjetoModeloCampanhaUpdateDraft = {
  itens: ModeloCampanhaItemFormDraft[];
};
