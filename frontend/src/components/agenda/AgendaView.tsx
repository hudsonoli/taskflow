"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { agendaMock } from "@/lib/agenda-mock";
import type { AgendaContato, AgendaTipo } from "@/types/agenda";
import { AgendaStats } from "./AgendaStats";
import { AgendaToolbar } from "./AgendaToolbar";
import { AgendaList } from "./AgendaList";

function normalize(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

function matchesContato(contato: AgendaContato, query: string) {
  const haystack = [
    contato.nome,
    contato.empresa,
    contato.cargo,
    contato.departamento,
    contato.email,
    contato.telefone,
    contato.celular,
  ]
    .join(" ")
    .toLowerCase();

  return normalize(haystack).includes(normalize(query));
}

export function AgendaView() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<AgendaTipo | "todos">("todos");

  const filteredContacts = useMemo(
    () =>
      agendaMock.filter((contato) => {
        const typeMatches =
          typeFilter === "todos" || contato.tipo === typeFilter;
        const queryMatches = query.trim() ? matchesContato(contato, query) : true;

        return typeMatches && queryMatches;
      }),
    [query, typeFilter]
  );

  const stats = useMemo(
    () => ({
      total: agendaMock.length,
      clientes: agendaMock.filter((contato) => contato.tipo === "clientes").length,
      fornecedores: agendaMock.filter((contato) => contato.tipo === "fornecedores").length,
      usuarios: agendaMock.filter((contato) => contato.tipo === "usuarios").length,
    }),
    []
  );

  return (
    <div className="p-8">
      <PageHeader
        title="Central de Contatos"
        description="Centralize e consulte rapidamente clientes, fornecedores, usuários e demais contatos da operação."
      />

      <p className="-mt-4 mb-6 text-sm text-zinc-500">
        Os contatos são atualizados automaticamente pelos módulos do sistema.
      </p>

      <div className="space-y-6">
        <AgendaStats
          total={stats.total}
          clientes={stats.clientes}
          fornecedores={stats.fornecedores}
          usuarios={stats.usuarios}
        />

        <AgendaToolbar
          query={query}
          onQueryChange={setQuery}
          typeFilter={typeFilter}
          onTypeFilterChange={setTypeFilter}
        />

        <AgendaList contacts={filteredContacts} />
      </div>
    </div>
  );
}
