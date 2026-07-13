type CadastroIndicator = {
  label: string;
  value: string | number;
  description?: string;
};

type CadastroIndicatorsProps = {
  items: CadastroIndicator[];
};

export function CadastroIndicators({ items }: CadastroIndicatorsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex min-h-[58px] items-center justify-between rounded-2xl border border-zinc-100 bg-white px-3 py-2.5 shadow-sm"
        >
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-zinc-500">{item.label}</p>
            {item.description ? (
              <p className="mt-0.5 truncate text-[11px] text-zinc-400">
                {item.description}
              </p>
            ) : null}
          </div>
          <p className="ml-3 text-xl font-semibold tabular-nums text-zinc-900">
            {item.value}
          </p>
        </div>
      ))}
    </div>
  );
}
