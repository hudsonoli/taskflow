// Filtros avançados da PAUTA operacional por etapa → parâmetros de `GET /pauta/operacional`. Lógica PURA (testável com `node --test`).
//
// Só o que ajuda a responder "quem tem o quê, quando": colaborador, departamento, cliente, projeto e prioridade. Colaborador e departamento se aplicam à
// RESPONSABILIDADE EFETIVA da etapa (não ao responsável geral bruto da Demanda nem ao departamento cadastral do usuário). O servidor só executa "é"/"é um de" (OR entre valores).
import type { FiltroAtivo } from "../types/filtros.ts";
import type { ParametrosPautaOperacional } from "../types/pauta-operacional.ts";

export const CAMPO_PAUTA = {
  departamento: "departamento",
  responsavel: "responsavel",
  cliente: "cliente",
  projeto: "projeto",
  prioridade: "prioridade",
} as const;

export type ParametrosFiltrosPauta = Pick<ParametrosPautaOperacional, "usuarioIds" | "departamentoIds" | "clienteIds" | "projetoIds" | "prioridades">;

const CAMPO_PARA_PARAMETRO: Record<string, keyof ParametrosFiltrosPauta> = {
  [CAMPO_PAUTA.responsavel]: "usuarioIds",
  [CAMPO_PAUTA.departamento]: "departamentoIds",
  [CAMPO_PAUTA.cliente]: "clienteIds",
  [CAMPO_PAUTA.projeto]: "projetoIds",
  [CAMPO_PAUTA.prioridade]: "prioridades",
};

export function filtrosPautaParaApi(filtros: readonly FiltroAtivo[]): ParametrosFiltrosPauta {
  const parametros: ParametrosFiltrosPauta = {};
  for (const filtro of filtros) {
    const parametro = CAMPO_PARA_PARAMETRO[filtro.campo];
    // "não é" não existe na Pauta (o servidor não o executa); filtro sem valor não vira parâmetro
    if (!parametro || filtro.valores.length === 0 || (filtro.operador !== "is" && filtro.operador !== "in")) continue;
    parametros[parametro] = [...filtro.valores];
  }
  return parametros;
}
