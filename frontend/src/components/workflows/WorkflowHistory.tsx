import { Badge } from "@/components/ui/Badge";
import type { WorkflowInstancia, WorkflowTransicaoHistorico } from "@/types/workflow";

type WorkflowHistoryProps = {
  history: WorkflowTransicaoHistorico[];
  workflow: WorkflowInstancia;
};

function resolveStepName(workflow: WorkflowInstancia, stepId: string) {
  if (!stepId) return "-";
  return workflow.etapas.find((etapa) => etapa.id === stepId)?.nome ?? stepId;
}

export function WorkflowHistory({ history, workflow }: WorkflowHistoryProps) {
  if (history.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-zinc-300 bg-[#faf8f4] p-6 text-center">
        <p className="text-sm font-medium text-zinc-900">
          Nenhuma transição registrada.
        </p>
        <p className="mt-1 text-sm text-zinc-500">
          As transições manuais aparecerão aqui.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {history.map((event) => (
        <div key={event.id} className="rounded-3xl border border-zinc-100 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-zinc-900">
                {resolveStepName(workflow, event.etapaOrigemId)} →{" "}
                {resolveStepName(workflow, event.etapaDestinoId)}
              </p>
              <p className="mt-1 text-sm text-zinc-500">
                {event.dataHora} · usuário {event.usuarioId}
              </p>
            </div>
            {event.observacao && <Badge>{event.observacao}</Badge>}
          </div>
        </div>
      ))}
    </div>
  );
}
