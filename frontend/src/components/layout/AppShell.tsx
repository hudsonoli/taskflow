"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { TopNav } from "@/components/layout/TopNav";
import { useAppData } from "@/lib/AppDataContext";

const ROTAS_PUBLICAS = ["/login"];
const ROTA_TROCA_SENHA = "/trocar-senha-inicial";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { sessaoCarregando, autenticado, mustChangePassword } = useAppData();

  const rotaPublica = ROTAS_PUBLICAS.includes(pathname);
  const rotaTrocaSenha = pathname === ROTA_TROCA_SENHA;

  useEffect(() => {
    if (sessaoCarregando) return;

    if (!autenticado && !rotaPublica) {
      router.replace("/login");
      return;
    }
    if (autenticado && mustChangePassword && !rotaTrocaSenha) {
      router.replace(ROTA_TROCA_SENHA);
      return;
    }
    if (autenticado && !mustChangePassword && (rotaPublica || rotaTrocaSenha)) {
      router.replace("/meu-dia");
    }
  }, [sessaoCarregando, autenticado, mustChangePassword, rotaPublica, rotaTrocaSenha, router]);

  // Login e troca de senha inicial são telas "nuas" — sem TopNav, sem exigir sessão.
  if (rotaPublica || rotaTrocaSenha) {
    return <>{children}</>;
  }

  if (sessaoCarregando || !autenticado || mustChangePassword) {
    // Enquanto carrega ou durante o redirect (useEffect acima), não renderiza a área
    // autenticada — evita um flash do conteúdo protegido antes do guard agir.
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-indigo-500 dark:border-zinc-700" />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-zinc-50 dark:bg-zinc-950">
      <TopNav />
      <main className="min-w-0 flex-1 overflow-y-auto px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}
