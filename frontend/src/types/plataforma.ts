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

// ── Dashboard (GET /plataforma/dashboard): só métricas agregadas e datas de acesso ──────────────────────────
export type DashboardResumo = {
  empresasTotal: number;
  empresasAtivas: number;
  usuarios: number;
  cadastrados: number;
  jaAcessaram: number;
  nuncaAcessaram: number;
  ativos7d: number;
  ativos30d: number;
  gestores: number;
};

export type DashboardEmpresa = {
  id: string;
  nome: string;
  nomeFantasia: string | null;
  slug: string;
  status: PlataformaEmpresaStatus;
  createdAt: string;
  /** usuários humanos utilizáveis (ativos, com acesso, sem conta de sistema) */
  usuarios: number;
  /** inclui inativos/bloqueados; arquivados e conta de sistema nunca entram */
  cadastrados: number;
  jaAcessaram: number;
  nuncaAcessaram: number;
  ativos7d: number;
  ativos30d: number;
  gestores: number;
  /** último LOGIN de qualquer usuário humano (só o login é rastreado) */
  ultimoAcesso: string | null;
  projetos: number;
  demandas: number;
};

export type DashboardAtencao = {
  tipo: "sem_gestor" | "nunca_acessaram" | "sem_acesso_30d";
  severidade: "aviso" | "info";
  empresaId: string;
  empresaNome: string;
  mensagem: string;
  quantidade: number | null;
};

export type PlataformaDashboard = {
  geradoEm: string;
  resumo: DashboardResumo;
  empresas: DashboardEmpresa[];
  atencoes: DashboardAtencao[];
};
