type BreadcrumbProps = {
  pathname: string;
};

const breadcrumbLabels: Record<string, string> = {
  "/": "Dashboard",
  "/tarefas": "Tarefas",
  "/projetos": "Projetos",
  "/clientes": "Clientes",
  "/fornecedores": "Fornecedores",
  "/equipe": "Equipe",
  "/relatorios": "Relatórios",
  "/configuracoes": "Configurações",
  "/configuracoes/agencias": "Agências",
  "/configuracoes/usuarios": "Usuários",
  "/configuracoes/clientes": "Clientes",
  "/configuracoes/grupos-clientes": "Grupos de Clientes",
  "/configuracoes/equipes": "Equipes",
  "/configuracoes/workflows": "Workflows",
  "/configuracoes/sla": "SLA",
  "/configuracoes/prioridades": "Prioridades",
  "/configuracoes/tipos-tarefa": "Tipos de Tarefa",
  "/configuracoes/permissoes": "Permissões",
  "/conta": "Conta",
  "/conta/perfil": "Perfil",
  "/conta/notificacoes": "Notificações",
  "/conta/alterar-senha": "Alterar senha",
};

function getBreadcrumbSegments(pathname: string) {
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length === 0) {
    return [breadcrumbLabels["/"]];
  }

  const paths: string[] = [];
  let current = "";

  for (const segment of segments) {
    current += `/${segment}`;
    paths.push(current);
  }

  const relevantPaths = pathname.startsWith("/configuracoes")
    ? paths
    : pathname === "/fornecedores"
      ? [pathname]
      : ["/", ...paths];

  return relevantPaths.map((path) => breadcrumbLabels[path] ?? path);
}

export function Breadcrumb({ pathname }: BreadcrumbProps) {
  const items = getBreadcrumbSegments(pathname);

  return (
    <nav aria-label="Breadcrumb" className="text-xs text-zinc-500">
      <ol className="flex flex-wrap items-center gap-1.5">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="flex items-center gap-1.5">
            {index > 0 ? <span className="text-zinc-300">/</span> : null}
            <span className={index === items.length - 1 ? "text-zinc-700" : ""}>
              {item}
            </span>
          </li>
        ))}
      </ol>
    </nav>
  );
}
