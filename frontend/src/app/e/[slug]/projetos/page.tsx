import { ProjetosAcessoGuard } from "@/components/operacional/ProjetosAcessoGuard";
import { ProjetosView } from "@/components/projetos/ProjetosView";

export default function ProjetosPage() {
  return (
    <ProjetosAcessoGuard>
      <ProjetosView />
    </ProjetosAcessoGuard>
  );
}
