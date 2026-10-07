// Central de Notificações — mesmo shape da API (camelCase via alias Pydantic).
// Notificação = visão tipada dos eventos de domínio das demandas do usuário + o estado "lida" DELE.
export type CategoriaNotificacao = "sistema" | "minhas";
export type GrupoPrazo = "atrasadas" | "hoje" | "proximas";

export type Notificacao = {
  /** id do evento */
  id: string;
  categoria: CategoriaNotificacao;
  tipo: string;
  titulo: string;
  detalhe: string | null;
  ocorridaEm: string;
  lida: boolean;
  demandaId: string | null;
  demandaReferencia: string | null;
  demandaNome: string | null;
  autorNome: string | null;
};

export type NotificacoesPagina = { itens: Notificacao[]; total: number; limit: number; offset: number };

export type NotificacoesResumo = {
  naoLidas: { sistema: number; minhas: number; total: number };
  prazos: { atrasadas: number; hoje: number; proximas: number };
};

export const RESUMO_VAZIO: NotificacoesResumo = {
  naoLidas: { sistema: 0, minhas: 0, total: 0 },
  prazos: { atrasadas: 0, hoje: 0, proximas: 0 },
};
