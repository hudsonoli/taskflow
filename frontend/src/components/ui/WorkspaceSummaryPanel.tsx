import type { ReactNode } from "react";

type WorkspaceSummaryHeaderProps = {
  icon: ReactNode;
  eyebrow: string;
  title: string;
  subtitle?: ReactNode;
  badges?: ReactNode;
  children?: ReactNode;
};

/**
 * Painel-resumo no topo do corpo de EntitySidePanel — extraído de
 * DemandaDetailsDrawer.tsx/ProjetoDetailsDrawer.tsx, onde vivia duplicado
 * quase byte a byte (mesmo chip de ícone, mesma grade de estatísticas).
 * children recebe os blocos WorkspaceSummaryStat — a quantidade/conteúdo
 * varia por entidade, por isso não é uma lista fixa de props.
 */
export function WorkspaceSummaryHeader({
  icon,
  eyebrow,
  title,
  subtitle,
  badges,
  children,
}: WorkspaceSummaryHeaderProps) {
  return (
    <div className="rounded-3xl border border-zinc-100 bg-zinc-50/70 p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-700 ring-1 ring-blue-100">
            {icon}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
              {eyebrow}
            </p>
            <h3 className="mt-1 text-lg font-semibold text-zinc-950">{title}</h3>
            {subtitle && (
              <p className="mt-1 flex items-center gap-2 text-sm text-zinc-500">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {badges && <div className="flex flex-wrap gap-2">{badges}</div>}
      </div>

      {children && <div className="mt-4 grid gap-3 sm:grid-cols-3">{children}</div>}
    </div>
  );
}

type WorkspaceSummaryStatProps = {
  label: string;
  icon?: ReactNode;
  value: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
};

export function WorkspaceSummaryStat({
  label,
  icon,
  value,
  footer,
  wide = false,
}: WorkspaceSummaryStatProps) {
  return (
    <div className={`rounded-2xl bg-white p-3 ring-1 ring-zinc-100 ${wide ? "sm:col-span-2" : ""}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
        {label}
      </p>
      <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-zinc-800">
        {icon}
        {value}
      </p>
      {footer && <p className="mt-1 text-xs text-zinc-500">{footer}</p>}
    </div>
  );
}
