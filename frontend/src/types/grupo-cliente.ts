export type GrupoClienteStatus = "ativo" | "arquivado";

export type GrupoCliente = {
  id: string;
  empresaId: string;
  codigoInterno: string;
  nome: string;
  corIdentificacao: string;
  status: GrupoClienteStatus;
  createdAt: string;
  updatedAt: string;
};
