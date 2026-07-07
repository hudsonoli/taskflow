import { Input } from "@/components/ui/Input";

type WorkspaceToolbarProps = {
  searchLabel?: string;
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  filters?: React.ReactNode;
  actions?: React.ReactNode;
};

export function WorkspaceToolbar({
  searchLabel = "Busca",
  searchPlaceholder = "Buscar",
  searchValue,
  onSearchChange,
  filters,
  actions,
}: WorkspaceToolbarProps) {
  return (
    <div className="rounded-3xl border border-zinc-100 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="w-full lg:max-w-sm">
          <Input
            label={searchLabel}
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(event) => onSearchChange?.(event.target.value)}
          />
        </div>

        {(filters || actions) && (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            {filters && (
              <div className="flex flex-wrap items-end gap-3">{filters}</div>
            )}

            {actions && (
              <div className="flex flex-wrap items-end justify-end gap-3">
                {actions}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
