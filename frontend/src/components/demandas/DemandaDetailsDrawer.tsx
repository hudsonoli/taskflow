"use client";

import { useState } from "react";
import { CalendarDays, ClipboardList, FolderKanban, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { StatusPill } from "@/components/ui/StatusPill";
import { Tabs } from "@/components/ui/Tabs";
import {
  prioridadeDemandaLabels,
  resolveProjetoDemandaNome,
  resolveResponsaveisProjetoNomes,
  statusDemandaLabels,
} from "@/lib/demandas-mock";
import type { Demanda, DemandaPrioridade, DemandaStatus } from "@/types/demanda";
import {
  BriefingDemandaSection,
  DadosDemandaSection,
  HistoricoDemandaSection,
  ResponsaveisDemandaSection,
  WorkflowDemandaSection,
} from "./DemandaFormSections";

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "briefing", label: "Briefing" },
  { id: "workflow", label: "Workflow" },
  { id: "responsaveis", label: "Responsáveis" },
  { id: "historico", label: "Histórico" },
];

const statusTone: Record<DemandaStatus, "neutral" | "blue" | "green" | "amber" | "red"> = {
  rascunho: "neutral",
  planejada: "blue",
  em_execucao: "green",
  pausada: "amber",
  bloqueada: "red",
  aguardando_cliente: "amber",
  concluida: "green",
  cancelada: "neutral",
};

const prioridadeTone: Record<DemandaPrioridade, "neutral" | "blue" | "green" | "amber" | "red"> = {
  alta: "blue",
  media: "blue",
  baixa: "neutral",
};

type DemandaDetailsDrawerProps = {
  demanda?: Demanda;
  onClose: () => void;
  onEdit: (demandaId: string) => void;
  onChange: (demanda: Demanda) => void;
};

export function DemandaDetailsDrawer({
  demanda,
  onClose,
  onEdit,
  onChange,
}: DemandaDetailsDrawerProps) {
  const [activeTab, setActiveTab] = useState("dados");

  return (
    <EntitySidePanel
      open={demanda !== undefined}
      onClose={onClose}
      onEdit={demanda ? () => onEdit(demanda.id) : undefined}
      editLabel="Editar demanda"
      title={demanda?.nome ?? "Demanda"}
      description={
        demanda
          ? `${demanda.codigoInterno} · ${resolveProjetoDemandaNome(
              demanda.projetoId
            )}`
          : undefined
      }
      footer={
        <div className="flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      }
    >
      {demanda && (
        <div className="space-y-5">
          <div className="rounded-3xl border border-zinc-100 bg-zinc-50/70 p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-700 ring-1 ring-blue-100">
                  <ClipboardList className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
                    Painel da demanda
                  </p>
                  <h3 className="mt-1 text-lg font-semibold text-zinc-950">
                    {demanda.nome}
                  </h3>
                  <p className="mt-1 flex items-center gap-2 text-sm text-zinc-500">
                    <FolderKanban className="h-4 w-4" />
                    {resolveProjetoDemandaNome(demanda.projetoId)}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusPill tone={statusTone[demanda.status]}>
                  {statusDemandaLabels[demanda.status]}
                </StatusPill>
                <StatusPill tone={prioridadeTone[demanda.prioridade]}>
                  {prioridadeDemandaLabels[demanda.prioridade]}
                </StatusPill>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-white p-3 ring-1 ring-zinc-100">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
                  Prazo atual
                </p>
                <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-zinc-800">
                  <CalendarDays className="h-4 w-4 text-zinc-400" />
                  {demanda.prazoEtapaAtual}
                </p>
              </div>
              <div className="rounded-2xl bg-white p-3 ring-1 ring-zinc-100 sm:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
                  Responsáveis
                </p>
                <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-zinc-800">
                  <UsersRound className="h-4 w-4 text-zinc-400" />
                  {resolveResponsaveisProjetoNomes(demanda.usuarioResponsavelIds)}
                </p>
              </div>
            </div>
          </div>

          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          {activeTab === "dados" && (
            <DadosDemandaSection demanda={demanda} onChange={onChange} />
          )}
          {activeTab === "briefing" && (
            <BriefingDemandaSection demanda={demanda} onChange={onChange} />
          )}
          {activeTab === "workflow" && (
            <WorkflowDemandaSection demanda={demanda} onChange={onChange} />
          )}
          {activeTab === "responsaveis" && (
            <ResponsaveisDemandaSection demanda={demanda} onChange={onChange} />
          )}
          {activeTab === "historico" && (
            <HistoricoDemandaSection demanda={demanda} />
          )}
        </div>
      )}
    </EntitySidePanel>
  );
}
