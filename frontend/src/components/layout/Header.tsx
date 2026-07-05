"use client";

import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/tarefas": "Tarefas",
  "/projetos": "Projetos",
  "/clientes": "Clientes",
  "/fornecedores": "Fornecedores",
  "/equipe": "Equipe",
  "/relatorios": "Relatórios",
  "/configuracoes": "Configurações",
};

export function Header() {
  const pathname = usePathname();

  return (
    <header className="flex h-20 items-center justify-between border-b border-zinc-200 bg-[#f4f1ec] px-8">
      <div>
        <h1 className="text-2xl font-semibold">
          {titles[pathname] ?? "TaskFloww"}
        </h1>

        <p className="text-sm text-zinc-500">
          Plataforma operacional para agências
        </p>
      </div>

      <div className="rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-600 shadow-sm">
        Fase 2.2
      </div>
    </header>
  );
}
