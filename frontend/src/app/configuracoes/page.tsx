import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function ConfiguracoesPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Configurações"
        description="Configurações gerais da plataforma."
      />

      <EmptyState
        title="Configurações ainda não implementadas"
        description="As opções administrativas serão criadas futuramente."
      />
    </div>
  );
}
