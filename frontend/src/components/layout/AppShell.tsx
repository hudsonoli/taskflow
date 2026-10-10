"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { TopNav } from "@/components/layout/TopNav";
import { useAppData } from "@/lib/AppDataContext";
import { useBranding } from "@/lib/BrandingContext";
import { ehRotaDeAprovacaoExterna, ehRotaDeLogin, ehRotaDeRecuperacaoDeSenha } from "@/lib/tenant";

// Login (legado `/login` ou `/e/<slug>/login`) e recuperação de senha (idem) são telas públicas "nuas". A recuperação
// NÃO redireciona quem já tem sessão nem quem precisa trocar a senha — o link do e-mail (com o token no fragmento) tem
// de chegar até a tela. Quem não tem sessão volta ao login DA EMPRESA (`loginHref`), não ao da empresa padrão.
const ROTA_TROCA_SENHA = "/trocar-senha-inicial";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { sessaoCarregando, autenticado, mustChangePassword } = useAppData();
  const { loginHref } = useBranding();

  const rotaPublica = ehRotaDeLogin(pathname);
  const rotaTrocaSenha = pathname === ROTA_TROCA_SENHA;
  const rotaRecuperacaoSenha = ehRotaDeRecuperacaoDeSenha(pathname);
  // Portal Externo de Aprovação (Fase 9B): tela pública nua para o CLIENTE. Sem TopNav/sidebar, sem redirecionar (nem para o login, nem para
  // /meu-dia quando o navegador por acaso tem sessão): a sessão do tenant é simplesmente ignorada aqui.
  const rotaPortalExterno = ehRotaDeAprovacaoExterna(pathname);

  useEffect(() => {
    if (sessaoCarregando || rotaRecuperacaoSenha || rotaPortalExterno) return;

    if (!autenticado && !rotaPublica) {
      router.replace(loginHref);
      return;
    }
    if (autenticado && mustChangePassword && !rotaTrocaSenha) {
      router.replace(ROTA_TROCA_SENHA);
      return;
    }
    if (autenticado && !mustChangePassword && (rotaPublica || rotaTrocaSenha)) {
      router.replace("/meu-dia");
    }
  }, [sessaoCarregando, autenticado, mustChangePassword, rotaPublica, rotaTrocaSenha, rotaRecuperacaoSenha, rotaPortalExterno, router, loginHref]);

  // Login, recuperação, troca de senha inicial e Portal de Aprovação são telas "nuas" — sem TopNav, sem exigir sessão.
  if (rotaPublica || rotaTrocaSenha || rotaRecuperacaoSenha || rotaPortalExterno) {
    return <>{children}</>;
  }

  if (sessaoCarregando || !autenticado || mustChangePassword) {
    // Enquanto carrega ou durante o redirect (useEffect acima), não renderiza a área
    // autenticada — evita um flash do conteúdo protegido antes do guard agir.
    return (
      <div className="flex h-screen items-center justify-center bg-app">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-indigo-500 dark:border-zinc-700" />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-app">
      <TopNav />
      <main className="min-w-0 flex-1 overflow-y-auto px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}
