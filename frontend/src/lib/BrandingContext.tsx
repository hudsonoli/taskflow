"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { BRANDING_PADRAO, type Branding } from "@/lib/branding";
import { variaveisDaMarca } from "@/lib/branding-tokens";

// Branding vindo do servidor (layout raiz) — nenhuma busca por componente. A tela Personalizar chama
// `aplicarBranding` com a resposta da API: o app inteiro muda na hora, sem recarregar.

type BrandingContextValue = {
  branding: Branding;
  aplicarBranding: (proximo: Branding) => void;
};

const BrandingContext = createContext<BrandingContextValue>({ branding: BRANDING_PADRAO, aplicarBranding: () => {} });

function aplicarNoDocumento(branding: Branding, anteriores: string[]): string[] {
  const raiz = document.documentElement;
  for (const nome of anteriores) raiz.style.removeProperty(nome);
  const vars = variaveisDaMarca(branding.corPrimaria, branding.corSecundaria);
  for (const [nome, valor] of Object.entries(vars)) raiz.style.setProperty(nome, valor);
  raiz.setAttribute("data-theme", branding.tema);
  return Object.keys(vars);
}

export function BrandingProvider({ inicial, children }: { inicial: Branding; children: ReactNode }) {
  const [branding, setBranding] = useState<Branding>(inicial);
  const [nomesAplicados, setNomesAplicados] = useState<string[]>(() => Object.keys(variaveisDaMarca(inicial.corPrimaria, inicial.corSecundaria)));

  const aplicarBranding = useCallback(
    (proximo: Branding) => {
      setBranding(proximo);
      setNomesAplicados(aplicarNoDocumento(proximo, nomesAplicados));
    },
    [nomesAplicados],
  );

  const valor = useMemo(() => ({ branding, aplicarBranding }), [branding, aplicarBranding]);
  return <BrandingContext.Provider value={valor}>{children}</BrandingContext.Provider>;
}

export function useBranding() {
  return useContext(BrandingContext);
}
