import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ListTodo, FolderKanban, Users, ShieldCheck } from "lucide-react";

const dashboardStats = {
  tarefas: 128,
  projetos: 24,
  clientes: 86,
  sla: 97,
};

const stats = [
  { title: "Tarefas", value: dashboardStats.tarefas, change: "+12%", icon: ListTodo },
  { title: "Projetos", value: dashboardStats.projetos, change: "+4%", icon: FolderKanban },
  { title: "Clientes", value: dashboardStats.clientes, change: "+8%", icon: Users },
  { title: "SLA", value: dashboardStats.sla, change: "+1,2%", icon: ShieldCheck },
];

export function DashboardStats() {
  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;

        return (
          <Card key={stat.title}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-zinc-500">{stat.title}</p>
                <p className="mt-3 text-3xl font-semibold text-zinc-900">
                  {stat.value}
                </p>
                <div className="mt-3">
                  <Badge>{stat.change}</Badge>
                </div>
              </div>

              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-zinc-100 text-zinc-600">
                <Icon className="h-5 w-5" strokeWidth={2} aria-hidden="true" />
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
