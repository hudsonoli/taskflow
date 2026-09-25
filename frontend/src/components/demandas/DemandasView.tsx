"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ClipboardList } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  atualizarDemandaReal,
  criarDemandaReal,
  ForaDeExpedienteError,
  listDemandasReais,
  patchDemandaReal,
} from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { resolverDepartamentoNome } from "@/lib/referencias";
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

// D2-B1: a lista visível de DemandasView deixa de vir de AppDataContext.demandas (array
// carregado uma única vez, limit=200 fixo) e passa a buscar do servidor com search/status/
// paginação reais — ver diagnóstico D2/D2-A. AppDataContext continua alimentando mutations e
// outras telas ainda não migradas (DemandasStats inclusive, de propósito — é agregação,
// fora do escopo do D2-B1, fica para D2-D).
const TAMANHO_PAGINA = 50;
const DEBOUNCE_BUSCA_MS = 300;

/**
 * Erro de expediente chega estruturado do servidor, com a janela vigente — a interface
 * apresenta, não recalcula. Qualquer outro erro vira a própria mensagem da API.
 */
function mensagemDeErro(error: unknown): string {
  if (error instanceof ForaDeExpedienteError) {
    const { manhaInicio, manhaFim, tardeInicio, tardeFim } = error.expediente;
    // Hoje pode não ser dia útil — os quatro horários vêm `null` nesse caso, e a mensagem já
    // diz isso sozinha ("hoje não é dia útil"), sem janela para completar entre parênteses.
    if (manhaInicio === null || manhaFim === null || tardeInicio === null || tardeFim === null) {
      return error.message;
    }
    return `${error.message} (${manhaInicio}–${manhaFim} e ${tardeInicio}–${tardeFim})`;
  }
  return error instanceof Error ? error.message : "Não foi possível salvar a tarefa.";
}

// `createHistoricoDemanda`, `createDemandaFromDraft` e `updateDemandaFromDraft` saíram na
// Fase 2E.1. Os três montavam uma Demanda no navegador — inclusive `codigoInterno` e entradas
// de `historico[]` com ip e dispositivo inventados. Agora quem cria a demanda e emite os dois
// números é o servidor, e o histórico é evento de domínio.

/** Único filtro de UI sem equivalente 1:1 no backend — agrupa dois status reais. O backend
 * aceita lista separada por vírgula (D2-B1, ver app/repositories/demanda_repository.py) pra
 * evitar que esse agrupamento precise ser refeito no cliente sobre uma página parcial. */
function statusParaBackend(filtro: DemandaStatusFiltro): string | undefined {
  if (filtro === "todos") return undefined;
  if (filtro === "pausadas_bloqueadas") return "pausada,bloqueada";
  return filtro;
}

export function DemandasView() {
  const { demandas, setDemandas, usuarioAtual, demandaParaAbrir, setDemandaParaAbrir } = useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<DemandaStatusFiltro>("todos");
  const [offset, setOffset] = useState(0);
  const [viewMode, setViewMode] = useState<DemandasViewMode>("lista");
  const [creatingDemand, setCreatingDemand] = useState(false);
  const [editingDemandId, setEditingDemandId] = useState<string | null>(null);
  const [selectedDemandId, setSelectedDemandId] = useState<string | null>(null);
  const [selectedInitialTab, setSelectedInitialTab] = useState<string | undefined>(undefined);
  const [erro, setErro] = useState<string | null>(null);
  // Id da demanda aguardando motivo de bloqueio; null quando o modal está fechado.
  const [bloqueandoId, setBloqueandoId] = useState<string | null>(null);

  // Página atual, vinda do servidor — fonte autoritativa da lista exibida.
  const [demandasPagina, setDemandasPagina] = useState<Demanda[]>([]);
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [buscandoPagina, setBuscandoPagina] = useState(true);
  const [temProximaPagina, setTemProximaPagina] = useState(false);
  const [erroPagina, setErroPagina] = useState<string | null>(null);
  // Incrementado após mutation bem-sucedida (create/edit/status) pra forçar refetch da página
  // atual mesmo quando search/status/offset não mudaram — ver upsertDemand/aplicarStatus.
  const [refetchTick, setRefetchTick] = useState(0);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setDebouncedQuery(query.trim());
      setOffset(0); // busca nova sempre volta pra primeira página
    }, DEBOUNCE_BUSCA_MS);
    return () => clearTimeout(timeout);
  }, [query]);

  function alterarStatusFilter(valor: DemandaStatusFiltro) {
    setStatusFilter(valor);
    setOffset(0); // troca de status também volta pra primeira página
  }

  // Chave da busca atual — muda a cada combinação de filtros/página/refetch explícito.
  // Comparada durante o RENDER (não dentro do efeito): setState síncrono no corpo do efeito é
  // o padrão que react-hooks/set-state-in-effect rejeita neste projeto — ver
  // lib/useAjustesProjeto.ts, mesma técnica endossada pelo próprio React pra "ajustar estado
  // quando algo muda" sem cascata de renders.
  const chaveBusca = `${debouncedQuery}\u0000${statusFilter}\u0000${offset}\u0000${refetchTick}`;
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  if (chaveBusca !== chaveConsultada) {
    setChaveConsultada(chaveBusca);
    setBuscandoPagina(true);
    setErroPagina(null);
  }

  useEffect(() => {
    let cancelado = false;
    listDemandasReais({
      search: debouncedQuery || undefined,
      status: statusParaBackend(statusFilter),
      limit: TAMANHO_PAGINA,
      offset,
    })
      .then((resultado) => {
        if (cancelado) return; // resposta obsoleta — outra busca já foi disparada depois desta
        // Página ficou vazia (ex.: uma mutation tirou o último item dela do filtro atual) —
        // volta uma página automaticamente em vez de mostrar uma página em branco no meio da
        // navegação. Só se aplica com offset > 0: navegação normal nunca chega aqui, porque
        // "Próxima" já fica desabilitada quando a página atual devolve menos que o limite.
        if (resultado.length === 0 && offset > 0) {
          setOffset((atual) => Math.max(0, atual - TAMANHO_PAGINA));
          return;
        }
        setDemandasPagina(resultado);
        setTemProximaPagina(resultado.length === TAMANHO_PAGINA);
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      })
      .catch((error) => {
        if (cancelado) return;
        // Não corrompe a lista já exibida — mantém a página anterior visível com o erro acima.
        setErroPagina(error instanceof Error ? error.message : "Não foi possível carregar as tarefas.");
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      });
    return () => {
      cancelado = true;
    };
  }, [debouncedQuery, statusFilter, offset, refetchTick]);

  useEffect(() => {
    if (!demandaParaAbrir) return;
    const timeoutId = setTimeout(() => {
      setSelectedDemandId(demandaParaAbrir.demandaId);
      setSelectedInitialTab(demandaParaAbrir.aba);
      setDemandaParaAbrir(null);
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [demandaParaAbrir, setDemandaParaAbrir]);

  // Busca primeiro na página atual (fonte do que está renderizado); cai pro contexto só na
  // janela entre "acabei de criar/mutar" e o refetch da página terminar — o contexto já tem o
  // objeto fresco ali (patch síncrono), a página ainda não.
  const selectedDemand =
    demandasPagina.find((demanda) => demanda.id === selectedDemandId) ??
    demandas.find((demanda) => demanda.id === selectedDemandId);
  const bloqueandoDemanda =
    demandasPagina.find((demanda) => demanda.id === bloqueandoId) ??
    demandas.find((demanda) => demanda.id === bloqueandoId);
  const editingDemand =
    demandasPagina.find((demanda) => demanda.id === editingDemandId) ??
    demandas.find((demanda) => demanda.id === editingDemandId);

  const departamentoAtualNome = usuarioAtual ? resolverDepartamentoNome(usuarioAtual.departamentoId, departamentos) : "";
  const podeCriar = usuarioAtual ? podeCriarDemanda(usuarioAtual, departamentoAtualNome) : false;

  const filtrosAtivos = useMemo(() => debouncedQuery.trim().length > 0 || statusFilter !== "todos", [debouncedQuery, statusFilter]);

  async function upsertDemand(draft: DemandaFormDraft, demandaId?: string): Promise<string | null> {
    setErro(null);
    try {
      if (!demandaId) {
        const criada = await criarDemandaReal(draft);
        setDemandas((current) => [criada, ...current]);
        // Onde a nova demanda deve aparecer depende dos filtros/ordenação do servidor — nunca
        // inserida manualmente na página, só refeita a busca a partir da primeira página.
        setOffset(0);
        setRefetchTick((tick) => tick + 1);
        return criada.id;
      }
      const atualizada = await atualizarDemandaReal(demandaId, draft);
      setDemandas((current) => current.map((demanda) => (demanda.id === demandaId ? atualizada : demanda)));
      // Edição pode mudar status/nome e tirar/colocar o item dentro do filtro atual.
      setRefetchTick((tick) => tick + 1);
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
    setDemandasPagina((current) => current.map((demanda) => (demanda.id === nextDemand.id ? nextDemand : demanda)));
  }

  async function aplicarStatus(demandaId: string, novoStatus: DemandaStatusEditavel, motivoBloqueio?: string) {
    setErro(null);
    try {
      const atualizada = await patchDemandaReal(demandaId, {
        status: novoStatus,
        ...(motivoBloqueio ? { motivoBloqueio } : {}),
      });
      setDemandas((current) => current.map((demanda) => (demanda.id === demandaId ? atualizada : demanda)));
      // Não confia em só mover o card localmente: a view é filtrada no servidor, e o novo
      // status pode tirar o item do filtro atual (ex.: filtro "Em execução" após concluir).
      setRefetchTick((tick) => tick + 1);
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

      {erroPagina && (
        <div
          role="alert"
          className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400"
        >
          {erroPagina}
        </div>
      )}

      <DemandasStats demandas={demandas} />

      <DemandasToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={alterarStatusFilter}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onNewDemand={() => setCreatingDemand(true)}
        podeCriar={podeCriar}
      />

      {carregandoInicial ? (
        <EmptyState title="Carregando tarefas…" description="Buscando a lista no servidor." />
      ) : demandasPagina.length === 0 ? (
        <EmptyState
          title={filtrosAtivos ? "Nenhuma tarefa encontrada para os filtros atuais" : "Nenhuma tarefa cadastrada"}
          description={
            filtrosAtivos
              ? "Ajuste a busca ou os filtros para visualizar outras tarefas."
              : "Cadastre a primeira tarefa para começar."
          }
        />
      ) : (
        <div className={buscandoPagina ? "opacity-60 transition-opacity" : "transition-opacity"}>
          {viewMode === "kanban" ? (
            <DemandasKanban demandas={demandasPagina} onOpenDetails={setSelectedDemandId} onMoveDemanda={handleMoveDemand} />
          ) : (
            <DemandasTable demandas={demandasPagina} onOpenDetails={setSelectedDemandId} onEdit={openEdit} />
          )}
        </div>
      )}

      {!carregandoInicial && (demandasPagina.length > 0 || offset > 0) && (
        <div className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white px-4 py-3 text-sm dark:border-zinc-800 dark:bg-zinc-900">
          <span className="text-zinc-500 dark:text-zinc-400">
            {offset > 0 ? `Itens ${offset + 1}–${offset + demandasPagina.length}` : `${demandasPagina.length} item(ns)`}
          </span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={offset === 0 || buscandoPagina}
              onClick={() => setOffset((current) => Math.max(0, current - TAMANHO_PAGINA))}
            >
              Anterior
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={!temProximaPagina || buscandoPagina}
              onClick={() => setOffset((current) => current + TAMANHO_PAGINA)}
            >
              Próxima
            </Button>
          </div>
        </div>
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
