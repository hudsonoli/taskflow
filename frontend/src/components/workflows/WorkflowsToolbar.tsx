"use client";

import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function WorkflowsToolbar({
  query,
  onQueryChange,
  onNewWorkflow,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  onNewWorkflow: () => void;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <label className="block flex-1 text-sm sm:max-w-sm">
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Busca</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Buscar por nome do modelo"
              className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
            />
          </span>
        </label>

        <Button onClick={onNewWorkflow}>
          <Plus className="h-4 w-4" />
          Novo workflow
        </Button>
      </div>
    </div>
  );
}
