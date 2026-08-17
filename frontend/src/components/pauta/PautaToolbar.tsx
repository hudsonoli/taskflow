"use client";

import { CalendarRange, List, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";

export type PautaViewMode = "lista" | "gantt";
export type PautaPeriodoFiltro = "hoje" | "7d" | "30d";

export function PautaToolbar({
  query,
  onQueryChange,
  departamentoIds,
  onDepartamentoIdsChange,
  periodo,
  onPeriodoChange,
  viewMode,
  onViewModeChange,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  departamentoIds: string[];
  onDepartamentoIdsChange: (values: string[]) => void;
  periodo: PautaPeriodoFiltro;
  onPeriodoChange: (value: PautaPeriodoFiltro) => void;
  viewMode: PautaViewMode;
  onViewModeChange: (value: PautaViewMode) => void;
}) {
  const { departamentos } = useDiretorioDepartamentos();

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <label className="block flex-1 text-sm lg:max-w-sm">
          <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">Busca</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Buscar por nome, código ou projeto"
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50/70 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
            />
          </span>
        </label>

        <div className="flex flex-wrap items-center gap-2">
          {[
            { value: "hoje" as const, label: "Hoje" },
            { value: "7d" as const, label: "7 dias" },
            { value: "30d" as const, label: "30 dias" },
          ].map((option) => (
            <Button
              key={option.value}
              type="button"
              variant={periodo === option.value ? "primary" : "secondary"}
              onClick={() => onPeriodoChange(option.value)}
              className="px-3 py-1.5 text-xs"
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex-1">
          <MultiSelect
            label="Departamento"
            values={departamentoIds}
            onChange={onDepartamentoIdsChange}
            // Filtro sobre Demandas existentes, não seleção de vínculo novo — inclui
            // departamento arquivado de propósito, senão um departamento descontinuado
            // ficaria impossível de filtrar nas demandas antigas que ainda o referenciam.
            options={departamentos.map((departamento) => ({
              value: departamento.id,
              label: departamento.status === "arquivado" ? `${departamento.nome} (arquivado)` : departamento.nome,
            }))}
          />
        </div>

        <div className="inline-flex rounded-xl border border-zinc-200 bg-zinc-50 p-1 dark:border-zinc-700 dark:bg-zinc-800">
          {[
            { value: "lista" as const, label: "Lista", icon: List },
            { value: "gantt" as const, label: "Gantt", icon: CalendarRange },
          ].map((option) => {
            const Icon = option.icon;
            const isActive = viewMode === option.value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => onViewModeChange(option.value)}
                className={
                  isActive
                    ? "inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-zinc-950 shadow-sm dark:bg-zinc-950 dark:text-zinc-50"
                    : "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200"
                }
              >
                <Icon className="h-4 w-4" />
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
