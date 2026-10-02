"use client";

import { useEffect, useRef, useState } from "react";
import { ExternalLink, FileText, Image as ImageIcon, Link2, Paperclip, Trash2, Upload } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  atualizarStatusLayoutArquivo,
  criarLinkArquivoDemanda,
  excluirArquivoDemanda,
  listArquivosDemanda,
  uploadArquivoDemanda,
  urlDownloadArquivoDemanda,
} from "@/lib/api-backend";
import type { DemandaArquivo, DemandaArquivoStatusLayout, DemandaArquivoTipo } from "@/types/demanda";

// Espelha ALLOWED_EXTENSIONS de backend/app/services/demanda_arquivo_service.py — só filtra o
// seletor nativo de arquivo (UX). O backend é quem decide de verdade: enviar uma extensão fora
// desta lista ainda é 422 no servidor, mesmo contornando este atributo.
const EXTENSOES_ACEITAS = ".png,.jpg,.jpeg,.pdf";

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

function formatarTamanho(bytes: number | null): string | null {
  if (bytes === null) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function IconeArquivo({ tipo, contentType }: { tipo: DemandaArquivoTipo; contentType: string | null }) {
  if (tipo === "link") return <Link2 className="h-4 w-4" />;
  if (contentType?.startsWith("image/")) return <ImageIcon className="h-4 w-4" />;
  return <FileText className="h-4 w-4" />;
}

/**
 * Arquivos de Demanda (Fase 2E.3; Gerenciador de Arquivos — Fase 2H.1). Mesmo endpoint de
 * sempre (`/demandas/{id}/arquivos`) — aqui o contexto (Demanda) já é conhecido, então nunca
 * pede Cliente/Projeto/Demanda de novo, só o tipo (Anexo/Layout/Link). O mesmo registro criado
 * aqui aparece no Gerenciador central (`/arquivos`), sem duplicação.
 */
export function DemandaArquivosCard({ demandaId }: { demandaId: string }) {
  const [arquivos, setArquivos] = useState<DemandaArquivo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);
  const [atualizandoStatusId, setAtualizandoStatusId] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [tipoSelecionado, setTipoSelecionado] = useState<DemandaArquivoTipo>("anexo");
  const [linkTitulo, setLinkTitulo] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkDescricao, setLinkDescricao] = useState("");
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
      const arquivo = await uploadArquivoDemanda(demandaId, file, tipoSelecionado === "layout" ? "layout" : "anexo");
      setArquivos((atual) => [arquivo, ...atual]);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível enviar o arquivo.");
    } finally {
      setEnviando(false);
    }
  }

  async function adicionarLink() {
    if (!linkTitulo.trim() || !linkUrl.trim()) return;
    setEnviando(true);
    setErro(null);
    try {
      const arquivo = await criarLinkArquivoDemanda(demandaId, {
        titulo: linkTitulo.trim(),
        url: linkUrl.trim(),
        descricao: linkDescricao.trim() || undefined,
      });
      setArquivos((atual) => [arquivo, ...atual]);
      setLinkTitulo("");
      setLinkUrl("");
      setLinkDescricao("");
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível adicionar o link.");
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

  async function alterarStatus(arquivoId: string, status: DemandaArquivoStatusLayout) {
    setAtualizandoStatusId(arquivoId);
    setErro(null);
    try {
      const atualizado = await atualizarStatusLayoutArquivo(demandaId, arquivoId, status);
      setArquivos((atual) => atual.map((existente) => (existente.id === arquivoId ? atualizado : existente)));
    } catch {
      setErro("Não foi possível atualizar o status do layout.");
    } finally {
      setAtualizandoStatusId(null);
    }
  }

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-zinc-50">
          <Paperclip className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          Arquivos
        </div>
      </div>

      <div className="mt-3 flex items-center gap-1.5">
        {(["anexo", "layout", "link"] as const).map((tipo) => (
          <button
            key={tipo}
            type="button"
            onClick={() => setTipoSelecionado(tipo)}
            className={
              tipoSelecionado === tipo
                ? "rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white"
                : "rounded-full border border-zinc-200 px-3 py-1 text-xs font-semibold text-zinc-500 hover:border-zinc-300 dark:border-zinc-800 dark:text-zinc-400"
            }
          >
            {tipo === "anexo" ? "Anexo" : tipo === "layout" ? "Layout" : "Link"}
          </button>
        ))}
      </div>

      {tipoSelecionado === "link" ? (
        <div className="mt-3 flex flex-col gap-2">
          <Input label="Título" value={linkTitulo} onChange={(event) => setLinkTitulo(event.target.value)} placeholder="Pasta de referência" />
          <Input label="URL" value={linkUrl} onChange={(event) => setLinkUrl(event.target.value)} placeholder="https://" />
          <Input
            label="Descrição (opcional)"
            value={linkDescricao}
            onChange={(event) => setLinkDescricao(event.target.value)}
          />
          <Button type="button" variant="secondary" disabled={enviando || !linkTitulo.trim() || !linkUrl.trim()} onClick={() => void adicionarLink()} className="self-start">
            <Link2 className="h-3.5 w-3.5" />
            {enviando ? "Adicionando…" : "Adicionar link"}
          </Button>
        </div>
      ) : (
        <>
          <div className="mt-3">
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              disabled={enviando}
              className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200/80 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-600 shadow-sm transition hover:border-zinc-300 hover:text-zinc-900 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:border-zinc-700 dark:hover:text-zinc-100"
            >
              <Upload className="h-3.5 w-3.5" />
              {enviando ? "Enviando…" : `Enviar ${tipoSelecionado === "layout" ? "layout" : "arquivo"}`}
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
        </>
      )}

      {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}

      <div className="mt-3 flex flex-col gap-1.5">
        {carregando ? (
          <p className="text-sm text-zinc-400">Carregando arquivos…</p>
        ) : arquivos.length === 0 ? (
          <p className="text-sm text-zinc-400">Nenhum arquivo enviado ainda.</p>
        ) : (
          arquivos.map((arquivo) => {
            const nome = arquivo.nomeOriginal ?? arquivo.titulo ?? "(sem nome)";
            const tamanho = formatarTamanho(arquivo.tamanhoBytes);
            return (
              <div
                key={arquivo.id}
                className="flex flex-col gap-1.5 rounded-xl border border-zinc-100 bg-zinc-50/60 px-3 py-2.5 dark:border-zinc-800 dark:bg-zinc-950/30"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
                    <IconeArquivo tipo={arquivo.tipo} contentType={arquivo.contentType} />
                  </span>
                  {arquivo.tipo === "link" ? (
                    <a
                      href={arquivo.url ?? "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex min-w-0 flex-1 items-center gap-1 truncate text-sm font-medium text-zinc-700 hover:text-indigo-600 dark:text-zinc-200 dark:hover:text-indigo-400"
                      title={nome}
                    >
                      <span className="truncate">{nome}</span>
                      <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                  ) : (
                    <a
                      href={urlDownloadArquivoDemanda(demandaId, arquivo.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="min-w-0 flex-1 truncate text-sm font-medium text-zinc-700 hover:text-indigo-600 dark:text-zinc-200 dark:hover:text-indigo-400"
                      title={nome}
                    >
                      {nome}
                    </a>
                  )}
                  {tamanho && <span className="shrink-0 text-xs text-zinc-400">{tamanho}</span>}
                  {arquivo.tipo === "layout" && arquivo.statusLayout && (
                    <Badge tone={STATUS_LAYOUT_TONE[arquivo.statusLayout]}>{STATUS_LAYOUT_LABELS[arquivo.statusLayout]}</Badge>
                  )}
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

                {arquivo.tipo === "layout" && (
                  <div className="max-w-[220px] pl-11">
                    <Select
                      label="Status"
                      value={arquivo.statusLayout ?? "novo"}
                      disabled={atualizandoStatusId === arquivo.id}
                      onChange={(event) => void alterarStatus(arquivo.id, event.target.value as DemandaArquivoStatusLayout)}
                      options={Object.entries(STATUS_LAYOUT_LABELS).map(([value, label]) => ({ value, label }))}
                    />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
