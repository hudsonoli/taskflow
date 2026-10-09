// Filtros avançados de MEU DEPARTAMENTO → parâmetros de `GET /demandas?escopo=meu-departamento`. Lógica PURA (testável com `node --test`).
//
// O departamento NÃO é um filtro: é o escopo da tela (o departamento atual do usuário, derivado no servidor). Estes filtros só
// REFINAM as demandas desse departamento. Entre campos: AND; dentro do campo: OR ("é um de"); "não é" mantém o registro cujo
// campo é vazio (cliente/projeto sem valor, demanda sem responsável) — a mesma regra de Arquivos e Tráfego.
import { ehNegativo, intervaloDaData } from "./filtros-avancados.ts";
import type { FiltroAtivo } from "../types/filtros.ts";

export const CAMPO_MEU_DEPARTAMENTO = {
  responsavel: "responsavel",
  equipe: "equipe",
  cliente: "cliente",
  projeto: "projeto",
  status: "status",
  prioridade: "prioridade",
  prazo: "prazo",
  origem: "origem",
} as const;

/** Parâmetros que os filtros avançados produzem (valores em CSV). */
export type ParametrosFiltrosMeuDepartamento = Partial<{
  responsavelId: string;
  responsavelIdExcluir: string;
  equipeId: string;
  equipeIdExcluir: string;
  clienteId: string;
  clienteIdExcluir: string;
  projetoId: string;
  projetoIdExcluir: string;
  status: string;
  statusExcluir: string;
  prioridade: string;
  prioridadeExcluir: string;
  origem: "interna" | "cliente";
  prazoInicio: string;
  prazoFim: string;
  atrasada: boolean;
}>;

const PARAMETRO_POR_CAMPO = {
  [CAMPO_MEU_DEPARTAMENTO.responsavel]: "responsavelId",
  [CAMPO_MEU_DEPARTAMENTO.equipe]: "equipeId",
  [CAMPO_MEU_DEPARTAMENTO.cliente]: "clienteId",
  [CAMPO_MEU_DEPARTAMENTO.projeto]: "projetoId",
  [CAMPO_MEU_DEPARTAMENTO.status]: "status",
  [CAMPO_MEU_DEPARTAMENTO.prioridade]: "prioridade",
} as const;

type CampoLista = keyof typeof PARAMETRO_POR_CAMPO;

export function filtrosMeuDepartamentoParaApi(filtros: readonly FiltroAtivo[], agora: Date = new Date()): ParametrosFiltrosMeuDepartamento {
  const parametros: ParametrosFiltrosMeuDepartamento = {};
  for (const filtro of filtros) {
    if (filtro.valores.length === 0) continue;
    const campo = filtro.campo;
    if (campo in PARAMETRO_POR_CAMPO) {
      const base = PARAMETRO_POR_CAMPO[campo as CampoLista];
      const chave = ehNegativo(filtro.operador) ? (`${base}Excluir` as const) : base;
      parametros[chave] = filtro.valores.join(",");
    } else if (campo === CAMPO_MEU_DEPARTAMENTO.origem) {
      const valor = filtro.valores[0];
      if (valor === "interna" || valor === "cliente") parametros.origem = valor;
    } else if (campo === CAMPO_MEU_DEPARTAMENTO.prazo) {
      // "Atrasado" mantém o significado que a tela já tinha: prazo vencido E ainda não finalizada (`atrasada=true`),
      // não só "data anterior a agora".
      if (filtro.operador === "is" && filtro.valores[0] === "atrasado") {
        parametros.atrasada = true;
        continue;
      }
      const intervalo = intervaloDaData(filtro.operador, filtro.valores[0], agora);
      if (intervalo?.inicio) parametros.prazoInicio = intervalo.inicio.toISOString();
      if (intervalo?.fim) parametros.prazoFim = intervalo.fim.toISOString();
    }
  }
  return parametros;
}
