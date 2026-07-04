import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function RelatoriosPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Relatórios"
        description="Indicadores operacionais e métricas."
      />

      <EmptyState
        title="Relatórios ainda não disponíveis"
        description="Os relatórios serão criados em fases futuras."
      />
    </div>
  );
}
