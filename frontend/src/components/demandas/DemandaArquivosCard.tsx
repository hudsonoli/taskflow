"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, Image as ImageIcon, Paperclip, Trash2, Upload } from "lucide-react";
import {
  excluirArquivoDemanda,
  listArquivosDemanda,
  uploadArquivoDemanda,
  urlDownloadArquivoDemanda,
} from "@/lib/api-backend";
import type { DemandaArquivo } from "@/types/demanda";

// Espelha ALLOWED_EXTENSIONS de backend/app/services/demanda_arquivo_service.py — só filtra o
// seletor nativo de arquivo (UX). O backend é quem decide de verdade: enviar uma extensão fora
// desta lista ainda é 422 no servidor, mesmo contornando este atributo.
const EXTENSOES_ACEITAS = ".png,.jpg,.jpeg,.pdf";

function formatarTamanho(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function IconeArquivo({ contentType }: { contentType: string | null }) {
  if (contentType?.startsWith("image/")) {
    return <ImageIcon className="h-4 w-4" />;
  }
  return <FileText className="h-4 w-4" />;
}

/**
 * Arquivos de Demanda — primeira versão real (Fase 2E.3). Metadado tem tabela própria e
 * endpoint dedicado (`/demandas/{id}/arquivos`); download exige o endpoint autenticado —
 * nunca URL estática (ver docs/pendencias-arquiteturais.md, item 9, resolvido nesta fase).
 */
export function DemandaArquivosCard({ demandaId }: { demandaId: string }) {
  const [arquivos, setArquivos] = useState<DemandaArquivo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelado = false;
    listArquivosDemanda(demandaId)
      .then((dados) => {
        if (!cancelado) setArquivos(dados);
      })
      .catch(() => {
        if (!cancelado) setErro("Não foi possível carregar os arquivos.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [demandaId]);

  async function enviarArquivo(file: File) {
    setEnviando(true);
    setErro(null);
    try {
      const arquivo = await uploadArquivoDemanda(demandaId, file);
      setArquivos((atual) => [arquivo, ...atual]);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível enviar o arquivo.");
    } finally {
      setEnviando(false);
    }
  }

  async function excluir(arquivoId: string) {
    setExcluindoId(arquivoId);
    setErro(null);
    try {
      await excluirArquivoDemanda(demandaId, arquivoId);
      setArquivos((atual) => atual.filter((existente) => existente.id !== arquivoId));
    } catch {
      setErro("Não foi possível excluir o arquivo.");
    } finally {
      setExcluindoId(null);
    }
  }

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-zinc-50">
          <Paperclip className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          Arquivos
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={enviando}
          className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200/80 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-600 shadow-sm transition hover:border-zinc-300 hover:text-zinc-900 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:border-zinc-700 dark:hover:text-zinc-100"
        >
          <Upload className="h-3.5 w-3.5" />
          {enviando ? "Enviando…" : "Enviar arquivo"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={EXTENSOES_ACEITAS}
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) void enviarArquivo(file);
          }}
        />
      </div>

      <p className="mt-1.5 text-xs text-zinc-400">PNG, JPG ou PDF.</p>

      {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}

      <div className="mt-3 flex flex-col gap-1.5">
        {carregando ? (
          <p className="text-sm text-zinc-400">Carregando arquivos…</p>
        ) : arquivos.length === 0 ? (
          <p className="text-sm text-zinc-400">Nenhum arquivo enviado ainda.</p>
        ) : (
          arquivos.map((arquivo) => (
            <div
              key={arquivo.id}
              className="flex items-center gap-3 rounded-xl border border-zinc-100 bg-zinc-50/60 px-3 py-2.5 dark:border-zinc-800 dark:bg-zinc-950/30"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
                <IconeArquivo contentType={arquivo.contentType} />
              </span>
              <a
                href={urlDownloadArquivoDemanda(demandaId, arquivo.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-0 flex-1 truncate text-sm font-medium text-zinc-700 hover:text-indigo-600 dark:text-zinc-200 dark:hover:text-indigo-400"
              >
                {arquivo.nomeOriginal}
              </a>
              <span className="shrink-0 text-xs text-zinc-400">{formatarTamanho(arquivo.tamanhoBytes)}</span>
              <button
                type="button"
                onClick={() => void excluir(arquivo.id)}
                disabled={excluindoId === arquivo.id}
                aria-label="Excluir arquivo"
                className="shrink-0 rounded-lg p-1 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-500/10 dark:hover:text-red-400"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
