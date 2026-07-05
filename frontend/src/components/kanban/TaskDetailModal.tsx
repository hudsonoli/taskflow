import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import type { KanbanTask } from "./KanbanColumn";

type TaskDetailModalProps = {
  task: KanbanTask | null;
  onClose: () => void;
};

export function TaskDetailModal({ task, onClose }: TaskDetailModalProps) {
  return (
    <Modal open={task !== null} onClose={onClose}>
      {task && (
        <div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex gap-2">
                <Badge>{task.priority}</Badge>
                <Badge>{task.taskType}</Badge>
              </div>
              <h2 className="mt-3 text-lg font-semibold text-zinc-900">
                {task.title}
              </h2>
            </div>

            <button
              onClick={onClose}
              aria-label="Fechar"
              className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
            >
              ✕
            </button>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-zinc-400">Cliente</p>
              <p className="font-medium text-zinc-800">{task.client}</p>
            </div>

            <div>
              <p className="text-xs text-zinc-400">Projeto</p>
              <p className="font-medium text-zinc-800">{task.project}</p>
            </div>

            <div>
              <p className="text-xs text-zinc-400">Responsável</p>
              <p className="font-medium text-zinc-800">{task.assignee}</p>
            </div>

            <div>
              <p className="text-xs text-zinc-400">Refação</p>
              <p className="font-medium text-zinc-800">{task.rework}</p>
            </div>

            <div className="rounded-xl bg-[#faf8f4] p-2">
              <p className="text-xs text-zinc-400">SLA</p>
              <p className="font-medium text-zinc-800">{task.sla}</p>
            </div>

            <div className="rounded-xl bg-[#faf8f4] p-2">
              <p className="text-xs text-zinc-400">Prazo</p>
              <p className="font-medium text-zinc-800">{task.deadline}</p>
            </div>
          </div>

          <div className="mt-4">
            <p className="text-xs text-zinc-400">Descrição</p>
            <p className="mt-1 text-sm text-zinc-600">{task.description}</p>
          </div>
        </div>
      )}
    </Modal>
  );
}
