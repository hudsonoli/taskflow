import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

const taskTypes = [
  {
    name: "Criação",
    department: "Criação",
    defaultSla: "3 dias",
    workflow: "Marketing Padrão",
    status: "Ativo",
  },
  {
    name: "Aprovação",
    department: "Atendimento",
    defaultSla: "1 dia",
    workflow: "Marketing Padrão",
    status: "Ativo",
  },
  {
    name: "Publicação",
    department: "Mídia",
    defaultSla: "1 dia",
    workflow: "Marketing Padrão",
    status: "Ativo",
  },
  {
    name: "Produção Gráfica",
    department: "Produção",
    defaultSla: "5 dias",
    workflow: "Produção Gráfica",
    status: "Ativo",
  },
  {
    name: "Laudo Médico",
    department: "Médico",
    defaultSla: "2 dias",
    workflow: "Clínica Clare",
    status: "Ativo",
  },
];

export default function TiposTarefaPage() {
  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Tipos de Tarefa"
          description="Categorias operacionais utilizadas pelos workflows."
        />

        <Button>Novo Tipo</Button>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Tipos Cadastrados</p>
          <p className="mt-3 text-3xl font-bold">{taskTypes.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Workflows</p>
          <p className="mt-3 text-3xl font-bold">3</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Departamentos</p>
          <p className="mt-3 text-3xl font-bold">5</p>
        </Card>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Tipo</th>
              <th className="px-6 py-4 font-medium">Departamento</th>
              <th className="px-6 py-4 font-medium">SLA</th>
              <th className="px-6 py-4 font-medium">Workflow</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {taskTypes.map((type) => (
              <tr
                key={type.name}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {type.name}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {type.department}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {type.defaultSla}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {type.workflow}
                </td>

                <td className="px-6 py-4">
                  <Badge>{type.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
