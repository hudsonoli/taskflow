"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Network } from "lucide-react";
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
import { Button } from "@/components/ui/Button";
import { EntityFieldRow } from "@/components/ui/EntityFieldRow";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { EntitySummaryPanel } from "@/components/ui/EntitySummaryPanel";
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
    <CadastroPage
      title="Grupos de Clientes"
      description="Agrupe empresas que pertencem ao mesmo cliente para compartilhamento de informações e relatórios."
      toolbar={
        <CadastroToolbar
          searchValue={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Buscar por nome, código ou sigla"
          actions={
            <Button onClick={openCreate} disabled={!canCreate} className="h-10 px-3">
              Novo Grupo
            </Button>
          }
        />
      }
      indicators={
        <CadastroIndicators
          items={[
            { label: "Total", value: gruposClientes.length },
            { label: "Ativos", value: gruposAtivos },
            { label: "Inativos", value: gruposInativos },
            { label: "Clientes", value: clientesVinculadosTotal },
          ]}
        />
      }
    >
      <CadastroTable minWidth="820px">
        <thead className={cadastroTableHeaderClassName}>
          <tr>
            <th className={cadastroTableHeaderCellClassName}>Grupo</th>
            <th className={cadastroTableHeaderCellClassName}>Código</th>
            <th className={cadastroTableHeaderCellClassName}>Sigla</th>
            <th className={cadastroTableHeaderCellClassName}>Clientes vinculados</th>
            <th className={cadastroTableHeaderCellClassName}>Status</th>
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
              className={`cursor-pointer ${cadastroTableRowClassName}`}
            >
              <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                <div className="flex items-center gap-2.5">
                  <CadastroAvatar label={grupoCliente.nome} icon={Network} />
                  <span>{grupoCliente.nome}</span>
                </div>
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                {grupoCliente.codigoInterno}
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                {grupoCliente.sigla}
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                <div className="space-y-0.5 text-xs leading-5">
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

                      if (clientes.length === 0) return <p>Nenhum cliente</p>;
                      if (clientes.length === 1) return <p>{clientes[0].nome}</p>;

                      return (
                        <>
                          <p>{clientes[0].nome}</p>
                          <p>{clientes[1].nome}</p>
                          {clientes.length > 2 ? <p>+{clientes.length - 2}</p> : null}
                        </>
                      );
                    })()
                  )}
                </div>
              </td>
              <td className={cadastroTableCellClassName}>
                <CadastroStatusBadge>{grupoCliente.status}</CadastroStatusBadge>
              </td>
            </tr>
          ))}
        </tbody>
      </CadastroTable>

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
    </CadastroPage>
  );
}
