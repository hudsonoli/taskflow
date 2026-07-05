"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import type { ClienteDraft } from "@/types/cliente";
import { NovoClienteButton } from "./NovoClienteButton";

type ClienteRow = {
  name: string;
  document: string;
  agency: string;
  owner: string;
  projects: number;
  status: string;
};

const initialClients: ClienteRow[] = [
  {
    name: "Cliente Exemplo",
    document: "12.345.678/0001-90",
    agency: "Agência Principal",
    owner: "João Silva",
    projects: 3,
    status: "Ativo",
  },
  {
    name: "Clínica Clare",
    document: "98.765.432/0001-10",
    agency: "Agência Exemplo",
    owner: "Maria Souza",
    projects: 2,
    status: "Ativo",
  },
  {
    name: "Loja Boxx",
    document: "11.222.333/0001-44",
    agency: "Agência Principal",
    owner: "Pedro Santos",
    projects: 1,
    status: "Ativo",
  },
  {
    name: "Cliente Inativo",
    document: "55.666.777/0001-88",
    agency: "Agência Exemplo",
    owner: "Ana Costa",
    projects: 0,
    status: "Inativo",
  },
];

function draftToRow(draft: ClienteDraft): ClienteRow {
  return {
    name: draft.nomeFantasia || draft.razaoSocial || "Novo Cliente",
    document: draft.documento,
    agency: "Agência Principal",
    owner: draft.atendimento || "-",
    projects: 0,
    status: draft.situacao,
  };
}

export function ClientesView() {
  const [clients, setClients] = useState<ClienteRow[]>(initialClients);

  const activeClients = clients.filter(
    (client) => client.status === "Ativo"
  ).length;

  const totalProjects = clients.reduce(
    (total, client) => total + client.projects,
    0
  );

  function handleCreate(draft: ClienteDraft) {
    setClients((current) => [draftToRow(draft), ...current]);
  }

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Clientes"
          description="Cadastro e gestão de clientes."
        />

        <NovoClienteButton onCreate={handleCreate} />
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total Clientes</p>
          <p className="mt-3 text-3xl font-bold">{clients.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Ativos</p>
          <p className="mt-3 text-3xl font-bold">{activeClients}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Total de Projetos</p>
          <p className="mt-3 text-3xl font-bold">{totalProjects}</p>
        </Card>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Cliente</th>
              <th className="px-6 py-4 font-medium">CNPJ</th>
              <th className="px-6 py-4 font-medium">Agência</th>
              <th className="px-6 py-4 font-medium">Responsável</th>
              <th className="px-6 py-4 font-medium">Projetos</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {clients.map((client, index) => (
              <tr
                key={`${client.document}-${index}`}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {client.name}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {client.document}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {client.agency}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {client.owner}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {client.projects}
                </td>

                <td className="px-6 py-4">
                  <Badge>{client.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
