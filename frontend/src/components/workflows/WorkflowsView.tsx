"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Workflow as WorkflowIcon } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  atualizarWorkflowModeloReal,
  criarWorkflowModeloReal,
  listWorkflowModelosReais,
  restaurarWorkflowModeloReal,
  WorkflowModeloArquivadoConflictError,
} from "@/lib/api-backend";
import type { WorkflowModelo, WorkflowModeloFormDraft } from "@/types/workflow-modelo";
import { WorkflowModeloFormModal } from "./WorkflowModeloFormModal";
import { WorkflowsGrid } from "./WorkflowsGrid";
import { WorkflowsStats } from "./WorkflowsStats";
import { WorkflowsToolbar } from "./WorkflowsToolbar";

export function WorkflowsView() {
  const [workflowModelos, setWorkflowModelos] = useState<WorkflowModelo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const editingModelo = workflowModelos.find((modelo) => modelo.id === editingId);

  // A busca vai para o backend: assim `codigoReferencia` (W26000001) também é pesquisável,
  // não só o que está carregado na tela.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const data = await listWorkflowModelosReais({ search: query.trim() || undefined });
      setWorkflowModelos(data);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os workflows.");
    } finally {
      setCarregando(false);
    }
  }, [query]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 250); // debounce da busca
    return () => clearTimeout(timeout);
  }, [carregar]);

  async function handleSave(draft: WorkflowModeloFormDraft, modeloId?: string) {
    setSalvando(true);
    setErro(null);
    try {
      if (!modeloId) {
        await criarWorkflowModeloReal(draft);
      } else {
        await atualizarWorkflowModeloReal(modeloId, draft);
      }
      await carregar();
      setCreating(false);
      setEditingId(null);
    } catch (error) {
      if (error instanceof WorkflowModeloArquivadoConflictError) {
        const restaurar = window.confirm(
          "Já existe um modelo de workflow arquivado com este nome. Deseja restaurá-lo em vez de criar um novo?",
        );
        if (restaurar) {
          try {
            await restaurarWorkflowModeloReal(error.workflowModeloArquivadoId);
            await carregar();
            setCreating(false);
            setEditingId(null);
          } catch (restoreError) {
            setErro(
              restoreError instanceof Error ? restoreError.message : "Não foi possível restaurar o workflow.",
            );
          }
        }
      } else {
        setErro(error instanceof Error ? error.message : "Não foi possível salvar o workflow.");
      }
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <WorkflowIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Workflows</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Modelos de etapas padrão, aplicados no cadastro de tarefas para acelerar a montagem do fluxo de execução.
              </p>
            </div>
          </div>
          <Badge tone="green">Banco real</Badge>
        </div>
      </motion.div>

      {erro && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      <WorkflowsStats workflowModelos={workflowModelos} />

      <WorkflowsToolbar query={query} onQueryChange={setQuery} onNewWorkflow={() => setCreating(true)} />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && workflowModelos.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <WorkflowsGrid workflowModelos={workflowModelos} onEdit={setEditingId} />
      )}

      {creating && (
        <WorkflowModeloFormModal open salvando={salvando} onClose={() => setCreating(false)} onSave={handleSave} />
      )}

      {editingModelo && (
        <WorkflowModeloFormModal
          key={editingModelo.id}
          open
          modelo={editingModelo}
          salvando={salvando}
          onClose={() => setEditingId(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
