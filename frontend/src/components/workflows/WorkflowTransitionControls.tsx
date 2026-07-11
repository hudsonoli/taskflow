import { Button } from "@/components/ui/Button";
import type { WorkflowInstancia } from "@/types/workflow";

type WorkflowTransitionControlsProps = {
  workflow: WorkflowInstancia;
  onNext: () => void;
  onPrevious: () => void;
  onBlock: () => void;
  onUnblock: () => void;
};

export function WorkflowTransitionControls({
  workflow,
  onNext,
  onPrevious,
  onBlock,
  onUnblock,
}: WorkflowTransitionControlsProps) {
  const currentIndex = workflow.etapas.findIndex(
    (etapa) => etapa.id === workflow.etapaAtualId
  );
  const currentStep = workflow.etapas[currentIndex];
  const isBlocked = currentStep?.status === "bloqueada";

  return (
    <div className="rounded-3xl border border-zinc-100 bg-white p-4 shadow-sm">
      <p className="text-sm font-medium text-zinc-900">Transição manual</p>
      <p className="mt-1 text-sm text-zinc-500">
        As ações alteram apenas o mock local e registram histórico da transição.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={currentIndex <= 0}
          onClick={onPrevious}
        >
          Etapa anterior
        </Button>
        <Button
          type="button"
          disabled={currentIndex < 0 || currentIndex >= workflow.etapas.length - 1}
          onClick={onNext}
        >
          Próxima etapa
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={currentIndex < 0 || isBlocked}
          onClick={onBlock}
        >
          Bloquear etapa
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={!isBlocked}
          onClick={onUnblock}
        >
          Desbloquear etapa
        </Button>
      </div>
    </div>
  );
}
