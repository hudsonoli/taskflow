import { DesignSystemBadges } from "@/components/design-system/DesignSystemBadges";
import { DesignSystemButtons } from "@/components/design-system/DesignSystemButtons";
import { DesignSystemCards } from "@/components/design-system/DesignSystemCards";
import { DesignSystemColors } from "@/components/design-system/DesignSystemColors";
import { DesignSystemInputs } from "@/components/design-system/DesignSystemInputs";
import { DesignSystemTypography } from "@/components/design-system/DesignSystemTypography";
import { DesignSystemWorkspace } from "@/components/design-system/DesignSystemWorkspace";
import { PageHeader } from "@/components/ui/PageHeader";
import { WorkspacePage } from "@/components/workspace/WorkspacePage";

export default function DesignSystemPage() {
  return (
    <WorkspacePage>
      <PageHeader
        title="Design System"
        description="Validação interna dos componentes reutilizáveis do TaskFloww."
      />

      <DesignSystemTypography />
      <DesignSystemColors />
      <DesignSystemButtons />
      <DesignSystemInputs />
      <DesignSystemBadges />
      <DesignSystemCards />
      <DesignSystemWorkspace />
    </WorkspacePage>
  );
}
