"use client";

import { Pencil, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useId, useRef } from "react";

type EntitySidePanelProps = {
  open: boolean;
  onClose: () => void;
  onEdit?: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  editLabel?: string;
  overlayClassName?: string;
};

export function EntitySidePanel({
  open,
  onClose,
  onEdit,
  title,
  description,
  children,
  footer,
  editLabel = "Editar",
  overlayClassName = "bg-zinc-900/40",
}: EntitySidePanelProps) {
  const titleId = useId();
  const descriptionId = useId();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    const previouslyFocusedElement = document.activeElement as HTMLElement | null;
    const focusFrame = window.requestAnimationFrame(() => {
      closeButtonRef.current?.focus();
    });

    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocusedElement?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div
        className={`absolute inset-0 ${overlayClassName}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        className="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-zinc-200 bg-white shadow-xl sm:max-w-lg sm:rounded-l-3xl lg:max-w-xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-zinc-100 px-4 py-4 sm:px-6">
          <div className="min-w-0">
            <h2
              id={titleId}
              className="truncate text-xl font-semibold text-zinc-900"
            >
              {title}
            </h2>

            {description && (
              <p id={descriptionId} className="mt-1 text-sm text-zinc-500">
                {description}
              </p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {onEdit && (
              <button
                type="button"
                onClick={onEdit}
                aria-label={editLabel}
                title={editLabel}
                className="rounded-full border border-zinc-200 p-2 text-zinc-500 transition hover:bg-zinc-50 hover:text-zinc-900"
              >
                <Pencil size={18} aria-hidden="true" />
              </button>
            )}

            <button
              ref={closeButtonRef}
              type="button"
              onClick={onClose}
              aria-label="Fechar painel"
              className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
            >
              <X size={20} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
          {children}
        </div>

        {footer && (
          <footer className="border-t border-zinc-100 bg-white px-4 py-4 sm:px-6">
            {footer}
          </footer>
        )}
      </section>
    </div>
  );
}
