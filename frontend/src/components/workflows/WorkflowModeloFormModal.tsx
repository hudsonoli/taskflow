"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Flag, Plus, Trash2, Workflow as WorkflowIcon, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { generateId } from "@/lib/workflow-modelos-mock";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { normalizarReferenciasParaCodigoInterno } from "@/lib/referencias";
import {
  workflowEtapaTipoLabels,
  workflowUnidadePrazoLabels,
  type WorkflowEtapaTipo,
  type WorkflowModelo,
  type WorkflowModeloEtapa,
  type WorkflowModeloFormDraft,
  type WorkflowUnidadePrazo,
} from "@/types/workflow-modelo";

function createEtapa(): WorkflowModeloEtapa {
  return {
    id: generateId("etapa-modelo"),
    nome: "Nova etapa",
    tipo: "execucao",
    quantidadeAntesDeadline: 1,
    unidadePrazo: "dias_corridos",
    usuarioResponsavelIds: [],
  };
}

function createInitialDraft(modelo?: WorkflowModelo): WorkflowModeloFormDraft {
  return {
    nome: modelo?.nome ?? "",
    ativo: modelo?.ativo ?? true,
    etapas: modelo?.etapas ?? [createEtapa()],
  };
}

export function WorkflowModeloFormModal({
  open,
  modelo,
  onClose,
  onSave,
}: {
  open: boolean;
  modelo?: WorkflowModelo;
  onClose: () => void;
  onSave: (draft: WorkflowModeloFormDraft, modeloId?: string) => void;
}) {
  const { usuarios } = useDiretorioUsuarios();
  const [draft, setDraft] = useState<WorkflowModeloFormDraft>(() => createInitialDraft(modelo));
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());

  const editing = modelo !== undefined;
  const canSave = draft.nome.trim().length > 0 && draft.etapas.length > 0;
  const todasExpandidas = draft.etapas.length > 0 && draft.etapas.every((etapa) => expandedIds.has(etapa.id));

  // Picker só oferece usuário ativo; grava codigoInterno enquanto Workflow continuar mock —
  // ver docs/padrao-arquivamento.md / lib/referencias.ts.
  const memberOptions = usuarios
    .filter((usuario) => usuario.status === "ativo")
    .map((usuario) => ({
      id: usuario.codigoInterno,
      nome: usuario.nome,
      corIdentificacao: usuario.corIdentificacao,
      fotoUrl: usuario.fotoUrl,
    }));

  function updateDraft(patch: Partial<WorkflowModeloFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function updateEtapa(etapaId: string, patch: Partial<WorkflowModeloEtapa>) {
    updateDraft({ etapas: draft.etapas.map((etapa) => (etapa.id === etapaId ? { ...etapa, ...patch } : etapa)) });
  }

  function toggleExpanded(etapaId: string) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(etapaId)) next.delete(etapaId);
      else next.add(etapaId);
      return next;
    });
  }

  function toggleExpandirTudo() {
    setExpandedIds(todasExpandidas ? new Set() : new Set(draft.etapas.map((etapa) => etapa.id)));
  }

  function addEtapa() {
    const novaEtapa = createEtapa();
    updateDraft({ etapas: [...draft.etapas, novaEtapa] });
    setExpandedIds((current) => new Set(current).add(novaEtapa.id));
  }

  function removeEtapa(etapaId: string) {
    updateDraft({ etapas: draft.etapas.filter((etapa) => etapa.id !== etapaId) });
  }

  function moveEtapa(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= draft.etapas.length) return;
    const proximo = [...draft.etapas];
    [proximo[index], proximo[target]] = [proximo[target], proximo[index]];
    updateDraft({ etapas: proximo });
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-2xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <WorkflowIcon className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${modelo.nome}` : "Novo workflow"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Modelo reutilizável de etapas — aplicado ao criar uma nova tarefa.
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
        <Input label="Nome do modelo de workflow" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

        <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch checked={draft.ativo} onChange={(checked) => updateDraft({ ativo: checked })} label={draft.ativo ? "Ativo" : "Inativo"} description="Modelos inativos não aparecem no cadastro de tarefas." />
        </div>

        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Etapas</p>
          <button
            type="button"
            onClick={toggleExpandirTudo}
            className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {todasExpandidas ? "Recolher tudo" : "Expandir tudo"}
          </button>
        </div>

        <div className="space-y-3">
          {draft.etapas.map((etapa, index) => {
            const expanded = expandedIds.has(etapa.id);
            const etapaResponsaveisNormalizados = normalizarReferenciasParaCodigoInterno(etapa.usuarioResponsavelIds, usuarios);
            const responsaveisSelecionados = memberOptions.filter((option) => etapaResponsaveisNormalizados.includes(option.id));
            const tone = etapa.tipo === "aprovacao" ? "amber" : "indigo";

            return (
              <div
                key={etapa.id}
                className={`overflow-hidden rounded-2xl border ${
                  tone === "amber"
                    ? "border-amber-200 dark:border-amber-500/30"
                    : "border-indigo-200 dark:border-indigo-500/30"
                }`}
              >
                <div
                  className={`flex items-center gap-3 px-3.5 py-2.5 ${
                    tone === "amber"
                      ? "bg-amber-50 dark:bg-amber-500/10"
                      : "bg-indigo-50 dark:bg-indigo-500/10"
                  }`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white ${
                      tone === "amber" ? "bg-amber-500" : "bg-indigo-500"
                    }`}
                  >
                    {index + 1}
                  </span>
                  <button type="button" onClick={() => toggleExpanded(etapa.id)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
                    <span className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">{etapa.nome || "Nova etapa"}</span>
                    <span className="shrink-0 text-xs text-zinc-500 dark:text-zinc-400">
                      {etapa.quantidadeAntesDeadline} {workflowUnidadePrazoLabels[etapa.unidadePrazo].toLowerCase()} antes do deadline
                    </span>
                  </button>

                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => moveEtapa(index, -1)}
                      disabled={index === 0}
                      aria-label="Mover para cima"
                      className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/70 disabled:opacity-30 dark:hover:bg-zinc-900/40"
                    >
                      <ChevronUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => moveEtapa(index, 1)}
                      disabled={index === draft.etapas.length - 1}
                      aria-label="Mover para baixo"
                      className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/70 disabled:opacity-30 dark:hover:bg-zinc-900/40"
                    >
                      <ChevronDown className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => removeEtapa(etapa.id)}
                      aria-label="Remover etapa"
                      className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/70 hover:text-red-600 dark:hover:bg-zinc-900/40"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleExpanded(etapa.id)}
                      aria-label={expanded ? "Recolher etapa" : "Expandir etapa"}
                      className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/70 dark:hover:bg-zinc-900/40"
                    >
                      <ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} />
                    </button>
                  </div>
                </div>

                {expanded && (
                  <div className="flex flex-col gap-3 bg-white p-3.5 dark:bg-zinc-900">
                    <Input label="Nome da etapa" value={etapa.nome} onChange={(event) => updateEtapa(etapa.id, { nome: event.target.value })} />

                    <div className="grid gap-3 sm:grid-cols-3">
                      <Input
                        label="Quantidade antes do deadline"
                        type="number"
                        min={0}
                        value={etapa.quantidadeAntesDeadline}
                        onChange={(event) => updateEtapa(etapa.id, { quantidadeAntesDeadline: Number(event.target.value) })}
                      />
                      <Select
                        label="Unidade"
                        value={etapa.unidadePrazo}
                        onChange={(event) => updateEtapa(etapa.id, { unidadePrazo: event.target.value as WorkflowUnidadePrazo })}
                        options={Object.entries(workflowUnidadePrazoLabels).map(([value, label]) => ({ value, label }))}
                      />
                      <Select
                        label="Tipo da etapa"
                        value={etapa.tipo}
                        onChange={(event) => updateEtapa(etapa.id, { tipo: event.target.value as WorkflowEtapaTipo })}
                        options={Object.entries(workflowEtapaTipoLabels).map(([value, label]) => ({ value, label }))}
                      />
                    </div>

                    <MemberSelector
                      label="Responsáveis padrão"
                      values={normalizarReferenciasParaCodigoInterno(etapa.usuarioResponsavelIds, usuarios)}
                      onChange={(values) => updateEtapa(etapa.id, { usuarioResponsavelIds: values })}
                      placeholder="Selecionar responsáveis…"
                      options={memberOptions}
                    />
                    {responsaveisSelecionados.length === 0 && (
                      <p className="text-xs text-zinc-400">Sem responsável padrão — definido na tarefa ao aplicar o modelo.</p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <Button type="button" variant="secondary" onClick={addEtapa} className="self-center px-4 py-2 text-xs">
          <Plus className="h-3.5 w-3.5" />
          Nova etapa do workflow
        </Button>

        <div className="flex items-center gap-3 rounded-2xl border border-dashed border-emerald-200 bg-emerald-50/60 px-3.5 py-2.5 text-sm font-medium text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/5 dark:text-emerald-400">
          <Flag className="h-4 w-4" />
          Finalizado
        </div>
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={() => onSave(draft, modelo?.id)}>
          Salvar
        </Button>
      </div>
    </Modal>
  );
}
