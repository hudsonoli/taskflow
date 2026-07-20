import { Search } from "lucide-react";

type HeaderSearchVariant = "header" | "sidebar" | "icon";

type HeaderSearchProps = {
  variant?: HeaderSearchVariant;
};

export function HeaderSearch({ variant = "header" }: HeaderSearchProps) {
  if (variant === "icon") {
    return (
      <button
        type="button"
        title="Pesquisar"
        aria-label="Pesquisar"
        className="mx-auto flex h-8 w-8 min-w-8 max-w-8 items-center justify-center rounded-2xl border border-zinc-200 bg-white p-0 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
      >
        <Search className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
      </button>
    );
  }

  if (variant === "sidebar") {
    return (
      <label className="flex h-8 w-full items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-2.5 text-[12px] text-zinc-500 transition-colors hover:bg-zinc-50">
        <Search className="h-4 w-4 text-zinc-400" strokeWidth={2} />
        <span className="min-w-0 flex-1 truncate text-zinc-400">Pesquisar...</span>
      </label>
    );
  }

  return (
    <label className="hidden w-full max-w-[320px] items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-500 shadow-sm transition hover:bg-zinc-100 md:flex md:w-[280px] lg:w-[320px]">
      <Search className="h-4 w-4 text-zinc-400" strokeWidth={2} />
      <span className="text-zinc-400">Pesquisar...</span>
    </label>
  );
}
