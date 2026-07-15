import Link from "next/link";
import { Clock3 } from "lucide-react";
import { StatusPill } from "@/components/ui/StatusPill";
import type { DashboardAgendaItem } from "@/types/dashboard";
import { DashboardWidget } from "./DashboardWidget";

type DashboardAgendaProps = {
  agenda: DashboardAgendaItem[];
};

const MAX_ITEMS = 4;

export function DashboardAgenda({ agenda }: DashboardAgendaProps) {
  const items = agenda.slice(0, MAX_ITEMS);

  return (
    <DashboardWidget title="Hoje na Agenda" description="Próximos compromissos do dia.">
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center gap-3 rounded-xl border border-zinc-100 px-3 py-2 transition hover:bg-zinc-50"
          >
            <div className="flex shrink-0 items-center gap-1.5 text-[11px] font-medium text-zinc-500">
              <Clock3 className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
              {item.horario}
            </div>

            <p className="min-w-0 flex-1 truncate text-[13px] font-normal text-zinc-800">
              {item.titulo}
            </p>

            <StatusPill
              density="compact"
              tone={item.tag === "Prioridade alta" ? "red" : "neutral"}
            >
              {item.tag}
            </StatusPill>
          </div>
        ))}
      </div>

      <Link
        href="/agenda"
        className="mt-3 inline-block text-[11px] font-medium text-primary hover:underline"
      >
        Ver agenda completa
      </Link>
    </DashboardWidget>
  );
}
