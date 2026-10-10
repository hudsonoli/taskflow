// Progressão do workflow da Demanda (Fase 8A) — lógica PURA (testável com `node --test`), sem React nem fetch.
//
// O SERVIDOR é a fonte da verdade: qual é a etapa atual (`etapaAtualId`), quem pode avançar (`podeAvancar`, calculado para o usuário da
// requisição) e o que acontece depois. Aqui só se traduz esse estado em rótulos/ações. O frontend NÃO reconstrói RBAC a partir de
// perfil/departamento e NÃO escolhe a próxima etapa (não existe `nextStepId`).
import type { DemandaWorkflowEtapa } from "../types/demanda.ts";

export type EstadoEtapa = "concluida" | "atual" | "pendente";
export type AcaoEtapa = "concluir" | "aprovar";

export const CODIGOS_CONFLITO_WORKFLOW = [
  "SEM_WORKFLOW",
  "WORKFLOW_SEM_ETAPAS",
  "WORKFLOW_CONCLUIDO",
  "ETAPA_NAO_ATUAL",
  "ETAPA_JA_CONCLUIDA",
  "ETAPA_PAUSADA",
  "DEMANDA_ARQUIVADA",
] as const;

/** 409 da progressão: o estado do servidor mudou (outra pessoa avançou, workflow já concluído…). A interface recarrega e explica. */
export class WorkflowEtapaConflitoError extends Error {
  codigo: string;

  constructor(message: string, codigo: string) {
    super(message);
    this.name = "WorkflowEtapaConflitoError";
    this.codigo = codigo;
  }
}

export function ehConflitoDeWorkflow(erro: unknown): erro is WorkflowEtapaConflitoError {
  return erro instanceof WorkflowEtapaConflitoError;
}

type DemandaComWorkflow = { workflowEtapas: DemandaWorkflowEtapa[]; etapaAtualId: string | null };

export function etapasOrdenadas(demanda: Pick<DemandaComWorkflow, "workflowEtapas">): DemandaWorkflowEtapa[] {
  return [...demanda.workflowEtapas].sort((a, b) => a.ordem - b.ordem);
}

/** Concluída → status do servidor; atual → o `etapaAtualId` do servidor; o resto é pendente. Nunca recalculado no cliente. */
export function estadoDaEtapa(etapa: Pick<DemandaWorkflowEtapa, "id" | "status">, etapaAtualId: string | null): EstadoEtapa {
  if (etapa.status === "concluida") return "concluida";
  return etapa.id === etapaAtualId ? "atual" : "pendente";
}

/** Workflow concluído = tem etapas e nenhuma é a atual. NÃO significa Demanda concluída. */
export function workflowConcluido(demanda: DemandaComWorkflow): boolean {
  return demanda.workflowEtapas.length > 0 && demanda.etapaAtualId === null;
}

export function acaoDaEtapa(etapa: Pick<DemandaWorkflowEtapa, "tipo">): AcaoEtapa {
  return etapa.tipo === "aprovacao" ? "aprovar" : "concluir";
}

export function rotuloDaAcao(etapa: Pick<DemandaWorkflowEtapa, "tipo">): string {
  return acaoDaEtapa(etapa) === "aprovar" ? "Aprovar etapa" : "Concluir etapa";
}

export function rotuloEstadoConcluido(etapa: Pick<DemandaWorkflowEtapa, "tipo">): string {
  return etapa.tipo === "aprovacao" ? "Aprovada" : "Concluída";
}

/** "Aprovada por" (aprovação) / "Concluída por" (execução) — um único campo persistido, o tipo decide o rótulo. */
export function rotuloQuemConcluiu(etapa: Pick<DemandaWorkflowEtapa, "tipo">): string {
  return etapa.tipo === "aprovacao" ? "Aprovada por" : "Concluída por";
}

export function ehUltimaEtapa(demanda: Pick<DemandaComWorkflow, "workflowEtapas">, etapa: Pick<DemandaWorkflowEtapa, "id" | "ordem">): boolean {
  return demanda.workflowEtapas.every((outra) => outra.id === etapa.id || outra.ordem < etapa.ordem);
}

export function perguntaDeConfirmacao(demanda: Pick<DemandaComWorkflow, "workflowEtapas">, etapa: DemandaWorkflowEtapa): string {
  const verbo = etapa.tipo === "aprovacao" ? "Aprovar" : "Concluir";
  if (ehUltimaEtapa(demanda, etapa)) {
    return `${verbo} esta etapa conclui o workflow, mas não conclui a tarefa. Continuar?`;
  }
  return `${verbo} esta etapa e avançar para a próxima?`;
}

/**
 * O botão só existe para a etapa ATUAL, quando o SERVIDOR disse `podeAvancar` e o drawer não está em leitura (Pauta global). Sem
 * autoridade a etapa continua visível, só em modo leitura.
 */
export function podeExibirAcao(
  etapa: Pick<DemandaWorkflowEtapa, "id" | "status" | "podeAvancar">,
  etapaAtualId: string | null,
  somenteLeitura: boolean,
): boolean {
  return !somenteLeitura && etapa.id === etapaAtualId && etapa.status !== "concluida" && etapa.podeAvancar === true;
}

export type ResultadoAvanco =
  | { ok: true; demanda: DemandaComWorkflow & Record<string, unknown> }
  | { ok: false; mensagem: string; conflito: boolean; demanda?: DemandaComWorkflow & Record<string, unknown> };

/**
 * Executa a ação e traduz o desfecho. No 409 recarrega o estado do servidor (o chamador mostra a mensagem e o workflow já aparece
 * atualizado); em outros erros devolve a mensagem sem recarregar. `avancar`/`recarregar` são injetados (API real na tela, stubs no teste).
 */
export async function avancarEtapaDoWorkflow<D extends DemandaComWorkflow & Record<string, unknown>>(entrada: {
  etapa: Pick<DemandaWorkflowEtapa, "id" | "tipo">;
  avancar: (acao: AcaoEtapa, etapaId: string) => Promise<D>;
  recarregar: () => Promise<D>;
}): Promise<{ ok: true; demanda: D } | { ok: false; mensagem: string; conflito: boolean; demanda?: D }> {
  try {
    const demanda = await entrada.avancar(acaoDaEtapa(entrada.etapa), entrada.etapa.id);
    return { ok: true, demanda };
  } catch (erro) {
    const mensagem = erro instanceof Error && erro.message ? erro.message : "Não foi possível avançar o workflow.";
    if (!ehConflitoDeWorkflow(erro)) return { ok: false, mensagem, conflito: false };
    try {
      return { ok: false, mensagem, conflito: true, demanda: await entrada.recarregar() };
    } catch {
      return { ok: false, mensagem, conflito: true };
    }
  }
}
