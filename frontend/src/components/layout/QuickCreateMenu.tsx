"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  FolderKanban,
  ListTodo,
  Plus,
  Truck,
  UserPlus,
  Users,
} from "lucide-react";

type QuickCreateVariant = "expanded" | "collapsed";

type QuickCreateMenuProps = {
  variant?: QuickCreateVariant;
};

type QuickActionItem = {
  label: string;
  href: string;
  icon: typeof Plus;
};

const quickActions: QuickActionItem[] = [
  { label: "+ Tarefa", href: "/tarefas", icon: ListTodo },
  { label: "+ Projeto", href: "/projetos", icon: FolderKanban },
  { label: "+ Cliente", href: "/configuracoes/clientes", icon: Users },
  { label: "+ Fornecedor", href: "/fornecedores", icon: Truck },
  { label: "+ Usuário", href: "/configuracoes/usuarios", icon: UserPlus },
];

export function QuickCreateMenu({ variant = "expanded" }: QuickCreateMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const isCollapsed = variant === "collapsed";

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  function closeMenu() {
    setOpen(false);
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        title="Criar novo"
        aria-label="Criar novo"
        onClick={() => setOpen((value) => !value)}
        className={`flex h-8 items-center rounded-lg border border-zinc-200 bg-white text-[12px] font-semibold text-zinc-700 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 ${
          isCollapsed ? "mx-auto w-8 min-w-8 max-w-8 justify-center p-0" : "w-full justify-center gap-2 px-2.5"
        }`}
      >
        <Plus className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
        {!isCollapsed ? <span>Criar novo</span> : null}
      </button>

      {open ? (
        <div className="absolute left-full top-0 z-50 ml-3 w-52 origin-top-left rounded-2xl border border-zinc-200 bg-white p-1.5 shadow-xl">
          <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-400">
            Criação rápida
          </p>

          <div className="space-y-1">
            {quickActions.map((item) => {
              const Icon = item.icon;

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={closeMenu}
                  className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-[12px] font-medium text-zinc-700 transition-colors hover:bg-zinc-100"
                >
                  <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
