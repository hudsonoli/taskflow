"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  BookUser,
  FolderKanban,
  LayoutDashboard,
  ListTodo,
  RadioTower,
  Settings,
  Truck,
} from "lucide-react";
import { UserMenu } from "./UserMenu";

const menuItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Tarefas", href: "/tarefas", icon: ListTodo },
  { label: "Projetos", href: "/projetos", icon: FolderKanban },
  { label: "Tráfego", href: "/trafego", icon: RadioTower },
  { label: "Agenda", href: "/agenda", icon: BookUser },
  { label: "Fornecedores", href: "/fornecedores", icon: Truck },
  { label: "Relatórios", href: "/relatorios", icon: BarChart3 },
  { label: "Configurações", href: "/configuracoes", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 flex h-screen w-20 shrink-0 flex-col border-r border-zinc-200 bg-white px-2 py-6">
      <div className="mb-10 flex justify-center">
        <div
          className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-900 text-base font-bold text-white"
          title="TaskFloww"
          aria-label="TaskFloww"
        >
          T
        </div>
      </div>

      <nav className="flex flex-1 flex-col items-center gap-2">
        {menuItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              aria-label={item.label}
              className={`group relative flex h-12 w-12 items-center justify-center rounded-2xl transition ${
                active
                  ? "bg-zinc-900 text-white ring-2 ring-zinc-300"
                  : "text-zinc-600 hover:bg-zinc-100"
              }`}
            >
              <div className="relative">
                <Icon className="h-5 w-5" strokeWidth={2} aria-hidden="true" />
                {/* Badge futuro */}
              </div>

              <span className="pointer-events-none absolute left-full z-50 ml-3 min-w-max whitespace-nowrap rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white opacity-0 translate-x-2 transition-all shadow-lg group-hover:opacity-100 group-hover:translate-x-0">
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

      <UserMenu />
    </aside>
  );
}
