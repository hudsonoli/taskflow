"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  CalendarDays,
  Flag,
  Hourglass,
  ListChecks,
  Lock,
  PauseCircle,
  PlayCircle,
  TrendingUp,
} from "lucide-react";
import { FiltrosAvancados } from "@/components/filtros/FiltrosAvancados";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { KpiStrip } from "@/components/ui/KpiStrip";
import {
  getResumoMinhaHome,
  listDemandasReais,
  listarMinhasSessoesAtivas,
  patchDemandaReal,
  type ResumoMinhaHome,
} from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { formatPrazo, prioridadeDemandaLabels, statusDemandaLabels } from "@/lib/demandas";
import { fimDaSemana, inicioDaSemana } from "@/lib/escopo-operacional";
import { filtrosMeuDepartamentoParaApi } from "@/lib/filtros-meu-departamento";
import { ROTULO_FAIXA, faixaDaFila, fronteirasDoDia, type FaixaFila } from "@/lib/meu-dia";
import { resolverClientePorReferencia, resolverDepartamentoNome, resolverProjetoNome, rotuloDemanda } from "@/lib/referencias";
import { useFiltrosNaUrl } from "@/lib/useFiltrosNaUrl";
import { podeCriarDemanda } from "@/types/usuario";
import type { Demanda } from "@/types/demanda";
import { useDefinicoesFiltrosMeuDia } from "./useDefinicoesFiltrosMeuDia";

// MEU DIA = a fila operacional PESSOAL do colaborador: "o que EU tenho para fazer?".
//
// Universo (decidido no SERVIDOR, a partir do token — o cliente nunca informa de quem é o dia): `escopo=meus` = demandas em que o
// usuário logado é responsável, ainda não finalizadas (`naoFinalizada`) e não arquivadas. Autoridade maior (Atendimento, Head,
// Gestor) NÃO amplia esta tela: departamento é o Meu Departamento; visão global é a Pauta. Não filtra por "hoje": uma tarefa
// atribuída continua na fila mesmo com prazo futuro ou atrasada — a ordem (`sort=fila_pessoal`) é que destaca o que é urgente.
//
// Lista e indicadores vêm do servidor (sem o limite de 200 de `AppDataContext`); o filtro vale antes da paginação.
const TAMANHO_PAGINA = 50;

const TOM_DA_FAIXA: Record<FaixaFila, BadgeTone> = {
  execucao: "green",
  atrasada: "red",
  hoje: "amber",
  futura: "neutral",
  sem_prazo: "neutral",
};

/** Limites de semana/ontem só para o resumo pessoal (mensagem de incentivo); a fila usa só `agora` e o dia de hoje. */
function limitesTemporais(agora: Date) {
  const ontemInicio = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate() - 1, 0, 0, 0, 0);
  const ontemFim = new Date(ontemInicio);
  ontemFim.setHours(23, 59, 59, 999);
  return {
    ...fronteirasDoDia(agora),
    semanaInicio: inicioDaSemana(agora).toISOString(),
    semanaFim: fimDaSemana(agora).toISOString(),
    ontemInicio: ontemInicio.toISOString(),
    ontemFim: ontemFim.toISOString(),
  };
}

export function DashboardView() {
  const { usuarioAtual } = useAppData();
  const { clientes, carregando: carregandoClientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();
  const { projetos, carregando: carregandoProjetos } = useDiretorioProjetos();

  const departamentoAtualNome = usuarioAtual ? resolverDepartamentoNome(usuarioAtual.departamentoId, departamentos) : "";
  const podeSinalizar = usuarioAtual ? podeCriarDemanda(usuarioAtual, departamentoAtualNome) : false;

  // Filtros (Status, Cliente, Projeto, Prioridade, Prazo) refinam a fila PESSOAL; ficam na URL.
  const definicoesFiltros = useDefinicoesFiltrosMeuDia({ clientes, projetos, diretoriosProntos: !carregandoClientes && !carregandoProjetos });
  const { filtros, definirFiltros } = useFiltrosNaUrl(definicoesFiltros, true);
  const parametrosFiltros = useMemo(() => filtrosMeuDepartamentoParaApi(filtros, new Date()), [filtros]);

  // Indicadores pessoais — universo INTEGRAL do usuário, independente da página e dos filtros da lista.
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

  // Fila — página do servidor, independente do resumo (falha de uma não afeta a outra).
  const [offset, setOffset] = useState(0);
  const [demandasPagina, setDemandasPagina] = useState<Demanda[]>([]);
  const [emExecucaoIds, setEmExecucaoIds] = useState<ReadonlySet<string>>(new Set());
  const [agoraDaConsulta, setAgoraDaConsulta] = useState(() => new Date());
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [buscandoPagina, setBuscandoPagina] = useState(true);
  const [temProximaPagina, setTemProximaPagina] = useState(false);
  const [erroPagina, setErroPagina] = useState<string | null>(null);
  // Incrementado após PATCH de sinalizada bem-sucedido — refaz a página atual (a ordem pode mudar).
  const [refetchTick, setRefetchTick] = useState(0);

  // Filtro novo volta à primeira página; comparado durante o RENDER (padrão do projeto), nunca em efeito.
  const chaveFiltros = JSON.stringify(parametrosFiltros);
  const [chaveFiltrosVista, setChaveFiltrosVista] = useState(chaveFiltros);
  if (chaveFiltros !== chaveFiltrosVista) {
    setChaveFiltrosVista(chaveFiltros);
    setOffset(0);
  }

  const chaveBusca = `${chaveFiltros}\u0000${offset}\u0000${refetchTick}`;
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  if (chaveBusca !== chaveConsultada) {
    setChaveConsultada(chaveBusca);
    setBuscandoPagina(true);
    setErroPagina(null);
  }

  useEffect(() => {
    if (!usuarioAtual) return;
    let cancelado = false;
    const agora = new Date();
    // `escopo=meus` + token: o servidor decide de quem é a fila. Nenhum id de usuário vai na consulta.
    const fila = listDemandasReais({
      ...parametrosFiltros,
      escopo: "meus",
      naoFinalizada: true,
      sort: "fila_pessoal",
      ...fronteirasDoDia(agora),
      limit: TAMANHO_PAGINA,
      offset,
    });
    // "Em execução agora" vem da SESSÃO ativa do próprio usuário; se essa consulta falhar, a fila continua (sem destaque).
    const sessoes = listarMinhasSessoesAtivas().catch(() => [] as string[]);
    Promise.all([fila, sessoes])
      .then(([resultado, ativas]) => {
        if (cancelado) return;
        if (resultado.length === 0 && offset > 0) {
          setOffset((atual) => Math.max(0, atual - TAMANHO_PAGINA));
          return;
        }
        setDemandasPagina(resultado);
        setEmExecucaoIds(new Set(ativas));
        setAgoraDaConsulta(agora);
        setTemProximaPagina(resultado.length === TAMANHO_PAGINA);
        setErroPagina(null);
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setErroPagina(error instanceof Error ? error.message : "Não foi possível carregar sua fila.");
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      });
    return () => {
      cancelado = true;
    };
  }, [usuarioAtual, parametrosFiltros, offset, refetchTick]);

  const valorIndicador = (valor: number | undefined): string => {
    if (resumo === null && !erroResumo) return "…";
    if (erroResumo || valor === undefined) return "—";
    return String(valor);
  };

  // Indicadores PESSOAIS e operacionais: o que ajuda a executar. Nada de carteira, SLA comercial ou projetos globais.
  const STATS = [
    { label: "Minha fila", value: valorIndicador(resumo?.ativas), icon: ListChecks, accent: "var(--brand-gradient, linear-gradient(135deg,var(--color-indigo-500),var(--color-violet-500)))", onAccent: "var(--on-brand, #ffffff)" },
    { label: "Em andamento", value: valorIndicador(resumo?.andamento), icon: TrendingUp, accent: "linear-gradient(135deg,#0ea5e9,var(--color-indigo-500))" },
    { label: "Pausadas", value: valorIndicador(resumo?.pausadas), icon: PauseCircle, accent: "linear-gradient(135deg,#f59e0b,#f97316)" },
    { label: "Aguardando", value: valorIndicador(resumo?.aguardando), icon: Hourglass, accent: "linear-gradient(135deg,#eab308,#f59e0b)" },
    { label: "Atrasadas", value: valorIndicador(resumo?.atrasadas), icon: AlertTriangle, accent: "linear-gradient(135deg,#ef4444,#dc2626)" },
    { label: "Vencem hoje", value: valorIndicador(resumo?.previstasHoje), icon: CalendarDays, accent: "linear-gradient(135deg,var(--color-violet-500),var(--color-indigo-500))" },
  ];

  const concluidasNaSemana = resumo?.concluidasSemana;
  const concluidasOntem = resumo?.concluidasOntem;

  const mensagemMotivacional =
    concluidasOntem !== undefined && concluidasOntem > 0
      ? `Você concluiu ${concluidasOntem} tarefa${concluidasOntem > 1 ? "s" : ""} ontem — continue nesse ritmo hoje!`
      : concluidasNaSemana !== undefined && concluidasNaSemana > 0
        ? `Você já concluiu ${concluidasNaSemana} tarefa${concluidasNaSemana > 1 ? "s" : ""} esta semana. Seu esforço está fazendo a diferença!`
        : "Um novo dia começa — cada tarefa concluída fortalece a entrega da equipe.";

  // Sem optimistic update: só atualiza após o PATCH real ter sucesso. Refaz a PÁGINA (sinalizar muda a ordem).
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
            <h1 className="text-lg font-semibold tracking-tight text-fg">Olá, {usuarioAtual?.nome.split(" ")[0] ?? "por aqui"}!</h1>
            <p className="mt-1 text-sm leading-6 text-fg-muted">{mensagemMotivacional}</p>
          </div>
        </div>
      </motion.div>

      <KpiStrip
        ariaLabel="Indicadores da sua fila"
        itens={STATS.map(({ label, value, icon: Icone, accent, onAccent }) => ({
          key: label,
          label,
          value,
          icon: <Icone size={16} />,
          accent,
          onAccent,
        }))}
      />
      {erroResumo && <p className="text-xs text-red-600">{erroResumo}</p>}

      <div className="rounded-2xl border border-line bg-surface shadow-sm">
        <div className="flex flex-col gap-3 border-b border-zinc-100 px-5 py-4 dark:border-zinc-800">
          <div>
            <h2 className="text-base font-semibold text-fg">Minha fila</h2>
            <p className="text-sm text-fg-muted">
              O que está designado para você, do mais urgente ao menos urgente.{" "}
              {podeSinalizar ? "Sinalize as prioritárias com a bandeira." : "A bandeira mostra as prioritárias."}
            </p>
          </div>
          <FiltrosAvancados definicoes={definicoesFiltros} filtros={filtros} onChange={definirFiltros} />
        </div>

        {carregandoInicial ? (
          <p className="px-5 py-6 text-sm text-fg-subtle">Carregando…</p>
        ) : erroPagina && demandasPagina.length === 0 ? (
          <p className="px-5 py-6 text-sm text-red-600">{erroPagina}</p>
        ) : demandasPagina.length === 0 ? (
          <p className="px-5 py-6 text-sm text-fg-subtle">
            {filtros.length > 0 ? "Nenhuma tarefa sua corresponde aos filtros." : "Nenhuma tarefa em aberto atribuída a você."}
          </p>
        ) : (
          <ul className={`divide-y divide-zinc-100 dark:divide-zinc-800 ${buscandoPagina ? "opacity-60 transition-opacity" : "transition-opacity"}`}>
            {demandasPagina.map((demanda) => {
              const faixa = faixaDaFila(demanda.prazoEtapaAtual, emExecucaoIds.has(demanda.id), agoraDaConsulta);
              const cliente = resolverClientePorReferencia(demanda.clienteId, clientes);
              const departamentosNomes = demanda.departamentoResponsavelIds
                .map((id) => resolverDepartamentoNome(id, departamentos))
                .filter(Boolean)
                .join(", ");
              return (
                <li key={demanda.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <span className="truncate text-sm font-semibold text-fg">
                        {rotuloDemanda(demanda)} · {demanda.nome}
                      </span>
                      {faixa !== "futura" && faixa !== "sem_prazo" && <Badge tone={TOM_DA_FAIXA[faixa]}>{faixa === "execucao" && <PlayCircle className="mr-1 h-3 w-3" />}{ROTULO_FAIXA[faixa]}</Badge>}
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-fg-muted">
                      <span>{cliente?.nome ?? "Sem cliente"}</span>
                      <span>·</span>
                      <span>{resolverProjetoNome(demanda.projetoId, projetos)}</span>
                      {departamentosNomes && (
                        <>
                          <span>·</span>
                          <span>{departamentosNomes}</span>
                        </>
                      )}
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-fg-muted">
                      <span>{statusDemandaLabels[demanda.status]}</span>
                      {demanda.status === "bloqueada" && (
                        <span className="inline-flex items-center gap-1 text-red-600" title="Tarefa bloqueada">
                          <Lock className="h-3 w-3" />
                        </span>
                      )}
                      <span>·</span>
                      <span>Prioridade {prioridadeDemandaLabels[demanda.prioridade]}</span>
                      <span>·</span>
                      <span className={faixa === "atrasada" ? "font-semibold text-red-600" : ""}>Prazo {formatPrazo(demanda.prazoEtapaAtual)}</span>
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
                        demanda.sinalizada ? "h-4 w-4 fill-red-500 text-red-600" : "h-4 w-4 text-zinc-300 hover:text-fg-subtle dark:text-zinc-700"
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
