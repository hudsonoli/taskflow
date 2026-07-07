import { Search } from "lucide-react";

export function HeaderSearch() {
  return (
    <label className="hidden w-full max-w-[320px] items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-500 shadow-sm transition hover:bg-zinc-100 md:flex md:w-[280px] lg:w-[320px]">
      <Search className="h-4 w-4 text-zinc-400" strokeWidth={2} />
      <span className="text-zinc-400">Pesquisar...</span>
    </label>
  );
}
