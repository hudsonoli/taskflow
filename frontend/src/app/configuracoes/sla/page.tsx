import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function SlaPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="SLA"
        description="Regras de prazo e atendimento."
      />

      <EmptyState
        title="Nenhum SLA cadastrado"
        description="Os SLAs serão implementados futuramente."
      />
    </div>
  );
}
