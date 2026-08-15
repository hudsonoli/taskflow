import type { ReactNode } from "react";
import { AreaAdministrativaGuard } from "@/components/operacional/AreaAdministrativaGuard";
import { ConfiguracoesSidebarNav } from "@/components/configuracoes/ConfiguracoesSidebarNav";

// O guard fica no LAYOUT: cobre de uma vez as 14 rotas de /configuracoes/**, inclusive as que
// vierem depois. Proteger página a página deixaria a próxima desprotegida por esquecimento.
export default function ConfiguracoesLayout({ children }: { children: ReactNode }) {
  return (
    <AreaAdministrativaGuard>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-stretch lg:gap-8">
        <ConfiguracoesSidebarNav />
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </AreaAdministrativaGuard>
  );
}
