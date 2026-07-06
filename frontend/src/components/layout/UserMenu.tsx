"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Bell, KeyRound, LogOut, User } from "lucide-react";
import { currentUser, getCurrentUserInitials, logout } from "@/lib/conta-mock";

type MenuItem = {
  label: string;
  href?: string;
  icon: typeof User;
  onClick?: () => void;
  variant?: "default" | "danger";
};

type MenuSection = {
  title?: string;
  items: MenuItem[];
};

const menuSections: MenuSection[] = [
  {
    title: "CONTA",
    items: [
      { label: "Perfil", href: "/conta/perfil", icon: User },
      { label: "Notificações", href: "/conta/notificacoes", icon: Bell },
      { label: "Alterar senha", href: "/conta/alterar-senha", icon: KeyRound },
    ],
  },
  {
    items: [{ label: "Sair", icon: LogOut, variant: "danger", onClick: logout }],
  },
];

const currentUserMeta = {
  ultimaAcesso: "05/07/2026 às 18:42",
  ultimoIp: "192.168.0.24",
};

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const avatarSrc = currentUser.avatarThumbnail ?? currentUser.avatarUrl;
  const initials = getCurrentUserInitials(currentUser.nome);

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

  function handleItemClick(item: MenuItem) {
    item.onClick?.();
    closeMenu();
  }

  return (
    <div ref={menuRef} className="relative mt-auto flex justify-center pt-4">
      <button
        type="button"
        title={currentUser.nome}
        aria-label={currentUser.nome}
        onClick={() => setOpen((value) => !value)}
        className="group relative flex h-12 w-12 items-center justify-center rounded-2xl text-zinc-600 transition hover:bg-zinc-100"
      >
        <div className="relative flex h-12 w-12 items-center justify-center overflow-hidden rounded-full bg-zinc-900 text-sm font-semibold text-white shadow-sm">
          {avatarSrc ? (
            <Image
              src={avatarSrc}
              alt={currentUser.nome}
              width={48}
              height={48}
              className="h-full w-full object-cover"
            />
          ) : (
            <span>{initials}</span>
          )}
          <div className="absolute right-0 top-0">
            {/* Badge futuro */}
          </div>
        </div>
      </button>

      <div
        className={`absolute bottom-0 left-full z-50 ml-3 w-72 origin-bottom-left rounded-3xl border border-zinc-200 bg-white p-2 shadow-xl transition-all duration-200 ${
          open
            ? "pointer-events-auto translate-x-0 scale-100 opacity-100"
            : "pointer-events-none translate-x-2 scale-95 opacity-0"
        }`}
      >
        <div className="px-3 py-2">
          <p className="text-sm font-semibold text-zinc-900">{currentUser.nome}</p>
          <p className="text-xs text-zinc-500">{currentUser.cargo}</p>
          <p className="text-xs text-zinc-500">{currentUser.departamento}</p>
          <p className="mt-1 text-xs text-zinc-500">{currentUser.email}</p>
        </div>

        <div className="my-2 h-px bg-zinc-100" />

        {menuSections.map((section, sectionIndex) => (
          <div key={section.title ?? `section-${sectionIndex}`} className="space-y-1">
            {section.title ? (
              <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
                {section.title}
              </p>
            ) : null}

            {section.items.map((item) => {
              const Icon = item.icon;
              const baseClassName =
                "flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left text-sm font-medium transition";
              const variantClassName =
                item.variant === "danger"
                  ? "text-red-600 hover:bg-red-50"
                  : "text-zinc-700 hover:bg-zinc-100";

              if (item.href) {
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    onClick={closeMenu}
                    className={`${baseClassName} ${variantClassName}`}
                  >
                    <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                );
              }

              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => handleItemClick(item)}
                  className={`${baseClassName} ${variantClassName}`}
                >
                  <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}

        <div className="mt-2 rounded-2xl bg-zinc-50 px-3 py-3 text-xs text-zinc-500">
          Último acesso: {currentUserMeta.ultimaAcesso}
          <br />
          Último IP: {currentUserMeta.ultimoIp}
        </div>
      </div>
    </div>
  );
}
