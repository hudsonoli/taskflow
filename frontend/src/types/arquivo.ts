import type { DemandaArquivoStatusLayout, DemandaArquivoTipo } from "@/types/demanda";

/**
 * `GET /arquivos` — item da listagem central (Gerenciador de Arquivos, Fase 2H.1).
 * Autossuficiente de propósito: cliente/projeto/demanda/usuário já vêm resolvidos nesta
 * mesma resposta (ver `ArquivoCentralRead` no backend) — nunca depende de
 * `AppDataContext`/diretório global pra renderizar o card (D2-D3C/D2-D4 ensinaram que um
 * diretório capado some de baixo de uma lista que não sabia que dependia dele).
 */
export type ArquivoCentral = {
  id: string;
  demandaId: string;
  nome: string;
  mimeType: string | null;
  tamanhoBytes: number | null;
  tipo: DemandaArquivoTipo;
  statusLayout: DemandaArquivoStatusLayout | null;
  url: string | null;
  descricao: string | null;
  createdAt: string;
  enviadoPorUsuarioId: string | null;
  usuarioNome: string | null;
  demanda: {
    id: string;
    numeroOperacional: number;
    codigoReferencia: string;
    nome: string;
  };
  projetoId: string | null;
  projetoNome: string | null;
  clienteId: string | null;
  clienteNome: string | null;
  previewDisponivel: boolean;
};

export type ArquivosCentralFiltros = {
  search?: string;
  clienteId?: string;
  projetoId?: string;
  demandaId?: string;
  tipo?: DemandaArquivoTipo;
  status?: DemandaArquivoStatusLayout;
  usuarioId?: string;
  dataInicio?: string;
  dataFim?: string;
  limit?: number;
  offset?: number;
};
