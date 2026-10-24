"use client";

import { motion } from "framer-motion";
import { estadoDoProgresso } from "@/lib/progresso-demanda";
import type { Demanda } from "@/types/demanda";

const RAIO = 6;
const CIRCUNFERENCIA = 2 * Math.PI * RAIO;

/**
 * Anel de progresso do card do Kanban. O número vem do servidor (`Demanda.progresso`, etapas concluídas ÷ etapas do fluxo): aqui só se desenha, nunca se recalcula. Sem fluxo,
 * cancelada ou sem percentual não há anel (a mesma regra da barra de acompanhamento: `estadoDoProgresso`). O percentual sempre aparece em texto — a cor não é o único sinal.
 */
export function KanbanProgressoAnel({ demanda }: { demanda: Pick<Demanda, "status" | "progresso"> }) {
  const estado = estadoDoProgresso(demanda);
  const percentual = demanda.progresso?.percentual;
  if (!estado.mostrarBarra || percentual == null) return null;
  const valor = Math.max(0, Math.min(100, percentual));
  const concluido = valor >= 100;

  return (
    <span className="inline-flex items-center gap-1" title={`Progresso do fluxo: ${valor}%`} data-testid="kanban-progresso">
      <svg viewBox="0 0 16 16" aria-hidden className="h-3.5 w-3.5 -rotate-90">
        <circle cx="8" cy="8" r={RAIO} fill="none" strokeWidth="2" className="stroke-black/10 dark:stroke-white/15" />
        <motion.circle
          cx="8"
          cy="8"
          r={RAIO}
          fill="none"
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray={CIRCUNFERENCIA}
          initial={false}
          animate={{ strokeDashoffset: CIRCUNFERENCIA - (CIRCUNFERENCIA * valor) / 100 }}
          transition={{ type: "spring", stiffness: 420, damping: 36, mass: 0.9 }}
          className={concluido ? "stroke-emerald-500" : "stroke-indigo-500 dark:stroke-indigo-400"}
        />
      </svg>
      <span className="text-[11.5px] font-medium tabular-nums text-fg-muted">{valor}%</span>
    </span>
  );
}
