"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function EquipesToolbar({
  query,
  onQueryChange,
  onNewEquipe,
  mostrarArquivadas,
  onMostrarArquivadasChange,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  onNewEquipe: () => void;
  mostrarArquivadas: boolean;
  onMostrarArquivadasChange: (value: boolean) => void;
}) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <label className="block flex-1 text-sm sm:max-w-sm">
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">Busca</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Buscar por nome ou código (E26000001)"
              className="w-full rounded-xl border border-zinc-200/80 bg-zinc-50/70 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
            />
          </span>
        </label>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => onMostrarArquivadasChange(!mostrarArquivadas)}
            className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {mostrarArquivadas ? "Ver ativas" : "Ver arquivadas"}
          </button>
          <Button onClick={onNewEquipe}>
          <Plus className="h-4 w-4" />
            Nova equipe
          </Button>
        </div>
      </div>
    </div>
  );
}
