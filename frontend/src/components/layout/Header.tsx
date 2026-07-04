export function Header() {
  return (
    <header className="flex h-20 items-center justify-between border-b border-zinc-200 bg-[#f4f1ec] px-8">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-zinc-500">
          Base visual da operação. Módulos serão ativados nas próximas fases.
        </p>
      </div>

      <div className="rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-600 shadow-sm">
        Fase 2.1
      </div>
    </header>
  );
}
