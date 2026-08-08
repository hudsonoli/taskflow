import { ShieldAlert } from "lucide-react";

/**
 * Estado "sem permissão" — nesta fase é bloqueio de UX (o dado nem chega a ser buscado
 * no client), não segurança real. Ver aviso em `lib/escopo-operacional.ts`.
 */
export function AcessoNegado({
  titulo = "Você não tem acesso a esta visão",
  descricao = "Esta área é restrita a um escopo específico de usuário.",
}: {
  titulo?: string;
  descricao?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50 p-12 text-center dark:border-zinc-800 dark:bg-zinc-900/40">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400">
        <ShieldAlert size={20} />
      </div>
      <div>
        <p className="text-sm font-semibold text-zinc-700 dark:text-zinc-200">{titulo}</p>
        <p className="mt-1 max-w-sm text-sm text-zinc-400">{descricao}</p>
      </div>
    </div>
  );
}
