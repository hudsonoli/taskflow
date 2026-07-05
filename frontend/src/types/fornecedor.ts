export type FornecedorDocumentoTipo = "cpf" | "cnpj";

export type FornecedorStatus = "Ativo" | "Inativo";

export type FornecedorCategoria =
  | "Gráfica"
  | "Brindes"
  | "Comunicação Visual"
  | "Fotografia"
  | "Vídeo"
  | "Freelancer"
  | "Programação"
  | "Hospedagem"
  | "Impressão"
  | "Transporte"
  | "Outros";

export type FornecedorEndereco = {
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  uf: string;
  pais: string;
  tipo: string;
};

export type FornecedorContato = {
  contatoId: string;
  nome: string;
  cargo: string;
  email: string;
  telefone: string;
  celular: string;
};

export type HistoricoFornecedor = {
  id: string;
  usuarioId: string;
  usuario: string;
  dataHora: string;
  dispositivo: string;
  ipOrigem: string;
  acao: string;
};

export type FornecedorDraft = {
  fornecedorId: string;
  empresaId: string;
  codigoInterno: string;
  tipoDocumento: FornecedorDocumentoTipo;
  documento: string;
  nomeRazaoSocial: string;
  nomeFantasia: string;
  sigla: string;
  categoria: FornecedorCategoria;
  email: string;
  telefone: string;
  celular: string;
  site: string;
  status: FornecedorStatus;
  endereco: FornecedorEndereco;
  contatos: FornecedorContato[];
  historico: HistoricoFornecedor[];
  createdAt: string;
  updatedAt: string;
};
