"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { CalendarClock } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { getDemandaReal, listDemandasReais } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { DemandaDetailsDrawer } from "@/components/demandas/DemandaDetailsDrawer";
import type { Demanda } from "@/types/demanda";
import { PautaGantt } from "./PautaGantt";
import { PautaLista } from "./PautaLista";
import { type PautaPeriodoFiltro, type PautaViewMode, PautaToolbar } from "./PautaToolbar";

// D2-B3: mesma razão do D2-B1/D2-B2 — AppDataContext.demandas vem limitado a 200 itens
// carregados uma única vez no login. A Pauta filtrava esse array localmente (busca,
// departamentos, período); uma tarefa fora dessa janela simplesmente não aparecia, sem
// nenhum aviso. A Pauta passa a buscar do servidor com search/departamentos/prazo/ordenação
// reais — ver diagnóstico D2-B3. AppDataContext continua alimentando mutations (patch) e
// outras telas ainda não migradas.
const TAMANHO_PAGINA = 50;
const DEBOUNCE_BUSCA_MS = 300;

function periodoParaIntervalo(periodo: PautaPeriodoFiltro): { inicio: Date; fim: Date } {
  const inicio = new Date();
  inicio.setHours(0, 0, 0, 0);

  const dias = periodo === "hoje" ? 0 : periodo === "7d" ? 6 : 29;
  const fim = new Date(inicio);
  fim.setDate(fim.getDate() + dias);
  fim.setHours(23, 59, 59, 999);

  return { inicio, fim };
}

export function PautaView() {
  const router = useRouter();
  const { demandas, setDemandas, usuarioAtual, setDemandaParaAbrir } = useAppData();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [departamentoIds, setDepartamentoIds] = useState<string[]>([]);
  const [periodo, setPeriodo] = useState<PautaPeriodoFiltro>("7d");
  const [viewMode, setViewMode] = useState<PautaViewMode>("lista");
  const [selectedDemandId, setSelectedDemandId] = useState<string | null>(null);

  const { inicio: periodoInicio, fim: periodoFim } = useMemo(() => periodoParaIntervalo(periodo), [periodo]);
  const departamentoIdsParam = departamentoIds.join(",");

  // Página acumulada, vinda do servidor — fonte autoritativa da lista exibida (lista e
  // gantt compartilham o mesmo array; trocar de modo não refaz a consulta).
  const [demandasPauta, setDemandasPauta] = useState<Demanda[]>([]);
  // `carregandoInicial` só é true até a PRIMEIRA resposta (sucesso ou erro) da sessão —
  // nunca mais volta a ser true depois disso. `buscandoPagina` cobre toda busca seguinte
  // (filtro novo ou refetch pós-mutation): esmaece a lista já exibida em vez de apagá-la —
  // mesmo padrão de DemandasView.tsx (D2-B1), pra não "piscar vazio" a cada tecla digitada
  // ou a cada mutation bem-sucedida.
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [buscandoPagina, setBuscandoPagina] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [temMais, setTemMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  // Incrementado após mutation bem-sucedida pra forçar refetch mesmo quando filtros não
  // mudaram — ver handleDemandChange.
  const [refetchTick, setRefetchTick] = useState(0);

  useEffect(() => {
    const timeout = setTimeout(() => setDebouncedQuery(query.trim()), DEBOUNCE_BUSCA_MS);
    return () => clearTimeout(timeout);
  }, [query]);

  // Chave da combinação atual de filtros — muda a cada busca/departamentos/período/refetch
  // explícito. Comparada durante o RENDER (não dentro do efeito): setState síncrono no corpo
  // do efeito é o padrão que react-hooks/set-state-in-effect rejeita neste projeto — mesma
  // técnica de DemandasView.tsx/ProjetoDemandasSection.tsx.
  const chaveBusca = `${debouncedQuery}\u0000${departamentoIdsParam}\u0000${periodo}\u0000${refetchTick}`;
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  if (chaveBusca !== chaveConsultada) {
    setChaveConsultada(chaveBusca);
    setBuscandoPagina(true);
    setErro(null);
    // Sem isto, um "carregar mais" em voo de uma geração anterior (filtro velho, ou
    // pré-mutation) nunca teria seu `carregandoMais` liberado — o guard de `chaveAtualRef`
    // recusa (corretamente) tocar o estado da geração nova a partir da promise antiga, então
    // ninguém mais reseta esse flag pra geração atual. Resultado sem isto: botão preso em
    // "Carregando…" desabilitado para sempre. `temMais` também reseta aqui — senão ficaria
    // com o valor da geração anterior até a resposta nova chegar.
    setCarregandoMais(false);
    setTemMais(false);
  }

  // Múltiplos filtros compõem a chave (não só um id, como no D2-B2) — ref sempre atualizada
  // via efeito guarda "carregar mais" contra resposta de uma combinação de filtros anterior.
  const chaveAtualRef = useRef(chaveBusca);
  useEffect(() => {
    chaveAtualRef.current = chaveBusca;
  }, [chaveBusca]);

  useEffect(() => {
    let cancelado = false;
    listDemandasReais({
      search: debouncedQuery || undefined,
      departamentoId: departamentoIdsParam || undefined,
      prazoInicio: periodoInicio.toISOString(),
      prazoFim: periodoFim.toISOString(),
      sort: "prazo_asc",
      limit: TAMANHO_PAGINA,
      offset: 0,
    })
      .then((resultado) => {
        if (cancelado) return; // combinação de filtros obsoleta — outra busca já foi disparada
        setDemandasPauta(resultado);
        setTemMais(resultado.length === TAMANHO_PAGINA);
        setErro(null);
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setErro(error instanceof Error ? error.message : "Não foi possível carregar a pauta.");
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      });
    return () => {
      cancelado = true;
    };
  }, [debouncedQuery, departamentoIdsParam, periodoInicio, periodoFim, refetchTick]);

  function carregarMais() {
    const chaveDoClique = chaveBusca;
    setCarregandoMais(true);
    listDemandasReais({
      search: debouncedQuery || undefined,
      departamentoId: departamentoIdsParam || undefined,
      prazoInicio: periodoInicio.toISOString(),
      prazoFim: periodoFim.toISOString(),
      sort: "prazo_asc",
      limit: TAMANHO_PAGINA,
      offset: demandasPauta.length,
    })
      .then((resultado) => {
        if (chaveAtualRef.current !== chaveDoClique) return; // filtros mudaram enquanto carregava
        setDemandasPauta((atual) => [...atual, ...resultado]);
        setTemMais(resultado.length === TAMANHO_PAGINA);
        setErro(null);
      })
      .catch((error) => {
        if (chaveAtualRef.current !== chaveDoClique) return;
        // Não corrompe a lista já exibida — mantém o que já veio, com o erro sinalizado.
        setErro(error instanceof Error ? error.message : "Não foi possível carregar mais tarefas.");
      })
      .finally(() => {
        if (chaveAtualRef.current === chaveDoClique) setCarregandoMais(false);
      });
  }

  // D2-C — mesmo padrão de DemandasView.tsx: só busca individual (GET /demandas/{id}) se o
  // id não estiver nem na página atual nem no contexto. `cancelado` protege troca de seleção
  // antes da resposta chegar.
  const [fallbackDemand, setFallbackDemand] = useState<Demanda | null>(null);
  useEffect(() => {
    if (!selectedDemandId) return;
    const jaResolvido =
      demandasPauta.some((demanda) => demanda.id === selectedDemandId) ||
      demandas.some((demanda) => demanda.id === selectedDemandId);
    if (jaResolvido) return;
    let cancelado = false;
    getDemandaReal(selectedDemandId)
      .then((demanda) => {
        if (!cancelado) setFallbackDemand(demanda);
      })
      .catch(() => {
        // Inexistente/fora do escopo: drawer permanece fechado.
      });
    return () => {
      cancelado = true;
    };
  }, [selectedDemandId, demandasPauta, demandas]);

  // Página do servidor é a fonte de verdade; contexto cobre o intervalo entre o patch
  // síncrono de uma mutation e o refetch assíncrono terminar; o fallback acima só entra se
  // nenhum dos dois resolveu.
  const selectedDemand =
    demandasPauta.find((demanda) => demanda.id === selectedDemandId) ??
    demandas.find((demanda) => demanda.id === selectedDemandId) ??
    (fallbackDemand?.id === selectedDemandId ? fallbackDemand : undefined);

  function handleDemandChange(nextDemand: Demanda) {
    // Só patch de contexto (outras telas ainda dependem dele) + refetch — NUNCA patch local
    // de demandasPauta: a mutation pode mudar prazo/departamento/nome/projeto e fazer a
    // demanda entrar, sair ou mudar de posição na pauta atual: só um refetch sabe decidir isso
    // corretamente.
    setDemandas((current) => current.map((demanda) => (demanda.id === nextDemand.id ? nextDemand : demanda)));
    setRefetchTick((tick) => tick + 1);
  }

  // Pauta não duplica o modal de edição — "Editar" leva para Tarefas com a tarefa já aberta.
  function handleEdit(demandaId: string) {
    setSelectedDemandId(null);
    setDemandaParaAbrir({ demandaId });
    router.push("/tarefas");
  }

  if (!usuarioAtual) return null;

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
              <CalendarClock className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Pauta</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Ordem das tarefas por prazo, para acompanhar o dia e preparar a reunião de pauta da equipe.
              </p>
            </div>
          </div>
          <Badge tone="green">Banco real</Badge>
        </div>
      </motion.div>

      <PautaToolbar
        query={query}
        onQueryChange={setQuery}
        departamentoIds={departamentoIds}
        onDepartamentoIdsChange={setDepartamentoIds}
        periodo={periodo}
        onPeriodoChange={setPeriodo}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      {carregandoInicial ? (
        <p className="text-sm text-zinc-400">Carregando pauta…</p>
      ) : erro && demandasPauta.length === 0 ? (
        <EmptyState title="Não foi possível carregar a pauta" description={erro} icon={<CalendarClock size={16} />} />
      ) : (
        <div className={buscandoPagina ? "opacity-60 transition-opacity" : "transition-opacity"}>
          {viewMode === "lista" ? (
            <PautaLista demandas={demandasPauta} onOpenDetails={setSelectedDemandId} />
          ) : (
            <PautaGantt demandas={demandasPauta} periodoInicio={periodoInicio} periodoFim={periodoFim} onOpenDetails={setSelectedDemandId} />
          )}
        </div>
      )}

      {erro && demandasPauta.length > 0 && <p className="text-xs text-red-500">{erro}</p>}

      {!carregandoInicial && temMais && (
        <div className="flex justify-center">
          <Button type="button" variant="secondary" onClick={carregarMais} disabled={carregandoMais || buscandoPagina}>
            {carregandoMais ? "Carregando…" : "Carregar mais"}
          </Button>
        </div>
      )}

      <DemandaDetailsDrawer
        key={selectedDemand?.id}
        demanda={selectedDemand}
        onClose={() => setSelectedDemandId(null)}
        onEdit={handleEdit}
        onChange={handleDemandChange}
      />
    </div>
  );
}
