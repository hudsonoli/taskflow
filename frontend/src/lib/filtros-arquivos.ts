// Filtros avançados de Arquivos → parâmetros do `GET /arquivos`. Lógica PURA (testável com `node --test`).
//
// Campos (ids estáveis, também usados na URL): cliente, projeto, demanda, tipo, status, enviadoPor, dataEnvio.
// "é"/"é um de" → `clienteId=a,b` (OR); "não é"/"não é um de" → `clienteIdExcluir=a,b`. Entre campos: AND (no servidor).
// A busca por nome (`search`) é separada dos filtros estruturados.
import { ehNegativo, intervaloDaData } from "./filtros-avancados.ts";
import type { FiltroAtivo } from "../types/filtros.ts";

export const CAMPO_ARQUIVOS = {
  cliente: "cliente",
  projeto: "projeto",
  demanda: "demanda",
  tipo: "tipo",
  status: "status",
  enviadoPor: "enviadoPor",
  dataEnvio: "dataEnvio",
} as const;

/** Subconjunto de `ArquivosCentralFiltros` que os filtros avançados produzem (valores em CSV). */
export type ParametrosFiltrosArquivos = Partial<{
  clienteId: string;
  clienteIdExcluir: string;
  projetoId: string;
  projetoIdExcluir: string;
  demandaId: string;
  demandaIdExcluir: string;
  tipo: string;
  tipoExcluir: string;
  status: string;
  statusExcluir: string;
  usuarioId: string;
  usuarioIdExcluir: string;
  dataInicio: string;
  dataFim: string;
}>;

const PARAMETRO_POR_CAMPO: Record<string, "clienteId" | "projetoId" | "demandaId" | "tipo" | "status" | "usuarioId"> = {
  [CAMPO_ARQUIVOS.cliente]: "clienteId",
  [CAMPO_ARQUIVOS.projeto]: "projetoId",
  [CAMPO_ARQUIVOS.demanda]: "demandaId",
  [CAMPO_ARQUIVOS.tipo]: "tipo",
  [CAMPO_ARQUIVOS.status]: "status",
  [CAMPO_ARQUIVOS.enviadoPor]: "usuarioId",
};

export function filtrosArquivosParaApi(filtros: readonly FiltroAtivo[], agora: Date = new Date()): ParametrosFiltrosArquivos {
  const parametros: ParametrosFiltrosArquivos = {};
  for (const filtro of filtros) {
    if (filtro.valores.length === 0) continue;
    if (filtro.campo === CAMPO_ARQUIVOS.dataEnvio) {
      const intervalo = intervaloDaData(filtro.operador, filtro.valores[0], agora);
      if (intervalo?.inicio) parametros.dataInicio = intervalo.inicio.toISOString();
      if (intervalo?.fim) parametros.dataFim = intervalo.fim.toISOString();
      continue;
    }
    const base = PARAMETRO_POR_CAMPO[filtro.campo];
    if (!base) continue;
    const chave = ehNegativo(filtro.operador) ? (`${base}Excluir` as const) : base;
    parametros[chave] = filtro.valores.join(",");
  }
  return parametros;
}
