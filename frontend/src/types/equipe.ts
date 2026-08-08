export type EquipeStatus = "ativo" | "inativo" | "arquivado";

export type Equipe = {
  /** UUID técnico — relações e rotas. Nunca exibido. */
  id: string;
  empresaId: string;
  /** Ponte transitória para mocks ainda não migrados (`equipe-1`). */
  codigoInterno: string;
  /** Código oficial (E26000001) — pesquisável e imutável. Não exibido para Equipe. */
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  descricao: string;
  /** null = equipe transversal (sem departamento) — caso legítimo. */
  departamentoId: string | null;
  liderId: string;
  membroIds: string[];
  corIdentificacao: string;
  status: EquipeStatus;
  createdAt: string;
  updatedAt: string;
};

export type EquipeFormDraft = {
  nome: string;
  descricao: string;
  departamentoId: string | null;
  liderId: string;
  membroIds: string[];
  corIdentificacao: string;
  status: Exclude<EquipeStatus, "arquivado">;
};
