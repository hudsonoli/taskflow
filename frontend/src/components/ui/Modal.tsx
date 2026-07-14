"use client";

import { useEffect } from "react";

type ModalLayout = "flow" | "panel";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  maxWidthClassName?: string;
  overlayClassName?: string;
  maxHeightClassName?: string;
  /**
   * "flow" (default) preserva o card único e rolável de sempre.
   * "panel" entrega um card em coluna (flex-col, overflow-hidden) para
   * modais com cabeçalho/abas/rodapé fixos e uma única área de scroll
   * interna controlada pelo próprio conteúdo — ver NovoClienteModal.
   */
  layout?: ModalLayout;
};

export function Modal({
  open,
  onClose,
  children,
  maxWidthClassName = "max-w-lg",
  overlayClassName = "bg-zinc-900/40",
  maxHeightClassName = "max-h-[90vh]",
  layout = "flow",
}: ModalProps) {
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const cardClassName =
    layout === "panel"
      ? `relative flex ${maxHeightClassName} w-full flex-col ${maxWidthClassName} overflow-hidden rounded-3xl bg-white shadow-lg`
      : `relative ${maxHeightClassName} w-full ${maxWidthClassName} overflow-y-auto rounded-3xl bg-white p-6 shadow-lg`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className={`absolute inset-0 ${overlayClassName}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <div className={cardClassName}>{children}</div>
    </div>
  );
}
