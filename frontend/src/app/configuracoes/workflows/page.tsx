import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

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
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Workflows"
          description="Fluxos operacionais, etapas do Kanban e regras de atendimento."
        />

        <Button>Novo Workflow</Button>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total Workflows</p>
          <p className="mt-3 text-3xl font-bold">{workflows.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Ativos</p>
          <p className="mt-3 text-3xl font-bold">{activeWorkflows}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Etapas Configuradas</p>
          <p className="mt-3 text-3xl font-bold">{totalStages}</p>
        </Card>
      </div>

      <div className="mt-8 grid gap-6">
        {workflows.map((workflow) => (
          <div
            key={workflow.name}
            className="rounded-3xl bg-white p-6 shadow-sm"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">
                  {workflow.name}
                </h2>

                <p className="mt-1 text-sm text-zinc-500">
                  {workflow.agency}
                </p>
              </div>

              <Badge>{workflow.status}</Badge>
            </div>

            <div className="mt-6 overflow-x-auto">
              <div className="flex min-w-max items-center gap-3">
                {workflow.stages.map((stage, index) => (
                  <div key={stage} className="flex items-center gap-3">
                    <div className="rounded-2xl bg-[#faf8f4] px-4 py-3 text-sm font-medium text-zinc-700">
                      {stage}
                    </div>

                    {index < workflow.stages.length - 1 && (
                      <span className="text-zinc-300">→</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
