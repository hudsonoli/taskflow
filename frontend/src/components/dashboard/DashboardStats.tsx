import { FolderKanban, ListTodo, ShieldCheck, Users } from "lucide-react";
import { DashboardGrid } from "@/components/ui/DashboardGrid";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusPill } from "@/components/ui/StatusPill";

const dashboardStats = {
  tarefas: 128,
  projetos: 24,
  clientes: 86,
  sla: 97,
};

const stats = [
  { title: "Tarefas", value: dashboardStats.tarefas, change: "+12%", icon: ListTodo, tone: "blue" },
  { title: "Projetos", value: dashboardStats.projetos, change: "+4%", icon: FolderKanban, tone: "amber" },
  { title: "Clientes", value: dashboardStats.clientes, change: "+8%", icon: Users, tone: "green" },
  { title: "SLA", value: dashboardStats.sla, change: "+1,2%", icon: ShieldCheck, tone: "blue" },
] as const;

export function DashboardStats() {
  return (
    <DashboardGrid columns="four">
      {stats.map((stat) => {
        const Icon = stat.icon;

        return (
          <MetricCard
            key={stat.title}
            title={stat.title}
            value={stat.value}
            tone={stat.tone}
            icon={<Icon className="h-5 w-5" strokeWidth={2} aria-hidden="true" />}
            badge={<StatusPill tone="green">{stat.change}</StatusPill>}
          />
        );
      })}
    </DashboardGrid>
  );
}
