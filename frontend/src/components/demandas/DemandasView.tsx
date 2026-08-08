"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ClipboardList } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  EMPRESA_PADRAO_ID,
  AGENCIA_PADRAO_ID,
  generateId,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveProjetoDemandaNome,
  resolveResponsaveisDemandaNomes,
  statusDemandaLabels,
} from "@/lib/demandas-mock";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { resolverDepartamentoNome } from "@/lib/referencias";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import { podeCriarDemanda } from "@/types/usuario";
import type { Demanda, DemandaFormDraft, DemandaHistoricoEvento, DemandaStatus } from "@/types/demanda";
import type { Usuario } from "@/types/usuario";
import { DemandaDetailsDrawer } from "./DemandaDetailsDrawer";
import { DemandasKanban } from "./DemandasKanban";
import { DemandasStats } from "./DemandasStats";
import { DemandasTable } from "./DemandasTable";
import { type DemandasViewMode, type DemandaStatusFiltro, DemandasToolbar } from "./DemandasToolbar";
import { NovaDemandaModal } from "./NovaDemandaModal";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesDemanda(demanda: Demanda, query: string, usuarios: UsuarioDiretorioItem[]) {
  const haystack = [
    demanda.nome,
    demanda.codigoInterno,
    demanda.pit ?? "",
    resolveProjetoDemandaNome(demanda.projetoId),
    resolveClienteProjetoNome(demanda.clienteId),
    resolveResponsaveisDemandaNomes(demanda.usuarioResponsavelIds, usuarios),
    resolveDepartamentosProjetoNomes(demanda.departamentoResponsavelIds),
  ].join(" ");

  return normalize(haystack).includes(normalize(query));
}

function createHistoricoDemanda(acao: string, usuarioAtual?: Usuario): DemandaHistoricoEvento {
  return {
    id: generateId("hist-demanda"),
    usuarioId: usuarioAtual?.id ?? "user-1",
    usuario: usuarioAtual?.nome ?? "Você",
    acao,
    dataHora: new Date().toLocaleString("pt-BR"),
    ip: "127.0.0.1",
    dispositivo: "Workspace local",
  };
}

function createDemandaFromDraft(draft: DemandaFormDraft, codigoInterno: string, usuarioAtual?: Usuario): Demanda {
  const now = new Date().toISOString();
  const today = now.slice(0, 10);

  return {
    id: generateId("demanda"),
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    projetoId: draft.projetoId,
    clienteId: draft.clienteId,
    codigoInterno,
    nome: draft.nome,
    pit: draft.pit?.trim() ? draft.pit.trim() : undefined,
    briefing: draft.briefing,
    status: draft.status,
    prioridade: draft.prioridade,
    usuarioResponsavelIds: draft.usuarioResponsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
    workflowEtapas: draft.workflowEtapas,
    etapaAtualId: draft.etapaAtualId,
    prazoEtapaAtual: draft.dataFimPrevista,
    dataCriacao: today,
    dataInicio: today,
    dataFimPrevista: draft.dataFimPrevista,
    emailConclusaoEnviado: false,
    sinalizada: false,
    checklist: [],
    arquivos: [],
    comentarios: [],
    createdAt: now,
    updatedAt: now,
    historico: [createHistoricoDemanda("Tarefa criada", usuarioAtual)],
  };
}

function updateDemandaFromDraft(demanda: Demanda, draft: DemandaFormDraft, usuarioAtual?: Usuario): Demanda {
  // Reabrir e concluir de novo deve poder oferecer o aviso de entrega novamente.
  const reconcluida = draft.status === "concluida" && demanda.status !== "concluida";

  return {
    ...demanda,
    projetoId: draft.projetoId,
    clienteId: draft.clienteId,
    nome: draft.nome,
    pit: draft.pit?.trim() ? draft.pit.trim() : undefined,
    briefing: draft.briefing,
    status: draft.status,
    prioridade: draft.prioridade,
    usuarioResponsavelIds: draft.usuarioResponsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
    workflowEtapas: draft.workflowEtapas,
    etapaAtualId: draft.etapaAtualId,
    dataFimPrevista: draft.dataFimPrevista,
    prazoEtapaAtual: draft.dataFimPrevista,
    emailConclusaoEnviado: reconcluida ? false : demanda.emailConclusaoEnviado,
    updatedAt: new Date().toISOString(),
    historico: [createHistoricoDemanda("Tarefa atualizada", usuarioAtual), ...demanda.historico],
  };
}

function statusMatchesFilter(demanda: Demanda, statusFilter: DemandaStatusFiltro) {
  if (statusFilter === "todos") return true;
  if (statusFilter === "pausadas_bloqueadas") {
    return demanda.status === "pausada" || demanda.status === "bloqueada";
  }
  return demanda.status === statusFilter;
}

export function DemandasView() {
  const { demandas, setDemandas, usuarioAtual, gerarProximoCodigoTarefa, demandaParaAbrir, setDemandaParaAbrir } =
    useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  const { usuarios } = useDiretorioUsuarios();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<DemandaStatusFiltro>("todos");
  const [viewMode, setViewMode] = useState<DemandasViewMode>("lista");
  const [creatingDemand, setCreatingDemand] = useState(false);
  const [editingDemandId, setEditingDemandId] = useState<string | null>(null);
  const [selectedDemandId, setSelectedDemandId] = useState<string | null>(null);
  const [selectedInitialTab, setSelectedInitialTab] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!demandaParaAbrir) return;
    const timeoutId = setTimeout(() => {
      setSelectedDemandId(demandaParaAbrir.demandaId);
      setSelectedInitialTab(demandaParaAbrir.aba);
      setDemandaParaAbrir(null);
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [demandaParaAbrir, setDemandaParaAbrir]);

  const selectedDemand = demandas.find((demanda) => demanda.id === selectedDemandId);
  const editingDemand = demandas.find((demanda) => demanda.id === editingDemandId);

  const departamentoAtualNome = usuarioAtual ? resolverDepartamentoNome(usuarioAtual.departamentoId, departamentos) : "";
  const podeCriar = usuarioAtual ? podeCriarDemanda(usuarioAtual, departamentoAtualNome) : false;

  const filteredDemands = useMemo(
    () =>
      demandas.filter((demanda) => {
        const queryMatches = query.trim() ? matchesDemanda(demanda, query, usuarios) : true;
        return statusMatchesFilter(demanda, statusFilter) && queryMatches;
      }),
    [demandas, query, statusFilter, usuarios],
  );

  function upsertDemand(draft: DemandaFormDraft, demandaId?: string) {
    if (!demandaId) {
      const newDemand = createDemandaFromDraft(draft, gerarProximoCodigoTarefa(), usuarioAtual);
      setDemandas((current) => [newDemand, ...current]);
      return newDemand.id;
    }

    setDemandas((current) =>
      current.map((demanda) => (demanda.id === demandaId ? updateDemandaFromDraft(demanda, draft, usuarioAtual) : demanda)),
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
    setDemandas((current) => current.map((demanda) => (demanda.id === nextDemand.id ? nextDemand : demanda)));
  }

  function handleMoveDemand(demandaId: string, novoStatus: DemandaStatus) {
    setDemandas((current) =>
      current.map((demanda) => {
        if (demanda.id !== demandaId) return demanda;
        const reconcluida = novoStatus === "concluida" && demanda.status !== "concluida";
        return {
          ...demanda,
          status: novoStatus,
          emailConclusaoEnviado: reconcluida ? false : demanda.emailConclusaoEnviado,
          updatedAt: new Date().toISOString(),
          historico: [
            createHistoricoDemanda(`Status alterado para ${statusDemandaLabels[novoStatus]} (Kanban)`, usuarioAtual),
            ...demanda.historico,
          ],
        };
      }),
    );
  }

  function openEdit(demandaId: string) {
    setSelectedDemandId(null);
    setEditingDemandId(demandaId);
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <ClipboardList className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Tarefas</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Fila operacional de tarefas, com visão em lista ou kanban por status.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <DemandasStats demandas={demandas} />

      <DemandasToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onNewDemand={() => setCreatingDemand(true)}
        podeCriar={podeCriar}
      />

      {filteredDemands.length === 0 ? (
        <EmptyState title="Nenhuma tarefa encontrada" description="Ajuste a busca ou os filtros para visualizar as tarefas cadastradas." />
      ) : viewMode === "kanban" ? (
        <DemandasKanban demandas={filteredDemands} onOpenDetails={setSelectedDemandId} onMoveDemanda={handleMoveDemand} />
      ) : (
        <DemandasTable demandas={filteredDemands} onOpenDetails={setSelectedDemandId} onEdit={openEdit} />
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
        key={selectedDemand?.id}
        demanda={selectedDemand}
        initialTab={selectedInitialTab}
        onClose={() => setSelectedDemandId(null)}
        onEdit={openEdit}
        onChange={handleDemandChange}
      />
    </div>
  );
}
