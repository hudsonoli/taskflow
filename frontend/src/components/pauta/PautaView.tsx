"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { CalendarClock } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { FiltrosAvancados } from "@/components/filtros/FiltrosAvancados";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { type EscopoLeituraDemanda, getDemandaReal, listDemandasReais, listarDemandasEmExecucaoNaPauta } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioEquipes } from "@/lib/diretorioEquipes";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { podeAcessarPautaGlobal } from "@/lib/escopo-operacional";
import { filtrosPautaParaApi } from "@/lib/filtros-pauta";
import { useFiltrosNaUrl } from "@/lib/useFiltrosNaUrl";
import { DemandaDetailsDrawer } from "@/components/demandas/DemandaDetailsDrawer";
import type { Demanda } from "@/types/demanda";
import { PautaGantt } from "./PautaGantt";
import { PautaLista } from "./PautaLista";
import { type PautaPeriodoFiltro, type PautaViewMode, PautaToolbar } from "./PautaToolbar";
import { useDefinicoesFiltrosPauta } from "./useDefinicoesFiltrosPauta";

// D2-B3: mesma razão do D2-B1/D2-B2 — AppDataContext.demandas vem limitado a 200 itens
// carregados uma única vez no login. A Pauta filtrava esse array localmente (busca,
// departamentos, período); uma tarefa fora dessa janela simplesmente não aparecia, sem
// nenhum aviso. A Pauta passa a buscar do servidor com search/departamentos/prazo/ordenação
// reais — ver diagnóstico D2-B3. AppDataContext continua alimentando mutations (patch) e
// outras telas ainda não migradas.
//
// Fase 7C.1 — a Pauta é a visão operacional GLOBAL da empresa, só para Atendimento, Heads e Gestão (protegida no servidor: `escopo=pauta`
// devolve 403 a quem não pode). Operador comum NÃO tem Pauta — o trabalho dele é o Meu Dia — e quem chega pela URL vê "acesso negado".
// O universo é TODA demanda em aberto da empresa (do tenant do token), com ou sem prazo e com as atrasadas incluídas; concluída,
// cancelada e arquivada ficam fora (o servidor garante). O período (Hoje / 7 dias / 30 dias) é só um FILTRO OPCIONAL de prazo: o padrão
// é "Todas". Prazo nunca decide se uma demanda pertence à operação.
const TAMANHO_PAGINA = 50;
const DEBOUNCE_BUSCA_MS = 300;
const PERIODOS_VALIDOS: ReadonlyArray<PautaPeriodoFiltro> = ["todas", "hoje", "7d", "30d"];
const MODOS_VALIDOS: ReadonlyArray<PautaViewMode> = ["lista", "gantt"];

// Janela exibida no Gantt (e teto de prazo quando o filtro de período está ativo). "todas" não filtra nada; o Gantt mostra 30 dias.
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
  const { departamentos, carregando: carregandoDepartamentos } = useDiretorioDepartamentos();
  const { equipes, carregando: carregandoEquipes } = useDiretorioEquipes();
  const { clientes, carregando: carregandoClientes } = useDiretorioClientes();
  const { projetos, carregando: carregandoProjetos } = useDiretorioProjetos();
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedDemandId, setSelectedDemandId] = useState<string | null>(null);

  // Mesma regra de papel do servidor (Atendimento, Head, Gestão). Só decidida com os departamentos carregados (Head e Atendimento
  // dependem deles): a consulta espera, e quem não pode nunca dispara a busca.
  const podeAcessar = usuarioAtual ? podeAcessarPautaGlobal(usuarioAtual, departamentos) : false;
  const pronto = Boolean(usuarioAtual) && !carregandoDepartamentos && podeAcessar;

  const definicoesFiltros = useDefinicoesFiltrosPauta({
    departamentos,
    equipes,
    clientes,
    projetos,
    diretoriosProntos: !carregandoDepartamentos && !carregandoEquipes && !carregandoClientes && !carregandoProjetos,
  });
  // Estado da Pauta na URL (filtros, busca, período, modo de exibição): ids/códigos estáveis, refresh preserva, inválido ignorado.
  const { filtros, definirFiltros, param, definirParam } = useFiltrosNaUrl(definicoesFiltros, podeAcessar);
  const query = param("q") ?? "";
  const periodo: PautaPeriodoFiltro = PERIODOS_VALIDOS.find((valor) => valor === param("periodo")) ?? "todas";
  const viewMode: PautaViewMode = MODOS_VALIDOS.find((valor) => valor === param("modo")) ?? "gantt";
  const setQuery = (texto: string) => definirParam("q", texto);
  const setPeriodo = (valor: PautaPeriodoFiltro) => definirParam("periodo", valor === "todas" ? null : valor);
  const setViewMode = (valor: PautaViewMode) => definirParam("modo", valor === "gantt" ? null : valor);
  const parametrosFiltros = useMemo(() => filtrosPautaParaApi(filtros, new Date()), [filtros]);

  const { inicio: periodoInicio, fim: periodoFim } = useMemo(() => periodoParaIntervalo(periodo === "todas" ? "30d" : periodo), [periodo]);
  const chaveFiltros = JSON.stringify(parametrosFiltros);

  // Parâmetros da consulta (a primeira página e o "carregar mais" usam EXATAMENTE os mesmos): escopo=pauta + só o que está em aberto
  // + filtros avançados. O prazo só entra se o período for escolhido (teto, sem piso: atrasadas continuam); "todas" não o envia, e
  // as sem prazo pertencem à Pauta.
  function parametrosDaConsulta(offset: number) {
    const base = { search: debouncedQuery || undefined, sort: "prazo_asc" as const, limit: TAMANHO_PAGINA, offset };
    const prazoDoPeriodo = periodo === "todas" ? {} : { prazoFim: periodoFim.toISOString() };
    return { ...base, escopo: "pauta" as const, naoFinalizada: true, ...prazoDoPeriodo, ...parametrosFiltros };
  }
  // Demandas com sessão ativa agora (selo discreto); falha não derruba a lista.
  const [emExecucaoIds, setEmExecucaoIds] = useState<ReadonlySet<string>>(new Set());

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
  const chaveBusca = `${chaveFiltros}\u0000${debouncedQuery}\u0000${periodo}\u0000${refetchTick}`;
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
    if (!pronto) return;
    let cancelado = false;
    const consulta = listDemandasReais(parametrosDaConsulta(0));
    const sessoes = listarDemandasEmExecucaoNaPauta().catch(() => [] as string[]);
    Promise.all([consulta, sessoes])
      .then(([resultado, ativas]) => {
        if (cancelado) return; // combinação de filtros obsoleta — outra busca já foi disparada
        setDemandasPauta(resultado);
        setEmExecucaoIds(new Set(ativas));
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `parametrosDaConsulta` é função de render; a lista abaixo resume tudo que ela lê
  }, [pronto, chaveFiltros, debouncedQuery, periodo, periodoFim, refetchTick]);

  function carregarMais() {
    const chaveDoClique = chaveBusca;
    setCarregandoMais(true);
    listDemandasReais(parametrosDaConsulta(demandasPauta.length))
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
    getDemandaReal(selectedDemandId, "pauta")
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

  // Fase 7C.1 — o detalhe aberto pela Pauta é SOMENTE LEITURA por padrão (ler pela Pauta global não dá escrita). Só vira editável se a
  // demanda também está no escopo-BASE de quem olha (a consulta sem `escopo` devolve 200; fora dele, 404): é a mesma autoridade do
  // servidor, que continua decidindo cada escrita. Enquanto a sonda não responde (ou falha), fica em leitura.
  const [acessoEscrita, setAcessoEscrita] = useState<{ demandaId: string; editavel: boolean } | null>(null);
  useEffect(() => {
    if (!selectedDemandId) return;
    let cancelado = false;
    getDemandaReal(selectedDemandId)
      .then(() => {
        if (!cancelado) setAcessoEscrita({ demandaId: selectedDemandId, editavel: true });
      })
      .catch(() => {
        if (!cancelado) setAcessoEscrita({ demandaId: selectedDemandId, editavel: false });
      });
    return () => {
      cancelado = true;
    };
  }, [selectedDemandId]);
  const modoLeitura: EscopoLeituraDemanda | undefined =
    acessoEscrita?.demandaId === selectedDemandId && acessoEscrita.editavel ? undefined : "pauta";

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

  // Operador comum não tem Pauta (tem o Meu Dia). Espera os departamentos antes de negar: Head e Atendimento dependem deles.
  if (carregandoDepartamentos) return <p className="text-sm text-fg-subtle">Carregando…</p>;
  if (!podeAcessar) {
    return (
      <div className="flex flex-col gap-6">
        <AcessoNegado
          titulo="A Pauta é restrita ao Atendimento, Heads e Gestão"
          descricao="Para acompanhar o seu trabalho, use o Meu dia. Fale com a Gestão se você precisa desta visão."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-line bg-surface p-4 shadow-sm"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <CalendarClock className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-fg">Pauta</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-fg-muted">
                Visão operacional da agência: todas as demandas em aberto de todos os departamentos, com ou sem prazo (atrasadas incluídas).
                O período é um filtro opcional.
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      <PautaToolbar
        query={query}
        onQueryChange={setQuery}
        periodo={periodo}
        onPeriodoChange={setPeriodo}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        filtrosAvancados={<FiltrosAvancados definicoes={definicoesFiltros} filtros={filtros} onChange={definirFiltros} />}
      />

      {carregandoInicial ? (
        <p className="text-sm text-fg-subtle">Carregando pauta…</p>
      ) : erro && demandasPauta.length === 0 ? (
        <EmptyState title="Não foi possível carregar a pauta" description={erro} icon={<CalendarClock size={16} />} />
      ) : (
        <div className={buscandoPagina ? "opacity-60 transition-opacity" : "transition-opacity"}>
          {viewMode === "lista" ? (
            <PautaLista demandas={demandasPauta} onOpenDetails={setSelectedDemandId} emExecucaoIds={emExecucaoIds} />
          ) : (
            <PautaGantt demandas={demandasPauta} periodoInicio={periodoInicio} periodoFim={periodoFim} onOpenDetails={setSelectedDemandId} emExecucaoIds={emExecucaoIds} />
          )}
        </div>
      )}

      {erro && demandasPauta.length > 0 && <p className="text-xs text-red-600">{erro}</p>}

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
        modoLeitura={modoLeitura}
      />
    </div>
  );
}
