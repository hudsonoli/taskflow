// Administração da Plataforma (Fase 1B) — formatos da API `/plataforma/*` (camelCase via alias Pydantic).
// Nada aqui carrega token, hash de senha, e-mail de autorização nem configuração interna.

export type PlataformaEmpresaStatus = "ativa" | "inativa" | "arquivada";

export type PlataformaEmpresa = {
  id: string;
  nome: string;
  nomeFantasia: string | null;
  documento: string | null;
  /** identificador de login de hoje (legado) — só a Plataforma altera */
  codigoInterno: string;
  /** identificador público de URL (futuro login multiempresa) — só a Plataforma altera */
  slug: string;
  status: PlataformaEmpresaStatus;
  createdAt: string;
  updatedAt: string;
  inativadoAt: string | null;
  motivoInativacao: string | null;
  gestoresAtivos: number;
  /** a empresa hospeda um Administrador da Plataforma ativo → não pode ser inativada */
  hospedaAdministradorPlataforma: boolean;
};

export type PlataformaEmpresaCreate = {
  nome: string;
  nomeFantasia?: string | null;
  documento?: string | null;
  codigoInterno: string;
  slug?: string | null;
};

export type PlataformaEmpresaUpdate = Partial<Omit<PlataformaEmpresaCreate, "codigoInterno" | "slug">> & {
  codigoInterno?: string;
  slug?: string;
};

export type PlataformaUsuario = {
  id: string;
  nome: string;
  email: string;
  perfilBase: "admin" | "gestor" | "operador";
  status: "ativo" | "inativo" | "bloqueado" | "arquivado";
  acessoSistema: boolean;
  createdAt: string;
};

export type PlataformaGestorCreate = { nome: string; email: string };

/** Resposta ÚNICA da criação de Gestor: a senha temporária só existe aqui. */
export type PlataformaGestorCriado = {
  usuario: PlataformaUsuario;
  senhaTemporaria: string;
  deveAlterarSenha: boolean;
};

export type PlataformaMe = {
  administradorId: string;
  usuarioId: string;
  nome: string;
  ativo: boolean;
  criadoEm: string;
};
