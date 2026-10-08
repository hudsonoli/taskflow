import { COR_PRIMARIA_PADRAO, COR_SECUNDARIA_PADRAO, hexValido } from "@/lib/branding-tokens";
import type { Branding } from "@/types/personalizacao";

export type { Branding, TemaVisual } from "@/types/personalizacao";

// Branding da Empresa no frontend: tipo, padrões e normalização (defensiva — a resposta do backend nunca é
// confiada às cegas, porque as cores viram CSS inline no <html>).

export const BRANDING_PADRAO: Branding = {
  corPrimaria: COR_PRIMARIA_PADRAO,
  corSecundaria: COR_SECUNDARIA_PADRAO,
  tema: "claro",
  logoDisponivel: false,
  logoVersao: null,
  padrao: true,
};

export const URL_LOGO = "/api/branding/logo";

export function normalizarBranding(bruto: unknown): Branding {
  if (!bruto || typeof bruto !== "object") return BRANDING_PADRAO;
  const b = bruto as Record<string, unknown>;
  const primaria = typeof b.corPrimaria === "string" && hexValido(b.corPrimaria) ? b.corPrimaria.toLowerCase() : null;
  const secundaria = typeof b.corSecundaria === "string" && hexValido(b.corSecundaria) ? b.corSecundaria.toLowerCase() : null;
  if (!primaria || !secundaria) return BRANDING_PADRAO;
  const versao = typeof b.logoVersao === "string" && /^[0-9a-f]{8,32}$/.test(b.logoVersao) ? b.logoVersao : null;
  const logoDisponivel = b.logoDisponivel === true && versao !== null;
  return {
    corPrimaria: primaria,
    corSecundaria: secundaria,
    tema: b.tema === "escuro" ? "escuro" : "claro",
    logoDisponivel,
    logoVersao: logoDisponivel ? versao : null,
    padrao: b.padrao === true,
  };
}

/** src do <img> do logo (com a versão: cache imutável no navegador e troca instantânea ao enviar outro). */
export function srcDoLogo(branding: Branding): string | null {
  if (!branding.logoDisponivel || !branding.logoVersao) return null;
  // Com slug, o logo é o DAQUELA empresa (rota pública por slug); sem slug, o da empresa padrão (acesso legado).
  return branding.slug ? `${URL_LOGO}?slug=${encodeURIComponent(branding.slug)}&v=${branding.logoVersao}` : `${URL_LOGO}?v=${branding.logoVersao}`;
}
