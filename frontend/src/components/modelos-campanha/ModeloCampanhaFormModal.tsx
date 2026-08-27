"use client";

import { useState } from "react";
import { Layers3, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Switch } from "@/components/ui/Switch";
import { Textarea } from "@/components/ui/Textarea";
import { criarItemModeloCampanhaVazio } from "@/lib/modeloCampanhaItens";
import type { ModeloCampanha, ModeloCampanhaFormDraft, ModeloCampanhaItem, ModeloCampanhaItemFormDraft } from "@/types/modelo-campanha";
import { ModeloCampanhaItensEditor } from "./ModeloCampanhaItensEditor";

function itemParaDraft(item: ModeloCampanhaItem): ModeloCampanhaItemFormDraft {
  return {
    id: item.id,
    // O id do servidor já é uma chave única e estável — reaproveitado como clientKey, sem
    // gerar outro identificador para o mesmo item.
    clientKey: item.id,
    nome: item.nome,
    briefingPadrao: item.briefingPadrao ?? "",
    prioridadePadrao: item.prioridadePadrao,
    pecaId: item.pecaId,
    pecaNome: item.pecaNome,
    tipoTarefaId: item.tipoTarefaId,
    tipoTarefaNome: item.tipoTarefaNome,
    workflowModeloId: item.workflowModeloId,
    workflowModeloNome: item.workflowModeloNome,
    responsavelUsuarioId: item.responsavelUsuarioId,
    responsavelUsuarioNome: item.responsavelUsuarioNome,
    responsavelDepartamentoId: item.responsavelDepartamentoId,
    responsavelDepartamentoNome: item.responsavelDepartamentoNome,
  };
}

function createInitialDraft(modelo?: ModeloCampanha): ModeloCampanhaFormDraft {
  return {
    nome: modelo?.nome ?? "",
    descricao: modelo?.descricao ?? "",
    status: modelo?.status === "inativo" ? "inativo" : "ativo",
    itens: modelo ? modelo.itens.map(itemParaDraft) : [criarItemModeloCampanhaVazio()],
  };
}

export function ModeloCampanhaFormModal({
  open,
  modelo,
  onClose,
  onSave,
  salvando,
  erro,
}: {
  open: boolean;
  modelo?: ModeloCampanha;
  onClose: () => void;
  onSave: (draft: ModeloCampanhaFormDraft, modeloId?: string) => void;
  salvando?: boolean;
  erro?: string | null;
}) {
  const [draft, setDraft] = useState<ModeloCampanhaFormDraft>(() => createInitialDraft(modelo));

  const editing = modelo !== undefined;
  const todosItensValidos = draft.itens.every((item) => item.nome.trim().length > 0);
  const canSave = draft.nome.trim().length > 0 && todosItensValidos && !salvando;

  function updateDraft(patch: Partial<ModeloCampanhaFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-2xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Layers3 className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${modelo.nome}` : "Novo modelo de campanha"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Estrutura reutilizável de itens sugeridos para campanhas recorrentes.
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
        <Input label="Nome do modelo" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

        <Textarea
          label="Descrição"
          rows={2}
          value={draft.descricao}
          onChange={(event) => updateDraft({ descricao: event.target.value })}
        />

        <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch
            checked={draft.status === "ativo"}
            onChange={(checked) => updateDraft({ status: checked ? "ativo" : "inativo" })}
            label={draft.status === "ativo" ? "Ativo" : "Inativo"}
            description="Modelos inativos continuam preservados, mas ficam fora do uso corrente."
          />
        </div>

        {erro && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        <ModeloCampanhaItensEditor itens={draft.itens} onItensChange={(itens) => updateDraft({ itens })} />
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose} disabled={salvando}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={() => onSave(draft, modelo?.id)}>
          {salvando ? "Salvando…" : "Salvar"}
        </Button>
      </div>
    </Modal>
  );
}
