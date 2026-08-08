import type { ComponentType } from "react";
import { Building2, Clock, ClipboardList, Hash, History, Layers3, Mail, ShieldCheck, Tag, Timer, Truck, UsersRound, Workflow } from "lucide-react";

export type ItemConfiguracao = {
  label: string;
  description: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  available: boolean;
  // Item administrativo — visível apenas para Admin/Gestor/Diretoria/SuperAdmin
  // (ver `podeAcessarAcessos` em lib/escopo-operacional.ts). Filtrado no ConfiguracoesSidebarNav.
  apenasAdministrativo?: boolean;
};

export type GrupoConfiguracao = {
  titulo: string;
  itens: ItemConfiguracao[];
};

export const gruposConfiguracao: GrupoConfiguracao[] = [
  {
    titulo: "Cadastros",
    itens: [
      { label: "Clientes", description: "Empresas e contatos atendidos pela operação.", href: "/configuracoes/clientes", icon: Building2, available: true },
      { label: "Grupos de clientes", description: "Etiquetas de grupo econômico, rede ou carteira.", href: "/configuracoes/grupos-clientes", icon: Tag, available: true },
      { label: "Peças", description: "Catálogo de peças/serviços reutilizáveis.", href: "/configuracoes/pecas", icon: Layers3, available: true },
      { label: "Fornecedores", description: "Gráficas, produtoras, freelancers, mídia.", href: "/configuracoes/fornecedores", icon: Truck, available: true },
      { label: "Usuários", description: "Pessoas com acesso ao workspace.", href: "/configuracoes/usuarios", icon: UsersRound, available: true },
      { label: "Departamentos", description: "Setores da operação e responsáveis.", href: "/configuracoes/departamentos", icon: Building2, available: true },
      { label: "Equipes", description: "Squads e times, com líder e membros.", href: "/configuracoes/equipes", icon: UsersRound, available: true },
      { label: "Workflows", description: "Modelos de etapas padrão para o cadastro de tarefas.", href: "/configuracoes/workflows", icon: Workflow, available: true },
      { label: "Tipos de tarefa", description: "Categorias de demanda.", href: "#", icon: ClipboardList, available: false },
    ],
  },
  {
    titulo: "Administrativo",
    itens: [
      {
        label: "Acesso",
        description: "Histórico de login: hora, IP, navegador e sistema operacional.",
        href: "/configuracoes/acessos",
        icon: History,
        available: true,
        apenasAdministrativo: true,
      },
      { label: "Permissões", description: "Perfis de acesso (RBAC).", href: "#", icon: ShieldCheck, available: false },
      { label: "SLA", description: "Prazos de resposta e resolução por prioridade, departamento ou cliente.", href: "/configuracoes/sla", icon: Timer, available: true },
      { label: "Horário de expediente", description: "Turnos da agência e pausa automática de tarefas.", href: "/configuracoes/horario-expediente", icon: Clock, available: true },
      { label: "Numeração de tarefas", description: "Próximo código de tarefa (#AA0000) — ajuste ao migrar do iClips.", href: "/configuracoes/numeracao-tarefas", icon: Hash, available: true },
    ],
  },
  {
    titulo: "Integrações",
    itens: [
      { label: "Configuração de e-mail", description: "Conta de disparo — login Google/M365 ou SMTP manual.", href: "/configuracoes/email", icon: Mail, available: true },
    ],
  },
];
