import type { ReactNode } from "react";

type WorkspaceHeaderProps = {
  icon: ReactNode;
  title: string;
  description: string;
  badges?: ReactNode;
};

/**
 * Hero de página dos workspaces operacionais (Demandas, Projetos) — extraído
 * de DemandasView.tsx/ProjetosView.tsx, onde vivia duplicado byte a byte
 * (mesmo wrapper, mesmo chip de ícone, mesma hierarquia de título/descrição).
 * TrafegoHeader.tsx não usa este componente: tem tratamento próprio mais
 * rico (círculo decorativo, ação de atualizar), intencionalmente distinto.
 */
export function WorkspaceHeader({
  icon,
  title,
  description,
  badges,
}: WorkspaceHeaderProps) {
  return (
    <div className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-3xl bg-blue-50 text-blue-700 ring-1 ring-blue-100">
            {icon}
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">
              {title}
            </h1>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-500">
              {description}
            </p>
          </div>
        </div>

        {badges && <div className="flex flex-wrap gap-2">{badges}</div>}
      </div>
    </div>
  );
}
