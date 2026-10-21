"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { TITULO_SECAO } from "@/lib/usuario-capacidade";
import { UsuarioCapacidadeSection } from "./UsuarioCapacidadeSection";

/** Consulta SOMENTE LEITURA da jornada e das ausências de um usuário que o ator pode ver, mas não editar (a lista de Usuários não abre o formulário de edição para ele). */
export function UsuarioCapacidadeModal({ usuarioId, nome, onClose }: { usuarioId: string; nome: string; onClose: () => void }) {
  return (
    <Modal open onClose={onClose} maxWidthClassName="max-w-2xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-4 dark:border-zinc-800">
        <div>
          <h2 className="text-lg font-semibold text-fg">{TITULO_SECAO}</h2>
          <p className="mt-0.5 text-sm text-fg-muted">{nome}</p>
        </div>
        <button type="button" onClick={onClose} aria-label="Fechar" className="rounded-full p-2 text-fg-subtle transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-4">
        <UsuarioCapacidadeSection usuarioId={usuarioId} somenteLeitura />
      </div>
      <div className="mt-5 flex justify-end border-t border-zinc-100 pt-4 dark:border-zinc-800">
        <Button type="button" variant="secondary" onClick={onClose}>
          Fechar
        </Button>
      </div>
    </Modal>
  );
}
