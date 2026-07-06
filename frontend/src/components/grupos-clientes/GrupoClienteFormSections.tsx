"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  clientesGrupoDisponiveis,
  type ClienteGrupoItem,
} from "@/lib/grupo-cliente-mock";
import type { GrupoClienteDraft } from "@/types/grupo-cliente";

const statusOptions = [
  { value: "Ativo", label: "Ativo" },
  { value: "Inativo", label: "Inativo" },
];

type SectionProps = {
  draft: GrupoClienteDraft;
  onChange: (updater: (current: GrupoClienteDraft) => GrupoClienteDraft) => void;
};

function resolveClienteNome(cliente: ClienteGrupoItem): string {
  return cliente.nomeFantasia || cliente.nomeRazaoSocial;
}

function matchesSearch(cliente: ClienteGrupoItem, term: string): boolean {
  if (!term) return true;

  return [
    cliente.clienteId,
    cliente.codigoInterno,
    cliente.nomeFantasia,
    cliente.nomeRazaoSocial,
    cliente.sigla,
    cliente.status,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .includes(term);
}

export function DadosSection({ draft, onChange }: SectionProps) {
  const [searchInput, setSearchInput] = useState("");

  const clientesVinculados = useMemo(
    () =>
      draft.clientesIds
        .map((clienteId) =>
          clientesGrupoDisponiveis.find(
            (cliente) => cliente.clienteId === clienteId
          )
        )
        .filter((cliente): cliente is ClienteGrupoItem => cliente !== undefined),
    [draft.clientesIds]
  );

  const filteredClientes = useMemo(() => {
    const term = searchInput.trim().toLowerCase();

    return clientesGrupoDisponiveis.filter(
      (cliente) =>
        !draft.clientesIds.includes(cliente.clienteId) &&
        matchesSearch(cliente, term)
    );
  }, [draft.clientesIds, searchInput]);

  function handleAddCliente(clienteId: string) {
    onChange((current) => {
      if (current.clientesIds.includes(clienteId)) return current;

      return {
        ...current,
        clientesIds: [...current.clientesIds, clienteId],
      };
    });
  }

  function handleRemoveCliente(clienteId: string) {
    onChange((current) => ({
      ...current,
      clientesIds: current.clientesIds.filter((id) => id !== clienteId),
    }));
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <Input
          label="Nome do Grupo"
          value={draft.nome}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              nome: event.target.value,
            }))
          }
        />

        <Input
          label="Sigla"
          value={draft.sigla}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              sigla: event.target.value,
            }))
          }
        />

        <Select
          label="Status"
          options={statusOptions}
          value={draft.status}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              status: event.target.value as GrupoClienteDraft["status"],
            }))
          }
        />
      </div>

      <section className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-zinc-900">Clientes</h3>
          <p className="mt-1 text-xs text-zinc-500">
            Busque clientes existentes e adicione ao grupo.
          </p>
        </div>

        <div className="space-y-3">
          <Input
            label="Cliente"
            placeholder="Buscar por nome, sigla ou código"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />

          <div className="rounded-2xl border border-zinc-200 bg-white">
            {filteredClientes.length > 0 ? (
              <ul className="max-h-56 overflow-y-auto">
                {filteredClientes.map((cliente) => (
                  <li
                    key={cliente.clienteId}
                    className="flex items-center justify-between gap-4 border-b border-zinc-100 px-4 py-3 last:border-0"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-zinc-900">
                        {resolveClienteNome(cliente)}
                      </p>
                      <p className="mt-1 text-xs text-zinc-400">
                        {cliente.codigoInterno} · {cliente.sigla}
                      </p>
                    </div>

                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => handleAddCliente(cliente.clienteId)}
                      className="shrink-0 px-3 py-2 text-xs"
                    >
                      Adicionar
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-4">
                <EmptyState
                  title="Nenhum cliente encontrado"
                  description="Ajuste a busca para localizar um cliente existente."
                />
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-zinc-900">
            Clientes vinculados ({draft.clientesIds.length})
          </h4>
        </div>

        {clientesVinculados.length === 0 ? (
          <EmptyState
            title="Nenhum cliente adicionado"
            description="Use a busca acima para vincular clientes ao grupo."
          />
        ) : (
          <div className="space-y-3">
            {clientesVinculados.map((cliente) => (
              <div
                key={cliente.clienteId}
                className="rounded-2xl border border-zinc-200 p-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-zinc-900">
                      {resolveClienteNome(cliente)}
                    </p>
                    <p className="mt-1 text-xs text-zinc-400">
                      {cliente.codigoInterno}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleRemoveCliente(cliente.clienteId)}
                    className="text-xs font-medium text-zinc-400 underline decoration-dotted hover:text-zinc-700"
                  >
                    Remover
                  </button>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge>{cliente.sigla}</Badge>
                  <Badge>{cliente.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export function ContatosSection() {
  return (
    <div className="rounded-2xl border border-dashed border-zinc-200 bg-zinc-50 px-4 py-5 text-sm text-zinc-500">
      Integração iJob prevista para fase futura.
    </div>
  );
}
