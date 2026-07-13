import { Clock3 } from "lucide-react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusPill } from "@/components/ui/StatusPill";

const agenda = [
  { time: "09:30", title: "Reunião com Cliente Alfa", tag: "Prioridade alta" },
  { time: "11:00", title: "Ajuste de briefing", tag: "Operação" },
  { time: "14:00", title: "Status do Projeto Aurora", tag: "Projeto" },
  { time: "16:30", title: "Revisão de SLA", tag: "Gestão" },
];

export function DashboardAgenda() {
  return (
    <section className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm">
      <SectionHeader
        title="Agenda"
        description="Compromissos mock de hoje."
        action={<StatusPill tone="amber">{agenda.length} itens</StatusPill>}
      />

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {agenda.map((item) => (
          <div
            key={`${item.time}-${item.title}`}
            className="rounded-2xl border border-zinc-100 p-3.5 transition hover:bg-zinc-50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-xs font-semibold text-zinc-500">
                  <Clock3 className="h-4 w-4" aria-hidden="true" />
                  <span>{item.time}</span>
                </div>
                <p className="mt-2 truncate font-semibold text-zinc-950">
                  {item.title}
                </p>
              </div>
              <StatusPill tone={item.tag === "Prioridade alta" ? "red" : "neutral"}>
                {item.tag}
              </StatusPill>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
