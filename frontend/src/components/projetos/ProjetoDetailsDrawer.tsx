"use client";

import { useState } from "react";
import { CalendarDays, FolderKanban, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { StatusPill } from "@/components/ui/StatusPill";
import { Tabs } from "@/components/ui/Tabs";
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
          <div className="rounded-3xl border border-zinc-100 bg-zinc-50/70 p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-700 ring-1 ring-blue-100">
                  <FolderKanban className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
                    Painel do projeto
                  </p>
                  <h3 className="mt-1 text-lg font-semibold text-zinc-950">
                    {projeto.campanha}
                  </h3>
                  <p className="mt-1 text-sm text-zinc-500">
                    {resolveClienteProjetoNome(projeto.clienteId)}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusPill tone={statusTone[projeto.status]}>
                  {statusProjetoLabels[projeto.status]}
                </StatusPill>
                <StatusPill tone="blue">
                  {prioridadeProjetoLabels[projeto.prioridade]}
                </StatusPill>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-white p-3 ring-1 ring-zinc-100">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
                  Prazo
                </p>
                <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-zinc-800">
                  <CalendarDays className="h-4 w-4 text-zinc-400" />
                  {projeto.dataFimPrevista}
                </p>
              </div>
              <div className="rounded-2xl bg-white p-3 ring-1 ring-zinc-100 sm:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
                  Responsáveis
                </p>
                <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-zinc-800">
                  <UsersRound className="h-4 w-4 text-zinc-400" />
                  {resolveResponsaveisProjetoNomes(projeto.responsavelIds)}
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {resolveDepartamentosProjetoNomes(
                    projeto.departamentoResponsavelIds
                  )}
                </p>
              </div>
            </div>
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
