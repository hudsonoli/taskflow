import type { PerfilAcesso } from "@/lib/access-control";
import type { DepartamentoOption, PermissaoItem } from "@/types/usuario";

export const EMPRESA_PADRAO_ID = "empresa-principal";

export const departamentos: DepartamentoOption[] = [
  { id: "dep-atendimento", nome: "Atendimento", ativo: true },
  { id: "dep-trafego", nome: "Tráfego", ativo: true },
  { id: "dep-criacao", nome: "Criação", ativo: true },
  { id: "dep-financeiro", nome: "Financeiro", ativo: true },
  { id: "dep-orcamento-producao", nome: "Orçamento/Produção", ativo: true },
  { id: "dep-midia", nome: "Mídia", ativo: true },
  { id: "dep-diretoria", nome: "Diretoria", ativo: true },
  { id: "dep-conteudo", nome: "Conteúdo", ativo: true },
  { id: "dep-ti", nome: "TI", ativo: true },
  { id: "dep-administrativo", nome: "Administrativo", ativo: true },
  { id: "dep-externo", nome: "Externo", ativo: true },
];

// Lista oficial do projeto (mesma união de lib/access-control.ts,
// PerfilAcesso) — SuperAdmin/Admin foram eliminados nesta migração.
// Tipado contra PerfilAcesso para não divergir de novo.
export const perfis: PerfilAcesso[] = [
  "Owner",
  "Diretoria",
  "Gestor",
  "Financeiro",
  "Operador",
  "Cliente",
];

export const paginasPrincipais = [
  "Dashboard",
  "Tarefas",
  "Projetos",
  "Clientes",
  "Relatórios",
];

const permissoesBase: Record<string, string[]> = {
  Cadastros: [
    "Colaboradores",
    "Colaboradores Externos",
    "Clientes",
    "Fornecedores",
    "Agência",
    "Departamentos",
    "Peças",
    "Tarefas",
    "Setor/Produtos/Serviços",
    "Blog",
    "Squad",
  ],
  Projetos: [
    "Projetos",
    "Carga de trabalho dos colaboradores",
    "Insights",
    "Estimativa",
    "Mídias",
    "Orçamentos",
    "Eventos",
    "Propostas",
    "OS",
    "Gestão de Atividades",
    "Controle de Horas",
  ],
  Relatórios: ["Relatórios", "Relatórios Produtividade", "Relatórios BI"],
  Financeiro: [
    "Cadastros",
    "Pré-lançamento",
    "Transferência",
    "Alterar Lançamentos",
    "Consulta Lançamentos",
    "Controles Financeiros",
    "Boleto, Nota, Recibo",
  ],
  Configurações: [
    "Usuários",
    "Permissões",
    "Workflows",
    "SLA",
    "Prioridades",
    "Tipos de Tarefa",
    "Auditoria",
  ],
};

export function createPermissoesCatalogo(): PermissaoItem[] {
  return Object.entries(permissoesBase).flatMap(([grupo, modulos]) =>
    modulos.map((modulo) => ({
      id: `${grupo}-${modulo}`,
      grupo,
      modulo,
      leitura: false,
      escrita: false,
      excluir: false,
      aprovar: false,
    }))
  );
}

export function generateId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function generateCodigoInterno(): string {
  const numero = Math.floor(Math.random() * 10000);
  return `#${numero.toString().padStart(4, "0")}`;
}

export function mockCepLookup(cepDigits: string) {
  const sufixo = cepDigits.slice(-3);

  return {
    logradouro: `Rua Mock ${sufixo}`,
    bairro: "Bairro Central",
    cidade: "São Paulo",
    uf: "SP",
    pais: "Brasil",
  };
}

export function generateInitials(nome: string): string {
  const words = nome.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();

  return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
}
