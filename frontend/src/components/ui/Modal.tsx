"use client";

import { useEffect } from "react";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  maxWidthClassName?: string;
};

export function Modal({
  open,
  onClose,
  children,
  maxWidthClassName = "max-w-lg",
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-zinc-900/40"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        className={`relative max-h-[90vh] w-full ${maxWidthClassName} overflow-y-auto rounded-3xl bg-white p-6 shadow-lg`}
      >
        {children}
      </div>
    </div>
  );
}
