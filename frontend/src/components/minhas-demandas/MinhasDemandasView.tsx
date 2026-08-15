"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { AlertTriangle, CalendarClock, ClipboardCheck, Gauge, Headset, PauseCircle, PlayCircle, Send } from "lucide-react";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Select } from "@/components/ui/Select";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { IndicadoresGrid, type IndicadorItem } from "@/components/operacional/IndicadoresGrid";
import { DemandaDetailsDrawer } from "@/components/demandas/DemandaDetailsDrawer";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { resolverUsuarioPorReferencia } from "@/lib/referencias";
import {
  formatPrazo,
  normalizarUsuarioId,
  resolveDepartamentosProjetoNomes,
  statusDemandaLabels,
  statusDemandaTone,
} from "@/lib/demandas";
import { classificarTarefa, podeAcessarMinhasDemandas, tarefasDoAtendimento } from "@/lib/escopo-operacional";
import type { DemandaStatus } from "@/types/demanda";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { resolverClientePorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";

type StatusFiltro = DemandaStatus | "todos";

export function MinhasDemandasView() {
  const { demandas, setDemandas, usuarioAtual, setDemandaParaAbrir } = useAppData();
  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();
  const { usuarios } = useDiretorioUsuarios();
  const router = useRouter();
  const [statusFiltro, setStatusFiltro] = useState<StatusFiltro>("todos");
  const [selecionadaId, setSelecionadaId] = useState<string | null>(null);
  const selecionada = demandas.find((demanda) => demanda.id === selecionadaId);

  const podeAcessar = usuarioAtual ? podeAcessarMinhasDemandas(usuarioAtual, departamentos) : false;

  const minhasDemandas = useMemo(
    () => (usuarioAtual ? tarefasDoAtendimento(demandas, usuarioAtual, clientes, usuarios) : []),
    [demandas, usuarioAtual, clientes, usuarios],
  );

  const classificacoes = useMemo(
    () => minhasDemandas.map((demanda) => ({ demanda, classificacao: classificarTarefa(demanda) })),
    [minhasDemandas],
  );

  const criadas = minhasDemandas.length;
  const naoIniciadas = classificacoes.filter((item) => item.classificacao.nova).length;
  const emExecucao = classificacoes.filter((item) => item.classificacao.emAndamento).length;
  const aguardandoCliente = classificacoes.filter((item) => item.classificacao.aguardando).length;
  const aguardandoAtendimento = classificacoes.filter((item) => item.demanda.status === "bloqueada").length;
  const pausadas = classificacoes.filter((item) => item.demanda.status === "pausada").length;
  const atrasadas = classificacoes.filter((item) => item.classificacao.atrasada).length;
  const dentroDoPrazo = classificacoes.filter(
    (item) => !item.classificacao.atrasada && !item.classificacao.concluida && !item.classificacao.cancelada,
  ).length;
  const concluidas = classificacoes.filter((item) => item.classificacao.concluida).length;

  const indicadores: IndicadorItem[] = [
    { key: "criadas", title: "Criadas", value: criadas, description: "No seu escopo de atendimento.", icon: <Headset size={16} />, tone: "blue" },
    { key: "nao-iniciadas", title: "Não iniciadas", value: naoIniciadas, description: "Rascunho ou planejada.", icon: <CalendarClock size={16} />, tone: "neutral" },
    { key: "em-execucao", title: "Em execução", value: emExecucao, description: "Em andamento agora.", icon: <PlayCircle size={16} />, tone: "green" },
    { key: "aguardando-cliente", title: "Aguardando cliente", value: aguardandoCliente, description: "Retorno externo pendente.", icon: <Send size={16} />, tone: "amber" },
    { key: "aguardando-atendimento", title: "Aguardando atendimento", value: aguardandoAtendimento, description: "Bloqueadas — ação interna pendente.", icon: <PauseCircle size={16} />, tone: "amber" },
    { key: "pausadas", title: "Pausadas", value: pausadas, description: "Fluxo suspenso.", icon: <PauseCircle size={16} />, tone: "amber" },
    { key: "atrasadas", title: "Atrasadas", value: atrasadas, description: "Prazo da etapa atual vencido.", icon: <AlertTriangle size={16} />, tone: "red" },
    { key: "dentro-prazo", title: "Dentro do prazo", value: dentroDoPrazo, description: "Ativas, sem atraso.", icon: <Gauge size={16} />, tone: "green" },
    { key: "concluidas", title: "Concluídas", value: concluidas, description: "Finalizadas.", icon: <ClipboardCheck size={16} />, tone: "green" },
  ];

  const listaFiltrada = useMemo(
    () => minhasDemandas.filter((demanda) => statusFiltro === "todos" || demanda.status === statusFiltro),
    [minhasDemandas, statusFiltro],
  );

  if (!usuarioAtual) return null;

  if (!podeAcessar) {
    return (
      <div className="flex flex-col gap-6">
        <Cabecalho />
        <AcessoNegado
          titulo="Visão restrita ao Atendimento"
          descricao="Minhas Demandas mostra as tarefas criadas, sob sua responsabilidade ou de clientes atendidos por você — disponível para quem está no departamento Atendimento."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Cabecalho />

      <IndicadoresGrid itens={indicadores} colunas={3} />

      <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="max-w-xs">
          <Select
            label="Status"
            value={statusFiltro}
            onChange={(event) => setStatusFiltro(event.target.value as StatusFiltro)}
            options={[{ value: "todos", label: "Todos" }, ...Object.entries(statusDemandaLabels).map(([value, label]) => ({ value, label }))]}
          />
        </div>
      </div>

      {listaFiltrada.length === 0 ? (
        <EmptyState title="Nenhuma demanda encontrada" description="Ajuste o filtro para visualizar suas demandas." />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <div className="overflow-x-auto">
            <table className="min-w-[1100px] w-full text-left text-sm">
              <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
                <tr>
                  {["Título", "Cliente", "Depto. executor", "Responsável", "Status", "Prazo", "Previsão", "Última atualização", "Pendência"].map(
                    (coluna) => (
                      <th key={coluna} className="px-4 py-2.5">
                        {coluna}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {listaFiltrada.map((demanda) => {
                  const classificacao = classificarTarefa(demanda);
                  const cliente = resolverClientePorReferencia(demanda.clienteId, clientes);
                  const responsaveis = demanda.usuarioResponsavelIds
                    .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
                    .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario));

                  const pendencia =
                    demanda.status === "aguardando_cliente"
                      ? { texto: "Aguardando retorno do cliente", origem: "Origem: cliente" }
                      : demanda.status === "bloqueada"
                        ? { texto: "Bloqueio interno", origem: "Origem: interna" }
                        : null;

                  return (
                    <tr key={demanda.id} className="group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => setSelecionadaId(demanda.id)}
                          className="max-w-[220px] text-left font-semibold text-zinc-950 transition hover:text-indigo-600 dark:text-zinc-50 dark:hover:text-indigo-400"
                        >
                          <span className="block truncate">{demanda.nome}</span>
                          <span className="mt-0.5 block truncate text-xs font-medium text-zinc-400">{rotuloDemanda(demanda)}</span>
                        </button>
                      </td>
                      <td className="max-w-[140px] truncate px-4 py-3 text-zinc-600 dark:text-zinc-400">{cliente?.nome ?? "Sem cliente"}</td>
                      <td className="max-w-[160px] truncate px-4 py-3 text-zinc-600 dark:text-zinc-400">
                        {resolveDepartamentosProjetoNomes(demanda.departamentoResponsavelIds)}
                      </td>
                      <td className="px-4 py-3">
                        <AvatarStack pessoas={responsaveis} max={2} size="h-7 w-7" />
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <span className={classificacao.atrasada ? "font-semibold text-red-500" : "text-zinc-600 dark:text-zinc-400"}>
                          {formatPrazo(demanda.prazoEtapaAtual)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{formatPrazo(demanda.dataFimPrevista)}</td>
                      <td className="px-4 py-3 text-xs text-zinc-500 dark:text-zinc-400">
                        {new Date(demanda.updatedAt).toLocaleDateString("pt-BR")}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {pendencia ? (
                          <div>
                            <p className="font-medium text-zinc-700 dark:text-zinc-200">{pendencia.texto}</p>
                            <p className="text-zinc-400">{pendencia.origem}</p>
                          </div>
                        ) : (
                          <span className="text-zinc-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <DemandaDetailsDrawer
        key={selecionada?.id}
        demanda={selecionada}
        onClose={() => setSelecionadaId(null)}
        onChange={(demandaAtualizada) =>
          setDemandas((current) => current.map((item) => (item.id === demandaAtualizada.id ? demandaAtualizada : item)))
        }
        onEdit={(demandaId) => {
          // Minhas Demandas não redistribui carga por aqui — edição completa acontece no módulo Tarefas.
          setDemandaParaAbrir({ demandaId, aba: "dados" });
          setSelecionadaId(null);
          router.push("/tarefas");
        }}
      />
    </div>
  );
}

function Cabecalho() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Headset className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Minhas Demandas</h1>
            <p className="mt-1 text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Demandas criadas por você, sob sua responsabilidade, ou de clientes que você atende.
            </p>
          </div>
        </div>
        <Badge tone="blue">Dados locais</Badge>
      </div>
    </motion.div>
  );
}
