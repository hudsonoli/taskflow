"use client";

import { useMemo, useState } from "react";
import { Building2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EMPRESA_PADRAO_ID, generateCodigoInterno, generateId } from "@/lib/clientes-mock";
import { resolverGrupoClienteNomes } from "@/lib/referencias";
import { useDiretorioGruposCliente } from "@/lib/diretorioGruposCliente";
import { useAppData } from "@/lib/AppDataContext";
import type { Cliente, ClienteFormDraft, ClienteHistoricoEvento } from "@/types/cliente";
import type { GrupoClienteDiretorioItem } from "@/lib/api-backend";
import { ClienteFormModal } from "./ClienteFormModal";
import { ClientesStats } from "./ClientesStats";
import { ClientesTable } from "./ClientesTable";
import { type ClienteStatusFiltro, ClientesToolbar } from "./ClientesToolbar";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesCliente(cliente: Cliente, query: string, grupos: GrupoClienteDiretorioItem[]) {
  const haystack = [
    cliente.nome,
    cliente.razaoSocial,
    cliente.documento,
    cliente.cidade,
    resolverGrupoClienteNomes(cliente.tagIds, grupos),
    cliente.codigoInterno,
  ].join(" ");
  return normalize(haystack).includes(normalize(query));
}

function createHistoricoCliente(acao: string): ClienteHistoricoEvento {
  return {
    id: generateId("hist-cliente"),
    usuarioId: "user-1",
    usuario: "Você",
    acao,
    dataHora: new Date().toLocaleString("pt-BR"),
    ip: "127.0.0.1",
    dispositivo: "Workspace local",
  };
}

function createClienteFromDraft(draft: ClienteFormDraft): Cliente {
  const now = new Date().toISOString();

  return {
    id: generateId("cliente"),
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: generateCodigoInterno(),
    ...draft,
    createdAt: now,
    updatedAt: now,
    historico: [createHistoricoCliente("Cliente criado")],
  };
}

function updateClienteFromDraft(cliente: Cliente, draft: ClienteFormDraft): Cliente {
  return {
    ...cliente,
    ...draft,
    updatedAt: new Date().toISOString(),
    historico: [createHistoricoCliente("Cliente atualizado"), ...cliente.historico],
  };
}

export function ClientesView() {
  const { clientes, setClientes, perfilAtual } = useAppData();
  const { grupos: gruposCliente } = useDiretorioGruposCliente();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<ClienteStatusFiltro>("todos");
  const [creatingCliente, setCreatingCliente] = useState(false);
  const [editingClienteId, setEditingClienteId] = useState<string | null>(null);

  const editingCliente = clientes.find((cliente) => cliente.id === editingClienteId);

  const filteredClientes = useMemo(
    () =>
      clientes.filter((cliente) => {
        const statusMatches = statusFilter === "todos" || cliente.status === statusFilter;
        const queryMatches = query.trim() ? matchesCliente(cliente, query, gruposCliente) : true;
        return statusMatches && queryMatches;
      }),
    [clientes, query, statusFilter, gruposCliente],
  );

  function handleSave(draft: ClienteFormDraft, clienteId?: string) {
    if (!clienteId) {
      const newCliente = createClienteFromDraft(draft);
      setClientes((current) => [newCliente, ...current]);
    } else {
      setClientes((current) => current.map((cliente) => (cliente.id === clienteId ? updateClienteFromDraft(cliente, draft) : cliente)));
    }
    setCreatingCliente(false);
    setEditingClienteId(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Building2 className="h-5 w-5" />}
        title="Clientes"
        description="Cadastro de clientes usados por projetos e demandas."
        action={<Badge tone="blue">Dados locais</Badge>}
      />

      <ClientesStats clientes={clientes} perfilAtual={perfilAtual} />

      <ClientesToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onNewCliente={() => setCreatingCliente(true)}
      />

      <ClientesTable clientes={filteredClientes} grupos={gruposCliente} onEdit={setEditingClienteId} />

      {creatingCliente && (
        <ClienteFormModal open grupos={gruposCliente} onClose={() => setCreatingCliente(false)} onSave={handleSave} />
      )}

      {editingCliente && (
        <ClienteFormModal
          key={editingCliente.id}
          open
          cliente={editingCliente}
          grupos={gruposCliente}
          onClose={() => setEditingClienteId(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
