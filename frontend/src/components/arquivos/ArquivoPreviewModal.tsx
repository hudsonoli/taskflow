"use client";

import { useState } from "react";
import { Download, ExternalLink, FileText, Link2, Trash2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { useAppData } from "@/lib/AppDataContext";
import type { ArquivoCentral } from "@/types/arquivo";
import type { DemandaArquivoStatusLayout } from "@/types/demanda";

const STATUS_LAYOUT_LABELS: Record<DemandaArquivoStatusLayout, string> = {
  novo: "Novo",
  aprovado: "Aprovado",
  reprovado: "Reprovado",
  solicitar_alteracao: "Solicitar alteração",
};

const STATUS_LAYOUT_TONE: Record<DemandaArquivoStatusLayout, BadgeTone> = {
  novo: "neutral",
  aprovado: "green",
  reprovado: "red",
  solicitar_alteracao: "amber",
};

function formatarTamanho(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatarData(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(
    new Date(iso),
  );
}

/**
 * Anterior/próximo navegam só dentro de `itens` (a página já carregada) — nunca sobre
 * registros ainda não buscados, pra não fingir uma navegação que exigiria outro fetch.
 */
export function ArquivoPreviewModal({
  itens,
  indiceAtual,
  onFechar,
  onNavegar,
  onExcluir,
  podeExcluir,
}: {
  itens: ArquivoCentral[];
  indiceAtual: number | null;
  onFechar: () => void;
  onNavegar: (indice: number) => void;
  onExcluir: (arquivo: ArquivoCentral) => Promise<void>;
  podeExcluir: boolean;
}) {
  const [excluindo, setExcluindo] = useState(false);
  const { setDemandaParaAbrir } = useAppData();
  const router = useRouter();
  const arquivo = indiceAtual !== null ? itens[indiceAtual] : null;

  if (!arquivo || indiceAtual === null) return null;

  const urlDownload = `/api/backend/demandas/${arquivo.demandaId}/arquivos/${arquivo.id}/download`;

  function abrirDemanda() {
    if (!arquivo) return;
    // Mesmo padrão de NotificationBell: Tarefas lê `demandaParaAbrir` do contexto e abre a
    // Demanda na aba "atividade" (onde DemandaArquivosCard vive) ao montar.
    setDemandaParaAbrir({ demandaId: arquivo.demandaId, aba: "atividade" });
    router.push("/tarefas");
  }

  async function handleExcluir() {
    if (!arquivo) return;
    setExcluindo(true);
    try {
      await onExcluir(arquivo);
    } finally {
      setExcluindo(false);
    }
  }

  return (
    <Modal open={indiceAtual !== null} onClose={onFechar} maxWidthClassName="max-w-4xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-4 dark:border-zinc-800">
        <h2 className="truncate text-base font-semibold text-zinc-950 dark:text-zinc-50" title={arquivo.nome}>
          {arquivo.nome}
        </h2>
        <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-full p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <div className="flex min-h-[260px] items-center justify-center rounded-2xl bg-zinc-50 dark:bg-zinc-950/40">
          {arquivo.previewDisponivel ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={urlDownload} alt={arquivo.nome} className="max-h-[420px] max-w-full rounded-xl object-contain" />
          ) : arquivo.tipo === "link" ? (
            <div className="flex flex-col items-center gap-2 p-10 text-center text-zinc-400">
              <Link2 className="h-10 w-10" />
              <p className="text-sm">Link externo — abre em nova aba.</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 p-10 text-center text-zinc-400">
              <FileText className="h-10 w-10" />
              <p className="text-sm">Sem preview inline — use download.</p>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-1.5">
            <Badge tone="neutral">{arquivo.tipo === "anexo" ? "Anexo" : arquivo.tipo === "layout" ? "Layout" : "Link"}</Badge>
            {arquivo.tipo === "layout" && arquivo.statusLayout && (
              <Badge tone={STATUS_LAYOUT_TONE[arquivo.statusLayout]}>{STATUS_LAYOUT_LABELS[arquivo.statusLayout]}</Badge>
            )}
          </div>

          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-sm">
            <dt className="text-zinc-400">Tamanho</dt>
            <dd className="text-zinc-700 dark:text-zinc-200">{formatarTamanho(arquivo.tamanhoBytes)}</dd>
            <dt className="text-zinc-400">Enviado em</dt>
            <dd className="text-zinc-700 dark:text-zinc-200">{formatarData(arquivo.createdAt)}</dd>
            <dt className="text-zinc-400">Uploader</dt>
            <dd className="text-zinc-700 dark:text-zinc-200">{arquivo.usuarioNome ?? "—"}</dd>
            <dt className="text-zinc-400">Cliente</dt>
            <dd className="text-zinc-700 dark:text-zinc-200">{arquivo.clienteNome ?? "—"}</dd>
            <dt className="text-zinc-400">Projeto</dt>
            <dd className="text-zinc-700 dark:text-zinc-200">{arquivo.projetoNome ?? "—"}</dd>
            <dt className="text-zinc-400">Demanda</dt>
            <dd className="truncate text-zinc-700 dark:text-zinc-200">
              #{arquivo.demanda.numeroOperacional} — {arquivo.demanda.nome}
            </dd>
            {arquivo.descricao && (
              <>
                <dt className="text-zinc-400">Descrição</dt>
                <dd className="text-zinc-700 dark:text-zinc-200">{arquivo.descricao}</dd>
              </>
            )}
          </dl>

          <div className="mt-auto flex flex-col gap-2 border-t border-zinc-100 pt-3 dark:border-zinc-800">
            {arquivo.tipo === "link" ? (
              <a href={arquivo.url ?? "#"} target="_blank" rel="noopener noreferrer">
                <Button type="button" variant="secondary" className="w-full justify-center">
                  <ExternalLink className="h-3.5 w-3.5" />
                  Abrir link
                </Button>
              </a>
            ) : (
              <a href={urlDownload} target="_blank" rel="noopener noreferrer">
                <Button type="button" variant="secondary" className="w-full justify-center">
                  <Download className="h-3.5 w-3.5" />
                  Download
                </Button>
              </a>
            )}
            <Button type="button" variant="ghost" onClick={abrirDemanda} className="w-full justify-center">
              Abrir demanda
            </Button>
            {podeExcluir && (
              <Button type="button" variant="ghost" disabled={excluindo} onClick={() => void handleExcluir()} className="w-full justify-center text-red-600 dark:text-red-400">
                <Trash2 className="h-3.5 w-3.5" />
                {excluindo ? "Excluindo…" : "Excluir"}
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-zinc-100 pt-3 dark:border-zinc-800">
        <Button type="button" variant="ghost" disabled={indiceAtual <= 0} onClick={() => onNavegar(indiceAtual - 1)}>
          Anterior
        </Button>
        <span className="text-xs text-zinc-400">
          {indiceAtual + 1} de {itens.length}
        </span>
        <Button type="button" variant="ghost" disabled={indiceAtual >= itens.length - 1} onClick={() => onNavegar(indiceAtual + 1)}>
          Próximo
        </Button>
      </div>
    </Modal>
  );
}
