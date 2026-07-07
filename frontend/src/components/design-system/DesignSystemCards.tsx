import { Card } from "@/components/ui/Card";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";

export function DesignSystemCards() {
  return (
    <WorkspaceSection
      title="Cards"
      description="Containers para resumos, agrupamentos e informações de apoio."
    >
      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Resumo operacional</p>
          <p className="mt-3 text-3xl font-bold text-zinc-900">24</p>
          <p className="mt-2 text-sm text-zinc-500">Itens em andamento</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">SLA</p>
          <p className="mt-3 text-3xl font-bold text-zinc-900">92%</p>
          <p className="mt-2 text-sm text-zinc-500">Dentro do prazo</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Equipe</p>
          <p className="mt-3 text-3xl font-bold text-zinc-900">8</p>
          <p className="mt-2 text-sm text-zinc-500">Usuários ativos</p>
        </Card>
      </div>
    </WorkspaceSection>
  );
}
