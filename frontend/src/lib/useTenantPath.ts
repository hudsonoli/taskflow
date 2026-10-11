"use client";

import { useCallback } from "react";
import { useBranding } from "@/lib/BrandingContext";
import { caminhoDoTenant } from "@/lib/tenant";

/**
 * Monta caminhos internos CANÔNICOS da empresa atual (`/e/<slug>/<caminho>`). O slug é o da URL (ou, em `/plataforma`, o da sessão);
 * sem slug conhecido devolve `/` (404 neutro) — nunca uma empresa padrão. Toda navegação interna de tenant passa por aqui.
 */
export function useTenantPath(): (caminho: string) => string {
  const { tenantSlug } = useBranding();
  return useCallback((caminho: string) => caminhoDoTenant(tenantSlug, caminho), [tenantSlug]);
}
