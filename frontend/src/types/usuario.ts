export type PerfilUsuario = "superadmin" | "admin" | "diretoria" | "gestor" | "financeiro" | "operador" | "cliente";

export const perfilUsuarioLabels: Record<PerfilUsuario, string> = {
  superadmin: "SuperAdmin",
  admin: "Admin",
  diretoria: "Diretoria",
  gestor: "Gestor",
  financeiro: "Financeiro",
  operador: "Operador",
  cliente: "Cliente",
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
  // Preenchida no autoatendimento de "Minha conta" — data URL local (sem upload real nesta fase).
  fotoUrl?: string;
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
};

export type UsuarioFormDraft = Omit<Usuario, "id" | "empresaId" | "createdAt" | "updatedAt">;
