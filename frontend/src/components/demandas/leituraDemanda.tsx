"use client";

import { createContext, useContext } from "react";
import type { EscopoLeituraDemanda } from "@/lib/api-backend";

/**
 * Fase 7C.1 — o drawer de detalhe da demanda aberto pela Pauta GLOBAL é SOMENTE LEITURA.
 *
 * Quem tem a Pauta global (Atendimento, Heads e Gestão) enxerga demandas de toda a empresa, mas isso NÃO dá poder de escrita sobre elas
 * (o servidor também recusa: as rotas de escrita ignoram `?escopo=pauta` e seguem no escopo-base). Este contexto leva, até os cartões do
 * drawer, o escopo de leitura: eles passam `escopo=pauta` nas consultas (comentários, histórico, checklist, arquivos, download) e
 * escondem os controles de escrita.
 *
 * `undefined` = drawer normal (editável pelas regras de sempre).
 */
const LeituraDemandaContext = createContext<EscopoLeituraDemanda | undefined>(undefined);

export const LeituraDemandaProvider = LeituraDemandaContext.Provider;

export function useEscopoLeituraDemanda(): EscopoLeituraDemanda | undefined {
  return useContext(LeituraDemandaContext);
}
