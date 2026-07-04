import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";

export default function TarefasPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Tarefas"
        description="Gestão operacional de tarefas da agência."
      />

      <Section title="Kanban">
        <EmptyState
          title="Kanban em desenvolvimento"
          description="O módulo Kanban será criado na Fase 3."
        />
      </Section>
    </div>
  );
}
