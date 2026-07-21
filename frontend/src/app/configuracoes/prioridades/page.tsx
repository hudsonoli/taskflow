import {
  CadastroTable,
  cadastroTableCellClassName,
  cadastroTableHeaderCellClassName,
  cadastroTableHeaderClassName,
  cadastroTableRowClassName,
} from "@/components/cadastros/CadastroTable";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";

// Sem enum próprio nesta tela (dados hardcoded) — comparação explícita por
// valor, não heurística de texto (docs/design-system/14-component-hierarchy.md).
function statusTone(status: string): "green" | "neutral" {
  return status === "Ativa" ? "green" : "neutral";
}

const priorities = [
  {
    name: "Urgente",
    color: "Vermelho",
    sla: "4 horas",
    usage: "Demandas críticas",
    status: "Ativa",
  },
  {
    name: "Alta",
    color: "Laranja",
    sla: "1 dia",
    usage: "Demandas importantes",
    status: "Ativa",
  },
  {
    name: "Média",
    color: "Amarelo",
    sla: "3 dias",
    usage: "Demandas normais",
    status: "Ativa",
  },
  {
    name: "Baixa",
    color: "Cinza",
    sla: "5 dias",
    usage: "Demandas sem urgência",
    status: "Ativa",
  },
];

export default function PrioridadesPage() {
  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Prioridades"
          description="Níveis de prioridade utilizados nas tarefas e SLAs."
        />

        <Button>Nova Prioridade</Button>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total Prioridades</p>
          <p className="mt-3 text-3xl font-bold">{priorities.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Ativas</p>
          <p className="mt-3 text-3xl font-bold">{priorities.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Vinculadas ao SLA</p>
          <p className="mt-3 text-3xl font-bold">4</p>
        </Card>
      </div>

      <div className="mt-8">
        <CadastroTable>
          <thead className={cadastroTableHeaderClassName}>
            <tr>
              <th className={cadastroTableHeaderCellClassName}>Prioridade</th>
              <th className={cadastroTableHeaderCellClassName}>Cor</th>
              <th className={cadastroTableHeaderCellClassName}>SLA Padrão</th>
              <th className={cadastroTableHeaderCellClassName}>Uso</th>
              <th className={cadastroTableHeaderCellClassName}>Status</th>
            </tr>
          </thead>

          <tbody>
            {priorities.map((priority) => (
              <tr key={priority.name} className={cadastroTableRowClassName}>
                <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                  {priority.name}
                </td>

                <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                  {priority.color}
                </td>

                <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                  {priority.sla}
                </td>

                <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                  {priority.usage}
                </td>

                <td className={cadastroTableCellClassName}>
                  <StatusPill tone={statusTone(priority.status)}>{priority.status}</StatusPill>
                </td>
              </tr>
            ))}
          </tbody>
        </CadastroTable>
      </div>
    </div>
  );
}
