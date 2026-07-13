import { CalendarDays, LayoutDashboard } from "lucide-react";
import { currentUser } from "@/lib/conta-mock";
import { StatusPill } from "@/components/ui/StatusPill";
import { DashboardStats } from "./DashboardStats";
import { DashboardAgenda } from "./DashboardAgenda";
import { DashboardActivities } from "./DashboardActivities";
import { DashboardShortcuts } from "./DashboardShortcuts";
import { DashboardChart } from "./DashboardChart";

const today = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "full",
});

function getGreeting(hour = new Date().getHours()) {
  if (hour < 12) return "Bom dia";
  if (hour < 18) return "Boa tarde";
  return "Boa noite";
}

export function DashboardView() {
  return (
    <div className="p-6">
      <div className="space-y-5">
        <section className="overflow-hidden rounded-3xl border border-zinc-100 bg-white shadow-sm">
          <div className="relative p-5 lg:p-6">
            <div className="absolute right-0 top-0 h-28 w-28 rounded-bl-full bg-blue-50" />

            <div className="relative flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-3xl bg-zinc-950 text-white shadow-sm">
                  <LayoutDashboard className="h-6 w-6" aria-hidden="true" />
                </div>

                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill tone="blue">Dashboard executivo</StatusPill>
                    <StatusPill tone="neutral">Operação mock</StatusPill>
                  </div>

                  <p className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
                    {today.format(new Date())}
                  </p>

                  <h2 className="mt-1 text-2xl font-bold tracking-tight text-zinc-950">
                    {getGreeting()}, {currentUser.nome}
                  </h2>

                  <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">
                    Aqui está um resumo do que merece atenção hoje no TaskFloww.
                  </p>
                </div>
              </div>

              <div className="relative rounded-2xl border border-zinc-100 bg-[#faf8f4] px-4 py-2.5 shadow-sm">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
                  <CalendarDays className="h-4 w-4" aria-hidden="true" />
                  Resumo do dia
                </div>
                <p className="mt-1 text-sm font-semibold text-zinc-900">
                  Plataforma operacional para agências
                </p>
              </div>
            </div>
          </div>
        </section>

        <DashboardStats />

        <div className="grid gap-5 xl:grid-cols-[1.4fr_0.9fr]">
          <DashboardAgenda />
          <DashboardActivities />
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <DashboardChart />
          <DashboardShortcuts />
        </div>
      </div>
    </div>
  );
}
