// 11B.2D-B — contratos da CAPACIDADE INDIVIDUAL de um Usuário (jornada própria + ausências). Espelham o OpenAPI publicado (backend/app/schemas/usuario_capacidade.py).
// Planejamento de capacidade, não folha: nada aqui é horas trabalhadas, banco de horas nem saldo de férias. Datas de ausência são DATE do calendário da empresa (`YYYY-MM-DD`).
import type { DiaSemana, PeriodoExpediente } from "./regra-expediente.ts";

export type TipoAusencia = "ferias" | "afastamento" | "folga" | "outro";

/** Um dia da jornada: 0 períodos = fechado. A API devolve "HH:MM:SS"; a tela normaliza para "HH:MM" (`lib/expediente-periodos`). */
export type JornadaDiaUsuario = { diaSemana: DiaSemana; periodos: PeriodoExpediente[] };

/** `personalizada=false`: a pessoa usa o expediente da EMPRESA e `dias` é só a semana da empresa (consulta do fallback — nada foi copiado). */
export type JornadaUsuario = {
  usuarioId: string;
  personalizada: boolean;
  dias: JornadaDiaUsuario[];
  updatedAt: string | null;
};

export type AusenciaUsuario = {
  id: string;
  usuarioId: string;
  tipo: TipoAusencia | string;
  inicio: string;
  fim: string;
  observacao: string | null;
  createdAt: string;
  updatedAt: string;
};

/** O que o formulário edita. `observacao` vazia vira "sem observação" no envio. */
export type AusenciaDraft = { tipo: TipoAusencia; inicio: string; fim: string; observacao: string };

/** Corpo do PATCH: só o que mudou (`observacao: null` limpa). */
export type AusenciaPatch = Partial<{ tipo: TipoAusencia; inicio: string; fim: string; observacao: string | null }>;
