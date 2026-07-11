"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { Tabs } from "@/components/ui/Tabs";
import {
  prioridadeProjetoLabels,
  resolveClienteProjetoNome,
  statusProjetoLabels,
} from "@/lib/projetos-mock";
import type { Projeto } from "@/types/projeto";
import {
  ArquivosProjetoSection,
  DadosProjetoSection,
  EquipeProjetoSection,
  HistoricoProjetoSection,
  ModeloCampanhaSection,
  ResumoProjetoSection,
} from "./ProjetoFormSections";

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "resumo", label: "Resumo" },
  { id: "modelo", label: "Modelo de Campanha" },
  { id: "equipe", label: "Equipe" },
  { id: "arquivos", label: "Arquivos" },
  { id: "historico", label: "Histórico" },
];

type ProjetoDetailsDrawerProps = {
  projeto?: Projeto;
  onClose: () => void;
  onEdit: (projetoId: string) => void;
  onChange: (projeto: Projeto) => void;
};

export function ProjetoDetailsDrawer({
  projeto,
  onClose,
  onEdit,
  onChange,
}: ProjetoDetailsDrawerProps) {
  const [activeTab, setActiveTab] = useState("dados");

  return (
    <EntitySidePanel
      open={projeto !== undefined}
      onClose={onClose}
      onEdit={projeto ? () => onEdit(projeto.id) : undefined}
      editLabel="Editar projeto"
      title={projeto?.nome ?? "Projeto"}
      description={
        projeto
          ? `${projeto.codigoInterno} · ${resolveClienteProjetoNome(
              projeto.clienteId
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
      {projeto && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700">
              {statusProjetoLabels[projeto.status]}
            </span>
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700">
              {prioridadeProjetoLabels[projeto.prioridade]}
            </span>
          </div>

          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          {activeTab === "dados" && (
            <DadosProjetoSection projeto={projeto} onChange={onChange} />
          )}

          {activeTab === "resumo" && (
            <ResumoProjetoSection projeto={projeto} onChange={onChange} />
          )}

          {activeTab === "modelo" && (
            <ModeloCampanhaSection projeto={projeto} onChange={onChange} />
          )}

          {activeTab === "equipe" && (
            <EquipeProjetoSection projeto={projeto} onChange={onChange} />
          )}

          {activeTab === "arquivos" && <ArquivosProjetoSection />}

          {activeTab === "historico" && (
            <HistoricoProjetoSection projeto={projeto} />
          )}
        </div>
      )}
    </EntitySidePanel>
  );
}
