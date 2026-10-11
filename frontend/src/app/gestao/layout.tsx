import type { Metadata } from "next";
import type { ReactNode } from "react";
import { PlataformaGuard } from "@/components/plataforma/PlataformaGuard";
import { PlataformaProvider } from "@/components/plataforma/PlataformaContext";
import { PlataformaShell } from "@/components/plataforma/PlataformaShell";

// Título da aba: "Gestão | TaskFlow" (o template do layout raiz acrescenta o produto).
export const metadata: Metadata = { title: "Gestão" };

// O guard fica no LAYOUT: cobre `/gestao` e todas as rotas filhas (inclusive as futuras). A autoridade real é
// do backend; o guard só evita pedir `/gestao` a quem não é Administrador da Plataforma.
export default function PlataformaLayout({ children }: { children: ReactNode }) {
  return (
    <PlataformaGuard>
      <PlataformaProvider>
        <PlataformaShell>{children}</PlataformaShell>
      </PlataformaProvider>
    </PlataformaGuard>
  );
}
