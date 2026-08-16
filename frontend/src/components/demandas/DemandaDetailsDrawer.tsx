"use client";

import { useState } from "react";
import { CalendarDays, ClipboardList, FileText, FolderKanban } from "lucide-react";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DetailsModal } from "@/components/ui/DetailsModal";
import { Tabs } from "@/components/ui/Tabs";
import { formatPrazo, normalizarUsuarioId, prioridadeDemandaLabels, resolveProjetoDemandaNome, resolveProjetoResumo, statusDemandaLabels, statusDemandaTone } from "@/lib/demandas";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { resolverUsuarioPorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";
import type { Demanda, DemandaPrioridade } from "@/types/demanda";
import { AtividadeDemandaSection } from "./AtividadeDemandaSection";
import { DemandaConclusaoBanner } from "./DemandaConclusaoBanner";
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
  { id: "atividade", label: "Atividade" },
  { id: "historico", label: "Histórico" },
];


const prioridadeTone: Record<DemandaPrioridade, BadgeTone> = {
  alta: "blue",
  media: "blue",
  baixa: "neutral",
};

export function DemandaDetailsDrawer({
  demanda,
  onClose,
  onEdit,
  onChange,
  initialTab,
}: {
  demanda?: Demanda;
  onClose: () => void;
  onEdit: (demandaId: string) => void;
  onChange: (demanda: Demanda) => void;
  initialTab?: string;
}) {
  const [activeTab, setActiveTab] = useState(initialTab ?? "dados");
  const { usuarios } = useDiretorioUsuarios();

  return (
    <DetailsModal
      open={demanda !== undefined}
      onClose={onClose}
      onEdit={demanda ? () => onEdit(demanda.id) : undefined}
      editLabel="Editar tarefa"
      title={demanda?.nome ?? "Tarefa"}
      description={demanda ? `${rotuloDemanda(demanda)} · ${resolveProjetoDemandaNome(demanda.projetoId)}` : undefined}
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
          <DemandaConclusaoBanner demanda={demanda} onChange={onChange} />

          <div className="rounded-2xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
                  <ClipboardList className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">Painel da tarefa</p>
                  <h3 className="mt-1 text-lg font-semibold text-zinc-950 dark:text-zinc-50">{demanda.nome}</h3>
                  <p className="mt-1 flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
                    <FolderKanban className="h-4 w-4" />
                    {resolveProjetoDemandaNome(demanda.projetoId)}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                <Badge tone={prioridadeTone[demanda.prioridade]}>{prioridadeDemandaLabels[demanda.prioridade]}</Badge>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-white p-3 ring-1 ring-zinc-100 dark:bg-zinc-900 dark:ring-zinc-800">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Prazo atual</p>
                <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                  <CalendarDays className="h-4 w-4 text-zinc-400" />
                  {formatPrazo(demanda.prazoEtapaAtual)}
                </p>
              </div>
              <div className="rounded-xl bg-white p-3 ring-1 ring-zinc-100 dark:bg-zinc-900 dark:ring-zinc-800 sm:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Responsáveis</p>
                <div className="mt-2">
                  <AvatarStack
                    pessoas={demanda.usuarioResponsavelIds
                      .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
                      .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario))
                      .map((usuario) => ({
                        id: usuario.id,
                        nome: usuario.nome,
                        corIdentificacao: usuario.corIdentificacao,
                        fotoUrl: usuario.fotoUrl,
                      }))}
                    max={5}
                    size="h-7 w-7"
                  />
                </div>
              </div>
            </div>
          </div>

          {resolveProjetoResumo(demanda.projetoId) && (
            <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-500/20 dark:bg-indigo-500/5">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-indigo-600 ring-1 ring-indigo-100 dark:bg-zinc-900 dark:text-indigo-400 dark:ring-indigo-500/20">
                  <FileText className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-500 dark:text-indigo-400">
                    Resumo do projeto
                  </p>
                  <p className="mt-1 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
                    {resolveProjetoResumo(demanda.projetoId)}
                  </p>
                </div>
              </div>
            </div>
          )}

          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          {activeTab === "dados" && <DadosDemandaSection demanda={demanda} onChange={onChange} />}
          {activeTab === "briefing" && <BriefingDemandaSection key={demanda.id} demanda={demanda} onChange={onChange} />}
          {activeTab === "workflow" && <WorkflowDemandaSection demanda={demanda} />}
          {activeTab === "responsaveis" && <ResponsaveisDemandaSection demanda={demanda} onChange={onChange} />}
          {activeTab === "atividade" && <AtividadeDemandaSection demanda={demanda} />}
          {activeTab === "historico" && <HistoricoDemandaSection demanda={demanda} />}
        </div>
      )}
    </DetailsModal>
  );
}
