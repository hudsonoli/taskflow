"use client";

import { Button } from "@/components/ui/Button";
import {
  CadastroIndicators,
  CadastroPage,
  CadastroStatusBadge,
  CadastroToolbar,
} from "@/components/cadastros";

const workflows = [
  {
    name: "Marketing Padrão",
    agency: "Agência Principal",
    status: "Ativo",
    stages: [
      "Solicitação",
      "Atendimento",
      "Criação",
      "Revisão",
      "Aprovação Cliente",
      "Publicação",
      "Concluído",
    ],
  },
  {
    name: "Produção Gráfica",
    agency: "Agência Principal",
    status: "Ativo",
    stages: ["Solicitação", "Orçamento", "Produção", "Entrega", "Concluído"],
  },
  {
    name: "Clínica Clare",
    agency: "Agência Exemplo",
    status: "Rascunho",
    stages: ["Recepção", "Técnico", "Médico", "Laudo", "Finalizado"],
  },
];

export default function WorkflowsPage() {
  const activeWorkflows = workflows.filter(
    (workflow) => workflow.status === "Ativo"
  ).length;

  const totalStages = workflows.reduce(
    (total, workflow) => total + workflow.stages.length,
    0
  );

  return (
    <CadastroPage
      title="Workflows"
      description="Fluxos operacionais, etapas do Kanban e regras de atendimento."
      toolbar={
        <CadastroToolbar
          searchPlaceholder="Pesquisar workflows..."
          actions={<Button>Novo Workflow</Button>}
        />
      }
      indicators={
        <CadastroIndicators
          items={[
            { label: "Total", value: workflows.length },
            { label: "Ativos", value: activeWorkflows },
            { label: "Etapas", value: totalStages },
          ]}
        />
      }
    >
      <div className="grid gap-3">
        {workflows.map((workflow) => (
          <div
            key={workflow.name}
            className="rounded-2xl border border-zinc-100 bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="truncate text-sm font-semibold text-zinc-900">
                  {workflow.name}
                </h2>
                <p className="mt-0.5 text-xs text-zinc-500">{workflow.agency}</p>
              </div>

              <CadastroStatusBadge>{workflow.status}</CadastroStatusBadge>
            </div>

            <div className="mt-3 overflow-x-auto">
              <div className="flex min-w-max items-center gap-2">
                {workflow.stages.map((stage, index) => (
                  <div key={stage} className="flex items-center gap-2">
                    <div className="rounded-xl bg-[#faf8f4] px-3 py-2 text-xs font-medium text-zinc-700">
                      {stage}
                    </div>

                    {index < workflow.stages.length - 1 && (
                      <span className="text-xs text-zinc-300">→</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </CadastroPage>
  );
}
