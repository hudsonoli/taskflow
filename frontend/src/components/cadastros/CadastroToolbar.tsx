import type { ReactNode } from "react";
import { Search } from "lucide-react";

type CadastroToolbarProps = {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  actions?: ReactNode;
  children?: ReactNode;
};

export function CadastroToolbar({
  searchValue = "",
  onSearchChange,
  searchPlaceholder = "Pesquisar...",
  actions,
  children,
}: CadastroToolbarProps) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-zinc-100 bg-white p-2.5 shadow-sm lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center">
        <label className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 text-sm text-zinc-500 lg:max-w-md">
          <Search className="h-4 w-4 shrink-0 text-zinc-400" strokeWidth={2} />
          <input
            value={searchValue}
            onChange={(event) => onSearchChange?.(event.target.value)}
            placeholder={searchPlaceholder}
            className="min-w-0 flex-1 bg-transparent text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
            aria-label={searchPlaceholder}
          />
        </label>

        {children}
      </div>

      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}
