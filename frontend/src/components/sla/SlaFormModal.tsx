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
import {
  slaPrioridadeAlvoLabels,
  slaUnidadePrazoLabels,
  type SlaPrioridadeAlvo,
  type SlaRegra,
  type SlaRegraFormDraft,
  type SlaUnidadePrazo,
} from "@/types/sla";
import type { ClienteDiretorioItem } from "@/lib/api-backend";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";

const opcoesPrioridade: { value: SlaPrioridadeAlvo | ""; label: string }[] = [
  { value: "", label: "Todas as prioridades" },
  ...Object.entries(slaPrioridadeAlvoLabels).map(([value, label]) => ({ value: value as SlaPrioridadeAlvo, label })),
];

const opcoesUnidade = Object.entries(slaUnidadePrazoLabels).map(([value, label]) => ({
  value: value as SlaUnidadePrazo,
  label,
}));

function createInitialDraft(regra?: SlaRegra): SlaRegraFormDraft {
  return {
    nome: regra?.nome ?? "",
    descricao: regra?.descricao ?? "",
    prioridadeAlvo: regra?.prioridadeAlvo ?? "",
    departamentoId: regra?.departamentoId ?? "",
    clienteId: regra?.clienteId ?? "",
    prioridadeRegra: regra?.prioridadeRegra ?? 100,
    prazoPrimeiraRespostaQuantidade: regra?.prazoPrimeiraRespostaQuantidade ?? 4,
    prazoPrimeiraRespostaUnidade: regra?.prazoPrimeiraRespostaUnidade ?? "horas",
    prazoResolucaoQuantidade: regra?.prazoResolucaoQuantidade ?? 48,
    prazoResolucaoUnidade: regra?.prazoResolucaoUnidade ?? "horas",
    considerarApenasExpediente: regra?.considerarApenasExpediente ?? true,
    status: regra?.status === "inativo" ? "inativo" : "ativo",
  };
}

export function SlaFormModal({
  open,
  regra,
  departamentos,
  clientes,
  salvando,
  erro,
  onClose,
  onSave,
}: {
  open: boolean;
  regra?: SlaRegra;
  departamentos: DepartamentoDiretorioItem[];
  clientes: ClienteDiretorioItem[];
  salvando: boolean;
  erro: string | null;
  onClose: () => void;
  onSave: (draft: SlaRegraFormDraft, slaRegraId?: string) => void;
}) {
  const [draft, setDraft] = useState<SlaRegraFormDraft>(() => createInitialDraft(regra));

  const editing = regra !== undefined;
  const canSave =
    !salvando &&
    draft.nome.trim().length > 0 &&
    draft.prioridadeRegra >= 1 &&
    draft.prazoPrimeiraRespostaQuantidade > 0 &&
    draft.prazoResolucaoQuantidade > 0;

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
              Define prazos de resposta e resolução para o escopo selecionado.
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
        {erro && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </div>
        )}

        <Input label="Nome da regra" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

        <Textarea
          label="Descrição"
          rows={2}
          value={draft.descricao}
          onChange={(event) => updateDraft({ descricao: event.target.value })}
        />

        <Select
          label="Prioridade alvo"
          value={draft.prioridadeAlvo}
          onChange={(event) => updateDraft({ prioridadeAlvo: event.target.value as SlaPrioridadeAlvo | "" })}
          options={opcoesPrioridade}
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

        <div>
          <Input
            label="Precedência da regra"
            type="number"
            min={1}
            value={draft.prioridadeRegra}
            onChange={(event) => updateDraft({ prioridadeRegra: Number(event.target.value) })}
          />
          <p className="mt-1 text-xs text-zinc-400">Menor número = maior precedência.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Prazo de 1ª resposta"
            type="number"
            min={1}
            value={draft.prazoPrimeiraRespostaQuantidade}
            onChange={(event) => updateDraft({ prazoPrimeiraRespostaQuantidade: Number(event.target.value) })}
          />
          <Select
            label="Unidade — 1ª resposta"
            value={draft.prazoPrimeiraRespostaUnidade}
            onChange={(event) => updateDraft({ prazoPrimeiraRespostaUnidade: event.target.value as SlaUnidadePrazo })}
            options={opcoesUnidade}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Prazo de resolução"
            type="number"
            min={1}
            value={draft.prazoResolucaoQuantidade}
            onChange={(event) => updateDraft({ prazoResolucaoQuantidade: Number(event.target.value) })}
          />
          <Select
            label="Unidade — resolução"
            value={draft.prazoResolucaoUnidade}
            onChange={(event) => updateDraft({ prazoResolucaoUnidade: event.target.value as SlaUnidadePrazo })}
            options={opcoesUnidade}
          />
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch
            checked={draft.considerarApenasExpediente}
            onChange={(checked) => updateDraft({ considerarApenasExpediente: checked })}
            label="Considerar apenas horário de expediente"
            description="Usa o Horário de expediente configurado — fora dele, o prazo não avança."
          />
        </div>

        {editing && (
          <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
            <Switch
              checked={draft.status === "ativo"}
              onChange={(checked) => updateDraft({ status: checked ? "ativo" : "inativo" })}
              label={draft.status === "ativo" ? "Ativa" : "Inativa"}
            />
          </div>
        )}
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={() => onSave(draft, regra?.id)}>
          {salvando ? "Salvando…" : "Salvar alterações"}
        </Button>
      </div>
    </Modal>
  );
}
