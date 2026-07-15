// Tons opcionais para o pontinho semântico ao lado do label — mesma
// convenção visual do dot de StatusPill. green e emerald são tons
// propositalmente distintos (não variações de um mesmo "verde"): green
// mais suave, emerald mais forte, para nunca ficarem visualmente iguais
// quando usados lado a lado (ex.: "No Prazo" vs "Concluídas" na Dashboard).
export type CadastroIndicatorTone =
  | "green"
  | "emerald"
  | "red"
  | "violet"
  | "amber"
  | "orange"
  | "slate";

const toneDotClassNames: Record<CadastroIndicatorTone, string> = {
  green: "bg-green-400",
  emerald: "bg-emerald-600",
  red: "bg-red-500",
  violet: "bg-violet-500",
  amber: "bg-amber-500",
  orange: "bg-orange-500",
  slate: "bg-slate-600",
};

type CadastroIndicator = {
  label: string;
  value: string | number;
  description?: string;
  // Opcional — sem ele, o item renderiza exatamente como antes (nenhum
  // consumidor existente passa tone, então nenhum visual muda).
  tone?: CadastroIndicatorTone;
};

type CadastroIndicatorsDensity = "compact" | "default";

type CadastroIndicatorsProps = {
  items: CadastroIndicator[];
  density?: CadastroIndicatorsDensity;
  // Opcional — grid padrão preservado quando omitido, byte-idêntico ao
  // comportamento anterior (usado hoje por Clientes).
  columnsClassName?: string;
};

const densityClassNames: Record<CadastroIndicatorsDensity, string> = {
  compact: "min-h-[32px] px-2.5 py-1",
  default: "min-h-[58px] px-3 py-2.5",
};

const defaultColumnsClassName = "grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5";

export function CadastroIndicators({
  items,
  density = "default",
  columnsClassName = defaultColumnsClassName,
}: CadastroIndicatorsProps) {
  return (
    <div className={columnsClassName}>
      {items.map((item) => (
        <div
          key={item.label}
          className={`flex items-center justify-between rounded-2xl border border-zinc-100 bg-white shadow-sm ${densityClassNames[density]}`}
        >
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 truncate text-xs font-medium text-zinc-500">
              {item.tone ? (
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${toneDotClassNames[item.tone]}`}
                  aria-hidden="true"
                />
              ) : null}
              {item.label}
            </p>
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
