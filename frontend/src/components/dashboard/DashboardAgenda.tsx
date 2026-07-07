import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

const agenda = [
  { time: "09:30", title: "Reunião com Cliente Alfa", tag: "Prioridade alta" },
  { time: "11:00", title: "Ajuste de briefing", tag: "Operação" },
  { time: "14:00", title: "Status do Projeto Aurora", tag: "Projeto" },
  { time: "16:30", title: "Revisão de SLA", tag: "Gestão" },
];

export function DashboardAgenda() {
  return (
    <Card>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-semibold text-zinc-900">Agenda</h3>
          <p className="mt-1 text-sm text-zinc-500">Compromissos mock de hoje.</p>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {agenda.map((item) => (
          <div
            key={`${item.time}-${item.title}`}
            className="flex items-center justify-between rounded-2xl border border-zinc-100 px-4 py-3"
          >
            <div>
              <p className="font-medium text-zinc-900">{item.title}</p>
              <p className="mt-1 text-sm text-zinc-500">{item.time}</p>
            </div>
            <Badge>{item.tag}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}
