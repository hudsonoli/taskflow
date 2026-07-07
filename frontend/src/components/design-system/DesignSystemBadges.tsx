import { Badge } from "@/components/ui/Badge";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";

export function DesignSystemBadges() {
  return (
    <WorkspaceSection
      title="Badges"
      description="Estados compactos para listagens, detalhes e painéis."
    >
      <div className="flex flex-wrap gap-3">
        <Badge>Ativo</Badge>
        <Badge>Inativo</Badge>
        <Badge>Em revisão</Badge>
        <Badge>SLA 4h</Badge>
        <Badge>Alta prioridade</Badge>
      </div>
    </WorkspaceSection>
  );
}
