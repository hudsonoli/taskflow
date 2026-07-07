import { Card } from "@/components/ui/Card";

type AgendaStatsProps = {
  total: number;
  clientes: number;
  fornecedores: number;
  usuarios: number;
};

const stats = [
  { label: "Total de contatos", key: "total" },
  { label: "Clientes", key: "clientes" },
  { label: "Fornecedores", key: "fornecedores" },
  { label: "Usuários", key: "usuarios" },
] as const;

export function AgendaStats({
  total,
  clientes,
  fornecedores,
  usuarios,
}: AgendaStatsProps) {
  const values = { total, clientes, fornecedores, usuarios };

  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.key}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm text-zinc-500">{stat.label}</p>
              <p className="mt-3 text-3xl font-semibold text-zinc-900">
                {values[stat.key]}
              </p>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
