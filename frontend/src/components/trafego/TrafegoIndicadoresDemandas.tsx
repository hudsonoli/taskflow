"use client";

import { ArrowDownToLine, Building2, CheckCircle2, Timer, Users } from "lucide-react";
import { IndicadoresGrid, type IndicadorItem } from "@/components/operacional/IndicadoresGrid";
import { formatHoras } from "@/lib/escopo-operacional";
import type { ResumoOperacional } from "@/lib/api-backend";

/**
 * D2-D3A — os 5 indicadores baseados em Demanda (interno/cliente, recebido/concluído, horas
 * estimadas, tarefas na base) vêm de `GET /demandas/operacional/resumo`, agregado no
 * servidor sobre o universo INTEGRAL permitido — nunca mais `AppDataContext.demandas` (200
 * mais recentes da empresa). `resumo === null` distingue "carregando" de "zero confirmado";
 * `erro` cobre falha da requisição — nenhum dos dois fabrica valor.
 *
 * D2-D3B — Horas EXECUTADAS deixa de vir de `horasExecutadasPorEscopo(sessoes, {})` (array
 * de `SessaoTrabalho` já sujeito ao cap de ~100 de `listSessoesTrabalho`) e passa a vir de
 * `GET /sessoes-trabalho/trafego/resumo`, agregado no servidor sem paginação. Estado
 * independente do resumo de Demandas: falha de um não afeta o outro.
 */
export function TrafegoIndicadoresDemandas({
  resumo,
  erro,
  horasExecutadas,
  erroHorasExecutadas,
}: {
  resumo: ResumoOperacional | null;
  erro: string | null;
  horasExecutadas: number | null;
  erroHorasExecutadas: string | null;
}) {
  const valor = (campo: number | undefined): number | string => {
    if (resumo === null && !erro) return "…";
    if (erro || campo === undefined) return "—";
    return campo;
  };

  const horasExecutadasTexto =
    horasExecutadas === null && !erroHorasExecutadas ? "…" : erroHorasExecutadas ? "—" : formatHoras(horasExecutadas ?? 0);

  const indicadores: IndicadorItem[] = [
    {
      key: "interno-cliente",
      title: "Interno vs. cliente",
      value: `${valor(resumo?.internas)} / ${valor(resumo?.clientes)}`,
      description: "Tarefas sem cliente vinculado vs. com cliente (total da base).",
      icon: <Building2 size={16} />,
      tone: "neutral",
    },
    {
      key: "recebido-concluido",
      title: "Recebido vs. concluído",
      value: `${valor(resumo?.recebidas)} / ${valor(resumo?.concluidasNoPeriodo)}`,
      description: "Criadas vs. concluídas no período filtrado.",
      icon: <ArrowDownToLine size={16} />,
      tone: "blue",
    },
    {
      key: "horas-estimadas-vs-executadas",
      title: "Horas estimadas (aprox.) vs. executadas",
      value: `${resumo === null && !erro ? "…" : erro ? "—" : formatHoras(resumo?.horasEstimadas ?? 0)} / ${horasExecutadasTexto}`,
      description: "Estimativa derivada do workflow vs. sessões de trabalho reais (toda a base).",
      icon: <Timer size={16} />,
      tone: "amber",
    },
    {
      key: "total-tarefas",
      title: "Tarefas na base",
      value: valor(resumo?.totalNaBase),
      description: "Total cadastrado.",
      icon: <Users size={16} />,
      tone: "neutral",
    },
    {
      key: "concluidas-periodo",
      title: "Concluídas no período",
      value: valor(resumo?.concluidasNoPeriodo),
      description: "Mesma janela do filtro de período acima.",
      icon: <CheckCircle2 size={16} />,
      tone: "green",
    },
  ];

  return <IndicadoresGrid itens={indicadores} colunas={5} />;
}
