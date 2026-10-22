import type { BadgeTone } from "@/components/ui/Badge";
import type { DemandaPrioridade } from "@/types/demanda";

/**
 * ÚNICA fonte da aparência da PRIORIDADE da tarefa (semáforo): Alta = vermelho, Média = âmbar, Baixa = verde. Tabela, Kanban, lista compacta e drawer consomem daqui — nada de
 * classes/cores de prioridade espalhadas pelos componentes. O tom usa os tokens do `Badge` (que já tem o contraste dos temas claro/escuro); o texto (Alta/Média/Baixa) sempre
 * acompanha a cor, que nunca é o único sinal. Cores de status, workflow, departamento e progresso são outras coisas e não passam por aqui.
 */
export const prioridadeTone: Record<DemandaPrioridade, BadgeTone> = {
  alta: "red",
  media: "amber",
  baixa: "green",
};

/** Borda esquerda do card do Kanban (mesmo semáforo). */
export const prioridadeBordaClasse: Record<DemandaPrioridade, string> = {
  alta: "border-l-red-500 dark:border-l-red-400",
  media: "border-l-amber-400 dark:border-l-amber-400",
  baixa: "border-l-emerald-500 dark:border-l-emerald-400",
};
