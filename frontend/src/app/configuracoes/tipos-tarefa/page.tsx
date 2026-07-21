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
  return status === "Ativo" ? "green" : "neutral";
}

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

      <div className="mt-8">
        <CadastroTable>
          <thead className={cadastroTableHeaderClassName}>
            <tr>
              <th className={cadastroTableHeaderCellClassName}>Tipo</th>
              <th className={cadastroTableHeaderCellClassName}>Departamento</th>
              <th className={cadastroTableHeaderCellClassName}>SLA</th>
              <th className={cadastroTableHeaderCellClassName}>Workflow</th>
              <th className={cadastroTableHeaderCellClassName}>Status</th>
            </tr>
          </thead>

          <tbody>
            {taskTypes.map((type) => (
              <tr key={type.name} className={cadastroTableRowClassName}>
                <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                  {type.name}
                </td>

                <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                  {type.department}
                </td>

                <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                  {type.defaultSla}
                </td>

                <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                  {type.workflow}
                </td>

                <td className={cadastroTableCellClassName}>
                  <StatusPill tone={statusTone(type.status)}>{type.status}</StatusPill>
                </td>
              </tr>
            ))}
          </tbody>
        </CadastroTable>
      </div>
    </div>
  );
}
