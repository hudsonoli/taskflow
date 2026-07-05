import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

const teams = [
  {
    name: "Atendimento",
    leader: "João Silva",
    members: 5,
    type: "Operacional",
    status: "Ativa",
  },
  {
    name: "Criação",
    leader: "Maria Souza",
    members: 8,
    type: "Operacional",
    status: "Ativa",
  },
  {
    name: "Mídia",
    leader: "Pedro Santos",
    members: 3,
    type: "Operacional",
    status: "Ativa",
  },
  {
    name: "Produção",
    leader: "Ana Costa",
    members: 6,
    type: "Operacional",
    status: "Ativa",
  },
  {
    name: "Financeiro",
    leader: "Carlos Lima",
    members: 2,
    type: "Administrativo",
    status: "Ativa",
  },
  {
    name: "TI",
    leader: "Hudson Cunha",
    members: 1,
    type: "Administrativo",
    status: "Ativa",
  },
];

export default function EquipesPage() {
  const totalMembers = teams.reduce((total, team) => total + team.members, 0);
  const operationalTeams = teams.filter(
    (team) => team.type === "Operacional"
  ).length;

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Equipes"
          description="Organização de departamentos, líderes e colaboradores."
        />

        <Button>Nova Equipe</Button>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total Equipes</p>
          <p className="mt-3 text-3xl font-bold">{teams.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Colaboradores</p>
          <p className="mt-3 text-3xl font-bold">{totalMembers}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Operacionais</p>
          <p className="mt-3 text-3xl font-bold">{operationalTeams}</p>
        </Card>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Equipe</th>
              <th className="px-6 py-4 font-medium">Líder</th>
              <th className="px-6 py-4 font-medium">Membros</th>
              <th className="px-6 py-4 font-medium">Tipo</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {teams.map((team) => (
              <tr
                key={team.name}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {team.name}
                </td>
                <td className="px-6 py-4 text-zinc-500">{team.leader}</td>
                <td className="px-6 py-4 text-zinc-500">{team.members}</td>
                <td className="px-6 py-4">
                  <Badge>{team.type}</Badge>
                </td>
                <td className="px-6 py-4">
                  <Badge>{team.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
