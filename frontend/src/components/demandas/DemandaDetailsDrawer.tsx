"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { Tabs } from "@/components/ui/Tabs";
import {
  prioridadeDemandaLabels,
  resolveProjetoDemandaNome,
  statusDemandaLabels,
} from "@/lib/demandas-mock";
import type { Demanda } from "@/types/demanda";
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
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700">
              {statusDemandaLabels[demanda.status]}
            </span>
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700">
              {prioridadeDemandaLabels[demanda.prioridade]}
            </span>
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
