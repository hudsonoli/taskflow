"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ClipboardList } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  arquivarTipoTarefaReal,
  atualizarTipoTarefaReal,
  criarTipoTarefaReal,
  listTiposTarefaReais,
  restaurarTipoTarefaReal,
  TipoTarefaArquivadoConflictError,
} from "@/lib/api-backend";
import { invalidarDiretorioTiposTarefa } from "@/lib/diretorioTiposTarefa";
import type { TipoTarefa, TipoTarefaFormDraft } from "@/types/tipo-tarefa";
import { ArquivarTipoTarefaModal } from "./ArquivarTipoTarefaModal";
import { TipoTarefaFormModal } from "./TipoTarefaFormModal";
import { TiposTarefaTable } from "./TiposTarefaTable";
import { TiposTarefaToolbar } from "./TiposTarefaToolbar";

export function TiposTarefaView() {
  const [tiposTarefa, setTiposTarefa] = useState<TipoTarefa[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [mostrarArquivados, setMostrarArquivados] = useState(false);
  const [creatingTipoTarefa, setCreatingTipoTarefa] = useState(false);
  const [editingTipoTarefaId, setEditingTipoTarefaId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [arquivarTipoTarefaId, setArquivarTipoTarefaId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);

  const editingTipoTarefa = tiposTarefa.find((item) => item.id === editingTipoTarefaId);
  const arquivarTipoTarefaAlvo = tiposTarefa.find((item) => item.id === arquivarTipoTarefaId);

  // A busca vai para o backend — mesmo padrão de DepartamentosView.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const data = await listTiposTarefaReais({
        search: query.trim() || undefined,
        status: mostrarArquivados ? "arquivado" : undefined,
      });
      setTiposTarefa(data);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os tipos de tarefa.");
    } finally {
      setCarregando(false);
    }
  }, [query, mostrarArquivados]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 250); // debounce da busca
    return () => clearTimeout(timeout);
  }, [carregar]);

  const filteredTiposTarefa = useMemo(() => tiposTarefa, [tiposTarefa]);

  async function handleSave(draft: TipoTarefaFormDraft, tipoTarefaId?: string) {
    setSalvando(true);
    setErro(null);
    try {
      if (!tipoTarefaId) {
        await criarTipoTarefaReal(draft);
      } else {
        await atualizarTipoTarefaReal(tipoTarefaId, draft);
      }
      await carregar();
      invalidarDiretorioTiposTarefa();
      setCreatingTipoTarefa(false);
      setEditingTipoTarefaId(null);
    } catch (error) {
      if (error instanceof TipoTarefaArquivadoConflictError) {
        const restaurar = window.confirm(
          "Já existe um tipo de tarefa arquivado com este nome. Deseja restaurá-lo em vez de criar um novo?",
        );
        if (restaurar) {
          try {
            await restaurarTipoTarefaReal(error.tipoTarefaArquivadoId);
            await carregar();
            invalidarDiretorioTiposTarefa();
            setCreatingTipoTarefa(false);
            setEditingTipoTarefaId(null);
          } catch (restoreError) {
            setErro(
              restoreError instanceof Error ? restoreError.message : "Não foi possível restaurar o tipo de tarefa.",
            );
          }
        }
      } else {
        setErro(error instanceof Error ? error.message : "Não foi possível salvar o tipo de tarefa.");
      }
    } finally {
      setSalvando(false);
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarTipoTarefaId) return;
    setArquivando(true);
    setErro(null);
    try {
      await arquivarTipoTarefaReal(arquivarTipoTarefaId, motivo);
      await carregar();
      invalidarDiretorioTiposTarefa();
      setArquivarTipoTarefaId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar o tipo de tarefa.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(tipoTarefaId: string) {
    setErro(null);
    try {
      await restaurarTipoTarefaReal(tipoTarefaId);
      await carregar();
      invalidarDiretorioTiposTarefa();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar o tipo de tarefa.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<ClipboardList className="h-5 w-5" />}
        title="Tipos de tarefa"
        description="Categorias de demanda usadas nos modelos de campanha."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {erro && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      <TiposTarefaToolbar
        query={query}
        onQueryChange={setQuery}
        onNewTipoTarefa={() => setCreatingTipoTarefa(true)}
        mostrarArquivados={mostrarArquivados}
        onMostrarArquivadosChange={setMostrarArquivados}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && tiposTarefa.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <TiposTarefaTable
          tiposTarefa={filteredTiposTarefa}
          onEdit={setEditingTipoTarefaId}
          onArquivar={setArquivarTipoTarefaId}
          onRestaurar={handleRestaurar}
        />
      )}

      {creatingTipoTarefa && (
        <TipoTarefaFormModal open salvando={salvando} onClose={() => setCreatingTipoTarefa(false)} onSave={handleSave} />
      )}

      {editingTipoTarefa && (
        <TipoTarefaFormModal
          key={editingTipoTarefa.id}
          open
          tipoTarefa={editingTipoTarefa}
          salvando={salvando}
          onClose={() => setEditingTipoTarefaId(null)}
          onSave={handleSave}
        />
      )}

      {arquivarTipoTarefaAlvo && (
        <ArquivarTipoTarefaModal
          open
          nome={arquivarTipoTarefaAlvo.nome}
          arquivando={arquivando}
          onClose={() => setArquivarTipoTarefaId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
