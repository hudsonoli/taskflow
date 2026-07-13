"use client";

import { usePathname } from "next/navigation";
import { Breadcrumb } from "./Breadcrumb";
import { HeaderActions } from "./HeaderActions";
import { HeaderSearch } from "./HeaderSearch";

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/tarefas": "Tarefas",
  "/projetos": "Projetos",
  "/trafego": "Central de Tráfego",
  "/clientes": "Clientes",
  "/fornecedores": "Fornecedores",
  "/equipe": "Equipe",
  "/relatorios": "Relatórios",
  "/configuracoes": "Configurações",
  "/conta/perfil": "Perfil",
  "/conta/notificacoes": "Notificações",
  "/conta/alterar-senha": "Alterar senha",
};

export function Header() {
  const pathname = usePathname();
  const title = titles[pathname] ?? "TaskFloww";

  return (
    <header className="border-b border-zinc-200 bg-[#f4f1ec] px-8 py-5">
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0">
          <Breadcrumb pathname={pathname} />

          <h1 className="mt-2 text-2xl font-semibold text-zinc-900">
            {title}
          </h1>

          <p className="mt-1 text-sm text-zinc-500">
            Plataforma operacional para agências
          </p>
        </div>

        <div className="flex flex-col items-end gap-3">
          <HeaderSearch />
          <HeaderActions />
        </div>
      </div>
    </header>
  );
}
