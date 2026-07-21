"use client";

import { useState } from "react";
import {
  Building2,
  CalendarDays,
  ClipboardList,
  FolderKanban,
  Gauge,
  Users,
  UsersRound,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { StatusPill } from "@/components/ui/StatusPill";
import { Tabs } from "@/components/ui/Tabs";
import { WorkspaceSummaryHeader, WorkspaceSummaryStat } from "@/components/ui/WorkspaceSummaryPanel";
import { demandasMock } from "@/lib/demandas-mock";
import {
  prioridadeProjetoLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  statusProjetoLabels,
} from "@/lib/projetos-mock";
import type { Projeto, ProjetoStatus } from "@/types/projeto";
import { ProjetoDemandasSection } from "./ProjetoDemandasSection";
import {
  AprovacoesProjetoSection,
  ArquivosProjetoSection,
  ChecklistProjetoSection,
  ComentariosProjetoSection,
  DadosProjetoSection,
  EquipeProjetoSection,
  HistoricoProjetoSection,
  ModeloCampanhaSection,
  ResumoProjetoSection,
  TimelineProjetoSection,
} from "./ProjetoFormSections";

const tabs = [
  { id: "dados", label: "Dados Gerais" },
  { id: "resumo", label: "Resumo" },
  { id: "equipe", label: "Equipe" },
  { id: "demandas", label: "Demandas" },
  { id: "modelo", label: "Modelo de Campanha" },
  { id: "timeline", label: "Timeline" },
  { id: "comentarios", label: "Comentários" },
  { id: "checklist", label: "Checklist" },
  { id: "arquivos", label: "Arquivos" },
  { id: "aprovacoes", label: "Aprovações" },
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
      {projeto && (() => {
        const projetoDemandas = demandasMock.filter(
          (demanda) => demanda.projetoId === projeto.id
        );
        const demandasConcluidas = projetoDemandas.filter(
          (demanda) => demanda.status === "concluida"
        ).length;
        const progresso =
          projetoDemandas.length > 0
            ? Math.round((demandasConcluidas / projetoDemandas.length) * 100)
            : null;

        return (
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
              label="Demandas"
              icon={<ClipboardList className="h-4 w-4 text-zinc-400" />}
              value={projetoDemandas.length}
            />
            <WorkspaceSummaryStat
              label="Progresso"
              icon={<Gauge className="h-4 w-4 text-zinc-400" />}
              value={progresso === null ? "-" : `${progresso}%`}
            />
            <WorkspaceSummaryStat
              label="Responsáveis"
              icon={<UsersRound className="h-4 w-4 text-zinc-400" />}
              value={resolveResponsaveisProjetoNomes(projeto.responsavelIds)}
              wide
            />
            <WorkspaceSummaryStat
              label="Equipe"
              icon={<Users className="h-4 w-4 text-zinc-400" />}
              value={`${projeto.equipe.length} ${projeto.equipe.length === 1 ? "membro" : "membros"}`}
            />
            <WorkspaceSummaryStat
              label="Departamento"
              icon={<Building2 className="h-4 w-4 text-zinc-400" />}
              value={resolveDepartamentosProjetoNomes(
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

          {activeTab === "equipe" && (
            <EquipeProjetoSection projeto={projeto} onChange={onChange} />
          )}

          {activeTab === "demandas" && (
            <ProjetoDemandasSection demandas={projetoDemandas} />
          )}

          {activeTab === "modelo" && (
            <ModeloCampanhaSection projeto={projeto} onChange={onChange} />
          )}

          {activeTab === "timeline" && (
            <TimelineProjetoSection projeto={projeto} />
          )}

          {activeTab === "comentarios" && (
            <ComentariosProjetoSection projeto={projeto} onChange={onChange} />
          )}

          {activeTab === "checklist" && (
            <ChecklistProjetoSection projeto={projeto} onChange={onChange} />
          )}

          {activeTab === "arquivos" && <ArquivosProjetoSection projeto={projeto} />}

          {activeTab === "aprovacoes" && (
            <AprovacoesProjetoSection projeto={projeto} />
          )}

          {activeTab === "historico" && (
            <HistoricoProjetoSection projeto={projeto} />
          )}
        </div>
        );
      })()}
    </EntitySidePanel>
  );
}
