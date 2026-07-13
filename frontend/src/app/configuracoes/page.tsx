import Link from "next/link";
import { Pencil } from "lucide-react";

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
      { title: "Agências", description: "Gestão das agências da plataforma.", href: "/configuracoes/agencias" },
      { title: "Usuários", description: "Cargos, acessos e usuários.", href: "/configuracoes/usuarios" },
      { title: "Clientes", description: "Clientes da agência.", href: "/configuracoes/clientes" },
      { title: "Grupos de Clientes", description: "Organização de clientes relacionados.", href: "/configuracoes/grupos-clientes" },
      { title: "Equipes", description: "Times, líderes e departamentos.", href: "/configuracoes/equipes" },
    ],
  },
  {
    title: "Operação",
    description: "Configurações que orientam o fluxo diário.",
    items: [
      { title: "Workflows", description: "Fluxos operacionais e etapas.", href: "/configuracoes/workflows" },
      { title: "SLA", description: "Regras de prazo e atendimento.", href: "/configuracoes/sla" },
      { title: "Prioridades", description: "Níveis de urgência das tarefas.", href: "/configuracoes/prioridades" },
      { title: "Tipos de Tarefa", description: "Categorias operacionais.", href: "/configuracoes/tipos-tarefa" },
    ],
  },
  {
    title: "Segurança",
    description: "Perfis e controles administrativos.",
    items: [
      { title: "Permissões", description: "Papéis e permissões administrativas.", href: "/configuracoes/permissoes" },
      { title: "Auditoria", description: "Histórico de ações administrativas.", disabled: true },
    ],
  },
];

export default function ConfiguracoesPage() {
  return (
    <div className="space-y-4 p-4 sm:p-5">
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">Configurações</h2>
        <p className="mt-0.5 text-sm text-zinc-500">
          Área administrativa da plataforma.
        </p>
      </div>

      <div className="space-y-4">
        {settingsSections.map((section) => (
          <section
            key={section.title}
            className="rounded-2xl border border-zinc-100 bg-white p-3 shadow-sm"
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-zinc-900">
                  {section.title}
                </h3>
                <p className="mt-0.5 text-xs text-zinc-500">
                  {section.description}
                </p>
              </div>
            </div>

            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {section.items.map((item) => {
                if (item.disabled) {
                  return (
                    <div
                      key={item.title}
                      aria-disabled="true"
                      className="flex min-h-[58px] items-center justify-between gap-3 rounded-xl border border-dashed border-zinc-200 bg-zinc-50 px-3 py-2 opacity-70"
                    >
                      <div className="min-w-0">
                        <h4 className="truncate text-sm font-semibold text-zinc-900">
                          {item.title}
                        </h4>
                        <p className="mt-0.5 truncate text-xs text-zinc-500">
                          {item.description}
                        </p>
                      </div>
                      <span className="shrink-0 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400">
                        Em breve
                      </span>
                    </div>
                  );
                }

                return (
                  <Link
                    key={item.title}
                    href={item.href ?? "#"}
                    aria-label={`Abrir ${item.title}`}
                    className="flex min-h-[58px] items-center justify-between gap-3 rounded-xl border border-zinc-100 bg-white px-3 py-2 transition-colors hover:border-zinc-200 hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
                  >
                    <div className="min-w-0">
                      <h4 className="truncate text-sm font-semibold text-zinc-900">
                        {item.title}
                      </h4>
                      <p className="mt-0.5 truncate text-xs text-zinc-500">
                        {item.description}
                      </p>
                    </div>
                    <Pencil
                      className="h-4 w-4 shrink-0 text-zinc-400"
                      strokeWidth={2}
                      aria-hidden="true"
                    />
                  </Link>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
