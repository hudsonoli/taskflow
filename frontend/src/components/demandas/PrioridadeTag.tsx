import { Badge } from "@/components/ui/Badge";
import { prioridadeDemandaLabels } from "@/lib/demandas";
import { prioridadeTone } from "@/lib/prioridade-demanda";
import type { DemandaPrioridade } from "@/types/demanda";

/** Etiqueta de prioridade (semáforo): cor + texto. Único componente usado por tabela, Kanban, lista compacta e drawer. */
export function PrioridadeTag({ prioridade }: { prioridade: DemandaPrioridade }) {
  return (
    <span data-prioridade={prioridade} className="inline-flex shrink-0">
      <Badge tone={prioridadeTone[prioridade]}>{prioridadeDemandaLabels[prioridade]}</Badge>
    </span>
  );
}
