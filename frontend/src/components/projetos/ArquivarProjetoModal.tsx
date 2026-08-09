"use client";

import { useState } from "react";
import { Archive, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Textarea } from "@/components/ui/Textarea";

// Arquivar = soft-delete permanente (docs/padrao-arquivamento.md). Motivo obrigatório, e o
// backend recusa motivo só com espaços — por isso o botão só habilita com conteúdo real.
export function ArquivarProjetoModal({
  open,
  nome,
  arquivando,
  onClose,
  onConfirm,
}: {
  open: boolean;
  nome: string;
  arquivando: boolean;
  onClose: () => void;
  onConfirm: (motivo: string) => void;
}) {
  const [motivo, setMotivo] = useState("");
  const podeConfirmar = motivo.trim().length > 0 && !arquivando;

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-md">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400">
            <Archive className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-zinc-950 dark:text-zinc-50">Arquivar {nome}</h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              O projeto não é apagado — sai da listagem e deixa de ser oferecido em novos vínculos. O nome continua
              reservado para este cliente, e o projeto pode ser restaurado depois.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4">
        <Textarea
          label="Motivo (obrigatório)"
          value={motivo}
          onChange={(event) => setMotivo(event.target.value)}
          placeholder="Por que este projeto está sendo arquivado?"
          rows={3}
        />
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!podeConfirmar} onClick={() => onConfirm(motivo.trim())}>
          {arquivando ? "Arquivando…" : "Arquivar"}
        </Button>
      </div>
    </Modal>
  );
}
