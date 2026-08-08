"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, Loader2, Paperclip, Trash2, Upload } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import {
  excluirArquivoDemanda,
  listarArquivosDemanda,
  resolveArquivoUrl,
  uploadArquivoDemanda,
  uploadArquivoFinalDemanda,
} from "@/lib/api";
import type { Demanda, DemandaArquivo } from "@/types/demanda";

const EXTENSOES_ACEITAS = [".png", ".jpg", ".jpeg", ".pdf"];
const ACCEPT = EXTENSOES_ACEITAS.join(",");

function extensaoValida(nome: string): boolean {
  const nomeLower = nome.toLowerCase();
  return EXTENSOES_ACEITAS.some((extensao) => nomeLower.endsWith(extensao));
}

function formatTamanho(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DemandaArquivosCard({ demanda, onChange }: { demanda: Demanda; onChange: (demanda: Demanda) => void }) {
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [enviandoFinal, setEnviandoFinal] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputFinalRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelado = false;
    listarArquivosDemanda(demanda.codigoInterno)
      .then((arquivos) => {
        if (!cancelado) onChange({ ...demanda, arquivos });
      })
      .catch(() => {
        // Backend indisponível — mantém os arquivos já conhecidos localmente.
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demanda.codigoInterno]);

  async function handleUpload(file: File, final: boolean) {
    setErro(null);
    if (!extensaoValida(file.name)) {
      setErro("Tipo de arquivo não permitido. Use PNG, JPG, JPEG ou PDF.");
      return;
    }

    if (final) setEnviandoFinal(true);
    else setEnviando(true);
    try {
      const arquivo = final
        ? await uploadArquivoFinalDemanda(demanda.codigoInterno, file)
        : await uploadArquivoDemanda(demanda.codigoInterno, file);
      onChange({ ...demanda, arquivos: [...demanda.arquivos, arquivo], updatedAt: new Date().toISOString() });
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Falha ao enviar arquivo");
    } finally {
      if (final) setEnviandoFinal(false);
      else setEnviando(false);
    }
  }

  async function handleRemover(arquivo: DemandaArquivo) {
    setErro(null);
    try {
      await excluirArquivoDemanda(demanda.codigoInterno, arquivo.nome, arquivo.finalDoCliente);
      onChange({
        ...demanda,
        arquivos: demanda.arquivos.filter((item) => item.nome !== arquivo.nome || item.finalDoCliente !== arquivo.finalDoCliente),
        updatedAt: new Date().toISOString(),
      });
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Falha ao excluir arquivo");
    }
  }

  return (
    <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/40">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Paperclip className="h-4 w-4 text-zinc-400" />
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Arquivos</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) void handleUpload(file, false);
            }}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={enviando}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
          >
            {enviando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
            Enviar arquivo
          </button>

          <input
            ref={inputFinalRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) void handleUpload(file, true);
            }}
          />
          <button
            type="button"
            onClick={() => inputFinalRef.current?.click()}
            disabled={enviandoFinal}
            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
          >
            {enviandoFinal ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
            Enviar entrega final
          </button>
        </div>
      </div>

      <p className="mt-2 text-xs text-zinc-400">Formatos aceitos: PNG, JPG, JPEG, PDF.</p>
      {erro && <p className="mt-2 text-xs font-medium text-red-500">{erro}</p>}

      <div className="mt-3 space-y-1.5">
        {demanda.arquivos.map((arquivo) => (
          <div
            key={`${arquivo.finalDoCliente ? "final" : "arquivo"}-${arquivo.nome}`}
            className="flex items-center gap-2.5 rounded-lg bg-white px-3 py-2 ring-1 ring-zinc-100 dark:bg-zinc-900 dark:ring-zinc-800"
          >
            <FileText className="h-4 w-4 shrink-0 text-zinc-400" />
            <a
              href={resolveArquivoUrl(arquivo.url)}
              target="_blank"
              rel="noreferrer"
              className="min-w-0 flex-1 truncate text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            >
              {arquivo.nome}
            </a>
            <span className="shrink-0 text-xs text-zinc-400">{formatTamanho(arquivo.tamanhoBytes)}</span>
            {arquivo.finalDoCliente && <Badge tone="green">Entrega final</Badge>}
            <button
              type="button"
              onClick={() => handleRemover(arquivo)}
              aria-label="Excluir arquivo"
              className="shrink-0 text-zinc-300 transition hover:text-red-500 dark:text-zinc-600"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        {demanda.arquivos.length === 0 && <p className="px-1 py-1 text-sm text-zinc-400">Nenhum arquivo enviado.</p>}
      </div>
    </div>
  );
}
