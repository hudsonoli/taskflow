"use client";

import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import type { DepartamentoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import type { TrafegoFiltersState } from "@/types/trafego";

export function TrafegoFilters({
  filters,
  onChange,
  usuarios,
  departamentos,
}: {
  filters: TrafegoFiltersState;
  onChange: (filters: TrafegoFiltersState) => void;
  usuarios: UsuarioDiretorioItem[];
  departamentos: DepartamentoDiretorioItem[];
}) {
  function updateFilter<Key extends keyof TrafegoFiltersState>(key: Key, value: TrafegoFiltersState[Key]) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
            <SlidersHorizontal className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">Filtros operacionais</p>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">Ajuste a visão sem alterar dados.</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {[
            { value: "hoje", label: "Hoje" },
            { value: "24h", label: "24h" },
            { value: "7d", label: "7 dias" },
            { value: "30d", label: "30 dias" },
          ].map((periodo) => (
            <Button
              key={periodo.value}
              type="button"
              variant={filters.periodo === periodo.value ? "primary" : "secondary"}
              onClick={() => updateFilter("periodo", periodo.value as TrafegoFiltersState["periodo"])}
              className="px-3 py-1.5 text-xs"
            >
              {periodo.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.15fr_1.15fr_1fr_0.85fr]">
        <MemberSelector
          label="Usuário"
          values={filters.usuarioIds}
          onChange={(values) => updateFilter("usuarioIds", values)}
          placeholder="Selecionar usuários…"
          options={usuarios.map((usuario) => ({ id: usuario.id, nome: usuario.nome }))}
        />
        <MultiSelect
          label="Departamento"
          values={filters.departamentoIds}
          onChange={(values) => updateFilter("departamentoIds", values)}
          options={departamentos.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
        />
        <Input
          label="Demanda"
          placeholder="Buscar demanda"
          value={filters.demandaQuery}
          onChange={(event) => updateFilter("demandaQuery", event.target.value)}
        />
        <Select
          label="Status"
          value={filters.status}
          onChange={(event) => updateFilter("status", event.target.value as TrafegoFiltersState["status"])}
          options={[
            { value: "todos", label: "Todos" },
            { value: "ativa", label: "Em execução" },
            { value: "encerrada", label: "Encerradas" },
          ]}
        />
      </div>
    </div>
  );
}
