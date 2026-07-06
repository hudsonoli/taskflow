"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { EntityFieldRow } from "@/components/ui/EntityFieldRow";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { EntitySummaryPanel } from "@/components/ui/EntitySummaryPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  clientesGrupoDisponiveis,
  initialGruposClientes,
} from "@/lib/grupo-cliente-mock";
import type { GrupoClienteDraft } from "@/types/grupo-cliente";
import { NovoGrupoClienteModal } from "./NovoGrupoClienteModal";

type GruposClientesViewProps = {
  canCreate?: boolean;
  canEdit?: boolean;
};

function resolveClienteResumo(clienteId: string): {
  nome: string;
  codigoInterno: string;
  sigla: string;
  status: string;
} | null {
  const cliente = clientesGrupoDisponiveis.find(
    (item) => item.clienteId === clienteId
  );

  if (!cliente) return null;

  return {
    nome: cliente.nomeFantasia || cliente.nomeRazaoSocial,
    codigoInterno: cliente.codigoInterno,
    sigla: cliente.sigla,
    status: cliente.status,
  };
}
export function GruposClientesView({
  canCreate = true,
  canEdit = true,
}: GruposClientesViewProps = {}) {
  const [gruposClientes, setGruposClientes] = useState<GrupoClienteDraft[]>(
    initialGruposClientes
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGrupoClienteId, setSelectedGrupoClienteId] = useState<
    string | null
  >(null);
  const [editingGrupoClienteId, setEditingGrupoClienteId] = useState<
    string | null
  >(null);
  const [creatingGrupoCliente, setCreatingGrupoCliente] = useState(false);

  const selectedGrupoCliente = gruposClientes.find(
    (grupoCliente) => grupoCliente.grupoClienteId === selectedGrupoClienteId
  );
  const editingGrupoCliente = gruposClientes.find(
    (grupoCliente) => grupoCliente.grupoClienteId === editingGrupoClienteId
  );

  const gruposFiltrados = gruposClientes
    .filter((grupoCliente) =>
      [
        grupoCliente.codigoInterno,
        grupoCliente.nome,
        grupoCliente.sigla,
      ]
        .join(" ")
        .toLowerCase()
        .includes(searchQuery.trim().toLowerCase())
    )
    .sort((a, b) => a.nome.localeCompare(b.nome));

  const gruposAtivos = gruposClientes.filter(
    (grupoCliente) => grupoCliente.status === "Ativo"
  ).length;
  const gruposInativos = gruposClientes.filter(
    (grupoCliente) => grupoCliente.status === "Inativo"
  ).length;
  const clientesVinculadosTotal = gruposClientes.reduce(
    (total, grupoCliente) => total + grupoCliente.clientesIds.length,
    0
  );

  function handleUpsert(draft: GrupoClienteDraft) {
    setGruposClientes((current) => {
      const exists = current.some(
        (grupoCliente) => grupoCliente.grupoClienteId === draft.grupoClienteId
      );

      if (!exists) return [draft, ...current];

      return current.map((grupoCliente) =>
        grupoCliente.grupoClienteId === draft.grupoClienteId
          ? draft
          : grupoCliente
      );
    });

    setCreatingGrupoCliente(false);
    setEditingGrupoClienteId(null);
  }

  function openCreate() {
    setSelectedGrupoClienteId(null);
    setEditingGrupoClienteId(null);
    setCreatingGrupoCliente(true);
  }

  function openEdit(grupoClienteId: string) {
    setSelectedGrupoClienteId(null);
    setCreatingGrupoCliente(false);
    setEditingGrupoClienteId(grupoClienteId);
  }

  function closeEdit() {
    setEditingGrupoClienteId(null);
    setCreatingGrupoCliente(false);
  }

  function closeCreate() {
    setCreatingGrupoCliente(false);
  }

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Grupo de Clientes"
          description="Agrupe empresas que pertencem ao mesmo cliente para compartilhamento de informações e relatórios."
        />

        <Button onClick={openCreate} disabled={!canCreate}>
          + Novo Grupo de Clientes
        </Button>
      </div>

      <div className="grid gap-5 sm:grid-cols-4">
        <Card>
          <p className="text-sm text-zinc-500">Total de grupos</p>
          <p className="mt-3 text-3xl font-bold">{gruposClientes.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Grupos ativos</p>
          <p className="mt-3 text-3xl font-bold">{gruposAtivos}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Grupos inativos</p>
          <p className="mt-3 text-3xl font-bold">{gruposInativos}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Clientes vinculados</p>
          <p className="mt-3 text-3xl font-bold">{clientesVinculadosTotal}</p>
        </Card>
      </div>

      <div className="mt-8 flex items-end justify-between gap-4">
        <Input
          label="Busca"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Buscar por nome, código ou sigla"
          className="max-w-md"
        />
      </div>

      <div className="mt-6 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Código</th>
              <th className="px-6 py-4 font-medium">Grupo</th>
              <th className="px-6 py-4 font-medium">Sigla</th>
              <th className="px-6 py-4 font-medium">Clientes vinculados</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {gruposFiltrados.map((grupoCliente) => (
              <tr
                key={grupoCliente.grupoClienteId}
                tabIndex={0}
                onClick={() =>
                  setSelectedGrupoClienteId(grupoCliente.grupoClienteId)
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setSelectedGrupoClienteId(grupoCliente.grupoClienteId);
                  }
                }}
                aria-label={`Ver grupo de clientes ${grupoCliente.nome}`}
                className="cursor-pointer border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50 focus:bg-zinc-50 focus:outline-none"
              >
                <td className="px-6 py-4 text-zinc-500">
                  {grupoCliente.codigoInterno}
                </td>
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {grupoCliente.nome}
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {grupoCliente.sigla}
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  <div className="space-y-0.5">
                    {grupoCliente.clientesIds.length === 0 ? (
                      <p>Nenhum cliente</p>
                    ) : (
                      (() => {
                        const clientes = grupoCliente.clientesIds
                          .map((clienteId) => resolveClienteResumo(clienteId))
                          .filter(
                            (cliente): cliente is NonNullable<typeof cliente> =>
                              cliente !== null
                          );

                        if (clientes.length === 0) {
                          return <p>Nenhum cliente</p>;
                        }

                        if (clientes.length === 1) {
                          return <p>{clientes[0].nome}</p>;
                        }

                        if (clientes.length === 2) {
                          return (
                            <>
                              <p>{clientes[0].nome}</p>
                              <p>{clientes[1].nome}</p>
                            </>
                          );
                        }

                        return (
                          <>
                            <p>{clientes[0].nome}</p>
                            <p>{clientes[1].nome}</p>
                            <p>+{clientes.length - 2}</p>
                          </>
                        );
                      })()
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <Badge>{grupoCliente.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <EntitySidePanel
        open={selectedGrupoCliente !== undefined}
        onClose={() => setSelectedGrupoClienteId(null)}
        onEdit={
          canEdit && selectedGrupoCliente
            ? () => openEdit(selectedGrupoCliente.grupoClienteId)
            : undefined
        }
        editLabel="Editar grupo de clientes"
        title={selectedGrupoCliente?.nome ?? "Grupo de Clientes"}
        description={selectedGrupoCliente?.codigoInterno}
        footer={
          <div className="flex justify-end">
            <Button
              variant="secondary"
              onClick={() => setSelectedGrupoClienteId(null)}
            >
              Fechar
            </Button>
          </div>
        }
      >
        {selectedGrupoCliente && (
          <EntitySummaryPanel
            badges={<Badge>{selectedGrupoCliente.status}</Badge>}
            sections={[
              {
                title: "Dados principais",
                children: (
                  <div className="space-y-3">
                    <EntityFieldRow
                      label="Código"
                      value={selectedGrupoCliente.codigoInterno}
                    />
                    <EntityFieldRow
                      label="Nome"
                      value={selectedGrupoCliente.nome}
                    />
                    <EntityFieldRow
                      label="Sigla"
                      value={selectedGrupoCliente.sigla}
                    />
                    <EntityFieldRow
                      label="Quantidade de clientes"
                      value={selectedGrupoCliente.clientesIds.length}
                    />
                  </div>
                ),
              },
              {
                title: "Clientes vinculados",
                children: selectedGrupoCliente.clientesIds.length > 0 ? (
                  <div className="space-y-3">
                    {selectedGrupoCliente.clientesIds.map((clienteId) => {
                      const cliente = resolveClienteResumo(clienteId);

                      if (!cliente) return null;

                      return (
                        <div
                          key={clienteId}
                          className="rounded-2xl border border-zinc-200 p-4"
                        >
                          <p className="text-sm font-medium text-zinc-900">
                            {cliente.nome}
                          </p>
                          <p className="mt-1 text-xs text-zinc-400">
                            {cliente.codigoInterno}
                          </p>
                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <Badge>{cliente.sigla}</Badge>
                            <Badge>{cliente.status}</Badge>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">
                    Nenhum cliente vinculado.
                  </p>
                ),
              },
              {
                title: "Atividade recente",
                children: selectedGrupoCliente.historico.length > 0 ? (
                  <div className="rounded-2xl bg-[#faf8f4] p-4">
                    <p className="text-sm text-zinc-700">
                      {
                        selectedGrupoCliente.historico[
                          selectedGrupoCliente.historico.length - 1
                        ].acao
                      }
                    </p>
                    <p className="mt-1 text-xs text-zinc-400">
                      {
                        selectedGrupoCliente.historico[
                          selectedGrupoCliente.historico.length - 1
                        ].usuario
                      }{" "}
                      ·{" "}
                      {
                        selectedGrupoCliente.historico[
                          selectedGrupoCliente.historico.length - 1
                        ].dataHora
                      }
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">
                    Nenhuma atividade recente.
                  </p>
                ),
              },
            ]}
          />
        )}
      </EntitySidePanel>

      {editingGrupoCliente && (
        <NovoGrupoClienteModal
          key={editingGrupoCliente.grupoClienteId}
          open
          grupoCliente={editingGrupoCliente}
          onClose={closeEdit}
          onSave={handleUpsert}
        />
      )}

      {creatingGrupoCliente && !editingGrupoCliente && (
        <NovoGrupoClienteModal
          open
          onClose={closeCreate}
          onSave={handleUpsert}
        />
      )}
    </div>
  );
}
