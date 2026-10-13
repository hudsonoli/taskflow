import { Check } from "lucide-react";
import clsx from "clsx";
import { workflowEtapaStatusLabels } from "@/lib/demandas";
import type { FluxoDaTarefa, PassoFluxo } from "@/lib/projetos-progresso";

const TEXTO_PASSO: Record<PassoFluxo, string> = {
  concluida: workflowEtapaStatusLabels.concluida,
  atual: "Etapa atual",
  atual_pausada: "Etapa atual (pausada)",
  pendente: workflowEtapaStatusLabels.pendente,
};

/** Acima disso os pontos deixam de caber numa coluna: fica só o texto "N/M etapas". */
const MAX_PONTOS = 10;

/**
 * Fluxo da tarefa: um ponto por etapa materializada (concluída ✓, atual ◉, pendente ○) + "N/M etapas". NÃO é percentual de trabalho (etapas têm esforços diferentes).
 * Sem workflow: "Sem workflow" discreto — nada de percentual inventado a partir do status.
 */
export function FluxoEtapas({ fluxo }: { fluxo: FluxoDaTarefa }) {
  if (fluxo.tipo === "sem_workflow") return <span className="text-xs text-fg-subtle">Sem workflow</span>;
  const resumo = `${fluxo.concluidas}/${fluxo.total} etapas`;
  const rotulo = `Fluxo: ${fluxo.concluidas} de ${fluxo.total} etapas concluídas${fluxo.atual ? `; etapa atual: ${fluxo.atual.nome}` : "; todas concluídas"}`;
  return (
    <div className="flex items-center gap-2" role="img" aria-label={rotulo}>
      {fluxo.total <= MAX_PONTOS && (
        <span className="flex items-center gap-1" aria-hidden>
          {fluxo.passos.map((passo) => (
            <span
              key={passo.id}
              title={`${passo.nome} — ${TEXTO_PASSO[passo.estado]}`}
              className={clsx(
                "flex h-3 w-3 shrink-0 items-center justify-center rounded-full",
                passo.estado === "concluida" && "bg-emerald-500 text-white",
                passo.estado === "atual" && "border-2 border-indigo-500 bg-indigo-500/20",
                passo.estado === "atual_pausada" && "border-2 border-amber-500 bg-amber-500/20",
                passo.estado === "pendente" && "border-[1.5px] border-zinc-500",
              )}
            >
              {passo.estado === "concluida" && <Check className="h-2 w-2" strokeWidth={4} />}
            </span>
          ))}
        </span>
      )}
      <span className="whitespace-nowrap text-xs font-medium text-fg-muted">{resumo}</span>
    </div>
  );
}
