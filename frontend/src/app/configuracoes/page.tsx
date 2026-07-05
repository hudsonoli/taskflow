import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";

const settingsItems = [
  {
    title: "Agências",
    description: "Cadastro e gestão das agências da plataforma.",
    href: "/configuracoes/agencias",
  },
  {
    title: "Usuários",
    description: "Gestão de usuários, cargos e acessos.",
    href: "/configuracoes/usuarios",
  },
  {
    title: "Equipes",
    description: "Organização de times e departamentos.",
    href: "/configuracoes/equipes",
  },
  {
    title: "Workflows",
    description: "Fluxos operacionais e etapas do Kanban.",
    href: "/configuracoes/workflows",
  },
  {
    title: "SLA",
    description: "Regras de prazo e atendimento operacional.",
    href: "/configuracoes/sla",
  },
  {
    title: "Prioridades",
    description: "Níveis de urgência das tarefas.",
    href: "/configuracoes/prioridades",
  },
  {
    title: "Tipos de Tarefa",
    description: "Categorias operacionais das demandas.",
    href: "/configuracoes/tipos-tarefa",
  },
  {
    title: "Permissões",
    description: "Perfis, papéis e permissões administrativas.",
    href: "/configuracoes/permissoes",
  },
];

export default function ConfiguracoesPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Configurações"
        description="Área administrativa para SuperAdmin, Admin, Diretoria, Gestores e usuários autorizados."
      />

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {settingsItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-3xl bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
          >
            <h2 className="text-lg font-semibold text-zinc-900">
              {item.title}
            </h2>

            <p className="mt-2 text-sm leading-6 text-zinc-500">
              {item.description}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
