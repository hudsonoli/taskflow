// Filtros avançados da Central de Tráfego → parâmetros de `/sessoes-trabalho/trafego/*`. Lógica PURA (testável com `node --test`).
//
// O domínio do Tráfego é a SESSÃO DE TRABALHO: usuário e departamento são da sessão; cliente, projeto, prioridade e prazo são
// da Demanda em que a sessão acontece. O período (Hoje/24h/7d/30d) e a busca de Demanda continuam fora dos filtros estruturados.
// Entre campos: AND; dentro do campo: OR ("é um de"); "não é" mantém a sessão cujo campo é vazio (NULL ≠ qualquer valor).
import { ehNegativo, intervaloDaData } from "./filtros-avancados.ts";
import type { FiltroAtivo } from "../types/filtros.ts";

export const CAMPO_TRAFEGO = {
  usuario: "usuario",
  departamento: "departamento",
  cliente: "cliente",
  projeto: "projeto",
  prioridade: "prioridade",
  prazo: "prazo",
  status: "status",
} as const;

export type TrafegoStatusSessao = "todos" | "ativa" | "encerrada";

/** O que a API de Tráfego entende (listas vazias = sem filtro). */
export type FiltrosTrafegoApi = {
  usuarioIds: string[];
  usuarioIdsExcluir: string[];
  departamentoIds: string[];
  departamentoIdsExcluir: string[];
  clienteIds: string[];
  clienteIdsExcluir: string[];
  projetoIds: string[];
  projetoIdsExcluir: string[];
  prioridades: string[];
  prioridadesExcluir: string[];
  prazoInicio?: string;
  prazoFim?: string;
  /** status da sessão: só os indicadores o usam ("encerrada" não esconde sessões ativas — regra de D3C1) */
  status: TrafegoStatusSessao;
};

export const FILTROS_TRAFEGO_VAZIOS: FiltrosTrafegoApi = {
  usuarioIds: [],
  usuarioIdsExcluir: [],
  departamentoIds: [],
  departamentoIdsExcluir: [],
  clienteIds: [],
  clienteIdsExcluir: [],
  projetoIds: [],
  projetoIdsExcluir: [],
  prioridades: [],
  prioridadesExcluir: [],
  status: "todos",
};

type CampoLista = "usuario" | "departamento" | "cliente" | "projeto" | "prioridade";
const LISTAS: Record<CampoLista, [keyof FiltrosTrafegoApi, keyof FiltrosTrafegoApi]> = {
  usuario: ["usuarioIds", "usuarioIdsExcluir"],
  departamento: ["departamentoIds", "departamentoIdsExcluir"],
  cliente: ["clienteIds", "clienteIdsExcluir"],
  projeto: ["projetoIds", "projetoIdsExcluir"],
  prioridade: ["prioridades", "prioridadesExcluir"],
};

export function filtrosTrafegoParaApi(filtros: readonly FiltroAtivo[], agora: Date = new Date()): FiltrosTrafegoApi {
  const api: FiltrosTrafegoApi = { ...FILTROS_TRAFEGO_VAZIOS };
  for (const filtro of filtros) {
    if (filtro.valores.length === 0) continue;
    if (filtro.campo in LISTAS) {
      const [positivo, negativo] = LISTAS[filtro.campo as CampoLista];
      (api[ehNegativo(filtro.operador) ? negativo : positivo] as string[]) = [...filtro.valores];
    } else if (filtro.campo === CAMPO_TRAFEGO.prazo) {
      const intervalo = intervaloDaData(filtro.operador, filtro.valores[0], agora);
      if (intervalo?.inicio) api.prazoInicio = intervalo.inicio.toISOString();
      if (intervalo?.fim) api.prazoFim = intervalo.fim.toISOString();
    } else if (filtro.campo === CAMPO_TRAFEGO.status) {
      const valor = filtro.valores[0];
      if (valor === "ativa" || valor === "encerrada") api.status = valor;
    }
  }
  return api;
}

/** Parâmetros de consulta dos filtros estruturados (sem período/busca/paginação), omitindo o que está vazio. */
export function parametrosFiltrosTrafego(filtros: FiltrosTrafegoApi): Array<[string, string]> {
  const pares: Array<[string, string]> = [];
  const lista = (nome: string, valores: string[]) => {
    if (valores.length > 0) pares.push([nome, valores.join(",")]);
  };
  lista("usuarioIds", filtros.usuarioIds);
  lista("usuarioIdsExcluir", filtros.usuarioIdsExcluir);
  lista("departamentoIds", filtros.departamentoIds);
  lista("departamentoIdsExcluir", filtros.departamentoIdsExcluir);
  lista("clienteIds", filtros.clienteIds);
  lista("clienteIdsExcluir", filtros.clienteIdsExcluir);
  lista("projetoIds", filtros.projetoIds);
  lista("projetoIdsExcluir", filtros.projetoIdsExcluir);
  lista("prioridades", filtros.prioridades);
  lista("prioridadesExcluir", filtros.prioridadesExcluir);
  if (filtros.prazoInicio) pares.push(["prazoInicio", filtros.prazoInicio]);
  if (filtros.prazoFim) pares.push(["prazoFim", filtros.prazoFim]);
  return pares;
}
