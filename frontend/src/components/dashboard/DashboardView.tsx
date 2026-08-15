"use client";

import { useMemo } from "react";
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
import { StatCard } from "@/components/dashboard/StatCard";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { resolverDepartamentoNome } from "@/lib/referencias";
import { formatPrazo, generateId, resolveProjetoDemandaNome, statusDemandaLabels } from "@/lib/demandas";
import { classificarTarefa, inicioDaSemana, mesmoDia, tarefasDoUsuario } from "@/lib/escopo-operacional";
import { podeCriarDemanda } from "@/types/usuario";
import type { Demanda } from "@/types/demanda";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { resolverClientePorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";

export function DashboardView() {
  const { demandas, setDemandas, usuarioAtual } = useAppData();
  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();
  const { usuarios: diretorio } = useDiretorioUsuarios();

  const departamentoAtualNome = usuarioAtual ? resolverDepartamentoNome(usuarioAtual.departamentoId, departamentos) : "";
  const podeSinalizar = usuarioAtual ? podeCriarDemanda(usuarioAtual, departamentoAtualNome) : false;

  const minhasTarefas = useMemo(
    () => (usuarioAtual ? tarefasDoUsuario(demandas, usuarioAtual.id, diretorio) : []),
    [demandas, usuarioAtual, diretorio],
  );

  const classificacoes = useMemo(
    () => minhasTarefas.map((demanda) => ({ demanda, classificacao: classificarTarefa(demanda) })),
    [minhasTarefas],
  );

  const ativas = classificacoes.filter((item) => !item.classificacao.concluida && !item.classificacao.cancelada).length;
  const novas = classificacoes.filter((item) => item.classificacao.nova).length;
  const andamento = classificacoes.filter((item) => item.classificacao.emAndamento).length;
  const pausadas = classificacoes.filter((item) => item.classificacao.pausada).length;
  const aguardando = classificacoes.filter((item) => item.classificacao.aguardando).length;
  const atrasadas = classificacoes.filter((item) => item.classificacao.atrasada).length;
  const concluidas = classificacoes.filter((item) => item.classificacao.concluida).length;
  const previstasHoje = classificacoes.filter((item) => item.classificacao.previstaHoje).length;
  const previstasSemana = classificacoes.filter((item) => item.classificacao.previstaSemana).length;

  const STATS = [
    { label: "Tarefas ativas", value: String(ativas), icon: Sparkles, accent: "linear-gradient(135deg,#6366f1,#8b5cf6)" },
    { label: "Novas", value: String(novas), icon: CalendarClock, accent: "linear-gradient(135deg,#38bdf8,#6366f1)" },
    { label: "Andamento", value: String(andamento), icon: TrendingUp, accent: "linear-gradient(135deg,#0ea5e9,#6366f1)" },
    { label: "Pausadas", value: String(pausadas), icon: PauseCircle, accent: "linear-gradient(135deg,#f59e0b,#f97316)" },
    { label: "Aguardando", value: String(aguardando), icon: Send, accent: "linear-gradient(135deg,#eab308,#f59e0b)" },
    { label: "Atrasadas", value: String(atrasadas), icon: AlertTriangle, accent: "linear-gradient(135deg,#ef4444,#dc2626)" },
    { label: "Concluídas", value: String(concluidas), icon: CheckCircle2, accent: "linear-gradient(135deg,#22c55e,#0ea5e9)" },
    { label: "Previstas para hoje", value: String(previstasHoje), icon: CalendarDays, accent: "linear-gradient(135deg,#8b5cf6,#6366f1)" },
    { label: "Previstas para a semana", value: String(previstasSemana), icon: Clock3, accent: "linear-gradient(135deg,#8b5cf6,#a855f7)" },
  ];

  const agora = new Date();
  const ontem = new Date(agora);
  ontem.setDate(agora.getDate() - 1);
  const inicioSemanaAtual = inicioDaSemana(agora);

  const concluidasNaSemana = minhasTarefas.filter(
    (demanda) => demanda.status === "concluida" && new Date(demanda.updatedAt) >= inicioSemanaAtual,
  ).length;
  const concluidasOntem = minhasTarefas.filter(
    (demanda) => demanda.status === "concluida" && mesmoDia(new Date(demanda.updatedAt), ontem),
  ).length;

  const mensagemMotivacional =
    concluidasOntem > 0
      ? `Você concluiu ${concluidasOntem} tarefa${concluidasOntem > 1 ? "s" : ""} ontem — continue nesse ritmo hoje!`
      : concluidasNaSemana > 0
        ? `Você já concluiu ${concluidasNaSemana} tarefa${concluidasNaSemana > 1 ? "s" : ""} esta semana. Seu esforço está fazendo a diferença!`
        : "Um novo dia começa — cada tarefa concluída fortalece a entrega da equipe.";

  const tarefasCadastradas = useMemo(
    () =>
      [...minhasTarefas]
        .filter((demanda) => demanda.status !== "concluida" && demanda.status !== "cancelada")
        .sort((a, b) => Number(b.sinalizada) - Number(a.sinalizada)),
    [minhasTarefas],
  );

  function alternarSinalizada(demanda: Demanda) {
    if (!podeSinalizar) return;
    setDemandas((current) =>
      current.map((item) => {
        if (item.id !== demanda.id) return item;
        const novaSinalizada = !item.sinalizada;
        return {
          ...item,
          sinalizada: novaSinalizada,
          updatedAt: new Date().toISOString(),
          historico: [
            {
              id: generateId("hist-demanda"),
              usuarioId: usuarioAtual?.id ?? "user-1",
              usuario: usuarioAtual?.nome ?? "Você",
              acao: novaSinalizada ? "Marcada como prioritária" : "Sinalização de prioridade removida",
              dataHora: new Date().toLocaleString("pt-BR"),
              ip: "127.0.0.1",
              dispositivo: "Workspace local",
            },
            ...item.historico,
          ],
        };
      }),
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-6"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              Olá, {usuarioAtual?.nome.split(" ")[0] ?? "por aqui"}!
            </h1>
            <p className="mt-1 text-sm leading-6 text-zinc-500 dark:text-zinc-400">{mensagemMotivacional}</p>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {STATS.map((stat, index) => (
          <StatCard key={stat.label} index={index} {...stat} />
        ))}
      </div>

      <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 shadow-sm dark:border-indigo-500/20 dark:bg-indigo-500/5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-500 dark:text-indigo-400">Resumo</p>
        <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-zinc-700 dark:text-zinc-300">
          <p>
            Esta semana: <span className="font-semibold text-zinc-900 dark:text-zinc-100">{concluidasNaSemana}</span> tarefa(s) concluída(s)
          </p>
          <p>
            Ontem: <span className="font-semibold text-zinc-900 dark:text-zinc-100">{concluidasOntem}</span> tarefa(s) concluída(s)
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="border-b border-zinc-100 px-5 py-4 dark:border-zinc-800">
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Tarefas cadastradas</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Suas tarefas em aberto. {podeSinalizar ? "Sinalize as prioritárias com a bandeira." : "A bandeira mostra as prioritárias."}
          </p>
        </div>

        {tarefasCadastradas.length === 0 ? (
          <p className="px-5 py-6 text-sm text-zinc-400">Nenhuma tarefa em aberto atribuída a você.</p>
        ) : (
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {tarefasCadastradas.map((demanda) => {
              const classificacao = classificarTarefa(demanda);
              const cliente = resolverClientePorReferencia(demanda.clienteId, clientes);
              return (
                <li key={demanda.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {rotuloDemanda(demanda)} · {demanda.nome}
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 truncate text-xs text-zinc-500 dark:text-zinc-400">
                      <span>{cliente?.nome ?? "Sem cliente"}</span>
                      <span>·</span>
                      <span>{resolveProjetoDemandaNome(demanda.projetoId)}</span>
                      <span>·</span>
                      <span>{statusDemandaLabels[demanda.status]}</span>
                      {demanda.status === "bloqueada" && (
                        <span className="inline-flex items-center gap-1 text-red-500" title="Tarefa bloqueada">
                          <Lock className="h-3 w-3" />
                        </span>
                      )}
                      <span>·</span>
                      <span className={classificacao.atrasada ? "inline-flex items-center gap-1 font-semibold text-red-500" : ""}>
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
                          ? "h-4 w-4 fill-red-500 text-red-500"
                          : "h-4 w-4 text-zinc-300 hover:text-zinc-400 dark:text-zinc-700"
                      }
                    />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
