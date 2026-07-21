export function splitResolvedNames(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

type CompactListProps = {
  items: string[];
};

/**
 * Lista compacta "primeiros 2 itens + N" usada em células de tabela com
 * múltiplos valores (responsáveis, departamentos). Extraído de
 * DemandasTable.tsx/ProjetosTable.tsx, onde vivia duplicado byte a byte.
 */
export function CompactList({ items }: CompactListProps) {
  const visibleItems = items.slice(0, 2);
  const extraItems = items.length - visibleItems.length;

  return (
    <div className="flex max-w-[220px] flex-wrap gap-1.5">
      {visibleItems.map((item) => (
        <span
          key={item}
          className="inline-flex max-w-[140px] items-center rounded-full bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-600"
          title={item}
        >
          <span className="truncate">{item}</span>
        </span>
      ))}
      {extraItems > 0 && (
        <span className="inline-flex items-center rounded-full bg-zinc-900 px-2 py-1 text-xs font-semibold text-white">
          +{extraItems}
        </span>
      )}
    </div>
  );
}
