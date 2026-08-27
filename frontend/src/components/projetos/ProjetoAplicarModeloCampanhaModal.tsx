"use client";

import { useState } from "react";
import { Layers3, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { useDiretorioModelosCampanha } from "@/lib/diretorioModelosCampanha";

/**
 * Seletor de Modelo de Campanha para aplicar/substituir num Projeto (Fase 2G.5C3). Mesmo
 * modal serve os dois casos — a diferença é só o aviso de substituição, que só aparece
 * quando o Projeto já tem um snapshot (`temSnapshotAtual`): reaplicar substitui os itens
 * atuais por inteiro, então o usuário precisa confirmar isso explicitamente antes do
 * `POST /aplicar` (o backend não pede uma flag "confirmar", a confirmação é só de UI).
 */
export function ProjetoAplicarModeloCampanhaModal({
  open,
  temSnapshotAtual,
  aplicando,
  erro,
  onClose,
  onConfirm,
}: {
  open: boolean;
  temSnapshotAtual: boolean;
  aplicando: boolean;
  erro?: string | null;
  onClose: () => void;
  onConfirm: (modeloCampanhaId: string) => void;
}) {
  const { modelosCampanha, carregando, erro: erroDiretorio } = useDiretorioModelosCampanha();
  const [modeloSelecionadoId, setModeloSelecionadoId] = useState("");

  const podeConfirmar = modeloSelecionadoId.length > 0 && !aplicando;

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-md">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Layers3 className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-zinc-950 dark:text-zinc-50">
              {temSnapshotAtual ? "Substituir Modelo de Campanha" : "Aplicar Modelo de Campanha"}
            </h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              {temSnapshotAtual
                ? "Isso substituirá todos os itens atuais deste Modelo de Campanha no Projeto. Alterações feitas nos itens atuais serão perdidas — a biblioteca original não é afetada."
                : "Os itens do Modelo escolhido serão copiados para este Projeto e podem ser editados livremente depois."}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4">
        <Select
          label="Modelo de campanha"
          value={modeloSelecionadoId}
          disabled={carregando || Boolean(erroDiretorio)}
          onChange={(event) => setModeloSelecionadoId(event.target.value)}
          options={[
            { value: "", label: carregando ? "Carregando…" : "Selecionar um modelo…" },
            ...modelosCampanha.map((modelo) => ({ value: modelo.id, label: modelo.nome })),
          ]}
        />
        {erroDiretorio && (
          <p className="mt-1 text-xs text-red-500 dark:text-red-400">Não foi possível carregar os modelos de campanha.</p>
        )}
        {!carregando && !erroDiretorio && modelosCampanha.length === 0 && (
          <p className="mt-1 text-xs text-zinc-400">Nenhum modelo de campanha ativo na biblioteca.</p>
        )}
      </div>

      {erro && (
        <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </p>
      )}

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose} disabled={aplicando}>
          Cancelar
        </Button>
        <Button type="button" disabled={!podeConfirmar} onClick={() => onConfirm(modeloSelecionadoId)}>
          {aplicando ? "Aplicando…" : temSnapshotAtual ? "Substituir Modelo" : "Aplicar Modelo"}
        </Button>
      </div>
    </Modal>
  );
}
