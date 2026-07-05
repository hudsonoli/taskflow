import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function WorkflowsPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Workflows"
        description="Fluxos operacionais e etapas do Kanban."
      />

      <EmptyState
        title="Nenhum workflow cadastrado"
        description="Os workflows serão implementados futuramente."
      />
    </div>
  );
}
