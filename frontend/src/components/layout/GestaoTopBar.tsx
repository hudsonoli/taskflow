"use client";

import Link from "next/link";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { ProfileMenu } from "@/components/layout/ProfileMenu";

/**
 * Barra da Gestão da plataforma (`/gestao`, Fase 10A). Identidade do PRODUTO (TaskFlow), sem logo nem nome de empresa e sem menu de tenant: a Gestão é
 * transversal e não pertence a nenhuma empresa. O menu do perfil continua para sair e escolher o tema; voltar à empresa é um link explícito
 * `/e/<slug>/...` (nunca uma troca implícita de tenant).
 */
export function GestaoTopBar() {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-white/70 backdrop-blur-xl dark:bg-zinc-950/70">
      <div className="flex items-center gap-3 px-4 py-3 sm:px-6">
        <Link href="/gestao" className="flex shrink-0 items-center" aria-label="Gestão da plataforma">
          <BrandLogo variant="header" />
        </Link>
        <span className="rounded-full bg-surface-2 px-2.5 py-1 text-xs font-semibold text-fg-muted">Gestão</span>
        <div className="flex-1" />
        <ProfileMenu />
      </div>
    </header>
  );
}
