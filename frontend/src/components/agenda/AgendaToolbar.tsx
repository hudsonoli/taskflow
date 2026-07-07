import { Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { AgendaTipo } from "@/types/agenda";

const filters: Array<{ label: string; value: AgendaTipo | "todos" }> = [
  { label: "Todos", value: "todos" },
  { label: "Clientes", value: "clientes" },
  { label: "Fornecedores", value: "fornecedores" },
  { label: "Usuários", value: "usuarios" },
];

type AgendaToolbarProps = {
  query: string;
  onQueryChange: (query: string) => void;
  typeFilter: AgendaTipo | "todos";
  onTypeFilterChange: (type: AgendaTipo | "todos") => void;
};

export function AgendaToolbar({
  query,
  onQueryChange,
  typeFilter,
  onTypeFilterChange,
}: AgendaToolbarProps) {
  return (
    <div className="rounded-3xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="relative w-full max-w-2xl">
          <Search className="pointer-events-none absolute left-3 top-9 h-4 w-4 text-zinc-400" strokeWidth={2} />
          <Input
            label="Pesquisar"
            placeholder="Pesquisar nome, empresa, telefone ou e-mail..."
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            className="pl-10"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => {
            const active = typeFilter === filter.value;

            return (
              <Button
                key={filter.value}
                type="button"
                variant={active ? "primary" : "secondary"}
                onClick={() => onTypeFilterChange(filter.value)}
              >
                {filter.label}
              </Button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
