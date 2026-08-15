"use client";

import { useState } from "react";
import { Lock, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Textarea } from "@/components/ui/Textarea";

/**
 * Bloquear exige motivo. O backend recusa (422) tanto motivo ausente quanto composto só de
 * espaços, então o botão só habilita com conteúdo real — o usuário descobre a regra antes de
 * enviar, não depois de um erro.
 *
 * Ao sair do bloqueio o campo é limpo pelo servidor, mas o motivo NÃO se perde: fica no
 * payload do evento `demanda.desbloqueada`, que é o histórico desta fase.
 */
export function MotivoBloqueioModal({
  open,
  rotulo,
  salvando,
  onClose,
  onConfirm,
}: {
  open: boolean;
  rotulo: string;
  salvando: boolean;
  onClose: () => void;
  onConfirm: (motivo: string) => void;
}) {
  const [motivo, setMotivo] = useState("");
  const podeConfirmar = motivo.trim().length > 0 && !salvando;

  function fechar() {
    setMotivo("");
    onClose();
  }

  return (
    <Modal open={open} onClose={fechar} maxWidthClassName="max-w-md">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-zinc-950 dark:text-zinc-50">Bloquear {rotulo}</h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              Registre o que impede o andamento. O motivo aparece na tarefa enquanto ela estiver bloqueada e fica no
              histórico depois de desbloqueada.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={fechar}
          aria-label="Fechar"
          className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4">
        <Textarea
          label="Motivo do bloqueio (obrigatório)"
          value={motivo}
          onChange={(event) => setMotivo(event.target.value)}
          placeholder="O que está impedindo o andamento desta tarefa?"
          rows={3}
        />
      </div>

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={fechar} disabled={salvando}>
          Cancelar
        </Button>
        <Button
          onClick={() => {
            onConfirm(motivo.trim());
            setMotivo("");
          }}
          disabled={!podeConfirmar}
        >
          {salvando ? "Bloqueando…" : "Bloquear"}
        </Button>
      </div>
    </Modal>
  );
}
