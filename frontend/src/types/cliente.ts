export type DocumentoTipo = "cnpj" | "cpf";

export type ClienteStatus = "Ativo" | "Inativo";

export type ClienteContato = {
  id: string;
  nome: string;
  email: string;
  telefone: string;
  celular: string;
  cargo: string;
  aniversario: string;
  acessoPortal: boolean;
};

export type ClienteEndereco = {
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

export type HistoricoCliente = {
  id: string;
  usuarioId: string;
  usuario: string;
  dataHora: string;
  dispositivo: string;
  ipOrigem: string;
  acao: string;
};

export type ClienteDraft = {
  clienteId: string;
  empresaId: string;
  codigoInterno: string;
  tipoDocumento: DocumentoTipo;
  documento: string;
  nomeRazaoSocial: string;
  nomeFantasia: string;
  sigla: string;
  email: string;
  telefone: string;
  celular: string;
  site: string;
  status: ClienteStatus;
  equipeResponsavelId?: string;
  responsavelComercialId?: string;
  responsavelAtendimentoId?: string;
  endereco: ClienteEndereco;
  contatos: ClienteContato[];
  historico: HistoricoCliente[];
};
