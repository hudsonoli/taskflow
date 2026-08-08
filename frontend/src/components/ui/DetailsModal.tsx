"use client";

import { useEffect, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Pencil, X } from "lucide-react";

export function DetailsModal({
  open,
  onClose,
  onEdit,
  editLabel = "Editar",
  title,
  description,
  footer,
  children,
  maxWidthClassName = "max-w-3xl",
}: {
  open: boolean;
  onClose: () => void;
  onEdit?: () => void;
  editLabel?: string;
  title?: string;
  description?: string;
  footer?: ReactNode;
  children?: ReactNode;
  maxWidthClassName?: string;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-zinc-950/35 backdrop-blur-md"
          />
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className={`relative flex max-h-[85vh] w-full flex-col overflow-hidden rounded-2xl border border-zinc-200/80 bg-white shadow-2xl dark:border-zinc-800/80 dark:bg-zinc-900 ${maxWidthClassName}`}
          >
            <div className="flex items-start justify-between gap-4 border-b border-zinc-100 p-6 dark:border-zinc-800">
              <div className="min-w-0">
                {title && <h2 className="truncate text-lg font-semibold text-zinc-950 dark:text-zinc-50">{title}</h2>}
                {description && <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{description}</p>}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {onEdit && (
                  <button
                    type="button"
                    onClick={onEdit}
                    aria-label={editLabel}
                    className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                  >
                    <Pencil size={16} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Fechar"
                  className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">{children}</div>

            {footer && <div className="border-t border-zinc-100 p-4 dark:border-zinc-800">{footer}</div>}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
