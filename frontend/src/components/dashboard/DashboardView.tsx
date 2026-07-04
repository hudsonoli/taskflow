import { StatCard } from "./StatCard";

const dashboardCards = [
  { title: "Tarefas", value: "—", description: "Aguardando módulo de tarefas" },
  { title: "Projetos", value: "—", description: "Aguardando módulo de projetos" },
  { title: "SLA", value: "—", description: "Aguardando regras operacionais" },
  { title: "Produtividade", value: "—", description: "Aguardando indicadores" },
];

export function DashboardView() {
  return (
    <div className="p-8">
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {dashboardCards.map((card) => (
          <StatCard
            key={card.title}
            title={card.title}
            value={card.value}
            description={card.description}
          />
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
  );
}
