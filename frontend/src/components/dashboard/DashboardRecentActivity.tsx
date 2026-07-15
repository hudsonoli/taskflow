import { Activity } from "lucide-react";
import type { DashboardAtividade, DashboardAtividadeTone } from "@/types/dashboard";
import { DashboardWidget } from "./DashboardWidget";

type DashboardRecentActivityProps = {
  atividades: DashboardAtividade[];
};

const MAX_ITEMS = 5;

const toneIconClassNames: Record<DashboardAtividadeTone, string> = {
  neutral: "bg-zinc-100 text-zinc-600",
  blue: "bg-blue-50 text-blue-600",
  green: "bg-emerald-50 text-emerald-600",
  amber: "bg-amber-50 text-amber-600",
  red: "bg-red-50 text-red-600",
};

// Sem link "Ver histórico completo" — não existe rota real de histórico
// ainda (ver plano aprovado).
export function DashboardRecentActivity({ atividades }: DashboardRecentActivityProps) {
  const items = atividades.slice(0, MAX_ITEMS);

  return (
    <DashboardWidget title="Atividade recente" description="Últimos eventos do sistema.">
      <div className="space-y-2">
        {items.map((atividade) => (
          <div
            key={atividade.id}
            className="flex items-center gap-3 rounded-xl border border-zinc-100 px-3 py-2 transition hover:bg-zinc-50"
          >
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${toneIconClassNames[atividade.tone]}`}
            >
              <Activity className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
            </span>

            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-normal text-zinc-800">
                {atividade.descricao}
              </p>
              <p className="truncate text-[11px] text-zinc-500">{atividade.usuario}</p>
            </div>

            <span className="shrink-0 text-[10px] text-zinc-400">{atividade.horario}</span>
          </div>
        ))}
      </div>
    </DashboardWidget>
  );
}
