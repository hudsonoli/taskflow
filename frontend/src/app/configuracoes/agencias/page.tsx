import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

const agencies = [
  {
    name: "Agência Principal",
    document: "00.000.000/0001-00",
    plan: "Operacional",
    status: "Ativa",
  },
  {
    name: "Agência Exemplo",
    document: "11.111.111/0001-11",
    plan: "Gestão",
    status: "Ativa",
  },
  {
    name: "Agência Inativa",
    document: "22.222.222/0001-22",
    plan: "Básico",
    status: "Inativa",
  },
];

export default function AgenciasPage() {
  const activeAgencies = agencies.filter(
    (agency) => agency.status === "Ativa"
  ).length;

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Agências"
          description="Cadastro e gestão das agências da plataforma."
        />

        <Button>Nova Agência</Button>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total</p>
          <p className="mt-3 text-3xl font-bold">{agencies.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Ativas</p>
          <p className="mt-3 text-3xl font-bold">{activeAgencies}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Inativas</p>
          <p className="mt-3 text-3xl font-bold">
            {agencies.length - activeAgencies}
          </p>
        </Card>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Agência</th>
              <th className="px-6 py-4 font-medium">CNPJ</th>
              <th className="px-6 py-4 font-medium">Plano</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {agencies.map((agency) => (
              <tr
                key={agency.document}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {agency.name}
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {agency.document}
                </td>
                <td className="px-6 py-4 text-zinc-500">{agency.plan}</td>
                <td className="px-6 py-4">
                  <Badge>{agency.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
