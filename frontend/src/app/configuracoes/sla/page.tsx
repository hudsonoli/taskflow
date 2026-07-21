import {
  CadastroTable,
  cadastroTableCellClassName,
  cadastroTableHeaderCellClassName,
  cadastroTableHeaderClassName,
  cadastroTableRowClassName,
} from "@/components/cadastros/CadastroTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";

// Sem enum próprio nesta tela (dados hardcoded) — comparação explícita por
// valor, não heurística de texto (docs/design-system/14-component-hierarchy.md).
function statusTone(status: string): "green" | "neutral" {
  return status === "Ativo" ? "green" : "neutral";
}

const slaRules = [
  {
    name: "Urgente",
    responseTime: "1 hora",
    resolutionTime: "4 horas",
    priority: "Alta",
    status: "Ativo",
  },
  {
    name: "Alta",
    responseTime: "4 horas",
    resolutionTime: "1 dia",
    priority: "Alta",
    status: "Ativo",
  },
  {
    name: "Normal",
    responseTime: "8 horas",
    resolutionTime: "3 dias",
    priority: "Media",
    status: "Ativo",
  },
  {
    name: "Baixa",
    responseTime: "24 horas",
    resolutionTime: "5 dias",
    priority: "Baixa",
    status: "Ativo",
  },
];

export default function SlaPage() {
  const activeRules = slaRules.filter(
    (rule) => rule.status === "Ativo"
  ).length;

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="SLA"
          description="Regras de prazo, atendimento e resolução."
        />

        <Button>Novo SLA</Button>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total Regras</p>
          <p className="mt-3 text-3xl font-bold">{slaRules.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Ativas</p>
          <p className="mt-3 text-3xl font-bold">{activeRules}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Prioridades</p>
          <p className="mt-3 text-3xl font-bold">4</p>
        </Card>
      </div>

      <div className="mt-8">
        <CadastroTable>
          <thead className={cadastroTableHeaderClassName}>
            <tr>
              <th className={cadastroTableHeaderCellClassName}>SLA</th>
              <th className={cadastroTableHeaderCellClassName}>Resposta</th>
              <th className={cadastroTableHeaderCellClassName}>Resolução</th>
              <th className={cadastroTableHeaderCellClassName}>Prioridade</th>
              <th className={cadastroTableHeaderCellClassName}>Status</th>
            </tr>
          </thead>

          <tbody>
            {slaRules.map((rule) => (
              <tr key={rule.name} className={cadastroTableRowClassName}>
                <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                  {rule.name}
                </td>

                <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                  {rule.responseTime}
                </td>

                <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                  {rule.resolutionTime}
                </td>

                <td className={cadastroTableCellClassName}>
                  <Badge>{rule.priority}</Badge>
                </td>

                <td className={cadastroTableCellClassName}>
                  <StatusPill tone={statusTone(rule.status)}>{rule.status}</StatusPill>
                </td>
              </tr>
            ))}
          </tbody>
        </CadastroTable>
      </div>
    </div>
  );
}
