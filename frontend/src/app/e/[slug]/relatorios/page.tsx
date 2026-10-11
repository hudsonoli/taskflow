import { AreaAdministrativaGuard } from "@/components/operacional/AreaAdministrativaGuard";
import { RelatoriosView } from "@/components/relatorios/RelatoriosView";

export default function RelatoriosPage() {
  return (
    <AreaAdministrativaGuard>
      <RelatoriosView />
    </AreaAdministrativaGuard>
  );
}
