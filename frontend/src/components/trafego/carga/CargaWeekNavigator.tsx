import { ChevronLeft, ChevronRight } from "lucide-react";
import type { CabecalhoSemana } from "@/lib/trafego-carga";
import { BotaoAtualizar } from "../TrafegoEstados";

/**
 * [ ← ] Semana 19–25 out [ → ]. A semana vem pronta da API (segunda a domingo no fuso da EMPRESA); o navegador só soma 7 dias ao calendário recebido. Na semana atual "←" fica desabilitado
 * (a v1 não tem histórico de capacidade), então a navegação normal nunca gera 422. Enquanto não há resposta, os controles ficam desabilitados.
 */
export function CargaWeekNavigator({
  cabecalho,
  onIr,
  onAtualizar,
  atualizando,
}: {
  cabecalho: CabecalhoSemana | null;
  onIr: (inicio: string) => void;
  onAtualizar: () => void;
  atualizando: boolean;
}) {
  const botao = "inline-flex h-8 w-8 items-center justify-center rounded-full border border-line-strong bg-surface text-fg-muted shadow-xs transition hover:bg-surface-hover hover:text-fg disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-focus";
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <button type="button" aria-label="Semana anterior" className={botao} disabled={cabecalho === null || !cabecalho.podeVoltar} onClick={() => cabecalho && onIr(cabecalho.anterior)}>
            <ChevronLeft className="h-4 w-4" />
          </button>
          <p className="min-w-[10rem] text-center text-sm font-semibold text-fg" aria-live="polite">
            {cabecalho ? `Semana ${cabecalho.rotulo}` : "Semana"}
          </p>
          <button type="button" aria-label="Próxima semana" className={botao} disabled={cabecalho === null} onClick={() => cabecalho && onIr(cabecalho.proxima)}>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
        {cabecalho?.aviso && <p className="max-w-xl text-xs text-fg-subtle">{cabecalho.aviso}</p>}
      </div>
      <BotaoAtualizar onClick={onAtualizar} atualizando={atualizando} />
    </div>
  );
}
