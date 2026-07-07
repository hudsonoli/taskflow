import { Button } from "@/components/ui/Button";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";

export function DesignSystemButtons() {
  return (
    <WorkspaceSection
      title="Botões"
      description="Ações principais, secundárias e estados desabilitados."
    >
      <div className="flex flex-wrap items-center gap-3">
        <Button>Novo registro</Button>
        <Button variant="secondary">Cancelar</Button>
        <Button disabled>Salvando</Button>
        <Button variant="secondary" disabled>
          Indisponível
        </Button>
      </div>
    </WorkspaceSection>
  );
}
