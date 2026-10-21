"use client";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

/** Confirmação curta de uma ação (remover jornada personalizada / remover ausência). Sem motivo obrigatório: não é arquivamento. */
export function ConfirmacaoCurta({
  titulo,
  texto,
  confirmar,
  ocupado,
  erro,
  onConfirm,
  onClose,
}: {
  titulo: string;
  texto: string;
  confirmar: string;
  ocupado: boolean;
  erro: string | null;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal open onClose={ocupado ? () => {} : onClose} maxWidthClassName="max-w-sm">
      <h2 className="text-base font-semibold text-fg">{titulo}</h2>
      <p className="mt-2 text-sm text-fg-muted">{texto}</p>
      {erro && (
        <p role="alert" className="mt-3 text-xs text-red-600 dark:text-red-400">
          {erro}
        </p>
      )}
      <div className="mt-5 flex justify-end gap-3">
        <Button type="button" variant="secondary" onClick={onClose} disabled={ocupado}>
          Cancelar
        </Button>
        <Button type="button" onClick={onConfirm} disabled={ocupado}>
          {ocupado ? "Removendo…" : confirmar}
        </Button>
      </div>
    </Modal>
  );
}
