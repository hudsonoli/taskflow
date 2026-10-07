export type PerfilUsuario = "superadmin" | "admin" | "diretoria" | "gestor" | "financeiro" | "operador" | "cliente";

export const perfilUsuarioLabels: Record<PerfilUsuario, string> = {
  superadmin: "SuperAdmin",
  admin: "Admin",
  diretoria: "Diretoria",
  gestor: "Gestor",
  financeiro: "Financeiro",
  // Rótulo VISÍVEL do perfil técnico `operador` (nome interno inalterado no banco/API/JWT).
  operador: "Usuário",
  cliente: "Cliente",
};

// Perfil técnico que a API realmente grava/devolve (`perfil_base`). `admin` é LEGADO: continua válido para
// leitura, mas a API nunca o atribui (Fase 1A).
export type UsuarioPerfilBaseApi = "admin" | "gestor" | "operador";

// perfil_base real só tem 3 valores. Mapeamento do rótulo rico antigo (mock) para o valor técnico — hoje só
// serve para ler o perfil de quem já existe (superadmin|diretoria -> admin, financeiro -> gestor, cliente ->
// operador): a UI de cadastro NÃO oferece mais essas opções, só Gestor e Usuário.
export const PERFIL_PARA_PERFIL_BASE: Record<PerfilUsuario, UsuarioPerfilBaseApi> = {
  superadmin: "admin",
  admin: "admin",
  diretoria: "admin",
  financeiro: "gestor",
  gestor: "gestor",
  operador: "operador",
  cliente: "operador",
};

// Perfis com visibilidade de dados financeiros sensíveis (ex: fee mensal de clientes,
// aba Comercial de clientes, aba Financeiro de usuários).
export const perfisComAcessoFinanceiro: PerfilUsuario[] = ["superadmin", "admin", "diretoria", "gestor", "financeiro"];

export function podeVerDadosFinanceiros(perfil: PerfilUsuario): boolean {
  return perfisComAcessoFinanceiro.includes(perfil);
}

// Perfis com acesso ao módulo administrativo "Acesso" (histórico de login: IP, navegador, SO).
export const perfisComAcessoAdministrativo: PerfilUsuario[] = ["superadmin", "admin", "diretoria", "gestor"];

// Perfis que podem cadastrar novas demandas independentemente do departamento.
export const perfisComCriacaoDemanda: PerfilUsuario[] = ["superadmin", "admin", "diretoria", "gestor"];

/**
 * Regra de criação de demandas: Gestão (Gestor/Diretoria/Admin/SuperAdmin), líderes de
 * departamento (heads) e qualquer pessoa do departamento Atendimento podem cadastrar.
 *
 * REGRA TRANSITÓRIA (D3-A): recebe o **nome já resolvido** do departamento, não o
 * identificador. Quem chama resolve `usuario.departamentoId` (UUID) por
 * `resolverDepartamentoNome` antes — o nome entra aqui só como classificação de UX e nunca
 * como identidade de relacionamento nem como valor aceito em payload. Junto com
 * `NOME_DEPARTAMENTO_ATENDIMENTO` (lib/escopo-operacional.ts), é o único lugar onde o nome
 * decide comportamento; ambos saem quando existir permissão granular real.
 */
export function podeCriarDemanda(usuario: { perfil: PerfilUsuario; liderDepartamento: boolean }, departamentoNome: string): boolean {
  if (perfisComCriacaoDemanda.includes(usuario.perfil)) return true;
  if (usuario.liderDepartamento) return true;
  if (departamentoNome.trim().toLowerCase() === "atendimento") return true;
  return false;
}

export type UsuarioContato = {
  id: string;
  nome: string;
  email: string;
  telefone: string;
  relacao: string;
};

export type Usuario = {
  id: string;
  empresaId: string;
  nome: string;
  email: string;
  telefone: string;
  cpf: string;
  dataNascimento: string;
  cep: string;
  bairro: string;
  enderecoCompleto: string;
  cidade: string;
  uf: string;
  contatos: UsuarioContato[];
  departamentoId: string;
  perfil: PerfilUsuario;
  cargo?: string;
  // Foto de perfil: caminho da API (`/usuarios/<id>/avatar?v=…`, foto própria enviada) ou URL externa (Google).
  fotoUrl?: string;
  // Só no usuário logado (GET /usuarios/me): último login bem-sucedido.
  ultimoAcesso?: { em: string; ip: string | null };
  // Marca a pessoa como líder/gerente do departamento (head) — dá permissão de cadastrar demandas.
  liderDepartamento: boolean;
  // Aba Financeiro (visível apenas para Gestão/Diretoria/Financeiro): cruzamento recebimento x hora.
  valorRecebidoMensal: number | null;
  horasTrabalhoAproximadas: number | null;
  ativo: boolean;
  observacoes: string;
  corIdentificacao: string;
  createdAt: string;
  updatedAt: string;
  // Só preenchido para o próprio usuário logado (GET /usuarios/me) — ver
  // UsuarioRead.permissoes no backend. Undefined para qualquer outra pessoa.
  permissoes?: string[];
};

export type UsuarioFormDraft = Omit<Usuario, "id" | "empresaId" | "createdAt" | "updatedAt">;
