import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

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

      <div className="mt-8 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Prioridade</th>
              <th className="px-6 py-4 font-medium">Cor</th>
              <th className="px-6 py-4 font-medium">SLA Padrão</th>
              <th className="px-6 py-4 font-medium">Uso</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {priorities.map((priority) => (
              <tr
                key={priority.name}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {priority.name}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {priority.color}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {priority.sla}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {priority.usage}
                </td>

                <td className="px-6 py-4">
                  <Badge>{priority.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
