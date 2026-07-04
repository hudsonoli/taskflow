import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function EquipePage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Equipe"
        description="Gestão de colaboradores e produtividade."
      />

      <EmptyState
        title="Módulo em construção"
        description="A gestão da equipe será implementada futuramente."
      />
    </div>
  );
}
