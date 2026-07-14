export type DocumentoTipo = "cnpj" | "cpf";

export type ClienteStatus = "Ativo" | "Suspenso" | "Inativo";

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

// Origem demonstrativa do evento — sem detecção automática (ver
// entity-component-api.md, seção "Guia Administrativa"). Dado mock até
// existir captura real no backend.
export type OrigemHistorico = "Web" | "API" | "Importação" | "Integração";

export type HistoricoCliente = {
  id: string;
  usuarioId: string;
  usuario: string;
  dataHora: string;
  dispositivo: string;
  ipOrigem: string;
  acao: string;
  origem: OrigemHistorico;
};

/**
 * Dados sensíveis — devem aparecer apenas na guia Administrativa do modo
 * Edit do EntityDrawer, restrita por hasAdministrativeAccess
 * (lib/access-control.ts). Não expor em tabela, Peek, resultados de busca
 * ou logs de console. Ocultar no frontend não substitui autorização real:
 * o backend deverá aplicar a mesma checagem ao servir/gravar estes campos
 * (ver entity-component-api.md, seção "Guia Administrativa").
 *
 * feeMensal representa receita (o que o cliente paga); nunca é misturado
 * com despesa (ex.: Salário, futuro em Usuários). valor é numérico — nunca
 * uma string já formatada com moeda.
 */
export type ClienteFeeMensal = {
  valor: number | null;
  moeda: "BRL";
  dataInicio: string;
  observacao: string;
};

export type ClienteDadosBancarios = {
  chavePix: string;
  banco: string;
  agencia: string;
  conta: string;
  tipoConta: "Corrente" | "Poupança" | "Pagamento";
};

export type ClienteAdministrativo = {
  feeMensal: ClienteFeeMensal;
  dadosBancarios: ClienteDadosBancarios;
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
  administrativo: ClienteAdministrativo;
  historico: HistoricoCliente[];
};
