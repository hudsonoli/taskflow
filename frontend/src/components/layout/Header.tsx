"use client";

import { usePathname } from "next/navigation";
import { Breadcrumb } from "./Breadcrumb";
import { HeaderActions } from "./HeaderActions";

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
    <header className="border-b border-zinc-200 bg-[#f4f1ec] px-6 py-2">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <Breadcrumb pathname={pathname} />

          <h1 className="mt-0.5 text-lg font-semibold text-zinc-900">
            {title}
          </h1>
        </div>

        <HeaderActions />
      </div>
    </header>
  );
}
