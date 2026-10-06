"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";

export type UsuarioSituacaoFiltro = "todos" | "ativo" | "inativo";

export function UsuariosToolbar({
  query,
  onQueryChange,
  situacaoFilter,
  onSituacaoFilterChange,
  departamentoFilter,
  onDepartamentoFilterChange,
  departamentos,
  onNewUsuario,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  situacaoFilter: UsuarioSituacaoFiltro;
  onSituacaoFilterChange: (value: UsuarioSituacaoFiltro) => void;
  departamentoFilter: string;
  onDepartamentoFilterChange: (value: string) => void;
  departamentos: DepartamentoDiretorioItem[];
  onNewUsuario: () => void;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1fr)_200px_180px]">
          <label className="block text-sm">
            <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
              <input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Buscar por nome, e-mail ou departamento"
                className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
              />
            </span>
          </label>

          <Select
            label="Departamento"
            value={departamentoFilter}
            onChange={(event) => onDepartamentoFilterChange(event.target.value)}
            options={[{ value: "", label: "Todos" }, ...departamentos.map((departamento) => ({ value: departamento.id, label: departamento.nome }))]}
          />

          <Select
            label="Situação"
            value={situacaoFilter}
            onChange={(event) => onSituacaoFilterChange(event.target.value as UsuarioSituacaoFiltro)}
            options={[
              { value: "todos", label: "Todos" },
              { value: "ativo", label: "Ativos" },
              { value: "inativo", label: "Inativos" },
            ]}
          />
        </div>

        <Button onClick={onNewUsuario}>
          <Plus className="h-4 w-4" />
          Nova pessoa
        </Button>
      </div>
    </div>
  );
}
