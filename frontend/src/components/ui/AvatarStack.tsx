import { Avatar } from "@/components/ui/Avatar";

export interface AvatarStackPerson {
  id: string;
  nome: string;
  corIdentificacao?: string;
  fotoUrl?: string;
}

export function AvatarStack({
  pessoas,
  max = 4,
  size = "h-8 w-8",
  emptyLabel = "Sem responsáveis",
}: {
  pessoas: AvatarStackPerson[];
  max?: number;
  size?: string;
  emptyLabel?: string;
}) {
  if (pessoas.length === 0) {
    return <span className="text-xs text-zinc-400">{emptyLabel}</span>;
  }

  const visiveis = pessoas.slice(0, max);
  const extras = pessoas.length - visiveis.length;

  return (
    <div className="flex items-center -space-x-2">
      {visiveis.map((pessoa) => (
        <div
          key={pessoa.id}
          title={pessoa.nome}
          aria-label={pessoa.nome}
          className="rounded-full ring-2 ring-white dark:ring-zinc-900"
        >
          <Avatar
            nome={pessoa.nome}
            corIdentificacao={pessoa.corIdentificacao ?? "zinc"}
            fotoUrl={pessoa.fotoUrl}
            className={`${size} rounded-full text-xs`}
          />
        </div>
      ))}
      {extras > 0 && (
        <span
          className={`flex ${size} items-center justify-center rounded-full bg-zinc-900 text-[10px] font-semibold text-white ring-2 ring-white dark:bg-zinc-100 dark:text-zinc-900 dark:ring-zinc-900`}
        >
          +{extras}
        </span>
      )}
    </div>
  );
}
