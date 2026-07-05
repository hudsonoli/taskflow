import { Badge } from "@/components/ui/Badge";

export type TaskPriority = "Baixa" | "Media" | "Alta";

type KanbanCardProps = {
  title: string;
  client: string;
  project: string;
  assignee: string;
  priority: TaskPriority;
};

export function KanbanCard({
  title,
  client,
  project,
  assignee,
  priority,
}: KanbanCardProps) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <Badge>{priority}</Badge>
      </div>

      <h3 className="mt-3 text-sm font-semibold text-zinc-900">{title}</h3>

      <p className="mt-2 text-xs text-zinc-500">{client}</p>

      <div className="mt-4 flex items-center justify-between text-xs text-zinc-500">
        <span>{project}</span>
        <span>{assignee}</span>
      </div>
    </div>
  );
}
