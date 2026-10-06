"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { BRANDING_PADRAO, type Branding } from "@/lib/branding";
import { variaveisDaMarca } from "@/lib/branding-tokens";
import {
  observarSistemaEscuro,
  resolveEffectiveTheme,
  trocarPreferencia,
  type TemaPreferencia,
  type TemaVisual,
} from "@/lib/tema";

// Branding da EMPRESA (logo, cores, tema padrão) vindo do servidor + preferência PESSOAL de tema do usuário
// autenticado. O tema efetivo = resolveEffectiveTheme(empresa, usuário, dispositivo); logo e cores nunca passam
// pela preferência pessoal. Nenhuma busca por componente: a empresa vem do layout (SSR), a preferência vem do
// cookie-espelho (SSR) e é reconciliada com o banco quando a sessão carrega (`sincronizarSessao`).

// Telas públicas / de troca de senha inicial usam SEMPRE o tema da empresa (não há preferência de usuário a aplicar).
const ROTAS_TEMA_DA_EMPRESA = ["/login", "/esqueci-senha", "/redefinir-senha", "/trocar-senha-inicial"];

type BrandingContextValue = {
  branding: Branding;
  aplicarBranding: (proximo: Branding) => void;
  /** preferência pessoal atual (null = usar o padrão da empresa) */
  preferenciaTema: TemaPreferencia;
  /** tema que está de fato aplicado ao <html> */
  temaEfetivo: TemaVisual;
  /** troca imediata + persistência; se falhar, restaura o tema anterior e relança o erro */
  definirPreferenciaTema: (preferencia: TemaPreferencia) => Promise<void>;
  /** chamado pelo AppDataProvider: sessão carregada (preferência real do banco) ou encerrada (null) */
  sincronizarSessao: (sessao: { temaPreferencia: TemaPreferencia } | null) => void;
};

const BrandingContext = createContext<BrandingContextValue>({
  branding: BRANDING_PADRAO,
  aplicarBranding: () => {},
  preferenciaTema: null,
  temaEfetivo: BRANDING_PADRAO.tema,
  definirPreferenciaTema: async () => {},
  sincronizarSessao: () => {},
});

function aplicarVariaveis(branding: Branding, anteriores: string[]): string[] {
  const raiz = document.documentElement;
  for (const nome of anteriores) raiz.style.removeProperty(nome);
  const vars = variaveisDaMarca(branding.corPrimaria, branding.corSecundaria);
  for (const [nome, valor] of Object.entries(vars)) raiz.style.setProperty(nome, valor);
  return Object.keys(vars);
}

async function persistirPreferencia(preferencia: TemaPreferencia): Promise<void> {
  const resposta = await fetch("/api/auth/tema", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tema: preferencia }),
    cache: "no-store",
  });
  if (!resposta.ok) throw new Error("Não foi possível salvar o tema.");
}

export function BrandingProvider({
  inicial,
  preferenciaInicial,
  autenticadoInicial,
  children,
}: {
  inicial: Branding;
  preferenciaInicial: TemaPreferencia;
  autenticadoInicial: boolean;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const [branding, setBranding] = useState<Branding>(inicial);
  const [nomesAplicados, setNomesAplicados] = useState<string[]>(() => Object.keys(variaveisDaMarca(inicial.corPrimaria, inicial.corSecundaria)));
  const [preferencia, setPreferencia] = useState<TemaPreferencia>(preferenciaInicial);
  const [autenticado, setAutenticado] = useState(autenticadoInicial);
  const [sistemaEscuro, setSistemaEscuro] = useState(false);
  const preferenciaRef = useRef(preferencia);
  useEffect(() => {
    preferenciaRef.current = preferencia;
  }, [preferencia]);

  const aplicarBranding = useCallback(
    (proximo: Branding) => {
      setBranding(proximo);
      setNomesAplicados(aplicarVariaveis(proximo, nomesAplicados));
    },
    [nomesAplicados],
  );

  const usaPreferencia = autenticado && !ROTAS_TEMA_DA_EMPRESA.includes(pathname);

  // "Sistema": acompanha o dispositivo em tempo de execução (listener do matchMedia, sem polling, removido no
  // cleanup). Só existe enquanto a preferência efetiva for "sistema".
  const acompanharSistema = usaPreferencia && preferencia === "sistema";
  useEffect(() => {
    if (!acompanharSistema) return;
    return observarSistemaEscuro(window.matchMedia("(prefers-color-scheme: dark)"), setSistemaEscuro);
  }, [acompanharSistema]);

  const temaEfetivo = resolveEffectiveTheme({
    temaEmpresa: branding.tema,
    preferencia,
    sistemaEscuro,
    autenticado: usaPreferencia,
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", temaEfetivo);
  }, [temaEfetivo]);

  const definirPreferenciaTema = useCallback(
    (nova: TemaPreferencia) =>
      trocarPreferencia({
        anterior: preferenciaRef.current,
        nova,
        aplicar: setPreferencia,
        persistir: persistirPreferencia,
      }),
    [],
  );

  const sincronizarSessao = useCallback((sessao: { temaPreferencia: TemaPreferencia } | null) => {
    setAutenticado(sessao !== null);
    // logout: o override do usuário anterior nunca fica na tela nem vale para o próximo login
    setPreferencia(sessao?.temaPreferencia ?? null);
  }, []);

  const valor = useMemo(
    () => ({ branding, aplicarBranding, preferenciaTema: preferencia, temaEfetivo, definirPreferenciaTema, sincronizarSessao }),
    [branding, aplicarBranding, preferencia, temaEfetivo, definirPreferenciaTema, sincronizarSessao],
  );
  return <BrandingContext.Provider value={valor}>{children}</BrandingContext.Provider>;
}

export function useBranding() {
  return useContext(BrandingContext);
}
