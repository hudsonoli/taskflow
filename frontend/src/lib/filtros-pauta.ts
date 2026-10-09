// Filtros avançados da PAUTA GLOBAL → parâmetros de `GET /demandas?escopo=pauta`. Lógica PURA (testável com `node --test`).
//
// Na Pauta global o escopo é a EMPRESA inteira (do tenant do token), então — ao contrário do Meu Departamento — o Departamento É um
// filtro (OR entre valores; sem "não é", que o servidor não executa para departamento). Os demais campos têm exatamente o mesmo
// mapeamento do Meu Departamento (responsável, equipe, cliente, projeto, status, prioridade, prazo, origem).
import { filtrosMeuDepartamentoParaApi, type ParametrosFiltrosMeuDepartamento } from "./filtros-meu-departamento.ts";
import type { FiltroAtivo } from "../types/filtros.ts";

export const CAMPO_PAUTA = {
  departamento: "departamento",
  responsavel: "responsavel",
  equipe: "equipe",
  cliente: "cliente",
  projeto: "projeto",
  status: "status",
  prioridade: "prioridade",
  prazo: "prazo",
  origem: "origem",
} as const;

export type ParametrosFiltrosPauta = ParametrosFiltrosMeuDepartamento & { departamentoId?: string };

export function filtrosPautaParaApi(filtros: readonly FiltroAtivo[], agora: Date = new Date()): ParametrosFiltrosPauta {
  const parametros: ParametrosFiltrosPauta = filtrosMeuDepartamentoParaApi(filtros, agora);
  const departamento = filtros.find((filtro) => filtro.campo === CAMPO_PAUTA.departamento);
  // só "é"/"é um de": "não é" não existe para departamento (o servidor não o executa)
  if (departamento && departamento.valores.length > 0 && (departamento.operador === "is" || departamento.operador === "in")) {
    parametros.departamentoId = departamento.valores.join(",");
  }
  return parametros;
}
