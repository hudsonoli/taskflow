import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function EquipesPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Equipes"
        description="Organização de departamentos e equipes."
      />

      <EmptyState
        title="Nenhuma equipe cadastrada"
        description="O cadastro de equipes será implementado futuramente."
      />
    </div>
  );
}
