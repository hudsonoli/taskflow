"use client";

import { useState } from "react";
import { Loader2, Tag, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import type { CategoriaPeca, CategoriaPecaFormDraft } from "@/types/categoria-peca";

type FormState = {
  nome: string;
  ordem: string;
};

function createInitialForm(categoria?: CategoriaPeca): FormState {
  return {
    nome: categoria?.nome ?? "",
    ordem: String(categoria?.ordem ?? 0),
  };
}

export function CategoriaPecaFormModal({
  open,
  categoria,
  salvando = false,
  erro = null,
  onClose,
  onSave,
}: {
  open: boolean;
  categoria?: CategoriaPeca;
  salvando?: boolean;
  erro?: string | null;
  onClose: () => void;
  onSave: (draft: CategoriaPecaFormDraft, categoriaId?: string) => void;
}) {
  const [form, setForm] = useState<FormState>(() => createInitialForm(categoria));

  const editing = categoria !== undefined;
  const canSave = form.nome.trim().length > 0 && !salvando;

  function updateForm(patch: Partial<FormState>) {
    setForm((current) => ({ ...current, ...patch }));
  }

  function handleSave() {
    const ordem = Number(form.ordem);
    onSave(
      { nome: form.nome.trim(), ordem: Number.isFinite(ordem) && ordem >= 0 ? ordem : 0 },
      categoria?.id,
    );
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-md">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Tag className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${categoria.nome}` : "Nova categoria"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Usada para classificar peças do catálogo.
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

      <div className="mt-5 flex flex-col gap-4">
        <Input
          label="Nome"
          value={form.nome}
          onChange={(event) => updateForm({ nome: event.target.value })}
          placeholder="ex.: Digital, Impresso, Vídeo"
        />
        <Input
          label="Ordem"
          type="number"
          min={0}
          value={form.ordem}
          onChange={(event) => updateForm({ ordem: event.target.value })}
        />
        {erro && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose} disabled={salvando}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={handleSave}>
          {salvando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          {editing ? "Salvar alterações" : "Criar categoria"}
        </Button>
      </div>
    </Modal>
  );
}
