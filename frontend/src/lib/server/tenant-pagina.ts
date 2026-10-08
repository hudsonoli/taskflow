import "server-only";
import { obterBrandingPublico } from "@/lib/server/branding";
import { normalizarSlug } from "@/lib/tenant";

/** Empresa de uma rota pública `/e/<slug>/...`: `{ slug, nome }` se o slug é válido e a empresa existe e está ativa;
 * `null` em qualquer outro caso (malformado, reservado, inexistente, inativa) — sem diferenciar. Reaproveita o cache
 * por tenant do layout, então não há segunda ida ao backend na mesma renderização. */
export async function empresaDisponivelDaRota(slugBruto: string): Promise<{ slug: string; nome: string | null } | null> {
  const slug = normalizarSlug(slugBruto);
  if (!slug) return null;
  const publico = await obterBrandingPublico({ tipo: "slug", slug });
  return publico.disponivel ? { slug, nome: publico.nome } : null;
}
