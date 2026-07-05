import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function TiposTarefaPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Tipos de Tarefa"
        description="Categorias operacionais das demandas."
      />

      <EmptyState
        title="Nenhum tipo cadastrado"
        description="Os tipos de tarefa serão implementados futuramente."
      />
    </div>
  );
}
