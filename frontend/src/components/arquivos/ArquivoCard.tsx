"use client";

import { FileText, Link2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { STATUS_LAYOUT_LABELS, STATUS_LAYOUT_TONE } from "@/lib/arquivo-status-layout";
import type { ArquivoCentral } from "@/types/arquivo";

function formatarTamanho(bytes: number | null): string | null {
  if (bytes === null) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatarData(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" }).format(new Date(iso));
}

export function ArquivoCard({ arquivo, onAbrir }: { arquivo: ArquivoCentral; onAbrir: () => void }) {
  const tamanho = formatarTamanho(arquivo.tamanhoBytes);

  return (
    <button
      type="button"
      onClick={onAbrir}
      className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-3 text-left shadow-sm transition hover:border-indigo-300 hover:shadow-md dark:hover:border-indigo-500/50"
    >
      <div className="flex h-24 items-center justify-center overflow-hidden rounded-xl bg-zinc-50 dark:bg-zinc-950/40">
        {arquivo.previewDisponivel ? (
          // eslint-disable-next-line @next/next/no-img-element -- miniatura autenticada via proxy, não um asset estático elegível a otimização do next/image
          <img
            src={`/api/backend/demandas/${arquivo.demandaId}/arquivos/${arquivo.id}/download`}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : arquivo.tipo === "link" ? (
          <Link2 className="h-8 w-8 text-zinc-300 dark:text-zinc-700" />
        ) : (
          <FileText className="h-8 w-8 text-zinc-300 dark:text-zinc-700" />
        )}
      </div>

      <p className="truncate text-sm font-medium text-fg" title={arquivo.nome}>
        {arquivo.nome}
      </p>

      <div className="flex flex-wrap items-center gap-1.5">
        <Badge tone="neutral">{arquivo.tipo === "anexo" ? "Anexo" : arquivo.tipo === "layout" ? "Layout" : "Link"}</Badge>
        {arquivo.tipo === "layout" && arquivo.statusLayout && (
          <Badge tone={STATUS_LAYOUT_TONE[arquivo.statusLayout]}>{STATUS_LAYOUT_LABELS[arquivo.statusLayout]}</Badge>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-fg-subtle">
        <span className="truncate">#{arquivo.demanda.numeroOperacional} — {arquivo.demanda.nome}</span>
      </div>
      <div className="flex items-center justify-between text-[11px] text-fg-subtle">
        <span>{arquivo.usuarioNome ?? "—"}</span>
        <span>{tamanho ? `${tamanho} · ` : ""}{formatarData(arquivo.createdAt)}</span>
      </div>
    </button>
  );
}
