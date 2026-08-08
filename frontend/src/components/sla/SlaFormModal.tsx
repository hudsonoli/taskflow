"use client";

import { useState } from "react";
import { Timer, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Combobox } from "@/components/ui/Combobox";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { Textarea } from "@/components/ui/Textarea";
import { slaPrioridadeAlvoLabels, type SlaPrioridadeAlvo, type SlaRegra, type SlaRegraFormDraft } from "@/types/sla";
import type { ClienteDiretorioItem } from "@/lib/api-backend";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";

function createInitialDraft(regra?: SlaRegra): SlaRegraFormDraft {
  return {
    nome: regra?.nome ?? "",
    descricao: regra?.descricao ?? "",
    prioridade: regra?.prioridade ?? "todas",
    departamentoId: regra?.departamentoId ?? "",
    clienteId: regra?.clienteId ?? "",
    prazoPrimeiraRespostaHoras: regra?.prazoPrimeiraRespostaHoras ?? 4,
    prazoResolucaoHoras: regra?.prazoResolucaoHoras ?? 48,
    considerarApenasExpediente: regra?.considerarApenasExpediente ?? true,
    ativo: regra?.ativo ?? true,
  };
}

export function SlaFormModal({
  open,
  regra,
  departamentos,
  clientes,
  onClose,
  onSave,
}: {
  open: boolean;
  regra?: SlaRegra;
  departamentos: DepartamentoDiretorioItem[];
  clientes: ClienteDiretorioItem[];
  onClose: () => void;
  onSave: (draft: SlaRegraFormDraft, slaRegraId?: string) => void;
}) {
  const [draft, setDraft] = useState<SlaRegraFormDraft>(() => createInitialDraft(regra));

  const editing = regra !== undefined;
  const canSave =
    draft.nome.trim().length > 0 && draft.prazoPrimeiraRespostaHoras > 0 && draft.prazoResolucaoHoras > 0;

  function updateDraft(patch: Partial<SlaRegraFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Timer className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${regra.nome}` : "Nova regra de SLA"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Cadastro local — define prazos de resposta e resolução para o escopo selecionado.
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
        <Input label="Nome da regra" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

        <Textarea
          label="Descrição"
          rows={2}
          value={draft.descricao}
          onChange={(event) => updateDraft({ descricao: event.target.value })}
        />

        <Select
          label="Prioridade alvo"
          value={draft.prioridade}
          onChange={(event) => updateDraft({ prioridade: event.target.value as SlaPrioridadeAlvo })}
          options={Object.entries(slaPrioridadeAlvoLabels).map(([value, label]) => ({ value, label }))}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <Combobox
            label="Departamento (opcional)"
            value={draft.departamentoId}
            onChange={(departamentoId) => updateDraft({ departamentoId })}
            options={departamentos.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
            placeholder="Todos os departamentos"
            emptyLabel="Nenhum departamento encontrado"
          />
          <Combobox
            label="Cliente (opcional)"
            value={draft.clienteId}
            onChange={(clienteId) => updateDraft({ clienteId })}
            options={clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome }))}
            placeholder="Todos os clientes"
            emptyLabel="Nenhum cliente encontrado"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Prazo de 1ª resposta (horas)"
            type="number"
            min={1}
            value={draft.prazoPrimeiraRespostaHoras}
            onChange={(event) => updateDraft({ prazoPrimeiraRespostaHoras: Number(event.target.value) })}
          />
          <Input
            label="Prazo de resolução (horas)"
            type="number"
            min={1}
            value={draft.prazoResolucaoHoras}
            onChange={(event) => updateDraft({ prazoResolucaoHoras: Number(event.target.value) })}
          />
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch
            checked={draft.considerarApenasExpediente}
            onChange={(checked) => updateDraft({ considerarApenasExpediente: checked })}
            label="Contar prazo apenas no horário de expediente"
            description="Usa o Horário de expediente configurado — fora dele, o prazo não avança."
          />
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch checked={draft.ativo} onChange={(checked) => updateDraft({ ativo: checked })} label={draft.ativo ? "Ativa" : "Inativa"} />
        </div>
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={() => onSave(draft, regra?.id)}>
          Salvar alterações
        </Button>
      </div>
    </Modal>
  );
}
