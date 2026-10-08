"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, Headset, LayoutDashboard, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { usePlataforma } from "@/components/plataforma/PlataformaContext";

const ITENS = [
  { href: "/plataforma", rotulo: "Dashboard", icone: LayoutDashboard, exato: true },
  { href: "/plataforma/empresas", rotulo: "Empresas", icone: Building2, exato: false },
] as const;

/**
 * Moldura da Administração da Plataforma: separada visualmente das Configurações do tenant (que administram UMA
 * empresa). Aqui se administra a plataforma e as empresas que existem nela. "Suporte" é só um marcador "Em breve" —
 * não há suporte nem impersonação nesta fase.
 */
export function PlataformaShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { empresaEmFoco } = usePlataforma();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<ShieldCheck className="h-5 w-5" />}
        title="Administração da Plataforma"
        description="Cadastro e gestão das empresas, identidade visual de cada uma e provisionamento do primeiro Gestor. Autoridade própria, separada dos perfis das empresas."
        action={<Badge tone="amber">Área da plataforma</Badge>}
      />

      <div className="flex flex-wrap items-center gap-3">
        <nav aria-label="Administração da Plataforma" className="flex flex-wrap gap-1 rounded-xl bg-surface-2 p-1">
          {ITENS.map(({ href, rotulo, icone: Icone, exato }) => {
            const ativo = exato ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={ativo ? "page" : undefined}
                className={clsx(
                  "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                  ativo ? "bg-surface text-fg shadow-sm" : "text-fg-muted hover:text-fg",
                )}
              >
                <Icone size={14} /> {rotulo}
              </Link>
            );
          })}
          <span
            aria-disabled="true"
            title="Em breve"
            className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold text-fg-subtle opacity-70"
          >
            <Headset size={14} /> Suporte <Badge>Em breve</Badge>
          </span>
        </nav>

        {empresaEmFoco && (
          <p
            className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-xs text-fg-muted"
            aria-label="Empresa em foco"
          >
            <span aria-hidden>🏢</span>
            <span className="font-semibold text-fg">Empresa em foco:</span>
            <span className="truncate">{empresaEmFoco.nome}</span>
            <span className="font-mono text-fg-subtle">{empresaEmFoco.slug}</span>
          </p>
        )}
      </div>

      {children}
    </div>
  );
}
