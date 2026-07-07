import { Card } from "@/components/ui/Card";

const activities = [
  { title: "Novo cliente cadastrado", detail: "Casa Brasil · há 12 min" },
  { title: "Projeto movido para revisão", detail: "Projeto Aurora · há 34 min" },
  { title: "SLA ajustado", detail: "Prioridade alta · há 1h" },
  { title: "Usuário adicionado à equipe", detail: "Equipe Criação · há 2h" },
];

export function DashboardActivities() {
  return (
    <Card>
      <div>
        <h3 className="text-xl font-semibold text-zinc-900">Atividades</h3>
        <p className="mt-1 text-sm text-zinc-500">Movimentações recentes mockadas.</p>
      </div>

      <div className="mt-6 space-y-4">
        {activities.map((activity) => (
          <div key={activity.title} className="border-l border-zinc-200 pl-4">
            <p className="font-medium text-zinc-900">{activity.title}</p>
            <p className="mt-1 text-sm text-zinc-500">{activity.detail}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
