import { Badge } from "@/components/ui/Badge";

export type TaskPriority = "Baixa" | "Media" | "Alta";

type KanbanCardProps = {
  id: string;
  title: string;
  client: string;
  project: string;
  assignee: string;
  priority: TaskPriority;
};

export function KanbanCard({
  id,
  title,
  client,
  project,
  assignee,
  priority,
}: KanbanCardProps) {
  return (
    <div
      data-task-id={id}
      className="rounded-2xl bg-white p-4 shadow-sm"
    >
      <Badge>{priority}</Badge>

      <h3 className="mt-3 text-sm font-semibold text-zinc-900">{title}</h3>

      <p className="mt-2 text-xs text-zinc-500">{client}</p>

      <div className="mt-4 flex items-center justify-between text-xs text-zinc-500">
        <span>{project}</span>
        <span>{assignee}</span>
      </div>
    </div>
  );
}
