"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { SessaoOutraEmpresaView } from "@/components/layout/SessaoOutraEmpresaView";
import { TopNav } from "@/components/layout/TopNav";
import { useAppData } from "@/lib/AppDataContext";
import { useBranding } from "@/lib/BrandingContext";
import {
  caminhoDoTenant,
  ehRotaDaPlataforma,
  ehRotaDeAprovacaoExterna,
  ehRotaDeLogin,
  ehRotaDeRecuperacaoDeSenha,
  ehRotaDeTrocaDeSenhaInicial,
  hrefLogin,
  slugDaRota,
} from "@/lib/tenant";

// Fase 9D — catálogo EXPLÍCITO de telas sem sessão (todas por slug): login, recuperação de senha e Portal Externo de Aprovação; a troca da senha
// inicial é "nua" mas exige sessão. Nenhum outro `/e/<slug>/...` é público. Fora de `/e/<slug>` e de `/plataforma` (domínio nu, `/login`, `/tarefas`…)
// não há empresa: a página (404 neutro) é renderizada como está, sem sessão, sem redirecionar e sem escolher empresa. A recuperação NÃO
// redireciona quem já tem sessão — o link do e-mail (token no fragmento) tem de chegar até a tela.
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { sessaoCarregando, autenticado, mustChangePassword, logout } = useAppData();
  const { sessaoSlug } = useBranding();
  const [saindo, setSaindo] = useState(false);

  const slugUrl = slugDaRota(pathname);
  const plataforma = ehRotaDaPlataforma(pathname);
  const rotaLogin = ehRotaDeLogin(pathname);
  const rotaTrocaSenha = ehRotaDeTrocaDeSenhaInicial(pathname);
  const rotaRecuperacaoSenha = ehRotaDeRecuperacaoDeSenha(pathname);
  // Portal Externo (Fase 9B): sem TopNav, sem redirecionar e sem usar a sessão do tenant (mesmo que o navegador tenha `tf_session`).
  const rotaPortalExterno = ehRotaDeAprovacaoExterna(pathname);
  const semEmpresa = slugUrl === null && !plataforma;

  // Sessão de OUTRA empresa que a da URL: nunca troca de empresa pela URL e nunca renderiza a área da empresa da URL.
  const sessaoDeOutraEmpresa = slugUrl !== null && autenticado && sessaoSlug !== null && sessaoSlug !== slugUrl;
  const exigeSessao = !rotaLogin && !rotaRecuperacaoSenha && !rotaPortalExterno;

  useEffect(() => {
    if (semEmpresa || sessaoCarregando || rotaRecuperacaoSenha || rotaPortalExterno || sessaoDeOutraEmpresa) return;

    if (!autenticado && exigeSessao) {
      // Sem slug (ex.: `/plataforma` aberto direto, sem sessão) não há login para onde mandar: a tela abaixo explica.
      if (slugUrl) router.replace(hrefLogin(slugUrl));
      return;
    }
    if (slugUrl === null) return;
    if (autenticado && mustChangePassword && !rotaTrocaSenha) {
      router.replace(caminhoDoTenant(slugUrl, "trocar-senha-inicial"));
      return;
    }
    if (autenticado && !mustChangePassword && (rotaLogin || rotaTrocaSenha)) {
      router.replace(caminhoDoTenant(slugUrl, "meu-dia"));
    }
  }, [semEmpresa, sessaoCarregando, autenticado, mustChangePassword, rotaLogin, rotaTrocaSenha, rotaRecuperacaoSenha, rotaPortalExterno, exigeSessao, sessaoDeOutraEmpresa, slugUrl, router]);

  if (semEmpresa) return <>{children}</>;

  async function sair() {
    setSaindo(true);
    try {
      await logout();
    } finally {
      setSaindo(false);
    }
    router.replace(slugUrl ? hrefLogin(slugUrl) : "/");
  }

  if (sessaoDeOutraEmpresa && sessaoSlug && exigeSessao) {
    return <SessaoOutraEmpresaView slugDaSessao={sessaoSlug} onSair={() => void sair()} saindo={saindo} />;
  }

  // Login, recuperação, troca de senha inicial e Portal de Aprovação são telas "nuas" — sem TopNav.
  if (rotaLogin || rotaTrocaSenha || rotaRecuperacaoSenha || rotaPortalExterno) {
    return <>{children}</>;
  }

  if (!sessaoCarregando && !autenticado && slugUrl === null) {
    // `/plataforma` sem sessão: não há empresa para devolver ao login. Mensagem única, sem nomear nem listar empresas.
    return (
      <div className="flex h-screen items-center justify-center bg-app px-4">
        <p className="max-w-sm text-center text-sm text-fg-muted">Acesso restrito. Entre pelo endereço de acesso da sua empresa.</p>
      </div>
    );
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
