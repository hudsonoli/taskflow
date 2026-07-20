"use client";

import { usePathname } from "next/navigation";
import { Info } from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { Breadcrumb } from "./Breadcrumb";
import { HeaderActions } from "./HeaderActions";

const scopedTitles: Record<string, string> = {
  "/configuracoes": "Configurações",
  "/configuracoes/clientes": "Clientes",
  "/configuracoes/grupos-clientes": "Grupos de Clientes",
  "/configuracoes/equipes": "Equipes",
  "/configuracoes/agencias": "Agências",
  "/configuracoes/usuarios": "Usuários",
  "/configuracoes/workflows": "Workflows",
  "/fornecedores": "Fornecedores",
};

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/tarefas": "Tarefas",
  "/projetos": "Projetos",
  "/trafego": "Central de Tráfego",
  "/clientes": "Clientes",
  "/equipe": "Equipe",
  "/relatorios": "Relatórios",
  "/conta/perfil": "Perfil",
  "/conta/notificacoes": "Notificações",
  "/conta/alterar-senha": "Alterar senha",
  ...scopedTitles,
};

function resolveTitle(pathname: string) {
  if (scopedTitles[pathname]) {
    return scopedTitles[pathname];
  }

  if (pathname.startsWith("/configuracoes/")) {
    const segment = pathname.split("/").filter(Boolean).at(-1);
    return segment
      ? segment
          .split("-")
          .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
          .join(" ")
      : "Configurações";
  }

  return titles[pathname] ?? "";
}

function shouldHideHeaderActions(pathname: string) {
  return (
    pathname === "/fornecedores" ||
    pathname === "/" ||
    pathname.startsWith("/configuracoes")
  );
}

// Descrições exibidas via tooltip ao lado do título — hoje só Clientes,
// que também dispensa o breadcrumb (título único na página, sem
// "Configurações > Clientes" duplicando contexto). Outras rotas continuam
// sem entrada aqui e mantêm o comportamento anterior inalterado.
const titleTooltips: Record<string, string> = {
  "/configuracoes/clientes": "Cadastro e gestão de clientes.",
};

// "/" (Dashboard) também dispensa o breadcrumb — mesma razão de Clientes
// (só "Dashboard" repetiria o próprio título), mas sem tooltip: o novo
// DashboardHeader já traz a saudação como conteúdo da página.
const routesWithoutBreadcrumb = new Set<string>([
  ...Object.keys(titleTooltips),
  "/",
]);

export function Header() {
  const pathname = usePathname();
  const title = resolveTitle(pathname);
  const titleTooltip = titleTooltips[pathname];

  return (
    <header className="border-b border-zinc-200 bg-[#f4f1ec] px-6 py-2">
      <div className="flex min-h-11 items-center justify-between gap-4">
        <div className="min-w-0">
          {!routesWithoutBreadcrumb.has(pathname) ? (
            <Breadcrumb pathname={pathname} />
          ) : null}

          {title ? (
            <div className="mt-0.5 flex items-center gap-1.5">
              <h1 className="text-lg font-semibold text-zinc-900">{title}</h1>

              {titleTooltip ? (
                <Tooltip content={titleTooltip}>
                  <button
                    type="button"
                    className="inline-flex h-4 w-4 items-center justify-center rounded-full text-zinc-400 hover:text-zinc-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-1"
                  >
                    <Info className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
                    <span className="sr-only">Sobre esta página</span>
                  </button>
                </Tooltip>
              ) : null}
            </div>
          ) : null}
        </div>

        {!shouldHideHeaderActions(pathname) ? <HeaderActions /> : null}
      </div>
    </header>
  );
}
