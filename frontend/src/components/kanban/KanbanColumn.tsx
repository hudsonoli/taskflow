"use client";

import { useDroppable, useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { KanbanCard, type TaskPriority } from "./KanbanCard";

export type KanbanTask = {
  id: string;
  title: string;
  client: string;
  project: string;
  assignee: string;
  priority: TaskPriority;
  columnId: string;
};

type KanbanColumnProps = {
  id: string;
  title: string;
  tasks: KanbanTask[];
};

function DraggableCard({ task }: { task: KanbanTask }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: task.id,
  });

  const style = {
    transform: CSS.Translate.toString(transform),
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="cursor-grab touch-none active:cursor-grabbing"
    >
      <KanbanCard
        id={task.id}
        title={task.title}
        client={task.client}
        project={task.project}
        assignee={task.assignee}
        priority={task.priority}
      />
    </div>
  );
}

export function KanbanColumn({ id, title, tasks }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id,
  });

  return (
    <div
      ref={setNodeRef}
      className={`w-80 shrink-0 rounded-3xl p-4 transition ${
        isOver ? "bg-zinc-200" : "bg-[#faf8f4]"
      }`}
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-semibold text-zinc-800">{title}</h2>

        <span className="rounded-full bg-zinc-200 px-2 py-1 text-xs">
          {tasks.length}
        </span>
      </div>

      <div className="space-y-3">
        {tasks.map((task) => (
          <DraggableCard key={task.id} task={task} />
        ))}
      </div>
    </div>
  );
}
