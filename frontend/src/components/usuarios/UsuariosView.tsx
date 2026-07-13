"use client";

import { useState } from "react";
import { User } from "lucide-react";
import {
  CadastroAvatar,
  CadastroIndicators,
  CadastroPage,
  CadastroStatusBadge,
  CadastroTable,
  CadastroToolbar,
  cadastroTableCellClassName,
  cadastroTableHeaderCellClassName,
  cadastroTableHeaderClassName,
  cadastroTableRowClassName,
} from "@/components/cadastros";
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
  const [searchQuery, setSearchQuery] = useState("");

  const activeUsers = users.filter((user) => user.status === "Ativo").length;

  const managers = users.filter(
    (user) =>
      user.profile === "SuperAdmin" ||
      user.profile === "Admin" ||
      user.profile === "Diretoria" ||
      user.profile === "Gestor"
  ).length;

  const filteredUsers = users.filter((user) =>
    [user.name, user.email, user.department, user.profile, user.agency, user.status]
      .join(" ")
      .toLowerCase()
      .includes(searchQuery.trim().toLowerCase())
  );

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
    <CadastroPage
      title="Usuários"
      description="Gestão de usuários, cargos e permissões."
      toolbar={
        <CadastroToolbar
          searchValue={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Pesquisar usuários..."
          actions={<NovoUsuarioButton onUpsert={handleUpsert} />}
        />
      }
      indicators={
        <CadastroIndicators
          items={[
            { label: "Total", value: users.length },
            { label: "Ativos", value: activeUsers },
            { label: "Gestão", value: managers },
          ]}
        />
      }
    >
      <CadastroTable minWidth="920px">
        <thead className={cadastroTableHeaderClassName}>
          <tr>
            <th className={cadastroTableHeaderCellClassName}>Nome</th>
            <th className={cadastroTableHeaderCellClassName}>E-mail</th>
            <th className={cadastroTableHeaderCellClassName}>Departamento</th>
            <th className={cadastroTableHeaderCellClassName}>Perfil</th>
            <th className={cadastroTableHeaderCellClassName}>Agência</th>
            <th className={cadastroTableHeaderCellClassName}>Status</th>
          </tr>
        </thead>

        <tbody>
          {filteredUsers.map((user) => (
            <tr key={user.id} className={cadastroTableRowClassName}>
              <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                <div className="flex items-center gap-2.5">
                  <CadastroAvatar label={user.name} icon={User} />
                  <span>{user.name}</span>
                </div>
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>{user.email}</td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>{user.department}</td>
              <td className={cadastroTableCellClassName}>
                <CadastroStatusBadge>{user.profile}</CadastroStatusBadge>
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>{user.agency}</td>
              <td className={cadastroTableCellClassName}>
                <CadastroStatusBadge>{user.status}</CadastroStatusBadge>
              </td>
            </tr>
          ))}
        </tbody>
      </CadastroTable>
    </CadastroPage>
  );
}
