import type { ReactNode } from "react";
import { PlataformaGuard } from "@/components/plataforma/PlataformaGuard";
import { PlataformaProvider } from "@/components/plataforma/PlataformaContext";
import { PlataformaShell } from "@/components/plataforma/PlataformaShell";

// O guard fica no LAYOUT: cobre `/plataforma` e todas as rotas filhas (inclusive as futuras). A autoridade real é
// do backend; o guard só evita pedir `/plataforma/*` a quem não é Administrador da Plataforma.
export default function PlataformaLayout({ children }: { children: ReactNode }) {
  return (
    <PlataformaGuard>
      <PlataformaProvider>
        <PlataformaShell>{children}</PlataformaShell>
      </PlataformaProvider>
    </PlataformaGuard>
  );
}
