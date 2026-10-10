// Portal Externo de Aprovação (Fase 9B) — tipos dos dois lados.
//
// INTERNO (usuário autenticado, via BFF `/api/backend`): gerenciar o link da etapa de aprovação atual.
// PÚBLICO (portador do token, via BFF dedicado `/api/aprovacao/*`): o mínimo para o cliente decidir. Nenhum id interno, e-mail interno, comentário ou
// outro arquivo da tarefa existe nestes tipos.

export type EstadoAprovacaoExterna = "pendente" | "aprovada" | "ajustes_solicitados" | "revogada" | "expirada" | "obsoleta";

export type AprovacaoExternaArtefato = {
  ordem: number;
  nome: string;
  contentType: string;
  tamanhoBytes: number;
  /** `null` quando o arquivo original foi excluído (só permitido em solicitação revogada sem decisão); o snapshot continua. */
  arquivoId: string | null;
};

export type AprovacaoExternaDecisao = {
  decisao: "aprovada" | "ajustes_solicitados";
  decididaEm: string;
  /** Nome DECLARADO pelo cliente (não verificado). */
  nomeAprovador: string;
  emailAprovador: string | null;
  motivo: string | null;
};

export type AprovacaoExterna = {
  id: string;
  etapaId: string;
  estado: EstadoAprovacaoExterna;
  instrucao: string | null;
  criadaEm: string;
  criadaPorNome: string | null;
  expiraEm: string;
  revogadaEm: string | null;
  revogadaMotivo: string | null;
  destinatarioNome: string | null;
  destinatarioEmail: string | null;
  artefatos: AprovacaoExternaArtefato[];
  decisao: AprovacaoExternaDecisao | null;
};

/** Resposta ÚNICA da criação: carrega o token em claro (nunca mais recuperável — o servidor guarda só o hash). */
export type AprovacaoExternaCriada = AprovacaoExterna & { token: string };

export type ContatoClienteAprovacao = {
  nome: string;
  email: string | null;
  cargo: string | null;
  recebeEntregas: boolean;
};

export type AprovacaoExternaPainel = {
  podeGerenciar: boolean;
  atual: AprovacaoExterna | null;
  contatos: ContatoClienteAprovacao[];
  validadePadraoDias: number;
  validadeMaxDias: number;
};

export type AprovacaoExternaNovaEntrada = {
  arquivoIds: string[];
  instrucao?: string | null;
  validadeDias: number;
  destinatarioNome?: string | null;
  destinatarioEmail?: string | null;
};

// ── público ──────────────────────────────────────────────────────────────────────────────────

export type EstadoPublicoAprovacao = "pendente" | "aprovada" | "ajustes_solicitados";
export type DecisaoPublica = "aprovar" | "solicitar_ajustes";

export type ArtefatoPublicoAprovacao = {
  ordem: number;
  nome: string;
  tipo: "imagem" | "pdf";
  contentType: string;
  tamanhoBytes: number;
};

export type AprovacaoPublica = {
  /** Branding público da empresa DONA do link (cores/tema/logo/nome). Sem id, sem documento, sem e-mail. */
  empresa: Record<string, unknown>;
  demandaIdentificador: string;
  demandaNome: string;
  instrucao: string | null;
  estado: EstadoPublicoAprovacao;
  expiraEm: string;
  destinatarioNome: string | null;
  /** Falso quando a etapa é a primeira do workflow: não há para onde devolver. */
  podeSolicitarAjustes: boolean;
  artefatos: ArtefatoPublicoAprovacao[];
  decisao: { decisao: "aprovada" | "ajustes_solicitados"; decididaEm: string } | null;
};

export type DecisaoPublicaEntrada = {
  decisao: DecisaoPublica;
  nome: string;
  email?: string | null;
  motivo?: string | null;
};
