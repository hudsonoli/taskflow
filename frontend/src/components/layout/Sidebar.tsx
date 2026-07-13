"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  BarChart3,
  BookUser,
  Building2,
  ChevronDown,
  Database,
  FolderKanban,
  GitBranch,
  LayoutDashboard,
  ListTodo,
  PanelLeftClose,
  PanelLeftOpen,
  RadioTower,
  Settings,
  Truck,
  Users,
} from "lucide-react";
import { HeaderSearch } from "./HeaderSearch";
import { QuickCreateMenu } from "./QuickCreateMenu";
import { useSidebar } from "./SidebarContext";
import { UserMenu } from "./UserMenu";

type SidebarItem = {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
};

const principalItems: SidebarItem[] = [
  { label: "Dashboard do Usuário", href: "/", icon: LayoutDashboard },
  { label: "Tarefas", href: "/tarefas", icon: ListTodo },
  { label: "Projetos", href: "/projetos", icon: FolderKanban },
  { label: "Agenda", href: "/agenda", icon: BookUser },
];

const operacaoItems: SidebarItem[] = [
  { label: "Tráfego", href: "/trafego", icon: RadioTower },
  { label: "Relatórios", href: "/relatorios", icon: BarChart3 },
];

const cadastroItems: SidebarItem[] = [
  { label: "Clientes", href: "/configuracoes/clientes", icon: Building2 },
  { label: "Fornecedores", href: "/fornecedores", icon: Truck },
  { label: "Equipes", href: "/configuracoes/equipes", icon: Users },
  { label: "Workflow", href: "/configuracoes/workflows", icon: GitBranch },
];

const administracaoItems: SidebarItem[] = [
  { label: "Configurações", href: "/configuracoes", icon: Settings },
];

function isItemActive(pathname: string, href: string) {
  return pathname === href;
}

function SidebarLink({
  item,
  isCollapsed,
  active,
  nested = false,
}: {
  item: SidebarItem;
  isCollapsed: boolean;
  active: boolean;
  nested?: boolean;
}) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      title={isCollapsed ? item.label : undefined}
      aria-label={item.label}
      className={`group relative flex items-center rounded-lg text-[12px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 ${
        isCollapsed
          ? "h-8 w-8 justify-center"
          : `h-8 w-full gap-2 px-2.5 ${nested ? "pl-7" : ""}`
      } ${
        active
          ? "bg-blue-50 text-blue-700"
          : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
      }`}
    >
      {active ? (
        <span
          className={`absolute left-0 rounded-r-full bg-blue-600 ${
            isCollapsed ? "h-4 w-0.5" : "h-4 w-1"
          }`}
          aria-hidden="true"
        />
      ) : null}

      <Icon className="h-4 w-4 shrink-0" strokeWidth={2} aria-hidden="true" />

      {!isCollapsed ? (
        <span className="min-w-0 flex-1 truncate">{item.label}</span>
      ) : null}



    </Link>
  );
}

function SectionTitle({ title }: { title: string }) {
  return (
    <p className="mb-1 px-2.5 text-[9px] font-semibold uppercase tracking-[0.12em] text-zinc-400">
      {title}
    </p>
  );
}

function CollapsedSeparator() {
  return (
    <div className="my-1 flex w-full max-w-full justify-center overflow-x-hidden box-border">
      <div className="h-px w-8 max-w-full bg-zinc-100" aria-hidden="true" />
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { isCollapsed, toggleSidebar } = useSidebar();
  const cadastrosActive = cadastroItems.some((item) =>
    isItemActive(pathname, item.href),
  );
  const [cadastrosOpen, setCadastrosOpen] = useState(false);
  const cadastrosExpanded = cadastrosOpen || cadastrosActive;

  function handleCadastrosClick() {
    if (isCollapsed) {
      toggleSidebar();
      setCadastrosOpen(true);
      return;
    }

    setCadastrosOpen((value) => !value);
  }

  return (
    <aside
      className={`sticky top-0 relative flex h-screen shrink-0 flex-col overflow-visible border-r border-zinc-200 bg-white py-2.5 shadow-sm transition-[width] duration-200 ease-out ${
        isCollapsed ? "w-14 px-1.5" : "w-48 px-2"
      }`}
    >
      <button
        type="button"
        onClick={toggleSidebar}
        title={isCollapsed ? "Expandir navegação" : "Recolher navegação"}
        aria-label={isCollapsed ? "Expandir navegação" : "Recolher navegação"}
        className="absolute -right-3 top-14 z-30 flex h-6 w-6 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-500 shadow-sm transition-colors hover:bg-zinc-50 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
      >
        {isCollapsed ? (
          <PanelLeftOpen className="h-3.5 w-3.5" strokeWidth={2} />
        ) : (
          <PanelLeftClose className="h-3.5 w-3.5" strokeWidth={2} />
        )}
      </button>

      <div className="flex shrink-0 flex-col gap-2">
        <div
          className={`flex items-center ${
            isCollapsed ? "justify-center" : "gap-2"
          }`}
        >
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-sm font-bold text-white shadow-sm"
            title="TaskFloww"
            aria-label="TaskFloww"
          >
            T
          </div>

          {!isCollapsed ? (
            <div className="min-w-0">
              <p className="truncate text-[13px] font-semibold text-zinc-900">
                TaskFloww
              </p>
              <p className="truncate text-[10px] text-zinc-500">
                Gestão operacional
              </p>
            </div>
          ) : null}
        </div>

        <HeaderSearch variant={isCollapsed ? "icon" : "sidebar"} />
        <QuickCreateMenu variant={isCollapsed ? "collapsed" : "expanded"} />
      </div>

      <nav
        className={`mt-2 min-h-0 flex-1 ${
          isCollapsed
            ? "flex min-w-0 max-w-full flex-col items-center overflow-x-hidden overflow-y-hidden"
            : "flex flex-col gap-2 overflow-y-auto"
        }`}
        aria-label="Navegação principal"
      >
        {isCollapsed ? (
          <>
            <CollapsedSeparator />
            <div className="flex w-full max-w-full flex-col items-center gap-0.5 overflow-x-hidden box-border">
              {principalItems.map((item) => (
                <SidebarLink
                  key={item.href}
                  item={item}
                  isCollapsed
                  active={isItemActive(pathname, item.href)}
                />
              ))}
            </div>

            <CollapsedSeparator />
            <div className="flex w-full max-w-full flex-col items-center gap-0.5 overflow-x-hidden box-border">
              {operacaoItems.map((item) => (
                <SidebarLink
                  key={item.href}
                  item={item}
                  isCollapsed
                  active={isItemActive(pathname, item.href)}
                />
              ))}
            </div>

            <CollapsedSeparator />
            <button
              type="button"
              title="Cadastros"
              aria-label="Cadastros"
              onClick={handleCadastrosClick}
              className={`group relative flex h-8 w-8 items-center justify-center rounded-lg text-zinc-600 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 ${
                cadastrosActive ? "bg-blue-50 text-blue-700" : ""
              }`}
            >
              {cadastrosActive ? (
                <span
                  className="absolute left-0 h-4 w-0.5 rounded-r-full bg-blue-600"
                  aria-hidden="true"
                />
              ) : null}
              <Database className="h-4 w-4" strokeWidth={2} aria-hidden="true" />

            </button>

            <CollapsedSeparator />
            <div className="flex w-full max-w-full flex-col items-center gap-0.5 overflow-x-hidden box-border">
              {administracaoItems.map((item) => (
                <SidebarLink
                  key={item.href}
                  item={item}
                  isCollapsed
                  active={isItemActive(pathname, item.href)}
                />
              ))}
            </div>
          </>
        ) : (
          <>
            <div>
              <SectionTitle title="Principal" />
              <div className="flex flex-col gap-0.5">
                {principalItems.map((item) => (
                  <SidebarLink
                    key={item.href}
                    item={item}
                    isCollapsed={false}
                    active={isItemActive(pathname, item.href)}
                  />
                ))}
              </div>
            </div>

            <div>
              <SectionTitle title="Operação" />
              <div className="flex flex-col gap-0.5">
                {operacaoItems.map((item) => (
                  <SidebarLink
                    key={item.href}
                    item={item}
                    isCollapsed={false}
                    active={isItemActive(pathname, item.href)}
                  />
                ))}
              </div>
            </div>

            <div>
              <button
                type="button"
                onClick={handleCadastrosClick}
                className={`mb-1 flex h-8 w-full items-center gap-2 rounded-lg px-2.5 text-[12px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 ${
                  cadastrosActive
                    ? "bg-blue-50 text-blue-700"
                    : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
                }`}
                aria-expanded={cadastrosExpanded}
                aria-controls="sidebar-cadastros"
              >
                <Database className="h-4 w-4 shrink-0" strokeWidth={2} />
                <span className="min-w-0 flex-1 truncate text-left">Cadastros</span>
                <ChevronDown
                  className={`h-3.5 w-3.5 shrink-0 transition-transform ${
                    cadastrosExpanded ? "rotate-180" : ""
                  }`}
                  strokeWidth={2}
                  aria-hidden="true"
                />
              </button>

              {cadastrosExpanded ? (
                <div id="sidebar-cadastros" className="flex flex-col gap-0.5">
                  {cadastroItems.map((item) => (
                    <SidebarLink
                      key={item.href}
                      item={item}
                      isCollapsed={false}
                      active={isItemActive(pathname, item.href)}
                      nested
                    />
                  ))}
                </div>
              ) : null}
            </div>

            <div>
              <SectionTitle title="Administração" />
              <div className="flex flex-col gap-0.5">
                {administracaoItems.map((item) => (
                  <SidebarLink
                    key={item.href}
                    item={item}
                    isCollapsed={false}
                    active={isItemActive(pathname, item.href)}
                  />
                ))}
              </div>
            </div>
          </>
        )}
      </nav>

      <div className="mt-2 shrink-0 border-t border-zinc-100 pt-2">
        <UserMenu isCollapsed={isCollapsed} />
      </div>
    </aside>
  );
}
