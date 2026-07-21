"use client";

import { useState } from "react";
import { CalendarDays, FolderKanban, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { StatusPill } from "@/components/ui/StatusPill";
import { Tabs } from "@/components/ui/Tabs";
import { WorkspaceSummaryHeader, WorkspaceSummaryStat } from "@/components/ui/WorkspaceSummaryPanel";
import {
  prioridadeProjetoLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  statusProjetoLabels,
} from "@/lib/projetos-mock";
import type { Projeto, ProjetoStatus } from "@/types/projeto";
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

const statusTone: Record<ProjetoStatus, "neutral" | "blue" | "green" | "amber" | "red"> = {
  planejamento: "blue",
  ativo: "green",
  pausado: "amber",
  concluido: "green",
  cancelado: "neutral",
};

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
        <div className="space-y-5">
          <WorkspaceSummaryHeader
            icon={<FolderKanban className="h-5 w-5" />}
            eyebrow="Painel do projeto"
            title={projeto.campanha}
            subtitle={resolveClienteProjetoNome(projeto.clienteId)}
            badges={
              <>
                <StatusPill tone={statusTone[projeto.status]}>
                  {statusProjetoLabels[projeto.status]}
                </StatusPill>
                <StatusPill tone="blue">
                  {prioridadeProjetoLabels[projeto.prioridade]}
                </StatusPill>
              </>
            }
          >
            <WorkspaceSummaryStat
              label="Prazo"
              icon={<CalendarDays className="h-4 w-4 text-zinc-400" />}
              value={projeto.dataFimPrevista}
            />
            <WorkspaceSummaryStat
              label="Responsáveis"
              icon={<UsersRound className="h-4 w-4 text-zinc-400" />}
              value={resolveResponsaveisProjetoNomes(projeto.responsavelIds)}
              footer={resolveDepartamentosProjetoNomes(
                projeto.departamentoResponsavelIds
              )}
              wide
            />
          </WorkspaceSummaryHeader>

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
