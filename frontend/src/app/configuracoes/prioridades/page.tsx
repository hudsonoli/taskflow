import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function PrioridadesPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Prioridades"
        description="Níveis de prioridade das tarefas."
      />

      <EmptyState
        title="Nenhuma prioridade cadastrada"
        description="As prioridades serão implementadas futuramente."
      />
    </div>
  );
}
