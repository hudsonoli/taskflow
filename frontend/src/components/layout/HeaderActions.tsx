import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  Bell,
  Building2,
  CalendarDays,
  Clock3,
  FolderKanban,
  ListTodo,
  Plus,
  UserPlus,
  Users,
} from "lucide-react";

type ActionButtonProps = {
  label: string;
  icon: typeof Bell;
  badge?: string;
};

function ActionButton({ label, icon: Icon, badge }: ActionButtonProps) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      className="relative flex h-11 w-11 items-center justify-center rounded-2xl border border-zinc-200 bg-white text-zinc-600 shadow-sm transition hover:bg-zinc-100"
    >
      <Icon className="h-5 w-5" strokeWidth={2} aria-hidden="true" />
      {badge ? (
        <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
          {badge}
        </span>
      ) : null}
    </button>
  );
}

type QuickActionItem = {
  label: string;
  href?: string;
  icon: typeof Plus;
  disabled?: boolean;
  helperText?: string;
};

const quickActions: QuickActionItem[] = [
  { label: "+ Tarefa", href: "/tarefas", icon: ListTodo },
  { label: "+ Cliente", href: "/configuracoes/clientes", icon: Users },
  { label: "+ Projeto", href: "/projetos", icon: FolderKanban },
  { label: "+ Usuário", href: "/configuracoes/usuarios", icon: UserPlus },
  {
    label: "+ Agência",
    href: "/configuracoes/agencias",
    icon: Building2,
    disabled: true,
    helperText: "Somente SuperAdmin",
  },
];

function QuickCreateMenu() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

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
        title="Criar rápido"
        aria-label="Criar rápido"
        onClick={() => setOpen((value) => !value)}
        className="flex h-11 w-11 items-center justify-center rounded-2xl border border-zinc-200 bg-white text-zinc-600 shadow-sm transition hover:bg-zinc-100"
      >
        <Plus className="h-5 w-5" strokeWidth={2} aria-hidden="true" />
      </button>

      <div
        className={`absolute right-0 top-full z-50 mt-3 w-64 origin-top-right rounded-3xl border border-zinc-200 bg-white p-2 shadow-xl transition-all duration-200 ${
          open
            ? "pointer-events-auto translate-y-0 scale-100 opacity-100"
            : "pointer-events-none translate-y-2 scale-95 opacity-0"
        }`}
      >
        <p className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
          Criação rápida
        </p>

        <div className="space-y-1">
          {quickActions.map((item) => {
            const Icon = item.icon;

            if (item.disabled) {
              return (
                <div
                  key={item.label}
                  aria-disabled="true"
                  className="flex cursor-not-allowed items-center justify-between rounded-2xl px-3 py-2.5 text-sm font-medium text-zinc-400"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
                    <span>{item.label}</span>
                  </div>
                  <span className="text-xs text-zinc-400">{item.helperText}</span>
                </div>
              );
            }

            return (
              <Link
                key={item.label}
                href={item.href ?? "#"}
                onClick={closeMenu}
                className="flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100"
              >
                <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function HeaderActions() {
  return (
    <div className="flex items-center gap-2">
      <QuickCreateMenu />
      <ActionButton label="Notificações" icon={Bell} badge="3" />
      <ActionButton label="Agenda" icon={CalendarDays} />
      <ActionButton label="Atividades" icon={Clock3} />
    </div>
  );
}
