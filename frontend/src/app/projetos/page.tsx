import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function ProjetosPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Projetos"
        description="Gestão de projetos e entregas."
      />

      <EmptyState
        title="Projetos ainda não implementados"
        description="Este módulo será desenvolvido nas próximas fases."
      />
    </div>
  );
}
