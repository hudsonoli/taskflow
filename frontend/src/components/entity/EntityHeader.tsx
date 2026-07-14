"use client";

import { ArrowLeft, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEntityDrawerContext } from "./EntityDrawer";

export type EntityHeaderProps = {
  title: string;
  description?: string;
  avatar?: ReactNode;
  statusBadge?: ReactNode;
  onClose: () => void;
  canGoBack?: boolean;
  onBack?: () => void;
  quickActions?: ReactNode;
};

/**
 * Bloco de identidade do EntityDrawer: avatar, título, descrição, status,
 * navegação de voltar e fechar. Não conhece a entidade, não busca dados, não
 * decide ações de ciclo de vida (Salvar/Excluir vivem em EntityActions).
 *
 * Regra única de precedência: prop explícita sempre vence. O Context só
 * fornece um valor padrão para props opcionais quando a página não as passa
 * (canGoBack/onBack). onClose é obrigatória e nunca é substituída pelo
 * Context — quem quiser bloquear o fechamento por isDirty deve compor esse
 * comportamento na própria função passada via prop, sem mágica implícita.
 */
export function EntityHeader({
  title,
  description,
  avatar,
  statusBadge,
  onClose,
  canGoBack,
  onBack,
  quickActions,
}: EntityHeaderProps) {
  const ctx = useEntityDrawerContext();

  const resolvedCanGoBack = canGoBack ?? ctx?.canGoBack ?? false;
  const resolvedOnBack = onBack ?? ctx?.back;

  return (
    <header className="flex shrink-0 items-start justify-between gap-3 border-b border-zinc-100 px-3 py-2.5">
      <div className="flex min-w-0 items-start gap-3">
        {resolvedCanGoBack && (
          <button
            type="button"
            onClick={resolvedOnBack}
            aria-label="Voltar"
            title="Voltar"
            className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
          >
            <ArrowLeft className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
          </button>
        )}

        {avatar}

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id={ctx?.titleId} className="truncate text-lg font-semibold text-zinc-900">
              {title}
            </h2>
            {statusBadge}
          </div>

          {description && (
            <p id={ctx?.descriptionId} className="mt-0.5 text-[11px] text-zinc-500">
              {description}
            </p>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        {quickActions}

        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
        >
          <X className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
