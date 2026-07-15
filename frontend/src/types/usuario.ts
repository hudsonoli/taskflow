import type { PerfilAcesso } from "@/lib/access-control";

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

// Dados pessoais — chavePix/banco/agencia/conta saíram daqui (Opção A):
// dados bancários passaram a existir só dentro de UsuarioAdministrativo,
// protegidos por hasAdministrativeAccess. Esta seção nunca teve gate e não
// deve voltar a acumular dado sensível.
export type UsuarioInformacoes = {
  avatarUrl?: string;
  telefone: string;
  celular: string;
  dataNascimento: string;
  rg: string;
  cpf: string;
};

// Origem demonstrativa do evento — sem detecção automática, mesmo padrão de
// OrigemHistorico em types/cliente.ts. Dado mock até existir captura real
// no backend.
export type OrigemHistoricoUsuario = "Web" | "API" | "Importação" | "Integração";

export type HistoricoUsuario = {
  id: string;
  usuarioId: string;
  usuario: string;
  dataHora: string;
  dispositivo: string;
  ipOrigem: string;
  acao: string;
  origem: OrigemHistoricoUsuario;
};

/**
 * Dados sensíveis — devem aparecer apenas na guia Administrativa do modo
 * Edit do EntityDrawer, restrita por hasAdministrativeAccess
 * (lib/access-control.ts). Não expor em tabela, Peek, resultados de busca
 * ou logs de console. Ocultar no frontend não substitui autorização real: o
 * backend deverá aplicar a mesma checagem ao servir/gravar estes campos.
 *
 * salario representa despesa/custo (o que a empresa paga ao colaborador).
 * Nunca confundir com Fee Mensal de Clientes, que representa receita — não
 * coexistem no mesmo campo/entidade, nunca são somados ou comparados
 * diretamente. valor é numérico — nunca uma string já formatada com moeda.
 */
export type UsuarioSalario = {
  valor: number | null;
  moeda: "BRL";
  dataInicio: string;
  observacao: string;
};

export type UsuarioDadosBancarios = {
  chavePix: string;
  banco: string;
  agencia: string;
  conta: string;
  tipoConta: "Corrente" | "Poupança" | "Pagamento";
};

export type UsuarioAdministrativo = {
  salario: UsuarioSalario;
  dadosBancarios: UsuarioDadosBancarios;
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
  // Cargo/perfil do usuário cadastrado — conceito distinto do gate da guia
  // Administrativa (que usa currentUser.perfil, o usuário logado agora).
  // Os dois passaram a compartilhar a mesma união de valores (PerfilAcesso,
  // lista oficial do projeto) para não divergir de novo, mas continuam
  // sendo lidos em pontos diferentes e com propósitos diferentes.
  perfil: PerfilAcesso;
  acessoSistema: boolean;
  emAtividade: boolean;
  permissoes: PermissaoItem[];
  enderecos: UsuarioEndereco[];
  informacoes: UsuarioInformacoes;
  administrativo: UsuarioAdministrativo;
  historico: HistoricoUsuario[];
};
