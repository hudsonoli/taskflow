import type { Demanda, DemandaStatus } from "@/types/demanda";

/**
 * Apresentação do PROGRESSO da tarefa na visão "Solicitadas por mim" (acompanhamento).
 *
 * A matemática (etapas concluídas ÷ etapas do fluxo, "Concluída = 100%", "sem fluxo") é do SERVIDOR (`Demanda.progresso`). Este módulo só decide COMO mostrar o que o servidor
 * já calculou: o rótulo do estado e a classificação visual de cada etapa. Nada de percentual calculado aqui, nada de tempo, estimativa, sessão ou prazo.
 */

export type EstadoProgresso = {
  /** Rótulo do estado quando ele precisa se destacar do percentual (`null` = só a barra e o %). */
  rotulo: "Cancelada" | "Sem fluxo" | "Bloqueada" | "Aguardando cliente" | "Pausada" | null;
  /** Cancelada e sem fluxo não mostram barra de andamento (nunca "0%" nem "100%" inventados). */
  mostrarBarra: boolean;
};

const ROTULO_POR_STATUS: Partial<Record<DemandaStatus, NonNullable<EstadoProgresso["rotulo"]>>> = {
  bloqueada: "Bloqueada",
  aguardando_cliente: "Aguardando cliente",
  pausada: "Pausada",
};

export function estadoDoProgresso(demanda: Pick<Demanda, "status" | "progresso">): EstadoProgresso {
  const progresso = demanda.progresso;
  if (demanda.status === "cancelada") return { rotulo: "Cancelada", mostrarBarra: false };
  if (!progresso || progresso.semFluxo || progresso.percentual === null) return { rotulo: "Sem fluxo", mostrarBarra: false };
  return { rotulo: ROTULO_POR_STATUS[demanda.status] ?? null, mostrarBarra: true };
}

export type EstadoSegmento = "concluida" | "atual" | "futura";

export type SegmentoProgresso = { id: string; nome: string; estado: EstadoSegmento };

/**
 * Um segmento por etapa do workflow materializado, na ordem do fluxo. Classificação só de EXIBIÇÃO: concluída = `status === "concluida"` (o mesmo critério do servidor);
 * atual = a etapa que o servidor apontou (`etapaAtualId`); as demais, futuras. Etapa reaberta/rejeitada volta a não ser concluída porque o status vem do servidor.
 */
export function segmentosDoProgresso(demanda: Pick<Demanda, "workflowEtapas" | "etapaAtualId" | "status">): SegmentoProgresso[] {
  const concluida = demanda.status === "concluida";
  return [...demanda.workflowEtapas]
    .sort((a, b) => a.ordem - b.ordem)
    .map((etapa) => ({
      id: etapa.id,
      nome: etapa.nome,
      estado: etapa.status === "concluida" || concluida ? "concluida" : etapa.id === demanda.etapaAtualId ? "atual" : "futura",
    }));
}

/** "2 de 5 etapas concluídas" — contagens do servidor. */
export function resumoDoProgresso(progresso: NonNullable<Demanda["progresso"]>): string {
  const { etapasConcluidas, etapasTotal } = progresso;
  return `${etapasConcluidas} de ${etapasTotal} ${etapasTotal === 1 ? "etapa concluída" : "etapas concluídas"}`;
}
