import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";

export default function PermissoesPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Permissões"
        description="Perfis, cargos e regras de acesso."
      />

      <EmptyState
        title="Nenhuma permissão configurada"
        description="O controle de permissões será implementado futuramente."
      />
    </div>
  );
}
