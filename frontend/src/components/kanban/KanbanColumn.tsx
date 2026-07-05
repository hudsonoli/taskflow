import { KanbanCard } from "./KanbanCard";

type Task = {
  id: string;
  title: string;
  client: string;
  priority: string;
};

type KanbanColumnProps = {
  title: string;
  tasks: Task[];
};

export function KanbanColumn({
  title,
  tasks,
}: KanbanColumnProps) {
  return (
    <div className="w-80 shrink-0">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-semibold text-zinc-800">
          {title}
        </h2>

        <span className="rounded-full bg-zinc-200 px-2 py-1 text-xs">
          {tasks.length}
        </span>
      </div>

      <div className="space-y-3">
        {tasks.map((task) => (
          <KanbanCard
            key={task.id}
            title={task.title}
            client={task.client}
            priority={task.priority}
          />
        ))}
      </div>
    </div>
  );
}
