import { AreaAdministrativaGuard } from "@/components/operacional/AreaAdministrativaGuard";
import { ProjetosView } from "@/components/projetos/ProjetosView";

export default function ProjetosPage() {
  return (
    <AreaAdministrativaGuard>
      <ProjetosView />
    </AreaAdministrativaGuard>
  );
}
