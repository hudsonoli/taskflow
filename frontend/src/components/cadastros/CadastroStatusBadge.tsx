type CadastroStatusBadgeProps = {
  children: React.ReactNode;
};

function getStatusClassName(status: string) {
  const normalized = status.toLowerCase();

  if (normalized.includes("ativo") || normalized.includes("ativa")) {
    return "bg-emerald-50 text-emerald-700 ring-emerald-100";
  }

  if (normalized.includes("inativo") || normalized.includes("inativa")) {
    return "bg-zinc-100 text-zinc-600 ring-zinc-200";
  }

  if (normalized.includes("pendente")) {
    return "bg-amber-50 text-amber-700 ring-amber-100";
  }

  return "bg-blue-50 text-blue-700 ring-blue-100";
}

export function CadastroStatusBadge({ children }: CadastroStatusBadgeProps) {
  const value = String(children);

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${getStatusClassName(value)}`}
    >
      {value}
    </span>
  );
}
