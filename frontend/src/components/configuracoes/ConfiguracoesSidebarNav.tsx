"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { gruposConfiguracao } from "@/lib/configuracoes-menu";
import { useAppData } from "@/lib/AppDataContext";
import { podeAcessarAcessos } from "@/lib/escopo-operacional";

export function ConfiguracoesSidebarNav() {
  const pathname = usePathname();
  const { usuarioAtual } = useAppData();
  const acessoAdministrativoLiberado = usuarioAtual ? podeAcessarAcessos(usuarioAtual) : false;

  const grupos = gruposConfiguracao
    .map((grupo) => ({
      ...grupo,
      itens: grupo.itens.filter((item) => !item.apenasAdministrativo || acessoAdministrativoLiberado),
    }))
    .filter((grupo) => grupo.itens.length > 0);

  return (
    <aside className="w-full shrink-0 lg:w-56">
      <nav className="flex flex-col gap-5 lg:sticky lg:top-6">
        {grupos.map((grupo) => (
          <div key={grupo.titulo}>
            <p className="mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
              {grupo.titulo}
            </p>
            <div className="flex flex-col gap-0.5">
              {grupo.itens.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;

                const content = (
                  <span
                    className={clsx(
                      "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-indigo-50 font-semibold text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400"
                        : item.available
                          ? "text-zinc-600 hover:bg-zinc-100/70 dark:text-zinc-300 dark:hover:bg-zinc-900"
                          : "cursor-not-allowed text-zinc-400 dark:text-zinc-600",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="truncate">{item.label}</span>
                    {!item.available && <span className="ml-auto shrink-0 text-[10px] text-zinc-400">em breve</span>}
                  </span>
                );

                return item.available ? (
                  <Link key={item.label} href={item.href}>
                    {content}
                  </Link>
                ) : (
                  <span key={item.label}>{content}</span>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
