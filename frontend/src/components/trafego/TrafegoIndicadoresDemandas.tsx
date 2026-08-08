"use client";

import { useMemo } from "react";
import { ArrowDownToLine, Building2, CheckCircle2, Timer, Users } from "lucide-react";
import { IndicadoresGrid, type IndicadorItem } from "@/components/operacional/IndicadoresGrid";
import { classificarTarefa, formatHoras, horasEstimadasDemanda, horasExecutadasPorEscopo } from "@/lib/escopo-operacional";
import type { Demanda } from "@/types/demanda";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";

/**
 * Indicadores de empresa cruzando Demanda (mock) com Sessão de trabalho (real, via API) —
 * escopo global, exclusivo desta visão (Central de Tráfego).
 */
export function TrafegoIndicadoresDemandas({
  demandas,
  sessoes,
  periodoInicio,
}: {
  demandas: Demanda[];
  sessoes: SessaoTrabalho[];
  periodoInicio: string;
}) {
  const dados = useMemo(() => {
    const inicio = new Date(periodoInicio).getTime();
    const internas = demandas.filter((demanda) => classificarTarefa(demanda).origem === "interna").length;
    const clientes = demandas.length - internas;
    const recebidas = demandas.filter((demanda) => new Date(demanda.createdAt).getTime() >= inicio).length;
    const concluidasNoPeriodo = demandas.filter(
      (demanda) => demanda.status === "concluida" && new Date(demanda.updatedAt).getTime() >= inicio,
    ).length;
    const horasEstimadas = demandas.reduce((total, demanda) => total + horasEstimadasDemanda(demanda), 0);
    const horasExecutadas = horasExecutadasPorEscopo(sessoes, {});

    return { internas, clientes, recebidas, concluidasNoPeriodo, horasEstimadas, horasExecutadas };
  }, [demandas, sessoes, periodoInicio]);

  const indicadores: IndicadorItem[] = [
    {
      key: "interno-cliente",
      title: "Interno vs. cliente",
      value: `${dados.internas} / ${dados.clientes}`,
      description: "Tarefas sem cliente vinculado vs. com cliente (total da base).",
      icon: <Building2 size={16} />,
      tone: "neutral",
    },
    {
      key: "recebido-concluido",
      title: "Recebido vs. concluído",
      value: `${dados.recebidas} / ${dados.concluidasNoPeriodo}`,
      description: "Criadas vs. concluídas no período filtrado.",
      icon: <ArrowDownToLine size={16} />,
      tone: "blue",
    },
    {
      key: "horas-estimadas-vs-executadas",
      title: "Horas estimadas (aprox.) vs. executadas",
      value: `${formatHoras(dados.horasEstimadas)} / ${formatHoras(dados.horasExecutadas)}`,
      description: "Estimativa derivada do workflow vs. sessões de trabalho reais (toda a base).",
      icon: <Timer size={16} />,
      tone: "amber",
    },
    {
      key: "total-tarefas",
      title: "Tarefas na base",
      value: demandas.length,
      description: "Total cadastrado (mock).",
      icon: <Users size={16} />,
      tone: "neutral",
    },
    {
      key: "concluidas-periodo",
      title: "Concluídas no período",
      value: dados.concluidasNoPeriodo,
      description: "Mesma janela do filtro de período acima.",
      icon: <CheckCircle2 size={16} />,
      tone: "green",
    },
  ];

  return <IndicadoresGrid itens={indicadores} colunas={5} />;
}
