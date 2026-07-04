"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const menuItems = [
  { label: "Dashboard", href: "/" },
  { label: "Tarefas", href: "/tarefas" },
  { label: "Projetos", href: "/projetos" },
  { label: "Clientes", href: "/clientes" },
  { label: "Equipe", href: "/equipe" },
  { label: "Relatórios", href: "/relatorios" },
  { label: "Configurações", href: "/configuracoes" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-72 border-r border-zinc-200 bg-white px-5 py-6">
      <div className="mb-10">
        <div className="text-2xl font-bold tracking-tight">
          TaskFloww
        </div>

        <div className="mt-1 text-sm text-zinc-500">
          Shell Boxx v2
        </div>
      </div>

      <nav className="space-y-1">
        {menuItems.map((item) => {
          const active = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-2xl px-4 py-3 text-sm font-medium transition ${
                active
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-600 hover:bg-zinc-100"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
