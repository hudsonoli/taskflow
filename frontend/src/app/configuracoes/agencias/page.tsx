import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function AgenciasPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Agências"
        description="Cadastro e gestão das agências da plataforma."
      />

      <EmptyState
        title="Nenhuma agência cadastrada"
        description="O cadastro de agências será implementado futuramente."
      />
    </div>
  );
}
