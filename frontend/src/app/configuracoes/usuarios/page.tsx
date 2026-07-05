import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

const users = [
  {
    name: "Hudson Cunha",
    email: "hudson@technetgo.com.br",
    department: "TI",
    profile: "SuperAdmin",
    status: "Ativo",
  },
  {
    name: "João Silva",
    email: "joao@empresa.com.br",
    department: "Atendimento",
    profile: "Gestor",
    status: "Ativo",
  },
  {
    name: "Maria Souza",
    email: "maria@empresa.com.br",
    department: "Criação",
    profile: "Operador",
    status: "Ativo",
  },
  {
    name: "Pedro Santos",
    email: "pedro@empresa.com.br",
    department: "Mídia",
    profile: "Operador",
    status: "Inativo",
  },
];

export default function UsuariosPage() {
  const activeUsers = users.filter(
    (user) => user.status === "Ativo"
  ).length;

  const managers = users.filter(
    (user) =>
      user.profile === "SuperAdmin" ||
      user.profile === "Admin" ||
      user.profile === "Diretoria" ||
      user.profile === "Gestor"
  ).length;

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Usuários"
          description="Gestão de usuários, cargos e permissões."
        />

        <Button>Novo Usuário</Button>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total</p>
          <p className="mt-3 text-3xl font-bold">{users.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Ativos</p>
          <p className="mt-3 text-3xl font-bold">{activeUsers}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Gestão</p>
          <p className="mt-3 text-3xl font-bold">{managers}</p>
        </Card>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Nome</th>
              <th className="px-6 py-4 font-medium">E-mail</th>
              <th className="px-6 py-4 font-medium">Departamento</th>
              <th className="px-6 py-4 font-medium">Perfil</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {users.map((user) => (
              <tr
                key={user.email}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {user.name}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {user.email}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {user.department}
                </td>

                <td className="px-6 py-4">
                  <Badge>{user.profile}</Badge>
                </td>

                <td className="px-6 py-4">
                  <Badge>{user.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
