import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function ClientesPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Clientes"
        description="Cadastro e gestão de clientes."
      />

      <EmptyState
        title="Módulo em construção"
        description="O cadastro de clientes será implementado futuramente."
      />
    </div>
  );
}
