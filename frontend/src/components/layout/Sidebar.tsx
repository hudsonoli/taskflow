const menuItems = [
  "Dashboard",
  "Tarefas",
  "Projetos",
  "Clientes",
  "Equipe",
  "Relatórios",
  "Configurações",
];

export function Sidebar() {
  return (
    <aside className="w-72 border-r border-zinc-200 bg-white px-5 py-6">
      <div className="mb-10">
        <div className="text-2xl font-bold tracking-tight">TaskFloww</div>
        <div className="mt-1 text-sm text-zinc-500">Shell Boxx v2</div>
      </div>

      <nav className="space-y-1">
        {menuItems.map((item, index) => (
          <div
            key={item}
            className={`rounded-2xl px-4 py-3 text-sm font-medium ${
              index === 0
                ? "bg-zinc-900 text-white"
                : "text-zinc-600 hover:bg-zinc-100"
            }`}
          >
            {item}
          </div>
        ))}
      </nav>
    </aside>
  );
}
