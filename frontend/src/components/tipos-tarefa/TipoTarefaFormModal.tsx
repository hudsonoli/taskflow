"use client";

import { useState } from "react";
import { ClipboardList, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Switch } from "@/components/ui/Switch";
import { Textarea } from "@/components/ui/Textarea";
import type { TipoTarefa, TipoTarefaFormDraft } from "@/types/tipo-tarefa";

function createInitialDraft(tipoTarefa?: TipoTarefa): TipoTarefaFormDraft {
  return {
    nome: tipoTarefa?.nome ?? "",
    descricao: tipoTarefa?.descricao ?? "",
    ordem: tipoTarefa?.ordem ?? 0,
    status: tipoTarefa?.status === "inativo" ? "inativo" : "ativo",
  };
}

export function TipoTarefaFormModal({
  open,
  tipoTarefa,
  onClose,
  onSave,
  salvando,
}: {
  open: boolean;
  tipoTarefa?: TipoTarefa;
  onClose: () => void;
  onSave: (draft: TipoTarefaFormDraft, tipoTarefaId?: string) => void;
  salvando?: boolean;
}) {
  const [draft, setDraft] = useState<TipoTarefaFormDraft>(() => createInitialDraft(tipoTarefa));

  const editing = tipoTarefa !== undefined;
  const canSave = draft.nome.trim().length > 0 && draft.ordem >= 0;

  function updateDraft(patch: Partial<TipoTarefaFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <ClipboardList className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${tipoTarefa.nome}` : "Novo tipo de tarefa"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Categoria de demanda usada nos modelos de campanha.
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

      <div className="mt-6 flex flex-col gap-4">
        <Input label="Nome" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

        <Textarea
          label="Descrição"
          rows={3}
          value={draft.descricao}
          onChange={(event) => updateDraft({ descricao: event.target.value })}
        />

        {/* Input numérico simples — sem drag-and-drop nesta fase (ver kickoff 2G.9). */}
        <Input
          label="Ordem"
          type="number"
          min={0}
          value={draft.ordem}
          onChange={(event) => updateDraft({ ordem: Math.max(0, Number(event.target.value) || 0) })}
        />

        <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch
            checked={draft.status === "ativo"}
            onChange={(checked) => updateDraft({ status: checked ? "ativo" : "inativo" })}
            label={draft.status === "ativo" ? "Ativo" : "Inativo"}
          />
        </div>
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave || salvando} onClick={() => onSave(draft, tipoTarefa?.id)}>
          {salvando ? "Salvando…" : "Salvar alterações"}
        </Button>
      </div>
    </Modal>
  );
}
