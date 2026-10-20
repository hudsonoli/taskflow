// Tráfego V2 — 11B.2B-C: contrato da CARGA semanal (`GET /trafego/operacional/carga`). Espelha o OpenAPI publicado (backend/app/schemas/trafego_carga.py) e docs/carga-semanal.md.
//
// Capacidade vem do expediente da empresa; carga vem da estimativa + janela planejada da ETAPA. Nada aqui é tempo pessoal (sessões) nem tempo operacional (intervalos de estado):
// não há "horas trabalhadas", ranking nem produtividade. Todos os valores de tempo são MINUTOS inteiros.

export type RefCarga = { id: string; nome: string };

export type DiaSemanaCarga = {
  /** Data do calendário da empresa (`YYYY-MM-DD`). */
  data: string;
  minutosNominais: number | null;
  /** Na semana atual só conta de hoje em diante. */
  considerado: boolean;
};

export type SemanaCarga = {
  /** Segunda-feira, no fuso da EMPRESA (`YYYY-MM-DD`). */
  inicio: string;
  /** Domingo (`YYYY-MM-DD`). */
  fim: string;
  /** `true` = semana atual: capacidade e carga contam de hoje até domingo. */
  recorteHoje: boolean;
  dias: DiaSemanaCarga[];
};

export type MetaCarga = { agoraServidor: string; fusoEmpresa: string };

export type MotivoCapacidadeIndisponivel = "expediente_desligado";

export type CapacidadeCarga = {
  /** Preenchido = não existe calendário confiável: minutos que dependem dele vêm `null` (nunca zero). */
  capacidadeIndisponivel: MotivoCapacidadeIndisponivel | string | null;
  fatorAlocavelPercentual: number;
};

export type EstadoJanelaCarga = "nao_planejado" | "incompleto" | "planejado";

export type JanelaCarga = {
  planejadoInicio: string | null;
  planejadoFim: string | null;
  estado: EstadoJanelaCarga | string;
};

export type AlocacaoEstadoCarga = "alocada" | "janela_vencida" | "sem_dia_util";
export type MotivoNaoPlanejadoCarga = "sem_janela" | "janela_incompleta";
export type OrigemCarga = "responsavel" | "pool_departamento" | "pool_sem_departamento";

/** Uma etapa que compõe um número (drill-down e pendências). Sem dados financeiros. */
export type ItemEtapaCarga = {
  demandaId: string;
  identificador: string;
  titulo: string;
  statusDemanda: string;
  cliente: RefCarga | null;
  projeto: RefCarga | null;
  etapaId: string;
  etapaNome: string;
  etapaTipo: string;
  estimativaMin: number | null;
  restanteMin: number | null;
  /** Valor da ETAPA inteira na semana (antes de dividir entre responsáveis). */
  planejadoNaSemanaMin: number | null;
  /** PARTE do alvo consultado (pessoa/departamento). */
  parteMin: number | null;
  janela: JanelaCarga;
  alocacaoEstado: AlocacaoEstadoCarga | string | null;
  motivoNaoPlanejado: MotivoNaoPlanejadoCarga | string | null;
  origem: OrigemCarga | string;
  divididoEntre: number;
};

export type PessoaCarga = {
  usuarioId: string;
  nome: string;
  departamentoId: string | null;
  capacidadeNominalMin: number | null;
  capacidadeAlocavelMin: number | null;
  planejadoMin: number | null;
  saldoMin: number | null;
  /** Pode passar de 100 (sobrecarga). `null` = sem denominador confiável. */
  ocupacaoPercentual: number | null;
  naoPlanejadoMin: number;
  pendenciasPlanejamentoMin: number;
  semEstimativaCount: number;
};

export type DepartamentoCarga = {
  departamentoId: string;
  nome: string;
  pessoasCount: number;
  capacidadeNominalMin: number | null;
  capacidadeAlocavelMin: number | null;
  /** Já INCLUI o pool (carga de etapas sem usuário atribuídas ao departamento). */
  planejadoMin: number | null;
  /** SUBCONJUNTO de `planejadoMin`: nunca somar de novo. */
  planejadoPoolMin: number | null;
  saldoMin: number | null;
  ocupacaoPercentual: number | null;
  naoPlanejadoMin: number;
  pendenciasPlanejamentoMin: number;
  semEstimativaCount: number;
};

export type PoolSemDepartamentoCarga = {
  etapasCount: number;
  planejadoMin: number | null;
  naoPlanejadoMin: number;
  pendenciasPlanejamentoMin: number;
  semEstimativaCount: number;
};

export type BucketCarga = { etapasCount: number; minutosConhecidos: number; semEstimativaCount: number };

export type NaoPlanejadoCarga = { semJanela: BucketCarga; janelaIncompleta: BucketCarga };

export type PendenciaCarga = BucketCarga & { itens: ItemEtapaCarga[]; truncado: boolean };

export type PendenciasPlanejamentoCarga = { janelaVencida: PendenciaCarga; semDiaUtil: PendenciaCarga };

export type TipoDetalheCarga = "usuario" | "departamento";

export type DetalheCarga = { tipo: TipoDetalheCarga | string; id: string; etapas: ItemEtapaCarga[]; etapasTotal: number; truncado: boolean };

export type CargaSemanal = {
  meta: MetaCarga;
  semana: SemanaCarga;
  capacidade: CapacidadeCarga;
  pessoas: PessoaCarga[];
  departamentos: DepartamentoCarga[];
  /** Só na visão sem filtro. */
  poolSemDepartamento: PoolSemDepartamentoCarga | null;
  naoPlanejado: NaoPlanejadoCarga;
  pendenciasPlanejamento: PendenciasPlanejamentoCarga;
  detalhe: DetalheCarga | null;
};

/** Parâmetros da consulta. A consulta PRINCIPAL nunca leva `detalhe`; o drill-down é uma consulta à parte, só ao abrir. */
export type ParametrosCarga = {
  /** Qualquer dia da semana desejada (`YYYY-MM-DD`); `null` = semana atual (o servidor normaliza para a segunda no fuso da empresa). */
  semana: string | null;
  departamentoId: string | null;
  usuarioId: string | null;
  detalhe: TipoDetalheCarga | null;
  limite: number | null;
};

export type FiltrosCarga = { departamentoId: string | null; usuarioId: string | null };
