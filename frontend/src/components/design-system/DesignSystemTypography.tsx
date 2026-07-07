import { Card } from "@/components/ui/Card";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";

export function DesignSystemTypography() {
  return (
    <WorkspaceSection
      title="Tipografia"
      description="Escala base para títulos, descrições e conteúdo de apoio."
    >
      <Card>
        <div className="space-y-5">
          <div>
            <p className="text-xs text-zinc-500">Título de página</p>
            <h1 className="mt-1 text-3xl font-bold text-zinc-900">
              Gestão operacional
            </h1>
          </div>

          <div>
            <p className="text-xs text-zinc-500">Título de seção</p>
            <h2 className="mt-1 text-xl font-semibold text-zinc-900">
              Atividades da equipe
            </h2>
          </div>

          <div>
            <p className="text-xs text-zinc-500">Texto de apoio</p>
            <p className="mt-1 text-sm text-zinc-500">
              Use descrições curtas para orientar decisões e leitura rápida.
            </p>
          </div>
        </div>
      </Card>
    </WorkspaceSection>
  );
}
