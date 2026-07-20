"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Bell, KeyRound, LogOut, User } from "lucide-react";
import { useAuth } from "@/components/auth/useAuth";
import { currentUser, getCurrentUserInitials } from "@/lib/conta-mock";
import { adaptCurrentUser } from "@/lib/auth/current-user-adapter";

type MenuItem = {
  label: string;
  href?: string;
  icon: typeof User;
  action?: "logout";
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
    items: [{ label: "Sair", icon: LogOut, variant: "danger", action: "logout" }],
  },
];

const currentUserMeta = {
  ultimaAcesso: "05/07/2026 às 18:42",
  ultimoIp: "192.168.0.24",
};

// Contador visual temporário até existir fonte real de notificações.
const notificationBadge = "3";

type UserMenuProps = {
  isCollapsed?: boolean;
};

export function UserMenu({ isCollapsed = false }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const { user, logout } = useAuth();
  const authenticatedUser = user ? adaptCurrentUser(user) : null;
  const displayName = authenticatedUser?.nome ?? currentUser.nome;
  const profileLabel = authenticatedUser?.perfilLabel ?? currentUser.cargo;
  const avatarSrc = currentUser.avatarThumbnail ?? currentUser.avatarUrl;
  const initials = getCurrentUserInitials(displayName);

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

  async function handleItemClick(item: MenuItem) {
    if (item.action === "logout") {
      await logout();
    }
    closeMenu();
  }

  return (
    <div
      ref={menuRef}
      className={`relative flex ${isCollapsed ? "justify-center" : "w-full"}`}
    >
      <button
        type="button"
        title={displayName}
        aria-label={displayName}
        onClick={() => setOpen((value) => !value)}
        className={`group relative flex rounded-2xl text-zinc-600 transition-colors hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 ${
          isCollapsed
            ? "h-8 w-8 items-center justify-center"
            : "w-full items-center gap-2 px-1.5 py-1 text-left"
        }`}
      >
        <div className="relative flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-zinc-900 text-sm font-semibold text-white shadow-sm">
          {avatarSrc ? (
            <Image
              src={avatarSrc}
              alt={displayName}
              width={32}
              height={32}
              className="h-full w-full object-cover"
            />
          ) : (
            <span>{initials}</span>
          )}
          <div className="absolute right-0 top-0">
            {/* Badge futuro */}
          </div>
        </div>

        {!isCollapsed ? (
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[13px] font-medium text-zinc-900">
              {displayName}
            </span>
            <span className="block truncate text-[11px] text-zinc-500">
              {profileLabel}
            </span>
          </span>
        ) : null}
      </button>

      <div
        className={`absolute bottom-0 left-full z-50 ml-3 w-64 origin-bottom-left rounded-3xl border border-zinc-200 bg-white p-2 shadow-xl transition-[opacity,transform] duration-200 ${
          open
            ? "pointer-events-auto translate-x-0 scale-100 opacity-100"
            : "pointer-events-none translate-x-2 scale-95 opacity-0"
        }`}
      >
        <div className="px-3 py-2">
          <p className="text-sm font-semibold text-zinc-900">{displayName}</p>
          <p className="text-xs text-zinc-500">{profileLabel}</p>
          <p className="text-xs text-zinc-500">{currentUser.departamento}</p>
          <p className="mt-1 text-xs text-zinc-500">{currentUser.email}</p>
        </div>

        <div className="my-2 h-px bg-zinc-100" />

        {menuSections.map((section, sectionIndex) => (
          <div key={section.title ?? `section-${sectionIndex}`} className="space-y-1">
            {section.title ? (
              <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
                {section.title}
              </p>
            ) : null}

            {section.items.map((item) => {
              const Icon = item.icon;
              const baseClassName =
                "flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-[13px] font-medium transition";
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
                    <span className="min-w-0 flex-1">{item.label}</span>
                    {item.label === "Notificações" ? (
                      <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
                        {notificationBadge}
                      </span>
                    ) : null}
                  </Link>
                );
              }

              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => void handleItemClick(item)}
                  className={`${baseClassName} ${variantClassName}`}
                >
                  <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
                  <span className="min-w-0 flex-1">{item.label}</span>
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
