import type { Metadata } from "next";
import { AprovacaoPublicaView } from "@/components/aprovacao/AprovacaoPublicaView";

// Portal Externo de Aprovação (Fase 9B): página PÚBLICA do cliente. O link (`/e/<slug>/aprovacao#token=…`) carrega o token no FRAGMENTO, que o navegador não envia
// ao servidor. Nada de indexação e nada de Referer.
export const metadata: Metadata = {
  title: "Aprovação",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function AprovacaoPage() {
  return <AprovacaoPublicaView />;
}
