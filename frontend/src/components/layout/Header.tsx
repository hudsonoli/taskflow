"use client";

import { usePathname } from "next/navigation";
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
  return pathname === "/fornecedores" || pathname.startsWith("/configuracoes");
}

export function Header() {
  const pathname = usePathname();
  const title = resolveTitle(pathname);

  return (
    <header className="border-b border-zinc-200 bg-[#f4f1ec] px-6 py-2">
      <div className="flex min-h-11 items-center justify-between gap-4">
        <div className="min-w-0">
          <Breadcrumb pathname={pathname} />

          {title ? (
            <h1 className="mt-0.5 text-lg font-semibold text-zinc-900">
              {title}
            </h1>
          ) : null}
        </div>

        {!shouldHideHeaderActions(pathname) ? <HeaderActions /> : null}
      </div>
    </header>
  );
}
