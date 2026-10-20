import clsx from "clsx";
import { AlertTriangle } from "lucide-react";
import type { IndicadorResumo, QualidadePlanejamento, TomOcupacao } from "@/lib/trafego-carga";
import {
  TEXTO_CAPACIDADE_INDISPONIVEL,
  TITULO_PLANEJAMENTO_INCOMPLETO,
  avisosDoPlanejamento,
  explicacaoCapacidadeIndisponivel,
} from "@/lib/trafego-carga";

const COR_VALOR: Record<TomOcupacao, string> = {
  neutro: "text-fg",
  normal: "text-fg",
  atencao: "text-amber-700 dark:text-amber-400",
  sobrecarga: "text-red-600 dark:text-red-400",
};

/** No máximo quatro indicadores compactos: capacidade alocável, planejado, disponível e ocupação (conhecida, quando o planejamento está incompleto). */
export function CargaSummary({ indicadores }: { indicadores: IndicadorResumo[] }) {
  return (
    <ul aria-label="Resumo da semana" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {indicadores.map((indicador) => (
        <li key={indicador.id} className="rounded-xl border border-line bg-surface px-3.5 py-3 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{indicador.rotulo}</p>
          <p className={clsx("mt-1 text-xl font-semibold tabular-nums leading-tight", COR_VALOR[indicador.tom])}>{indicador.valor}</p>
          <p className="mt-0.5 text-xs text-fg-subtle">{indicador.ajuda}</p>
        </li>
      ))}
    </ul>
  );
}

/** Expediente desligado: nada de capacidade "0" — a capacidade está INDISPONÍVEL, e o texto diz por quê. */
export function CargaCapacidadeIndisponivel({ motivo }: { motivo: string }) {
  return (
    <div role="status" className="flex items-start gap-2.5 rounded-xl border border-line bg-surface-2 px-3.5 py-3 text-sm text-fg-muted">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-fg-subtle" aria-hidden />
      <div>
        <p className="font-medium text-fg">{TEXTO_CAPACIDADE_INDISPONIVEL}</p>
        <p className="text-xs">{explicacaoCapacidadeIndisponivel(motivo)}</p>
        <p className="mt-1 text-xs text-fg-subtle">A ocupação não é calculada. O que ainda precisa de planejamento continua listado abaixo.</p>
      </div>
    </div>
  );
}

/** Aviso âmbar: o planejamento está incompleto, então 0% (ou qualquer ocupação) é só o que já está estimado e com janela — não é "equipe livre". */
export function CargaPlanningWarnings({ qualidade }: { qualidade: QualidadePlanejamento }) {
  const avisos = avisosDoPlanejamento(qualidade);
  if (avisos.length === 0) return null;
  return (
    <div role="note" className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
      <p className="flex items-center gap-2 font-medium">
        <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
        {TITULO_PLANEJAMENTO_INCOMPLETO}
      </p>
      <ul className="mt-1.5 list-disc space-y-0.5 pl-9 text-xs">
        {avisos.map((aviso) => (
          <li key={aviso}>{aviso}</li>
        ))}
      </ul>
    </div>
  );
}
