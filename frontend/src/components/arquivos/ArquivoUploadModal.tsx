"use client";

import { useRef, useState } from "react";
import { Link2, Upload, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { criarLinkArquivoDemanda, uploadArquivoDemanda } from "@/lib/api-backend";
import type { ClienteDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import type { DemandaArquivo, DemandaArquivoTipo } from "@/types/demanda";
import type { DemandaDiretorio } from "@/types/demanda";

const EXTENSOES_ACEITAS = ".png,.jpg,.jpeg,.pdf";

/**
 * Upload central — fluxo contextual Cliente → Projeto → Demanda (Demanda obrigatória, nunca
 * um arquivo "solto" em Cliente/Projeto). Mesmo endpoint físico de sempre
 * (`POST /demandas/{id}/arquivos`) ou o de link (`POST /demandas/{id}/arquivos/link`) — este
 * modal só resolve QUAL Demanda antes de chamar o fluxo já existente.
 */
export function ArquivoUploadModal({
  open,
  onClose,
  clientes,
  projetos,
  demandas,
  onCreated,
  clienteFixoId,
  projetoFixoId,
}: {
  open: boolean;
  onClose: () => void;
  clientes: ClienteDiretorioItem[];
  projetos: ProjetoDiretorioItem[];
  demandas: DemandaDiretorio[];
  onCreated: (arquivo: DemandaArquivo) => void;
  // Aba de Cliente/Projeto: o recorte já é conhecido — não é perguntado de novo. A Demanda
  // continua obrigatória (nunca um arquivo ligado só ao Cliente/Projeto).
  clienteFixoId?: string;
  projetoFixoId?: string;
}) {
  const [clienteId, setClienteId] = useState(clienteFixoId ?? "");
  const [projetoId, setProjetoId] = useState(projetoFixoId ?? "");
  const [demandaId, setDemandaId] = useState("");
  const [tipo, setTipo] = useState<DemandaArquivoTipo>("anexo");
  const [linkTitulo, setLinkTitulo] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkDescricao, setLinkDescricao] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const projetosFiltrados = clienteId ? projetos.filter((projeto) => projeto.clienteId === clienteId) : projetos;
  const demandasFiltradas = demandas.filter(
    (demanda) => (!clienteId || demanda.clienteId === clienteId) && (!projetoId || demanda.projetoId === projetoId),
  );

  function fechar() {
    setClienteId(clienteFixoId ?? "");
    setProjetoId(projetoFixoId ?? "");
    setDemandaId("");
    setTipo("anexo");
    setLinkTitulo("");
    setLinkUrl("");
    setLinkDescricao("");
    setErro(null);
    onClose();
  }

  async function enviarArquivo(file: File) {
    if (!demandaId) return;
    setEnviando(true);
    setErro(null);
    try {
      const arquivo = await uploadArquivoDemanda(demandaId, file, tipo === "layout" ? "layout" : "anexo");
      onCreated(arquivo);
      fechar();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível enviar o arquivo.");
    } finally {
      setEnviando(false);
    }
  }

  async function enviarLink() {
    if (!demandaId || !linkTitulo.trim() || !linkUrl.trim()) return;
    setEnviando(true);
    setErro(null);
    try {
      const arquivo = await criarLinkArquivoDemanda(demandaId, {
        titulo: linkTitulo.trim(),
        url: linkUrl.trim(),
        descricao: linkDescricao.trim() || undefined,
      });
      onCreated(arquivo);
      fechar();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível adicionar o link.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal open={open} onClose={fechar} maxWidthClassName="max-w-lg">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-4 dark:border-zinc-800">
        <h2 className="text-base font-semibold text-fg">Novo arquivo</h2>
        <button type="button" onClick={fechar} aria-label="Fechar" className="rounded-full p-2 text-fg-subtle hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4 flex flex-col gap-3">
        {!clienteFixoId && !projetoFixoId && (
          <Select
            label="Cliente (opcional)"
            value={clienteId}
            onChange={(event) => {
              setClienteId(event.target.value);
              setProjetoId("");
              setDemandaId("");
            }}
            options={[{ value: "", label: "Todos" }, ...clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome }))]}
          />
        )}
        {!projetoFixoId && (
          <Select
            label="Projeto (opcional)"
            value={projetoId}
            onChange={(event) => {
              setProjetoId(event.target.value);
              setDemandaId("");
            }}
            options={[{ value: "", label: "Todos" }, ...projetosFiltrados.map((projeto) => ({ value: projeto.id, label: projeto.nome }))]}
          />
        )}
        <Select
          label="Demanda"
          value={demandaId}
          onChange={(event) => setDemandaId(event.target.value)}
          options={[
            { value: "", label: "Selecionar…" },
            ...demandasFiltradas.map((demanda) => ({ value: demanda.id, label: `#${demanda.numeroOperacional} — ${demanda.nome}` })),
          ]}
        />
        {demandasFiltradas.length === 0 && (
          <p className="text-xs text-fg-subtle">Nenhuma demanda neste recorte — um arquivo sempre pertence a uma Demanda.</p>
        )}

        <div className="mt-1 flex items-center gap-1.5">
          {(["anexo", "layout", "link"] as const).map((valor) => (
            <button
              key={valor}
              type="button"
              onClick={() => setTipo(valor)}
              className={
                tipo === valor
                  ? "rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white"
                  : "rounded-full border border-line px-3 py-1 text-xs font-semibold text-fg-muted hover:border-field-line"
              }
            >
              {valor === "anexo" ? "Anexo" : valor === "layout" ? "Layout" : "Link"}
            </button>
          ))}
        </div>

        {tipo === "link" ? (
          <div className="flex flex-col gap-2">
            <Input label="Título" value={linkTitulo} onChange={(event) => setLinkTitulo(event.target.value)} placeholder="Pasta de referência" />
            <Input label="URL" value={linkUrl} onChange={(event) => setLinkUrl(event.target.value)} placeholder="https://" />
            <Input label="Descrição (opcional)" value={linkDescricao} onChange={(event) => setLinkDescricao(event.target.value)} />
          </div>
        ) : (
          <p className="text-xs text-fg-subtle">PNG, JPG ou PDF.</p>
        )}

        {erro && <p className="text-xs text-red-600 dark:text-red-400">{erro}</p>}

        {tipo === "link" ? (
          <Button type="button" disabled={enviando || !demandaId || !linkTitulo.trim() || !linkUrl.trim()} onClick={() => void enviarLink()} className="justify-center">
            <Link2 className="h-3.5 w-3.5" />
            {enviando ? "Adicionando…" : "Adicionar link"}
          </Button>
        ) : (
          <>
            <Button type="button" disabled={enviando || !demandaId} onClick={() => inputRef.current?.click()} className="justify-center">
              <Upload className="h-3.5 w-3.5" />
              {enviando ? "Enviando…" : "Selecionar arquivo"}
            </Button>
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
          </>
        )}
      </div>
    </Modal>
  );
}
