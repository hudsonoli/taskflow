import { redirect } from "next/navigation";
import { hrefLogin, normalizarSlug } from "@/lib/tenant";

// `/e/<slug>` sozinho leva à tela de login da empresa (slug inválido cai no acesso padrão, que explica o que fazer).
export default async function EmpresaRaizPage({ params }: { params: Promise<{ slug: string }> }) {
  redirect(hrefLogin(normalizarSlug((await params).slug)));
}
