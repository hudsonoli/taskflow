/** Skeleton compartilhado — cards de indicador + bloco de lista, usado enquanto a visão calcula o escopo. */
export function EstadoCarregando({ cards = 4 }: { cards?: number }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="h-24 animate-pulse rounded-2xl border border-zinc-200 bg-zinc-100/70 dark:border-zinc-800 dark:bg-zinc-900/60" />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: cards }).map((_, index) => (
          <div
            key={index}
            className="h-28 animate-pulse rounded-2xl border border-zinc-200 bg-zinc-100/70 dark:border-zinc-800 dark:bg-zinc-900/60"
          />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-2xl border border-zinc-200 bg-zinc-100/70 dark:border-zinc-800 dark:bg-zinc-900/60" />
    </div>
  );
}
