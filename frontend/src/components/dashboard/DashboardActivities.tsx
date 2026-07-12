import { Activity } from "lucide-react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusPill } from "@/components/ui/StatusPill";

const activities = [
  { title: "Novo cliente cadastrado", detail: "Casa Brasil · há 12 min" },
  { title: "Projeto movido para revisão", detail: "Projeto Aurora · há 34 min" },
  { title: "SLA ajustado", detail: "Prioridade alta · há 1h" },
  { title: "Usuário adicionado à equipe", detail: "Equipe Criação · há 2h" },
];

export function DashboardActivities() {
  return (
    <section className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm">
      <SectionHeader
        title="Atividades"
        description="Movimentações recentes mockadas."
        action={<StatusPill tone="blue">{activities.length} eventos</StatusPill>}
      />

      <div className="mt-5 space-y-3">
        {activities.map((activity, index) => (
          <div
            key={activity.title}
            className="group flex gap-3 rounded-2xl border border-zinc-100 p-3 transition hover:bg-zinc-50"
          >
            <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-zinc-950 text-white">
              <Activity className="h-4 w-4" aria-hidden="true" />
            </span>

            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-3">
                <p className="font-semibold text-zinc-950">{activity.title}</p>
                <span className="font-mono text-xs text-zinc-400">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </div>
              <p className="mt-1 text-sm text-zinc-500">{activity.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
