"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";
import {
  createWorkflowInstanceFromTemplate,
  createWorkflowTransitionHistory,
  generateId,
  workflowTemplatesMock,
} from "@/lib/workflows-mock";
import type {
  WorkflowEtapa,
  WorkflowInstancia,
  WorkflowTransicaoHistorico,
} from "@/types/workflow";
import { WorkflowHistory } from "./WorkflowHistory";
import { WorkflowStepCard } from "./WorkflowStepCard";
import { WorkflowTemplateSelector } from "./WorkflowTemplateSelector";
import { WorkflowTransitionControls } from "./WorkflowTransitionControls";

type WorkflowEditorProps = {
  demandaId: string;
  workflow: WorkflowInstancia;
  history: WorkflowTransicaoHistorico[];
  onWorkflowChange: (
    workflow: WorkflowInstancia,
    history: WorkflowTransicaoHistorico[]
  ) => void;
};

function reorderSteps(etapas: WorkflowEtapa[]) {
  return etapas.map((etapa, index) => ({ ...etapa, ordem: index + 1 }));
}

function createEmptyStep(ordem: number): WorkflowEtapa {
  return {
    id: generateId("workflow-etapa-instancia"),
    nome: "Nova etapa",
    ordem,
    usuarioResponsavelIds: [],
    departamentoResponsavelIds: [],
    prazoHoras: 8,
    status: "pendente",
  };
}

function ensureSingleCurrent(
  etapas: WorkflowEtapa[],
  etapaAtualId: string
): WorkflowEtapa[] {
  return etapas.map((etapa) => {
    if (etapa.id === etapaAtualId) {
      return { ...etapa, status: etapa.status === "bloqueada" ? "bloqueada" : "atual" };
    }

    return etapa.status === "atual" ? { ...etapa, status: "pendente" } : etapa;
  });
}

export function WorkflowEditor({
  demandaId,
  workflow,
  history,
  onWorkflowChange,
}: WorkflowEditorProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState(
    workflow.templateId ?? workflowTemplatesMock[0].id
  );

  function updateWorkflow(patch: Partial<WorkflowInstancia>) {
    onWorkflowChange(
      {
        ...workflow,
        ...patch,
        updatedAt: new Date().toISOString(),
      },
      history
    );
  }

  function updateStep(nextStep: WorkflowEtapa) {
    const etapas = workflow.etapas.map((etapa) =>
      etapa.id === nextStep.id ? nextStep : etapa
    );

    updateWorkflow({
      etapas: ensureSingleCurrent(etapas, workflow.etapaAtualId),
    });
  }

  function addStep() {
    updateWorkflow({
      etapas: [...workflow.etapas, createEmptyStep(workflow.etapas.length + 1)],
    });
  }

  function removeStep(stepId: string) {
    const etapas = reorderSteps(
      workflow.etapas.filter((etapa) => etapa.id !== stepId)
    );
    const nextCurrentId =
      workflow.etapaAtualId === stepId
        ? etapas[0]?.id ?? ""
        : workflow.etapaAtualId;

    updateWorkflow({
      etapas: ensureSingleCurrent(etapas, nextCurrentId),
      etapaAtualId: nextCurrentId,
    });
  }

  function moveStep(stepId: string, direction: "up" | "down") {
    const currentIndex = workflow.etapas.findIndex((etapa) => etapa.id === stepId);
    const targetIndex = direction === "up" ? currentIndex - 1 : currentIndex + 1;

    if (currentIndex < 0 || targetIndex < 0 || targetIndex >= workflow.etapas.length) {
      return;
    }

    const nextEtapas = [...workflow.etapas];
    const [item] = nextEtapas.splice(currentIndex, 1);
    nextEtapas.splice(targetIndex, 0, item);

    updateWorkflow({ etapas: reorderSteps(nextEtapas) });
  }

  function applyTemplate() {
    const template = workflowTemplatesMock.find(
      (item) => item.id === selectedTemplateId
    );

    if (!template) return;

    if (workflow.etapas.length > 0) {
      const confirmed = window.confirm(
        "Substituir o workflow atual por este template? As edições locais serão perdidas."
      );

      if (!confirmed) return;
    }

    onWorkflowChange(
      createWorkflowInstanceFromTemplate(template, demandaId),
      [
        createWorkflowTransitionHistory(
          demandaId,
          "",
          template.etapas[0]?.id ?? "",
          `Template aplicado: ${template.nome}`
        ),
        ...history,
      ]
    );
  }

  function transitionTo(nextCurrentId: string, observacao: string) {
    const currentStepId = workflow.etapaAtualId;
    const etapas: WorkflowEtapa[] = workflow.etapas.map((etapa) => {
      if (etapa.id === currentStepId && nextCurrentId !== currentStepId) {
        return {
          ...etapa,
          status: observacao === "Voltou etapa" ? "pendente" : "concluida",
        };
      }

      if (etapa.id === nextCurrentId) {
        return { ...etapa, status: "atual" };
      }

      return etapa.status === "atual" ? { ...etapa, status: "pendente" } : etapa;
    });

    onWorkflowChange(
      {
        ...workflow,
        etapas,
        etapaAtualId: nextCurrentId,
        updatedAt: new Date().toISOString(),
      },
      [
        createWorkflowTransitionHistory(
          demandaId,
          currentStepId,
          nextCurrentId,
          observacao
        ),
        ...history,
      ]
    );
  }

  function goNext() {
    const currentIndex = workflow.etapas.findIndex(
      (etapa) => etapa.id === workflow.etapaAtualId
    );
    const nextStep = workflow.etapas[currentIndex + 1];
    if (!nextStep) return;

    transitionTo(nextStep.id, "Avançou etapa");
  }

  function goPrevious() {
    const currentIndex = workflow.etapas.findIndex(
      (etapa) => etapa.id === workflow.etapaAtualId
    );
    const previousStep = workflow.etapas[currentIndex - 1];
    if (!previousStep) return;

    transitionTo(previousStep.id, "Voltou etapa");
  }

  function blockCurrent() {
    const currentStepId = workflow.etapaAtualId;
    const etapas = workflow.etapas.map((etapa) =>
      etapa.id === currentStepId ? { ...etapa, status: "bloqueada" as const } : etapa
    );

    onWorkflowChange(
      { ...workflow, etapas, updatedAt: new Date().toISOString() },
      [
        createWorkflowTransitionHistory(
          demandaId,
          currentStepId,
          currentStepId,
          "Bloqueou etapa"
        ),
        ...history,
      ]
    );
  }

  function unblockCurrent() {
    const currentStepId = workflow.etapaAtualId;
    const etapas = workflow.etapas.map((etapa) =>
      etapa.id === currentStepId ? { ...etapa, status: "atual" as const } : etapa
    );

    onWorkflowChange(
      { ...workflow, etapas, updatedAt: new Date().toISOString() },
      [
        createWorkflowTransitionHistory(
          demandaId,
          currentStepId,
          currentStepId,
          "Desbloqueou etapa"
        ),
        ...history,
      ]
    );
  }

  return (
    <div className="space-y-6">
      <WorkspaceSection
        title="Workflow"
        description="Editor mock por demanda. Templates são copiados para uma instância própria da demanda."
      >
        <WorkflowTemplateSelector
          selectedTemplateId={selectedTemplateId}
          onTemplateChange={setSelectedTemplateId}
          onApplyTemplate={applyTemplate}
        />

        <div className="mt-6">
          <WorkflowTransitionControls
            workflow={workflow}
            onNext={goNext}
            onPrevious={goPrevious}
            onBlock={blockCurrent}
            onUnblock={unblockCurrent}
          />
        </div>

        <div className="mt-6 flex justify-end">
          <Button type="button" onClick={addStep}>
            Adicionar etapa
          </Button>
        </div>

        <div className="mt-4 space-y-4">
          {workflow.etapas.map((etapa, index) => (
            <WorkflowStepCard
              key={etapa.id}
              etapa={etapa}
              isCurrent={workflow.etapaAtualId === etapa.id}
              canMoveUp={index > 0}
              canMoveDown={index < workflow.etapas.length - 1}
              onChange={updateStep}
              onRemove={() => removeStep(etapa.id)}
              onMoveUp={() => moveStep(etapa.id, "up")}
              onMoveDown={() => moveStep(etapa.id, "down")}
            />
          ))}
        </div>
      </WorkspaceSection>

      <WorkspaceSection
        title="Histórico de transições"
        description="Registro mock das mudanças manuais de etapa."
      >
        <WorkflowHistory history={history} workflow={workflow} />
      </WorkspaceSection>
    </div>
  );
}
