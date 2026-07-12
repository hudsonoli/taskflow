"use client";

import { useMemo, useState } from "react";
import { ClipboardList } from "lucide-react";
import { StatusPill } from "@/components/ui/StatusPill";
import { WorkspaceEmptyState } from "@/components/workspace/WorkspaceEmptyState";
import { WorkspacePage } from "@/components/workspace/WorkspacePage";
import {
  AGENCIA_PADRAO_ID,
  EMPRESA_PADRAO_ID,
  demandasMock,
  generateCodigoInterno,
  generateId,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveProjetoDemandaNome,
  resolveResponsaveisProjetoNomes,
} from "@/lib/demandas-mock";
import type {
  Demanda,
  DemandaFormDraft,
  DemandaWorkflowEtapa,
} from "@/types/demanda";
import { DemandaDetailsDrawer } from "./DemandaDetailsDrawer";
import { DemandasKanban } from "./DemandasKanban";
import { DemandasStats } from "./DemandasStats";
import { DemandasTable } from "./DemandasTable";
import {
  type DemandasViewMode,
  DemandaStatusFiltro,
  DemandasToolbar,
} from "./DemandasToolbar";
import { NovaDemandaModal } from "./NovaDemandaModal";

function normalize(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function matchesDemanda(demanda: Demanda, query: string) {
  const haystack = [
    demanda.nome,
    demanda.codigoInterno,
    resolveProjetoDemandaNome(demanda.projetoId),
    resolveClienteProjetoNome(demanda.clienteId),
    resolveResponsaveisProjetoNomes(demanda.usuarioResponsavelIds),
    resolveDepartamentosProjetoNomes(demanda.departamentoResponsavelIds),
  ].join(" ");

  return normalize(haystack).includes(normalize(query));
}

function createHistoricoDemanda(acao: string) {
  return {
    id: generateId("hist-demanda"),
    usuarioId: "user-1",
    usuario: "Hudson Cunha",
    acao,
    dataHora: new Date().toLocaleString("pt-BR"),
    ip: "127.0.0.1",
    dispositivo: "Workspace mock",
  };
}

function createInitialWorkflow(draft: DemandaFormDraft): DemandaWorkflowEtapa[] {
  return [
    {
      id: generateId("etapa-demanda"),
      nome: "Atendimento",
      ordem: 1,
      usuarioResponsavelIds: draft.usuarioResponsavelIds,
      departamentoResponsavelIds: draft.departamentoResponsavelIds,
      prazoHoras: 8,
      status: "pendente",
    },
  ];
}

function createDemandaFromDraft(draft: DemandaFormDraft): Demanda {
  const now = new Date().toISOString();
  const workflowEtapas = createInitialWorkflow(draft);
  const today = now.slice(0, 10);

  return {
    id: generateId("demanda"),
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    projetoId: draft.projetoId,
    clienteId: draft.clienteId,
    codigoInterno: generateCodigoInterno().replace("#", "#D"),
    nome: draft.nome,
    briefing: draft.briefing,
    status: draft.status,
    prioridade: draft.prioridade,
    usuarioResponsavelIds: draft.usuarioResponsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
    workflowEtapas,
    etapaAtualId: workflowEtapas[0].id,
    prazoEtapaAtual: draft.dataFimPrevista,
    dataCriacao: today,
    dataInicio: today,
    dataFimPrevista: draft.dataFimPrevista,
    createdAt: now,
    updatedAt: now,
    historico: [createHistoricoDemanda("Demanda criada no mock local")],
  };
}

function updateDemandaFromDraft(
  demanda: Demanda,
  draft: DemandaFormDraft
): Demanda {
  return {
    ...demanda,
    projetoId: draft.projetoId,
    clienteId: draft.clienteId,
    nome: draft.nome,
    briefing: draft.briefing,
    status: draft.status,
    prioridade: draft.prioridade,
    usuarioResponsavelIds: draft.usuarioResponsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
    dataFimPrevista: draft.dataFimPrevista,
    prazoEtapaAtual: draft.dataFimPrevista,
    updatedAt: new Date().toISOString(),
    historico: [
      createHistoricoDemanda("Demanda atualizada no mock local"),
      ...demanda.historico,
    ],
  };
}

function statusMatchesFilter(
  demanda: Demanda,
  statusFilter: DemandaStatusFiltro
) {
  if (statusFilter === "todos") return true;
  if (statusFilter === "pausadas_bloqueadas") {
    return demanda.status === "pausada" || demanda.status === "bloqueada";
  }

  return demanda.status === statusFilter;
}

export function DemandasView() {
  const [demandas, setDemandas] = useState<Demanda[]>(demandasMock);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] =
    useState<DemandaStatusFiltro>("todos");
  const [viewMode, setViewMode] = useState<DemandasViewMode>("lista");
  const [creatingDemand, setCreatingDemand] = useState(false);
  const [editingDemandId, setEditingDemandId] = useState<string | null>(null);
  const [selectedDemandId, setSelectedDemandId] = useState<string | null>(null);

  const selectedDemand = demandas.find(
    (demanda) => demanda.id === selectedDemandId
  );
  const editingDemand = demandas.find(
    (demanda) => demanda.id === editingDemandId
  );

  const filteredDemands = useMemo(
    () =>
      demandas.filter((demanda) => {
        const queryMatches = query.trim()
          ? matchesDemanda(demanda, query)
          : true;

        return statusMatchesFilter(demanda, statusFilter) && queryMatches;
      }),
    [demandas, query, statusFilter]
  );

  function upsertDemand(draft: DemandaFormDraft, demandaId?: string) {
    if (!demandaId) {
      const newDemand = createDemandaFromDraft(draft);
      setDemandas((current) => [newDemand, ...current]);
      return newDemand.id;
    }

    setDemandas((current) =>
      current.map((demanda) =>
        demanda.id === demandaId
          ? updateDemandaFromDraft(demanda, draft)
          : demanda
      )
    );

    return demandaId;
  }

  function handleSaveAndClose(draft: DemandaFormDraft, demandaId?: string) {
    upsertDemand(draft, demandaId);
    setCreatingDemand(false);
    setEditingDemandId(null);
  }

  function handleSaveAndContinue(draft: DemandaFormDraft, demandaId?: string) {
    const nextDemandId = upsertDemand(draft, demandaId);

    setCreatingDemand(false);
    setEditingDemandId(null);
    setSelectedDemandId(nextDemandId);
  }

  function handleDemandChange(nextDemand: Demanda) {
    setDemandas((current) =>
      current.map((demanda) =>
        demanda.id === nextDemand.id ? nextDemand : demanda
      )
    );
  }

  function openEdit(demandaId: string) {
    setSelectedDemandId(null);
    setEditingDemandId(demandaId);
  }

  return (
    <WorkspacePage>
      <div className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-3xl bg-blue-50 text-blue-700 ring-1 ring-blue-100">
              <ClipboardList className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">
                Demandas
              </h1>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-500">
                Lista operacional de demandas. O Kanban existente permanece disponível na base para uma próxima alternância por abas.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusPill tone="blue">Workspace operacional</StatusPill>
            <StatusPill tone="green">Mock local</StatusPill>
          </div>
        </div>
      </div>

      <DemandasStats demandas={demandas} />

      <DemandasToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onNewDemand={() => setCreatingDemand(true)}
      />

      {filteredDemands.length === 0 ? (
        <WorkspaceEmptyState
          title="Nenhuma demanda encontrada"
          description="Ajuste a busca ou os filtros para visualizar as demandas cadastradas."
        />
      ) : viewMode === "kanban" ? (
        <DemandasKanban
          demandas={filteredDemands}
          onOpenDetails={setSelectedDemandId}
        />
      ) : (
        <DemandasTable
          demandas={filteredDemands}
          onOpenDetails={setSelectedDemandId}
          onEdit={openEdit}
        />
      )}

      {creatingDemand && (
        <NovaDemandaModal
          open
          onClose={() => setCreatingDemand(false)}
          onSaveAndClose={handleSaveAndClose}
          onSaveAndContinue={handleSaveAndContinue}
        />
      )}

      {editingDemand && (
        <NovaDemandaModal
          key={editingDemand.id}
          open
          demanda={editingDemand}
          onClose={() => setEditingDemandId(null)}
          onSaveAndClose={handleSaveAndClose}
          onSaveAndContinue={handleSaveAndContinue}
        />
      )}

      <DemandaDetailsDrawer
        demanda={selectedDemand}
        onClose={() => setSelectedDemandId(null)}
        onEdit={openEdit}
        onChange={handleDemandChange}
      />
    </WorkspacePage>
  );
}
