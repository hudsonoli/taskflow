"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Workflow as WorkflowIcon } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EMPRESA_PADRAO_ID, generateId } from "@/lib/workflow-modelos-mock";
import { useAppData } from "@/lib/AppDataContext";
import type { WorkflowModelo, WorkflowModeloFormDraft } from "@/types/workflow-modelo";
import { WorkflowModeloFormModal } from "./WorkflowModeloFormModal";
import { WorkflowsGrid } from "./WorkflowsGrid";
import { WorkflowsStats } from "./WorkflowsStats";
import { WorkflowsToolbar } from "./WorkflowsToolbar";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesModelo(modelo: WorkflowModelo, query: string) {
  return normalize(modelo.nome).includes(normalize(query));
}

function createModeloFromDraft(draft: WorkflowModeloFormDraft): WorkflowModelo {
  const now = new Date().toISOString();
  return {
    id: generateId("workflow-modelo"),
    empresaId: EMPRESA_PADRAO_ID,
    ...draft,
    createdAt: now,
    updatedAt: now,
  };
}

function updateModeloFromDraft(modelo: WorkflowModelo, draft: WorkflowModeloFormDraft): WorkflowModelo {
  return { ...modelo, ...draft, updatedAt: new Date().toISOString() };
}

export function WorkflowsView() {
  const { workflowModelos, setWorkflowModelos } = useAppData();
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const editingModelo = workflowModelos.find((modelo) => modelo.id === editingId);

  const filteredModelos = useMemo(
    () => workflowModelos.filter((modelo) => (query.trim() ? matchesModelo(modelo, query) : true)),
    [workflowModelos, query],
  );

  function handleSave(draft: WorkflowModeloFormDraft, modeloId?: string) {
    if (!modeloId) {
      setWorkflowModelos((current) => [createModeloFromDraft(draft), ...current]);
    } else {
      setWorkflowModelos((current) => current.map((modelo) => (modelo.id === modeloId ? updateModeloFromDraft(modelo, draft) : modelo)));
    }
    setCreating(false);
    setEditingId(null);
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
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <WorkflowsStats workflowModelos={workflowModelos} />

      <WorkflowsToolbar query={query} onQueryChange={setQuery} onNewWorkflow={() => setCreating(true)} />

      <WorkflowsGrid workflowModelos={filteredModelos} onEdit={setEditingId} />

      {creating && <WorkflowModeloFormModal open onClose={() => setCreating(false)} onSave={handleSave} />}

      {editingModelo && (
        <WorkflowModeloFormModal
          key={editingModelo.id}
          open
          modelo={editingModelo}
          onClose={() => setEditingId(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
