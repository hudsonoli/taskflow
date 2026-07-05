"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { departamentos } from "@/lib/usuario-mock";
import type { UsuarioDraft } from "@/types/usuario";
import { NovoUsuarioButton } from "./NovoUsuarioButton";

type UsuarioRow = {
  id: string;
  name: string;
  email: string;
  department: string;
  profile: string;
  agency: string;
  status: string;
};

const initialUsers: UsuarioRow[] = [
  {
    id: "user-1",
    name: "Hudson Cunha",
    email: "hudson@technetgo.com.br",
    department: "TI",
    profile: "SuperAdmin",
    agency: "Agência Principal",
    status: "Ativo",
  },
  {
    id: "user-2",
    name: "Ana Costa",
    email: "ana@empresa.com.br",
    department: "Direção",
    profile: "Diretoria",
    agency: "Agência Principal",
    status: "Ativo",
  },
  {
    id: "user-3",
    name: "Carlos Lima",
    email: "carlos@agenciaexemplo.com.br",
    department: "Administrativo",
    profile: "Admin",
    agency: "Agência Exemplo",
    status: "Ativo",
  },
  {
    id: "user-4",
    name: "João Silva",
    email: "joao@empresa.com.br",
    department: "Atendimento",
    profile: "Gestor",
    agency: "Agência Principal",
    status: "Ativo",
  },
  {
    id: "user-5",
    name: "Maria Souza",
    email: "maria@empresa.com.br",
    department: "Criação",
    profile: "Operador",
    agency: "Agência Principal",
    status: "Ativo",
  },
  {
    id: "user-6",
    name: "Pedro Santos",
    email: "pedro@empresa.com.br",
    department: "Mídia",
    profile: "Operador",
    agency: "Agência Principal",
    status: "Inativo",
  },
  {
    id: "user-7",
    name: "Cliente Exemplo",
    email: "contato@clienteexemplo.com.br",
    department: "Externo",
    profile: "Cliente",
    agency: "Agência Exemplo",
    status: "Ativo",
  },
];

function resolveDepartamentoNome(departamentoId: string): string {
  return (
    departamentos.find((departamento) => departamento.id === departamentoId)
      ?.nome ?? departamentoId
  );
}

function draftToRow(draft: UsuarioDraft): UsuarioRow {
  return {
    id: draft.id,
    name: draft.nome,
    email: draft.email,
    department: resolveDepartamentoNome(draft.departamentoId),
    profile: draft.perfil,
    agency: "Agência Principal",
    status: draft.emAtividade ? "Ativo" : "Inativo",
  };
}

export function UsuariosView() {
  const [users, setUsers] = useState<UsuarioRow[]>(initialUsers);

  const activeUsers = users.filter((user) => user.status === "Ativo").length;

  const managers = users.filter(
    (user) =>
      user.profile === "SuperAdmin" ||
      user.profile === "Admin" ||
      user.profile === "Diretoria" ||
      user.profile === "Gestor"
  ).length;

  function handleUpsert(draft: UsuarioDraft) {
    setUsers((current) => {
      const row = draftToRow(draft);
      const exists = current.some((user) => user.id === draft.id);

      if (exists) {
        return current.map((user) => (user.id === draft.id ? row : user));
      }

      return [row, ...current];
    });
  }

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Usuários"
          description="Gestão de usuários, cargos e permissões."
        />

        <NovoUsuarioButton onUpsert={handleUpsert} />
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
              <th className="px-6 py-4 font-medium">Agência</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {users.map((user) => (
              <tr
                key={user.id}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {user.name}
                </td>

                <td className="px-6 py-4 text-zinc-500">{user.email}</td>

                <td className="px-6 py-4 text-zinc-500">
                  {user.department}
                </td>

                <td className="px-6 py-4">
                  <Badge>{user.profile}</Badge>
                </td>

                <td className="px-6 py-4 text-zinc-500">{user.agency}</td>

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
