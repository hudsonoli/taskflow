"use client";

import { CalendarDays, CheckCircle2, CircleDot, Plus, Trash2, UsersRound } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Select } from "@/components/ui/Select";
import {
  departamentosProjetoDisponiveis,
  generateId,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  responsaveisProjetoDisponiveis,
  workflowEtapaStatusLabels,
} from "@/lib/demandas-mock";
import type { DemandaWorkflowEtapa, DemandaWorkflowEtapaStatus } from "@/types/demanda";
import { workflowEtapaTipoLabels } from "@/types/workflow-modelo";

const workflowStatusTone: Record<DemandaWorkflowEtapaStatus, BadgeTone> = {
  pendente: "neutral",
  em_execucao: "green",
  pausada: "amber",
  concluida: "green",
};

function createWorkflowEtapa(ordem: number): DemandaWorkflowEtapa {
  return {
    id: generateId("etapa-demanda"),
    nome: "Nova etapa",
    ordem,
    usuarioResponsavelIds: [],
    departamentoResponsavelIds: [],
    prazoHoras: 8,
    status: "pendente",
  };
}

export function WorkflowEtapasEditor({
  etapas,
  etapaAtualId,
  onEtapasChange,
  onEtapaAtualChange,
}: {
  etapas: DemandaWorkflowEtapa[];
  etapaAtualId: string;
  onEtapasChange: (etapas: DemandaWorkflowEtapa[]) => void;
  onEtapaAtualChange: (id: string) => void;
}) {
  function updateEtapa(etapaId: string, patch: Partial<DemandaWorkflowEtapa>) {
    onEtapasChange(etapas.map((etapa) => (etapa.id === etapaId ? { ...etapa, ...patch } : etapa)));
  }

  function removeEtapa(etapaId: string) {
    const nextEtapas = etapas.filter((etapa) => etapa.id !== etapaId).map((etapa, index) => ({ ...etapa, ordem: index + 1 }));
    onEtapasChange(nextEtapas);
    if (etapaAtualId === etapaId) {
      onEtapaAtualChange(nextEtapas[0]?.id ?? "");
    }
  }

  function addEtapa() {
    const novaEtapa = createWorkflowEtapa(etapas.length + 1);
    onEtapasChange([...etapas, novaEtapa]);
    if (!etapaAtualId) {
      onEtapaAtualChange(novaEtapa.id);
    }
  }

  const totalEtapas = etapas.length;
  const etapasConcluidas = etapas.filter((etapa) => etapa.status === "concluida").length;
  const progressoEtapas = totalEtapas ? Math.round((etapasConcluidas / totalEtapas) * 100) : 0;
  const etapaAtual = etapas.find((etapa) => etapa.id === etapaAtualId);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="blue">{totalEtapas} etapa(s)</Badge>
          <Badge tone={etapaAtual ? workflowStatusTone[etapaAtual.status] : "neutral"}>
            {etapaAtual ? etapaAtual.nome : "Sem etapa atual"}
          </Badge>
          {totalEtapas > 0 && <Badge tone="green">{etapasConcluidas} concluída(s)</Badge>}
        </div>
        <Button type="button" onClick={addEtapa} className="px-3 py-1.5 text-xs">
          <Plus className="h-3.5 w-3.5" />
          Adicionar etapa
        </Button>
      </div>

      {totalEtapas > 0 && (
        <div className="mb-4 rounded-xl bg-zinc-50/70 p-2.5 ring-1 ring-zinc-100 dark:bg-zinc-950/40 dark:ring-zinc-800">
          <ProgressBar value={progressoEtapas} tone="green" label="Etapas concluídas" />
        </div>
      )}

      <div className="space-y-4">
        {etapas.map((etapa) => {
          const etapaAtualSelecionada = etapaAtualId === etapa.id;

          return (
            <div
              key={etapa.id}
              className={`rounded-2xl border p-3.5 transition ${
                etapaAtualSelecionada
                  ? "border-indigo-200 bg-indigo-50/40 dark:border-indigo-500/30 dark:bg-indigo-500/5"
                  : "border-zinc-100 bg-zinc-50/60 dark:border-zinc-800 dark:bg-zinc-950/30"
              }`}
            >
              <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 ${
                      etapaAtualSelecionada
                        ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white ring-indigo-500"
                        : etapa.status === "concluida"
                          ? "bg-emerald-50 text-emerald-700 ring-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20"
                          : etapa.tipo === "aprovacao"
                            ? "bg-amber-50 text-amber-700 ring-amber-100 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20"
                            : etapa.tipo === "execucao"
                              ? "bg-indigo-50 text-indigo-700 ring-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-500/20"
                              : "bg-white text-zinc-500 ring-zinc-100 dark:bg-zinc-900 dark:ring-zinc-800"
                    }`}
                  >
                    {etapa.status === "concluida" ? <CheckCircle2 className="h-5 w-5" /> : <CircleDot className="h-5 w-5" />}
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={workflowStatusTone[etapa.status]}>Etapa {etapa.ordem}</Badge>
                      {etapaAtualSelecionada && <Badge tone="blue">Etapa atual</Badge>}
                      {etapa.tipo && <Badge tone={etapa.tipo === "aprovacao" ? "amber" : "blue"}>{workflowEtapaTipoLabels[etapa.tipo]}</Badge>}
                    </div>
                    <p className="mt-1.5 text-sm font-semibold text-zinc-950 dark:text-zinc-50">{etapa.nome}</p>
                    <div className="mt-1.5 flex flex-wrap gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 font-medium ring-1 ring-zinc-100 dark:bg-zinc-900 dark:ring-zinc-800">
                        <CalendarDays className="h-3.5 w-3.5" />
                        {etapa.prazoHoras}h
                      </span>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 font-medium ring-1 ring-zinc-100 dark:bg-zinc-900 dark:ring-zinc-800">
                        <UsersRound className="h-3.5 w-3.5" />
                        {resolveResponsaveisProjetoNomes(etapa.usuarioResponsavelIds) || "Sem usuário"}
                      </span>
                    </div>
                  </div>
                </div>

                <Button type="button" variant="secondary" onClick={() => removeEtapa(etapa.id)} className="px-3 py-1.5 text-xs">
                  <Trash2 className="h-3.5 w-3.5" />
                  Remover
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <Input label="Nome da etapa" value={etapa.nome} onChange={(event) => updateEtapa(etapa.id, { nome: event.target.value })} />
                <Input
                  label="Prazo em horas"
                  type="number"
                  min={1}
                  value={etapa.prazoHoras}
                  onChange={(event) => updateEtapa(etapa.id, { prazoHoras: Number(event.target.value) })}
                />
                <Select
                  label="Status da etapa"
                  value={etapa.status}
                  onChange={(event) => updateEtapa(etapa.id, { status: event.target.value as DemandaWorkflowEtapaStatus })}
                  options={Object.entries(workflowEtapaStatusLabels).map(([value, label]) => ({ value, label }))}
                />
                <Select
                  label="Etapa atual"
                  value={etapaAtualId === etapa.id ? etapa.id : ""}
                  onChange={() => onEtapaAtualChange(etapa.id)}
                  options={[
                    { value: "", label: "Não" },
                    { value: etapa.id, label: "Sim" },
                  ]}
                />
                <Select
                  label="Tipo da etapa"
                  value={etapa.tipo ?? ""}
                  onChange={(event) => updateEtapa(etapa.id, { tipo: event.target.value ? (event.target.value as "execucao" | "aprovacao") : undefined })}
                  options={[{ value: "", label: "Não classificada" }, ...Object.entries(workflowEtapaTipoLabels).map(([value, label]) => ({ value, label }))]}
                />
              </div>

              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <MultiSelect
                  label="Usuários da etapa"
                  values={etapa.usuarioResponsavelIds}
                  onChange={(values) => updateEtapa(etapa.id, { usuarioResponsavelIds: values })}
                  options={responsaveisProjetoDisponiveis.map((responsavel) => ({ value: responsavel.id, label: responsavel.nome }))}
                />
                <MultiSelect
                  label="Departamentos da etapa"
                  values={etapa.departamentoResponsavelIds}
                  onChange={(values) => updateEtapa(etapa.id, { departamentoResponsavelIds: values })}
                  options={departamentosProjetoDisponiveis.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
                />
              </div>

              <div className="mt-3 rounded-xl bg-white p-2.5 text-xs text-zinc-500 ring-1 ring-zinc-100 dark:bg-zinc-900 dark:text-zinc-400 dark:ring-zinc-800">
                Departamentos: {resolveDepartamentosProjetoNomes(etapa.departamentoResponsavelIds) || "Sem departamento"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
