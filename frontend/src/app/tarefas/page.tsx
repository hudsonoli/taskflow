import { KanbanBoard } from "@/components/kanban/KanbanBoard";
import { PageHeader } from "@/components/ui/PageHeader";

export default function TarefasPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Tarefas"
        description="Kanban operacional do TaskFloww."
      />

      <KanbanBoard />
    </div>
  );
}
