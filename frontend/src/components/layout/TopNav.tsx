"use client";

import { useState } from "react";
import {
  Activity,
  BarChart3,
  Building2,
  CalendarClock,
  Headset,
  Kanban,
  ListChecks,
  Menu,
  Settings,
  Sparkles,
  Sun,
  X,
} from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import {
  podeAcessarAreaAdministrativa,
  podeAcessarCentralTrafego,
  podeAcessarMeuDepartamento,
  podeAcessarMinhasDemandas,
} from "@/lib/escopo-operacional";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { ProfileMenu } from "@/components/layout/ProfileMenu";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";
import type { Usuario } from "@/types/usuario";

// Disponível a qualquer autenticado — o que cada um enxerga dentro delas é decidido pelo
// escopo no servidor, não pela navegação.
const NAV_ITEMS_BASE = [
  { label: "Meu dia", href: "/meu-dia", icon: Sun },
  { label: "Tarefas", href: "/tarefas", icon: ListChecks },
  { label: "Pauta", href: "/pauta", icon: CalendarClock },
];

/**
 * O menu **espelha** a autorização real; não a substitui.
 *
 * Esconder um item continua sendo UX — a URL direta segue acessível, e é por isso que cada
 * tela mantém seu gate e a API responde 403/404 por conta própria. O que mudou é o inverso:
 * antes o menu oferecia caminhos que a API recusa (Projetos, Relatórios e Configurações para
 * operador), transformando "Acesso negado" em navegação normal. Um item que sempre falha não
 * é informação, é ruído.
 *
 * `AcessoNegado` fica como proteção de URL direta, sessão desatualizada ou tentativa externa.
 */
function buildNavItems(usuarioAtual: Usuario | undefined, departamentos: DepartamentoDiretorioItem[]) {
  const items = [...NAV_ITEMS_BASE];
  if (!usuarioAtual) return items;

  if (podeAcessarMeuDepartamento(usuarioAtual, departamentos)) {
    items.splice(1, 0, { label: "Meu Departamento", href: "/meu-departamento", icon: Building2 });
  }
  if (podeAcessarMinhasDemandas(usuarioAtual, departamentos)) {
    items.splice(1, 0, { label: "Minhas Demandas", href: "/minhas-demandas", icon: Headset });
  }
  if (podeAcessarCentralTrafego(usuarioAtual)) {
    items.push({ label: "Tráfego", href: "/trafego", icon: Activity });
  }
  // Projetos, Relatórios e Configurações dependem de rotas que devolvem 403 para operador
  // (`/projetos`, `/clientes`, `/usuarios`, …). Enquanto for assim, não entram no menu.
  if (podeAcessarAreaAdministrativa(usuarioAtual)) {
    items.push(
      { label: "Projetos", href: "/projetos", icon: Kanban },
      { label: "Relatórios", href: "/relatorios", icon: BarChart3 },
      { label: "Configurações", href: "/configuracoes", icon: Settings },
    );
  }
  return items;
}

function isItemActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function TopNav() {
  const pathname = usePathname();
  const { usuarioAtual } = useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  const [mobileOpen, setMobileOpen] = useState(false);
  const navItems = buildNavItems(usuarioAtual, departamentos);

  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/70 backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-950/70">
      <div className="flex items-center gap-3 px-4 py-3 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30">
            <Sparkles size={18} />
          </div>
          <span className="hidden text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 sm:inline">
            Taskfloww
          </span>
        </Link>

        <nav className="hidden flex-1 items-center justify-center gap-1.5 overflow-x-auto md:flex">
          {navItems.map((item) => {
            const isActive = isItemActive(pathname, item.href);
            return (
              <Link
                key={item.label}
                href={item.href}
                className={clsx(
                  "relative flex shrink-0 items-center gap-2 rounded-full px-3.5 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "text-indigo-600 dark:text-indigo-400"
                    : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100",
                )}
              >
                {isActive && (
                  <motion.span
                    layoutId="topnav-active"
                    className="absolute inset-0 rounded-full bg-indigo-50 dark:bg-indigo-500/10"
                    transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  />
                )}
                <item.icon size={21} className="relative z-10" />
                {isActive && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: "auto" }}
                    transition={{ duration: 0.2 }}
                    className="relative z-10 overflow-hidden whitespace-nowrap"
                  >
                    {item.label}
                  </motion.span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <NotificationBell />
          <ProfileMenu />

          <button
            type="button"
            onClick={() => setMobileOpen((current) => !current)}
            aria-label={mobileOpen ? "Fechar menu" : "Abrir menu"}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 text-zinc-500 transition-colors hover:text-zinc-900 md:hidden dark:border-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-100"
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="flex flex-col gap-1 border-t border-zinc-100 px-3 py-3 md:hidden dark:border-zinc-800">
          {navItems.map((item) => {
            const isActive = isItemActive(pathname, item.href);
            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={clsx(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400"
                    : "text-zinc-600 hover:bg-zinc-50 dark:text-zinc-300 dark:hover:bg-zinc-900",
                )}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
