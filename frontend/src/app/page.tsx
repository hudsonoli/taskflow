const menuItems = [
  "Dashboard",
  "Tarefas",
  "Projetos",
  "Clientes",
  "Equipe",
  "Relatórios",
  "Configurações",
];

const dashboardCards = [
  { title: "Tarefas", value: "—", description: "Aguardando módulo de tarefas" },
  { title: "Projetos", value: "—", description: "Aguardando módulo de projetos" },
  { title: "SLA", value: "—", description: "Aguardando regras operacionais" },
  { title: "Produtividade", value: "—", description: "Aguardando indicadores" },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f4f1ec] text-zinc-900">
      <div className="flex min-h-screen">
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

        <section className="flex-1">
          <header className="flex h-20 items-center justify-between border-b border-zinc-200 bg-[#f4f1ec] px-8">
            <div>
              <h1 className="text-2xl font-semibold">Dashboard</h1>
              <p className="text-sm text-zinc-500">
                Base visual da operação. Módulos serão ativados nas próximas fases.
              </p>
            </div>

            <div className="rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-600 shadow-sm">
              Fase 2
            </div>
          </header>

          <div className="p-8">
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              {dashboardCards.map((card) => (
                <div
                  key={card.title}
                  className="rounded-3xl bg-white p-6 shadow-sm"
                >
                  <div className="text-sm font-medium text-zinc-500">
                    {card.title}
                  </div>
                  <div className="mt-4 text-4xl font-bold">{card.value}</div>
                  <div className="mt-3 text-sm text-zinc-500">
                    {card.description}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 rounded-3xl bg-white p-8 shadow-sm">
              <h2 className="text-xl font-semibold">Shell principal</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">
                Esta tela representa a base visual do TaskFloww v2: sidebar,
                header e dashboard inicial. Kanban, banco de dados, autenticação
                e integrações serão tratados em fases futuras.
              </p>

              <div className="mt-8 rounded-3xl border border-dashed border-zinc-300 bg-[#faf8f4] p-10 text-center text-sm text-zinc-500">
                Área reservada para os próximos módulos operacionais
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
