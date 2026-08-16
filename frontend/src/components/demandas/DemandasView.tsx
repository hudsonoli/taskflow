"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ClipboardList } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  resolveClienteProjetoNome,
  resolveProjetoDemandaNome,
  resolveResponsaveisDemandaNomes,
} from "@/lib/demandas";
import {
  atualizarDemandaReal,
  criarDemandaReal,
  ForaDeExpedienteError,
  patchDemandaReal,
} from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { resolverDepartamentoNome } from "@/lib/referencias";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import type { DepartamentoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import { rotuloDemanda } from "@/lib/referencias";
import { podeCriarDemanda } from "@/types/usuario";
import type { Demanda, DemandaFormDraft, DemandaStatusEditavel } from "@/types/demanda";
import { DemandaDetailsDrawer } from "./DemandaDetailsDrawer";
import { DemandasKanban } from "./DemandasKanban";
import { DemandasStats } from "./DemandasStats";
import { DemandasTable } from "./DemandasTable";
import { type DemandasViewMode, type DemandaStatusFiltro, DemandasToolbar } from "./DemandasToolbar";
import { MotivoBloqueioModal } from "./MotivoBloqueioModal";
import { NovaDemandaModal } from "./NovaDemandaModal";

/**
 * Erro de expediente chega estruturado do servidor, com a janela vigente — a interface
 * apresenta, não recalcula. Qualquer outro erro vira a própria mensagem da API.
 */
function mensagemDeErro(error: unknown): string {
  if (error instanceof ForaDeExpedienteError) {
    const { manhaInicio, manhaFim, tardeInicio, tardeFim } = error.expediente;
    return `${error.message} (${manhaInicio}–${manhaFim} e ${tardeInicio}–${tardeFim})`;
  }
  return error instanceof Error ? error.message : "Não foi possível salvar a tarefa.";
}

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesDemanda(
  demanda: Demanda,
  query: string,
  usuarios: UsuarioDiretorioItem[],
  departamentos: DepartamentoDiretorioItem[],
) {
  const haystack = [
    demanda.nome,
    rotuloDemanda(demanda),
    demanda.pit ?? "",
    resolveProjetoDemandaNome(demanda.projetoId),
    resolveClienteProjetoNome(demanda.clienteId),
    resolveResponsaveisDemandaNomes(demanda.usuarioResponsavelIds, usuarios),
    demanda.departamentoResponsavelIds.map((id) => resolverDepartamentoNome(id, departamentos)).join(" "),
  ].join(" ");

  return normalize(haystack).includes(normalize(query));
}

// `createHistoricoDemanda`, `createDemandaFromDraft` e `updateDemandaFromDraft` saíram na
// Fase 2E.1. Os três montavam uma Demanda no navegador — inclusive `codigoInterno` e entradas
// de `historico[]` com ip e dispositivo inventados. Agora quem cria a demanda e emite os dois
// números é o servidor, e o histórico é evento de domínio.

function statusMatchesFilter(demanda: Demanda, statusFilter: DemandaStatusFiltro) {
  if (statusFilter === "todos") return true;
  if (statusFilter === "pausadas_bloqueadas") {
    return demanda.status === "pausada" || demanda.status === "bloqueada";
  }
  return demanda.status === statusFilter;
}

export function DemandasView() {
  const { demandas, setDemandas, usuarioAtual, demandaParaAbrir, setDemandaParaAbrir } = useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  const { usuarios } = useDiretorioUsuarios();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<DemandaStatusFiltro>("todos");
  const [viewMode, setViewMode] = useState<DemandasViewMode>("lista");
  const [creatingDemand, setCreatingDemand] = useState(false);
  const [editingDemandId, setEditingDemandId] = useState<string | null>(null);
  const [selectedDemandId, setSelectedDemandId] = useState<string | null>(null);
  const [selectedInitialTab, setSelectedInitialTab] = useState<string | undefined>(undefined);
  const [erro, setErro] = useState<string | null>(null);
  // Id da demanda aguardando motivo de bloqueio; null quando o modal está fechado.
  const [bloqueandoId, setBloqueandoId] = useState<string | null>(null);

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
  const bloqueandoDemanda = demandas.find((demanda) => demanda.id === bloqueandoId);
  const editingDemand = demandas.find((demanda) => demanda.id === editingDemandId);

  const departamentoAtualNome = usuarioAtual ? resolverDepartamentoNome(usuarioAtual.departamentoId, departamentos) : "";
  const podeCriar = usuarioAtual ? podeCriarDemanda(usuarioAtual, departamentoAtualNome) : false;

  const filteredDemands = useMemo(
    () =>
      demandas.filter((demanda) => {
        const queryMatches = query.trim() ? matchesDemanda(demanda, query, usuarios, departamentos) : true;
        return statusMatchesFilter(demanda, statusFilter) && queryMatches;
      }),
    [demandas, query, statusFilter, usuarios, departamentos],
  );

  async function upsertDemand(draft: DemandaFormDraft, demandaId?: string): Promise<string | null> {
    setErro(null);
    try {
      if (!demandaId) {
        const criada = await criarDemandaReal(draft);
        setDemandas((current) => [criada, ...current]);
        return criada.id;
      }
      const atualizada = await atualizarDemandaReal(demandaId, draft);
      setDemandas((current) => current.map((demanda) => (demanda.id === demandaId ? atualizada : demanda)));
      return demandaId;
    } catch (error) {
      setErro(mensagemDeErro(error));
      return null;
    }
  }

  async function handleSaveAndClose(draft: DemandaFormDraft, demandaId?: string) {
    const salvo = await upsertDemand(draft, demandaId);
    if (!salvo) return; // erro já exibido — o formulário continua aberto com o que foi digitado
    setCreatingDemand(false);
    setEditingDemandId(null);
  }

  async function handleSaveAndContinue(draft: DemandaFormDraft, demandaId?: string) {
    const nextDemandId = await upsertDemand(draft, demandaId);
    if (!nextDemandId) return;
    setCreatingDemand(false);
    setEditingDemandId(null);
    setSelectedDemandId(nextDemandId);
  }

  function handleDemandChange(nextDemand: Demanda) {
    setDemandas((current) => current.map((demanda) => (demanda.id === nextDemand.id ? nextDemand : demanda)));
  }

  async function aplicarStatus(demandaId: string, novoStatus: DemandaStatusEditavel, motivoBloqueio?: string) {
    setErro(null);
    try {
      const atualizada = await patchDemandaReal(demandaId, {
        status: novoStatus,
        ...(motivoBloqueio ? { motivoBloqueio } : {}),
      });
      setDemandas((current) => current.map((demanda) => (demanda.id === demandaId ? atualizada : demanda)));
    } catch (error) {
      // Inclui o 409 de expediente: a mensagem e a janela vêm do servidor, que é onde a regra
      // mora agora. A UI não recalcula horário nenhum.
      setErro(mensagemDeErro(error));
    }
  }

  function handleMoveDemand(demandaId: string, novoStatus: DemandaStatusEditavel) {
    // Bloquear exige motivo — pedir antes evita um 422 previsível.
    if (novoStatus === "bloqueada") {
      setBloqueandoId(demandaId);
      return;
    }
    void aplicarStatus(demandaId, novoStatus);
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
          <Badge tone="green">Banco real</Badge>
        </div>
      </motion.div>

      {erro && (
        <div
          role="alert"
          className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400"
        >
          {erro}
        </div>
      )}

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

      <MotivoBloqueioModal
        open={bloqueandoId !== null}
        rotulo={bloqueandoDemanda ? rotuloDemanda(bloqueandoDemanda) : ""}
        salvando={false}
        onClose={() => setBloqueandoId(null)}
        onConfirm={(motivo) => {
          const alvo = bloqueandoId;
          setBloqueandoId(null);
          if (alvo) void aplicarStatus(alvo, "bloqueada", motivo);
        }}
      />
    </div>
  );
}
