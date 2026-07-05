export type PermissaoItem = {
  id: string;
  grupo: string;
  modulo: string;
  leitura: boolean;
  escrita: boolean;
  excluir: boolean;
  aprovar: boolean;
  extras?: Record<string, boolean>;
};

export type UsuarioEndereco = {
  id: string;
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  caixaPostal: string;
  pais: string;
  uf: string;
  cidade: string;
  tipo: string;
};

export type UsuarioInformacoes = {
  avatarUrl?: string;
  telefone: string;
  celular: string;
  dataNascimento: string;
  chavePix: string;
  banco: string;
  agencia: string;
  conta: string;
  rg: string;
  cpf: string;
};

export type HistoricoUsuario = {
  id: string;
  usuarioId: string;
  usuario: string;
  dataHora: string;
  dispositivo: string;
  ipOrigem: string;
  acao: string;
};

export type DepartamentoOption = {
  id: string;
  nome: string;
  ativo: boolean;
};

export type UsuarioDraft = {
  id: string;
  codigoInterno: string;
  empresaId: string;
  clienteId?: string;
  nome: string;
  email: string;
  departamentoId: string;
  squad: string;
  paginaPrincipal: string;
  perfil: string;
  acessoSistema: boolean;
  emAtividade: boolean;
  permissoes: PermissaoItem[];
  enderecos: UsuarioEndereco[];
  informacoes: UsuarioInformacoes;
  historico: HistoricoUsuario[];
};
