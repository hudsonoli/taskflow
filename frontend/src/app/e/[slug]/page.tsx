import { notFound, redirect } from "next/navigation";
import { caminhoDoTenant, normalizarSlug } from "@/lib/tenant";

// `/e/<slug>` sozinho entra na home da empresa; quem não tem sessão da PRÓPRIA empresa é levado pelo AppShell a `/e/<slug>/login`.
// Slug malformado/reservado não vira empresa nenhuma: 404 neutro (nunca um destino "padrão").
export default async function EmpresaRaizPage({ params }: { params: Promise<{ slug: string }> }) {
  const slug = normalizarSlug((await params).slug);
  if (!slug) notFound();
  redirect(caminhoDoTenant(slug, "meu-dia"));
}
