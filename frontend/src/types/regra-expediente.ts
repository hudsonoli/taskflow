export type DiaSemana = 0 | 1 | 2 | 3 | 4 | 5 | 6; // 0 = segunda .. 6 = domingo (Fase 2G.3)

/** Um período de trabalho do dia. A API devolve "HH:MM:SS"; a tela e o envio usam "HH:MM" (ver `lib/expediente-periodos.ts`). Fim exclusivo; não atravessa a meia-noite. */
export type PeriodoExpediente = {
  inicio: string;
  fim: string;
};

/** Um dia da semana: 0 períodos = FECHADO; 1 ou mais = dia útil (Fase Expediente 1). */
export type JanelaDia = {
  diaSemana: DiaSemana;
  /** derivado: há pelo menos um período */
  ativo: boolean;
  periodos: PeriodoExpediente[];
  // LEGADO (espelho informativo do backend; a fonte é `periodos`)
  manhaInicio?: string | null;
  manhaFim?: string | null;
  tardeInicio?: string | null;
  tardeFim?: string | null;
};

export type TipoDiaEspecial = "feriado" | "recesso" | "trabalho_excepcional" | "ignorado";
export type OrigemDiaEspecial = "automatico" | "manual";

/** Dia especial do calendário: vence a regra semanal (feriado/recesso fecham; trabalho excepcional usa períodos próprios; "ignorado" neutraliza a data). */
export type DiaEspecial = {
  id: string;
  data: string; // YYYY-MM-DD
  nome: string;
  origem: OrigemDiaEspecial;
  tipo: TipoDiaEspecial;
  ativo: boolean;
  periodos: PeriodoExpediente[];
  createdAt: string;
  updatedAt: string;
};

export type DiaEspecialDraft = {
  data: string;
  nome: string;
  tipo: TipoDiaEspecial;
  ativo: boolean;
  periodos: PeriodoExpediente[];
};

export type RegraExpediente = {
  id: string;
  empresaId: string;
  /** Chave-mestra do controle de expediente (hoje: o gate de ENTRADA em execução). */
  ativo: boolean;
  /** LEGADO: minutos antes do início do 2º período em que a ENTRADA em execução já é aceita. NÃO é a antecedência de acesso. */
  toleranciaRetomadaMinutos: number;
  // Fase Expediente 1 — as duas primeiras existem mas AINDA não têm efeito (nascem falsas; a API recusa ligá-las até a próxima etapa).
  bloquearForaExpediente: boolean;
  pausarNoFimPeriodo: boolean;
  antecedenciaAcessoMinutos: number;
  /** IANA, ex.: America/Sao_Paulo */
  timezone: string;
  feriadosAutomaticos: boolean;
  dias: JanelaDia[];
  diasEspeciais: DiaEspecial[];
  createdAt: string;
  updatedAt: string;
};

export type DiaSemanaWrite = { diaSemana: DiaSemana; periodos: PeriodoExpediente[] };

// Full-replace: quando `dias` é enviado, precisa cobrir os 7 dias — mesma regra do backend
// (RegraExpedienteUpdate.validar_dias_completos).
export type RegraExpedienteUpdateDraft = {
  ativo?: boolean;
  toleranciaRetomadaMinutos?: number;
  antecedenciaAcessoMinutos?: number;
  timezone?: string;
  dias?: DiaSemanaWrite[];
};

// GET /expediente/estado — leitura operacional enxuta (Kanban, capacidade de Meu
// Departamento). Nunca as janelas por dia, só agregados: ver EstadoExpedienteRead no backend.
export type EstadoExpediente = {
  ativo: boolean;
  dentroExpediente: boolean;
  agora: string;
  toleranciaRetomadaMinutos: number;
  horasUteisHoje: number;
};
