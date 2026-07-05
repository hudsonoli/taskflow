import { Badge } from "@/components/ui/Badge";

export type TaskPriority = "Baixa" | "Media" | "Alta";
export type TaskRework = "Sim" | "Não";

type KanbanCardProps = {
  id: string;
  title: string;
  client: string;
  project: string;
  assignee: string;
  priority: TaskPriority;
  deadline: string;
  sla: string;
  taskType: string;
  rework: TaskRework;
};

export function KanbanCard({
  id,
  title,
  client,
  project,
  assignee,
  priority,
  deadline,
  sla,
  taskType,
  rework,
}: KanbanCardProps) {
  return (
    <div data-task-id={id} className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <Badge>{priority}</Badge>
        <Badge>{taskType}</Badge>
      </div>

      <h3 className="mt-3 text-sm font-semibold text-zinc-900">{title}</h3>

      <div className="mt-3 space-y-1 text-xs text-zinc-500">
        <p>Cliente: {client}</p>
        <p>Projeto: {project}</p>
        <p>Responsável: {assignee}</p>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-xl bg-[#faf8f4] p-2">
          <p className="text-zinc-400">SLA</p>
          <p className="font-medium text-zinc-800">{sla}</p>
        </div>

        <div className="rounded-xl bg-[#faf8f4] p-2">
          <p className="text-zinc-400">Prazo</p>
          <p className="font-medium text-zinc-800">{deadline}</p>
        </div>
      </div>

      <div className="mt-3 text-xs text-zinc-500">
        Refação:{" "}
        <span className="font-medium text-zinc-800">
          {rework}
        </span>
      </div>
    </div>
  );
}
