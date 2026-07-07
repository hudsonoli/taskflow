import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

type SettingsItem = {
  title: string;
  description: string;
  href?: string;
  disabled?: boolean;
};

type SettingsSection = {
  title: string;
  description: string;
  items: SettingsItem[];
};

const settingsSections: SettingsSection[] = [
  {
    title: "Cadastros",
    description: "Entidades base para operação e organização da plataforma.",
    items: [
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
        title: "Clientes",
        description: "Cadastro e gestão de clientes da agência.",
        href: "/configuracoes/clientes",
      },
      {
        title: "Grupos de Clientes",
        description: "Segmentação e organização dos clientes.",
        href: "/configuracoes/grupos-clientes",
      },
      {
        title: "Equipes",
        description: "Organização de times e departamentos.",
        href: "/configuracoes/equipes",
      },
    ],
  },
  {
    title: "Operação",
    description: "Configurações que orientam o fluxo de trabalho diário.",
    items: [
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
    ],
  },
  {
    title: "Segurança",
    description: "Perfis e controles administrativos de acesso.",
    items: [
      {
        title: "Permissões",
        description: "Perfis, papéis e permissões administrativas.",
        href: "/configuracoes/permissoes",
      },
      {
        title: "Auditoria",
        description: "Histórico e rastreio de ações administrativas.",
        disabled: true,
      },
    ],
  },
];

export default function ConfiguracoesPage() {
  return (
    <div className="p-8">
      <PageHeader
        title="Configurações"
        description="Área administrativa para SuperAdmin, Admin, Diretoria, Gestores e usuários autorizados."
      />

      <div className="space-y-8">
        {settingsSections.map((section) => (
          <Card key={section.title}>
            <div className="mb-5">
              <h2 className="text-xl font-semibold text-zinc-900">
                {section.title}
              </h2>

              <p className="mt-2 text-sm leading-6 text-zinc-500">
                {section.description}
              </p>
            </div>

            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              {section.items.map((item) => {
                if (item.disabled) {
                  return (
                    <div
                      key={item.title}
                      aria-disabled="true"
                      className="rounded-3xl border border-dashed border-zinc-200 bg-zinc-50 p-6 opacity-70"
                    >
                      <h3 className="text-lg font-semibold text-zinc-900">
                        {item.title}
                      </h3>

                      <p className="mt-2 text-sm leading-6 text-zinc-500">
                        {item.description}
                      </p>

                      <p className="mt-4 text-xs font-medium uppercase tracking-[0.2em] text-zinc-400">
                        Em breve
                      </p>
                    </div>
                  );
                }

                return (
                  <Link
                    key={item.title}
                    href={item.href ?? "#"}
                    className="rounded-3xl bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
                  >
                    <h3 className="text-lg font-semibold text-zinc-900">
                      {item.title}
                    </h3>

                    <p className="mt-2 text-sm leading-6 text-zinc-500">
                      {item.description}
                    </p>
                  </Link>
                );
              })}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
