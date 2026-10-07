"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  CalendarClock,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Flag,
  Lock,
  PauseCircle,
  Send,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { StatCard } from "@/components/dashboard/StatCard";
import { getResumoMinhaHome, listDemandasReais, patchDemandaReal, type ResumoMinhaHome } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { resolverDepartamentoNome, resolverProjetoNome } from "@/lib/referencias";
import { formatPrazo, statusDemandaLabels } from "@/lib/demandas";
import { classificarTarefa, fimDaSemana, inicioDaSemana } from "@/lib/escopo-operacional";
import { podeCriarDemanda } from "@/types/usuario";
import type { Demanda } from "@/types/demanda";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { resolverClientePorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";

// D2-D2: mesma razão do D2-B1/B2/B3/B4/D2-C/D2-D1 — AppDataContext.demandas vem limitado a
// 200 itens carregados uma única vez no login, GLOBAIS (não por usuário). Os 9 cards + os 2
// números do resumo textual passam a vir de `GET /demandas/minha-home/resumo`, agregados no
// servidor sobre o universo INTEGRAL permitido (escopo normal + responsável N:N == eu) — a
// lista "Tarefas cadastradas" passa a consultar `GET /demandas` com paginação real
// (`responsavelId` + `naoFinalizada`, ambos já existentes; `sort=sinalizada_desc`, novo).
// AppDataContext continua fornecendo só `usuarioAtual` — nenhuma leitura/escrita de
// `demandas`/`setDemandas` aqui.
const TAMANHO_PAGINA = 50;

/**
 * Todos os limites derivam da MESMA referência (`agora`), nunca de `new Date()` chamado
 * separadamente — mesma exigência de `periodoParaIntervalo` (PautaView.tsx)/`atrasada`
 * (D2-B5): fronteiras calculadas no cliente, enviadas como ISO explícito, nunca recalculadas
 * no backend.
 */
function limitesTemporais(agora: Date) {
  const hojeInicio = new Date(agora);
  hojeInicio.setHours(0, 0, 0, 0);
  const hojeFim = new Date(hojeInicio);
  hojeFim.setHours(23, 59, 59, 999);

  const ontemInicio = new Date(hojeInicio);
  ontemInicio.setDate(ontemInicio.getDate() - 1);
  const ontemFim = new Date(ontemInicio);
  ontemFim.setHours(23, 59, 59, 999);

  return {
    agora: agora.toISOString(),
    hojeInicio: hojeInicio.toISOString(),
    hojeFim: hojeFim.toISOString(),
    semanaInicio: inicioDaSemana(agora).toISOString(),
    semanaFim: fimDaSemana(agora).toISOString(),
    ontemInicio: ontemInicio.toISOString(),
    ontemFim: ontemFim.toISOString(),
  };
}

export function DashboardView() {
  const { usuarioAtual } = useAppData();
  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();
  const { projetos } = useDiretorioProjetos();

  const departamentoAtualNome = usuarioAtual ? resolverDepartamentoNome(usuarioAtual.departamentoId, departamentos) : "";
  const podeSinalizar = usuarioAtual ? podeCriarDemanda(usuarioAtual, departamentoAtualNome) : false;

  // Resumo — universo INTEGRAL, independente da página da lista abaixo (nenhum dos 11 campos
  // depende de offset/sinalizada). `cancelado` evita resposta obsoleta; `resumo === null`
  // distingue "ainda carregando" de "zero confirmado" (nunca mostrar 0 como se fosse dado).
  const [resumo, setResumo] = useState<ResumoMinhaHome | null>(null);
  const [erroResumo, setErroResumo] = useState<string | null>(null);
  useEffect(() => {
    if (!usuarioAtual) return;
    let cancelado = false;
    getResumoMinhaHome(limitesTemporais(new Date()))
      .then((resultado) => {
        if (!cancelado) {
          setResumo(resultado);
          setErroResumo(null);
        }
      })
      .catch((error) => {
        if (!cancelado) setErroResumo(error instanceof Error ? error.message : "Não foi possível carregar os indicadores.");
      });
    return () => {
      cancelado = true;
    };
  }, [usuarioAtual]);

  // Lista — página do servidor, independente do resumo (falha de uma não afeta a outra).
  const [offset, setOffset] = useState(0);
  const [demandasPagina, setDemandasPagina] = useState<Demanda[]>([]);
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [buscandoPagina, setBuscandoPagina] = useState(true);
  const [temProximaPagina, setTemProximaPagina] = useState(false);
  const [erroPagina, setErroPagina] = useState<string | null>(null);
  // Incrementado após PATCH de sinalizada bem-sucedido — força refetch da página atual
  // (a ordenação pode mudar) sem refazer o resumo (nenhum dos 11 campos depende disso).
  const [refetchTick, setRefetchTick] = useState(0);

  // Comparado durante o RENDER, não dentro do efeito: setState síncrono no corpo do efeito é
  // o padrão que react-hooks/set-state-in-effect rejeita neste projeto — mesma técnica de
  // DemandasView.tsx/PautaView.tsx/MinhasDemandasView.tsx.
  const chaveBusca = `${offset}\u0000${refetchTick}`;
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  if (chaveBusca !== chaveConsultada) {
    setChaveConsultada(chaveBusca);
    setBuscandoPagina(true);
    setErroPagina(null);
  }

  useEffect(() => {
    if (!usuarioAtual) return;
    let cancelado = false;
    listDemandasReais({
      responsavelId: usuarioAtual.id,
      naoFinalizada: true,
      sort: "sinalizada_desc",
      limit: TAMANHO_PAGINA,
      offset,
    })
      .then((resultado) => {
        if (cancelado) return;
        if (resultado.length === 0 && offset > 0) {
          setOffset((atual) => Math.max(0, atual - TAMANHO_PAGINA));
          return;
        }
        setDemandasPagina(resultado);
        setTemProximaPagina(resultado.length === TAMANHO_PAGINA);
        setErroPagina(null);
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setErroPagina(error instanceof Error ? error.message : "Não foi possível carregar suas tarefas.");
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      });
    return () => {
      cancelado = true;
    };
  }, [usuarioAtual, offset, refetchTick]);

  const valorIndicador = (valor: number | undefined): number | string => {
    if (resumo === null && !erroResumo) return "…";
    if (erroResumo || valor === undefined) return "—";
    return valor;
  };

  const STATS = [
    { label: "Tarefas ativas", value: String(valorIndicador(resumo?.ativas)), icon: Sparkles, accent: "var(--brand-gradient, linear-gradient(135deg,var(--color-indigo-500),var(--color-violet-500)))", onAccent: "var(--on-brand, #ffffff)" },
    { label: "Novas", value: String(valorIndicador(resumo?.novas)), icon: CalendarClock, accent: "linear-gradient(135deg,#38bdf8,var(--color-indigo-500))" },
    { label: "Andamento", value: String(valorIndicador(resumo?.andamento)), icon: TrendingUp, accent: "linear-gradient(135deg,#0ea5e9,var(--color-indigo-500))" },
    { label: "Pausadas", value: String(valorIndicador(resumo?.pausadas)), icon: PauseCircle, accent: "linear-gradient(135deg,#f59e0b,#f97316)" },
    { label: "Aguardando", value: String(valorIndicador(resumo?.aguardando)), icon: Send, accent: "linear-gradient(135deg,#eab308,#f59e0b)" },
    { label: "Atrasadas", value: String(valorIndicador(resumo?.atrasadas)), icon: AlertTriangle, accent: "linear-gradient(135deg,#ef4444,#dc2626)" },
    { label: "Concluídas", value: String(valorIndicador(resumo?.concluidas)), icon: CheckCircle2, accent: "linear-gradient(135deg,#22c55e,#0ea5e9)" },
    { label: "Previstas para hoje", value: String(valorIndicador(resumo?.previstasHoje)), icon: CalendarDays, accent: "linear-gradient(135deg,var(--color-violet-500),var(--color-indigo-500))" },
    { label: "Previstas para a semana", value: String(valorIndicador(resumo?.previstasSemana)), icon: Clock3, accent: "linear-gradient(135deg,var(--color-violet-500),#a855f7)" },
  ];

  const concluidasNaSemana = resumo?.concluidasSemana;
  const concluidasOntem = resumo?.concluidasOntem;

  const mensagemMotivacional =
    concluidasOntem !== undefined && concluidasOntem > 0
      ? `Você concluiu ${concluidasOntem} tarefa${concluidasOntem > 1 ? "s" : ""} ontem — continue nesse ritmo hoje!`
      : concluidasNaSemana !== undefined && concluidasNaSemana > 0
        ? `Você já concluiu ${concluidasNaSemana} tarefa${concluidasNaSemana > 1 ? "s" : ""} esta semana. Seu esforço está fazendo a diferença!`
        : "Um novo dia começa — cada tarefa concluída fortalece a entrega da equipe.";

  // Sem optimistic update, como antes da migração — só atualiza após o PATCH real ter
  // sucesso. Refetch da PÁGINA (não patch local): sinalizar/dessinalizar muda a ordenação
  // (`sinalizada_desc`) — a demanda pode legitimamente sair da página atual, e só um refetch
  // decide isso corretamente. Não refaz o resumo: nenhum dos 11 campos depende de sinalizada.
  async function alternarSinalizada(demanda: Demanda) {
    if (!podeSinalizar) return;
    try {
      await patchDemandaReal(demanda.id, { sinalizada: !demanda.sinalizada });
      setRefetchTick((tick) => tick + 1);
    } catch (error) {
      console.error("Não foi possível atualizar a sinalização da tarefa", error);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-fg">
              Olá, {usuarioAtual?.nome.split(" ")[0] ?? "por aqui"}!
            </h1>
            <p className="mt-1 text-sm leading-6 text-fg-muted">{mensagemMotivacional}</p>
          </div>
          <Badge tone="green">Banco real</Badge>
        </div>
      </motion.div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {STATS.map((stat, index) => (
          <StatCard key={stat.label} index={index} {...stat} />
        ))}
      </div>
      {erroResumo && <p className="text-xs text-red-600">{erroResumo}</p>}

      <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 shadow-sm dark:border-indigo-500/20 dark:bg-indigo-500/5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-600 dark:text-indigo-400">Resumo</p>
        <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-zinc-700 dark:text-zinc-300">
          <p>
            Esta semana: <span className="font-semibold text-fg">{valorIndicador(resumo?.concluidasSemana)}</span> tarefa(s) concluída(s)
          </p>
          <p>
            Ontem: <span className="font-semibold text-fg">{valorIndicador(resumo?.concluidasOntem)}</span> tarefa(s) concluída(s)
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-line bg-surface shadow-sm">
        <div className="border-b border-zinc-100 px-5 py-4 dark:border-zinc-800">
          <h2 className="text-base font-semibold text-fg">Tarefas cadastradas</h2>
          <p className="text-sm text-fg-muted">
            Suas tarefas em aberto. {podeSinalizar ? "Sinalize as prioritárias com a bandeira." : "A bandeira mostra as prioritárias."}
          </p>
        </div>

        {carregandoInicial ? (
          <p className="px-5 py-6 text-sm text-fg-subtle">Carregando…</p>
        ) : erroPagina && demandasPagina.length === 0 ? (
          <p className="px-5 py-6 text-sm text-red-600">{erroPagina}</p>
        ) : demandasPagina.length === 0 ? (
          <p className="px-5 py-6 text-sm text-fg-subtle">Nenhuma tarefa em aberto atribuída a você.</p>
        ) : (
          <ul className={`divide-y divide-zinc-100 dark:divide-zinc-800 ${buscandoPagina ? "opacity-60 transition-opacity" : "transition-opacity"}`}>
            {demandasPagina.map((demanda) => {
              const classificacao = classificarTarefa(demanda);
              const cliente = resolverClientePorReferencia(demanda.clienteId, clientes);
              return (
                <li key={demanda.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-fg">
                      {rotuloDemanda(demanda)} · {demanda.nome}
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 truncate text-xs text-fg-muted">
                      <span>{cliente?.nome ?? "Sem cliente"}</span>
                      <span>·</span>
                      <span>{resolverProjetoNome(demanda.projetoId, projetos)}</span>
                      <span>·</span>
                      <span>{statusDemandaLabels[demanda.status]}</span>
                      {demanda.status === "bloqueada" && (
                        <span className="inline-flex items-center gap-1 text-red-600" title="Tarefa bloqueada">
                          <Lock className="h-3 w-3" />
                        </span>
                      )}
                      <span>·</span>
                      <span className={classificacao.atrasada ? "inline-flex items-center gap-1 font-semibold text-red-600" : ""}>
                        {classificacao.atrasada && <AlertTriangle className="h-3 w-3" />}
                        Prazo {formatPrazo(demanda.prazoEtapaAtual)}
                      </span>
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => alternarSinalizada(demanda)}
                    disabled={!podeSinalizar}
                    title={
                      podeSinalizar
                        ? demanda.sinalizada
                          ? "Remover sinalização de prioridade"
                          : "Marcar como prioritária"
                        : "Apenas Gestão, líderes de departamento (heads) e Atendimento podem sinalizar prioridade"
                    }
                    className="shrink-0 rounded-full p-2 transition disabled:cursor-not-allowed"
                  >
                    <Flag
                      className={
                        demanda.sinalizada
                          ? "h-4 w-4 fill-red-500 text-red-600"
                          : "h-4 w-4 text-zinc-300 hover:text-fg-subtle dark:text-zinc-700"
                      }
                    />
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {erroPagina && demandasPagina.length > 0 && <p className="px-5 pb-3 text-xs text-red-600">{erroPagina}</p>}

        {!carregandoInicial && (demandasPagina.length > 0 || offset > 0) && (
          <div className="flex items-center justify-between border-t border-zinc-100 px-5 py-3 dark:border-zinc-800">
            <span className="text-xs text-fg-subtle">
              {offset > 0 ? `Itens ${offset + 1}–${offset + demandasPagina.length}` : `${demandasPagina.length} item(ns)`}
            </span>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={offset === 0 || buscandoPagina}
                onClick={() => setOffset((atual) => Math.max(0, atual - TAMANHO_PAGINA))}
              >
                Anterior
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={!temProximaPagina || buscandoPagina}
                onClick={() => setOffset((atual) => atual + TAMANHO_PAGINA)}
              >
                Próxima
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
