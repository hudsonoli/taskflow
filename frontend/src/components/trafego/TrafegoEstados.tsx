import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";

/** Erro LOCAL da visão (não derruba o Shell): mensagem + "Tentar novamente". */
export function TrafegoErroLocal({ mensagem, onTentarNovamente }: { mensagem: string; onTentarNovamente: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
      <span>{mensagem}</span>
      <Button variant="secondary" onClick={onTentarNovamente}>
        Tentar novamente
      </Button>
    </div>
  );
}

/** Falha de uma atualização quando já há dados na tela: o conteúdo fica, e o aviso é discreto. */
export function TrafegoAvisoAtualizacao({ mensagem, onTentarNovamente }: { mensagem: string; onTentarNovamente: () => void }) {
  return (
    <p role="status" className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
      <span>{mensagem} Exibindo a última atualização.</span>
      <button type="button" onClick={onTentarNovamente} className="font-medium underline underline-offset-2">
        Tentar novamente
      </button>
    </p>
  );
}

function Bloco({ className }: { className: string }) {
  return <div aria-hidden className={`animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-800 ${className}`} />;
}

/** Skeleton da PRIMEIRA carga (nunca usado nos refreshes, para a tela não piscar). */
export function TrafegoSkeleton({ kpis = 0, linhas = 4 }: { kpis?: number; linhas?: number }) {
  return (
    <div role="status" aria-label="Carregando" className="flex flex-col gap-4">
      {kpis > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
          {Array.from({ length: kpis }, (_, indice) => (
            <Bloco key={indice} className="h-[84px]" />
          ))}
        </div>
      )}
      <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
        <Bloco className="mb-4 h-5 w-48" />
        <div className="flex flex-col gap-2">
          {Array.from({ length: linhas }, (_, indice) => (
            <Bloco key={indice} className="h-9 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}

/** Botão "Atualizar" das visões: o ícone gira enquanto há requisição em voo, sem trocar o conteúdo. */
export function BotaoAtualizar({ onClick, atualizando }: { onClick: () => void; atualizando: boolean }) {
  return (
    <Button variant="secondary" onClick={onClick} disabled={atualizando}>
      <RefreshCw className={`h-4 w-4 ${atualizando ? "animate-spin" : ""}`} />
      Atualizar
    </Button>
  );
}
