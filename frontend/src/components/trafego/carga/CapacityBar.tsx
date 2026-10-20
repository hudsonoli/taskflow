import clsx from "clsx";
import type { LinhaOcupacao, TomOcupacao } from "@/lib/trafego-carga";

const COR_BARRA: Record<TomOcupacao, string> = {
  neutro: "bg-zinc-300 dark:bg-zinc-600",
  normal: "bg-indigo-500",
  atencao: "bg-amber-500",
  sobrecarga: "bg-red-500",
};

const COR_TEXTO: Record<TomOcupacao, string> = {
  neutro: "text-fg-subtle",
  normal: "text-fg",
  atencao: "text-amber-700 dark:text-amber-400",
  sobrecarga: "text-red-600 dark:text-red-400",
};

/**
 * Percentual + barra simples. A barra limita o PREENCHIMENTO a 100%, mas o texto mostra o valor real (128% continua 128%). Sem gauge, sem donut, sem ranking.
 * Sem denominador confiável (capacidade indisponível/zero) a barra fica vazia e o texto é "—" (ou "Sem capacidade" quando há carga).
 */
export function CapacityBar({ ocupacao }: { ocupacao: LinhaOcupacao }) {
  return (
    <div className="flex items-center justify-end gap-2" title={ocupacao.texto === "—" ? "Ocupação indisponível" : `Ocupação: ${ocupacao.texto}`}>
      <div role="img" aria-label={`Ocupação ${ocupacao.texto}`} className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800 xl:block">
        <div className={clsx("h-full rounded-full", COR_BARRA[ocupacao.tom])} style={{ width: `${ocupacao.preenchimento}%` }} />
      </div>
      <span className={clsx("min-w-[4.5rem] whitespace-nowrap text-right font-mono text-sm tabular-nums", COR_TEXTO[ocupacao.tom], ocupacao.tom === "sobrecarga" && "font-semibold")}>{ocupacao.texto}</span>
    </div>
  );
}
