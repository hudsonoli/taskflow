export type DepartamentoStatus = "ativo" | "inativo" | "arquivado";

export type Departamento = {
  /** UUID técnico — usado em relações e rotas. Nunca exibido na interface. */
  id: string;
  empresaId: string;
  /** Ponte transitória para os mocks de Projeto/Demanda (`dep-criacao`). Sai quando eles migrarem. */
  codigoInterno: string;
  /** Código oficial de negócio (D26000001) — pesquisável e imutável. Não exibido para Departamento. */
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  descricao: string;
  responsavelId: string;
  status: DepartamentoStatus;
  corIdentificacao: string;
  createdAt: string;
  updatedAt: string;
};

/** Campos que o formulário edita — os códigos e a empresa são responsabilidade do backend. */
export type DepartamentoFormDraft = {
  nome: string;
  descricao: string;
  responsavelId: string;
  corIdentificacao: string;
  status: Exclude<DepartamentoStatus, "arquivado">;
};
