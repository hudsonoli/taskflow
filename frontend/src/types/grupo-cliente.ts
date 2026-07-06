export type GrupoClienteStatus = "Ativo" | "Inativo";

export type HistoricoGrupoCliente = {
  id: string;
  usuarioId: string;
  usuario: string;
  dataHora: string;
  dispositivo: string;
  ipOrigem: string;
  acao: string;
};

export type GrupoClienteDraft = {
  grupoClienteId: string;
  empresaId: string;
  codigoInterno: string;
  nome: string;
  sigla: string;
  clientesIds: string[];
  status: GrupoClienteStatus;
  historico: HistoricoGrupoCliente[];
  createdAt: string;
  updatedAt: string;
};
