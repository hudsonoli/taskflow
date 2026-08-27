import { generateId } from "@/lib/ids";
import type { ModeloCampanhaItemFormDraft } from "@/types/modelo-campanha";

/**
 * Fábrica/mapeador compartilhados entre a biblioteca de Modelos de Campanha
 * (ModeloCampanhaFormModal) e o snapshot aplicado num Projeto (ModeloCampanhaSection) — os
 * dois editam a mesma forma de item (`ModeloCampanhaItemFormDraft`) através do componente
 * `ModeloCampanhaItensEditor` (Fase 2G.5C3). Mantido em `lib/` (não em `components/`) porque
 * `itemEditorDraftParaPayload` é consumido por `api-backend.ts`, que nunca importa de
 * `components/` — ver CLAUDE.md.
 */

export function criarItemModeloCampanhaVazio(): ModeloCampanhaItemFormDraft {
  return {
    clientKey: generateId("item-modelo-campanha"),
    nome: "Novo item",
    briefingPadrao: "",
    prioridadePadrao: "media",
    pecaId: null,
    pecaNome: null,
    tipoTarefaId: null,
    tipoTarefaNome: null,
    workflowModeloId: null,
    workflowModeloNome: null,
    responsavelUsuarioId: null,
    responsavelUsuarioNome: null,
    responsavelDepartamentoId: null,
    responsavelDepartamentoNome: null,
  };
}

// `id` só quando o item já existia — item novo nunca manda id (o servidor gera). Nomes
// resolvidos (`pecaNome` etc.) são só exibição local, nunca fazem parte do payload — os dois
// schemas de entrada do backend (ModeloCampanhaItemInput e
// ProjetoModeloCampanhaItemInput) usam `extra="forbid"` e não os conhecem.
export function itemModeloCampanhaDraftParaPayload(item: ModeloCampanhaItemFormDraft) {
  return {
    ...(item.id ? { id: item.id } : {}),
    nome: item.nome,
    briefingPadrao: item.briefingPadrao.trim() || null,
    prioridadePadrao: item.prioridadePadrao,
    pecaId: item.pecaId,
    tipoTarefaId: item.tipoTarefaId,
    workflowModeloId: item.workflowModeloId,
    responsavelUsuarioId: item.responsavelUsuarioId,
    responsavelDepartamentoId: item.responsavelDepartamentoId,
  };
}
