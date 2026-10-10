"use client";

import { useState } from "react";
import { Download, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { confirmacaoDeExclusao, quantidadeSelecionada, textoDoContador, type SelecaoArquivos } from "@/lib/selecao-arquivos";

/**
 * Barra de ações da seleção em lote (Fase 8B): contador, Baixar ZIP, Excluir e Limpar seleção. Aparece só com algo selecionado e fica
 * visível ao rolar (sticky). Excluir só existe para quem pode (`podeExcluir`); a confirmação é inline — com ciência extra quando a seleção
 * é "todos os resultados do filtro" — e diz que a ação não pode ser desfeita (a exclusão é definitiva).
 */
export function ArquivosSelecaoBar({
  selecao,
  podeExcluir,
  baixando,
  excluindo,
  aviso,
  erro,
  limiteAtingido,
  onBaixar,
  onExcluir,
  onLimpar,
}: {
  selecao: SelecaoArquivos;
  podeExcluir: boolean;
  baixando: boolean;
  excluindo: boolean;
  aviso: string | null;
  erro: string | null;
  limiteAtingido: boolean;
  onBaixar: () => void;
  onExcluir: () => Promise<void>;
  onLimpar: () => void;
}) {
  const quantidade = quantidadeSelecionada(selecao);
  const [confirmando, setConfirmando] = useState(false);
  const [ciente, setCiente] = useState(false);
  if (quantidade === 0 && !erro && !aviso) return null;

  const confirmacao = confirmacaoDeExclusao(selecao);
  const ocupado = baixando || excluindo;

  async function confirmarExclusao() {
    await onExcluir();
    setConfirmando(false);
    setCiente(false);
  }

  return (
    <div
      role="region"
      aria-label="Ações da seleção"
      className="sticky bottom-4 z-20 flex flex-col gap-2 rounded-2xl border border-line bg-surface p-3 shadow-lg"
    >
      {erro && (
        <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erro}
        </p>
      )}
      {aviso && <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">{aviso}</p>}
      {limiteAtingido && (
        <p className="text-xs text-fg-subtle">Limite de seleção manual atingido — para mais arquivos use “Selecionar todos os resultados”.</p>
      )}

      {quantidade > 0 && !confirmando && (
        <div className="flex flex-wrap items-center gap-2">
          <span aria-live="polite" className="mr-auto text-sm font-medium text-fg">
            {textoDoContador(quantidade)}
          </span>
          <Button type="button" onClick={onBaixar} disabled={ocupado}>
            <Download className="h-3.5 w-3.5" />
            {baixando ? "Gerando ZIP…" : "Baixar ZIP"}
          </Button>
          {podeExcluir && (
            <Button type="button" variant="secondary" onClick={() => setConfirmando(true)} disabled={ocupado}>
              <Trash2 className="h-3.5 w-3.5" />
              Excluir
            </Button>
          )}
          <Button type="button" variant="ghost" onClick={onLimpar} disabled={ocupado}>
            <X className="h-3.5 w-3.5" />
            Limpar seleção
          </Button>
        </div>
      )}

      {quantidade > 0 && confirmando && podeExcluir && (
        <div role="group" aria-label="Confirmação de exclusão" className="flex flex-col gap-2">
          <p className="text-sm font-semibold text-fg">{confirmacao.titulo}</p>
          <p className="text-xs text-fg-muted">{confirmacao.aviso}</p>
          {confirmacao.exigeCiencia && (
            <label className="flex items-start gap-2 text-xs text-fg">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-indigo-600"
                checked={ciente}
                onChange={(event) => setCiente(event.target.checked)}
                disabled={excluindo}
              />
              <span>{confirmacao.textoCiencia}</span>
            </label>
          )}
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void confirmarExclusao()} disabled={excluindo || (confirmacao.exigeCiencia && !ciente)}>
              {excluindo ? "Excluindo…" : "Excluir"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setConfirmando(false);
                setCiente(false);
              }}
              disabled={excluindo}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
