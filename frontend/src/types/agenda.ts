export type AgendaTipo =
  | "clientes"
  | "fornecedores"
  | "usuarios"
  | "parceiros"
  | "freelancers"
  | "transportadoras"
  | "leads"
  | "outros";

export type AgendaContato = {
  id: string;
  tipo: AgendaTipo;
  nome: string;
  empresa: string;
  cargo: string;
  departamento: string;
  email: string;
  telefone: string;
  celular: string;
  favorito?: boolean;
  ultimaInteracao?: string;
  empresaId?: string;
  agenciaId?: string;
  avatarUrl: string | null;
  avatarThumbnail: string | null;
};
