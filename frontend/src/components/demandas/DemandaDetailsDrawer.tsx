"use client";

import { useState } from "react";
import { CalendarDays, ClipboardList, FolderKanban, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { StatusPill } from "@/components/ui/StatusPill";
import { Tabs } from "@/components/ui/Tabs";
import { WorkspaceSummaryHeader, WorkspaceSummaryStat } from "@/components/ui/WorkspaceSummaryPanel";
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
          <WorkspaceSummaryHeader
            icon={<ClipboardList className="h-5 w-5" />}
            eyebrow="Painel da demanda"
            title={demanda.nome}
            subtitle={
              <>
                <FolderKanban className="h-4 w-4" />
                {resolveProjetoDemandaNome(demanda.projetoId)}
              </>
            }
            badges={
              <>
                <StatusPill tone={statusTone[demanda.status]}>
                  {statusDemandaLabels[demanda.status]}
                </StatusPill>
                <StatusPill tone={prioridadeTone[demanda.prioridade]}>
                  {prioridadeDemandaLabels[demanda.prioridade]}
                </StatusPill>
              </>
            }
          >
            <WorkspaceSummaryStat
              label="Prazo atual"
              icon={<CalendarDays className="h-4 w-4 text-zinc-400" />}
              value={demanda.prazoEtapaAtual}
            />
            <WorkspaceSummaryStat
              label="Responsáveis"
              icon={<UsersRound className="h-4 w-4 text-zinc-400" />}
              value={resolveResponsaveisProjetoNomes(demanda.usuarioResponsavelIds)}
              wide
            />
          </WorkspaceSummaryHeader>

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
