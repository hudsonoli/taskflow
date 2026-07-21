"use client";

import { useState } from "react";
import { Building2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
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

const agencies = [
  { name: "Agência Principal", document: "00.000.000/0001-00", plan: "Operacional", status: "Ativa" },
  { name: "Agência Exemplo", document: "11.111.111/0001-11", plan: "Gestão", status: "Ativa" },
  { name: "Agência Inativa", document: "22.222.222/0001-22", plan: "Básico", status: "Inativa" },
];

export default function AgenciasPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const activeAgencies = agencies.filter((agency) => agency.status === "Ativa").length;
  const filteredAgencies = agencies.filter((agency) =>
    [agency.name, agency.document, agency.plan, agency.status]
      .join(" ")
      .toLowerCase()
      .includes(searchQuery.trim().toLowerCase())
  );

  return (
    <CadastroPage
      title="Agências"
      description="Cadastro e gestão das agências da plataforma."
      toolbar={
        <CadastroToolbar
          searchValue={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Pesquisar agências..."
          actions={<Button>Nova Agência</Button>}
        />
      }
      indicators={
        <CadastroIndicators
          items={[
            { label: "Total", value: agencies.length },
            { label: "Ativas", value: activeAgencies },
            { label: "Inativas", value: agencies.length - activeAgencies },
          ]}
        />
      }
    >
      <CadastroTable minWidth="720px">
        <thead className={cadastroTableHeaderClassName}>
          <tr>
            <th className={cadastroTableHeaderCellClassName}>Agência</th>
            <th className={cadastroTableHeaderCellClassName}>CNPJ</th>
            <th className={cadastroTableHeaderCellClassName}>Plano</th>
            <th className={cadastroTableHeaderCellClassName}>Status</th>
          </tr>
        </thead>

        <tbody>
          {filteredAgencies.map((agency) => (
            <tr key={agency.document} className={cadastroTableRowClassName}>
              <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                <div className="flex items-center gap-2.5">
                  <CadastroAvatar label={agency.name} icon={Building2} />
                  <span>{agency.name}</span>
                </div>
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>{agency.document}</td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>{agency.plan}</td>
              <td className={cadastroTableCellClassName}>
                <CadastroStatusBadge>{agency.status}</CadastroStatusBadge>
              </td>
            </tr>
          ))}
        </tbody>
      </CadastroTable>
    </CadastroPage>
  );
}
