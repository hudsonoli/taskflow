export type DocumentoTipo = "cnpj" | "cpf";

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

export type ClienteComplementares = {
  banco: string;
  agencia: string;
  conta: string;
  chavePix: string;
  observacao: string;
  setor: string;
  produtosServicos: string;
  retencoesFiscais: string[];
};

export type ClienteDraft = {
  codigoInterno: string;
  documentoTipo: DocumentoTipo;
  documento: string;
  nomeFantasia: string;
  razaoSocial: string;
  email: string;
  telefone: string;
  celular: string;
  site: string;
  grupoCliente: string;
  atendimento: string;
  auxiliar: string;
  sigla: string;
  situacao: string;
  endereco: ClienteEndereco;
  complementares: ClienteComplementares;
  contatos: ClienteContato[];
};
