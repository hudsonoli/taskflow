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
  /** Chave-mestra do controle de expediente (gate de acesso, de TRABALHO e logout automático — cada um com sua flag). */
  ativo: boolean;
  /** LEGADO/deprecated (Fase 2): NÃO é mais autoridade de nada — o trabalho usa a janela NOMINAL. Mantido só por compatibilidade. NÃO é a antecedência de acesso. */
  toleranciaRetomadaMinutos: number;
  /** Fase 2: TEM efeito — operadores sujeitos só usam o sistema dentro da janela de ACESSO (403 FORA_DO_EXPEDIENTE). */
  bloquearForaExpediente: boolean;
  /** Fase 3: TEM efeito — ao fim de cada período o servidor pausa as tarefas em execução (sem logout, sem retomar). */
  pausarNoFimPeriodo: boolean;
  /** Instante em que a pausa foi "armada" (informativo; quem decide é o servidor). */
  pausaAutomaticaAtivadaEm?: string | null;
  antecedenciaAcessoMinutos: number;
  /** IANA, ex.: America/Sao_Paulo */
  timezone: string;
  feriadosAutomaticos: boolean;
  /** Fase 2: logout automático com horário PRÓPRIO, independente de bloqueio e pausa. */
  logoutAutomaticoAtivo: boolean;
  /** "HH:MM:SS" da API; a tela usa "HH:MM". `null` = sem horário. */
  logoutHorario: string | null;
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
  bloquearForaExpediente?: boolean;
  pausarNoFimPeriodo?: boolean;
  logoutAutomaticoAtivo?: boolean;
  /** "HH:MM"; `null` limpa (só aceito com o logout desligado). */
  logoutHorario?: string | null;
  dias?: DiaSemanaWrite[];
};

// GET /expediente/estado — leitura operacional enxuta (Kanban, capacidade de Meu
// Departamento). Nunca as janelas por dia, só agregados: ver EstadoExpedienteRead no backend.
export type EstadoExpediente = {
  ativo: boolean;
  /** Da EMPRESA: dentro da janela de trabalho NOMINAL agora (sem isenção, sem tolerância legada). */
  dentroExpediente: boolean;
  agora: string;
  toleranciaRetomadaMinutos: number;
  horasUteisHoje: number;
  // Fase 2 — o que vale para ESTA pessoa, decidido pelo servidor (fuso da empresa; nunca o relógio do navegador).
  sujeitoAoExpediente: boolean;
  bloqueioAtivo: boolean;
  acessoPermitido: boolean;
  trabalhoPermitido: boolean;
  proximoAcesso: string | null;
  proximoTrabalho: string | null;
  proximoTrabalhoFim: string | null;
  timezone: string | null;
  /** Fase 3: a última pausa automática que atingiu ESTA pessoa; `null` = nunca. Fonte do aviso "Tarefas pausadas automaticamente.". */
  ultimaPausaAutomatica?: UltimaPausaAutomatica | null;
};

export type UltimaPausaAutomatica = {
  eventoId: string;
  /** instante do corte (ex.: 12:00) */
  em: string;
  quantidade: number;
};

/** Corpo do `403 FORA_DO_EXPEDIENTE` (sessão válida; a política recusa o uso agora). */
export type DetalheForaDoExpediente = {
  code: "FORA_DO_EXPEDIENTE";
  message: string;
  proximoAcesso: string | null;
  proximoTrabalho: string | null;
  proximoTrabalhoFim: string | null;
  timezone: string | null;
};
