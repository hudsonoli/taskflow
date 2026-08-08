"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Truck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EMPRESA_PADRAO_ID, generateId } from "@/lib/fornecedores-mock";
import { useAppData } from "@/lib/AppDataContext";
import type { Fornecedor, FornecedorFormDraft } from "@/types/fornecedor";
import { FornecedorFormModal } from "./FornecedorFormModal";
import { FornecedoresStats } from "./FornecedoresStats";
import { FornecedoresTable } from "./FornecedoresTable";
import { type FornecedorStatusFiltro, FornecedoresToolbar } from "./FornecedoresToolbar";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesFornecedor(fornecedor: Fornecedor, query: string) {
  const haystack = [fornecedor.nome, fornecedor.categoria, fornecedor.documento, fornecedor.cidade, fornecedor.email].join(" ");
  return normalize(haystack).includes(normalize(query));
}

function createFornecedorFromDraft(draft: FornecedorFormDraft): Fornecedor {
  const now = new Date().toISOString();
  return {
    id: generateId("fornecedor"),
    empresaId: EMPRESA_PADRAO_ID,
    ...draft,
    createdAt: now,
    updatedAt: now,
  };
}

function updateFornecedorFromDraft(fornecedor: Fornecedor, draft: FornecedorFormDraft): Fornecedor {
  return { ...fornecedor, ...draft, updatedAt: new Date().toISOString() };
}

export function FornecedoresView() {
  const { fornecedores, setFornecedores } = useAppData();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<FornecedorStatusFiltro>("todos");
  const [creatingFornecedor, setCreatingFornecedor] = useState(false);
  const [editingFornecedorId, setEditingFornecedorId] = useState<string | null>(null);

  const editingFornecedor = fornecedores.find((fornecedor) => fornecedor.id === editingFornecedorId);

  const filteredFornecedores = useMemo(
    () =>
      fornecedores.filter((fornecedor) => {
        const statusMatches = statusFilter === "todos" || fornecedor.status === statusFilter;
        const queryMatches = query.trim() ? matchesFornecedor(fornecedor, query) : true;
        return statusMatches && queryMatches;
      }),
    [fornecedores, query, statusFilter],
  );

  function handleSave(draft: FornecedorFormDraft, fornecedorId?: string) {
    if (!fornecedorId) {
      setFornecedores((current) => [createFornecedorFromDraft(draft), ...current]);
    } else {
      setFornecedores((current) => current.map((fornecedor) => (fornecedor.id === fornecedorId ? updateFornecedorFromDraft(fornecedor, draft) : fornecedor)));
    }
    setCreatingFornecedor(false);
    setEditingFornecedorId(null);
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
              <Truck className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Fornecedores</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Gráficas, produtoras, freelancers, mídia — vincule-os aos custos das demandas.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <FornecedoresStats fornecedores={fornecedores} />

      <FornecedoresToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onNewFornecedor={() => setCreatingFornecedor(true)}
      />

      <FornecedoresTable fornecedores={filteredFornecedores} onEdit={setEditingFornecedorId} />

      {creatingFornecedor && (
        <FornecedorFormModal open onClose={() => setCreatingFornecedor(false)} onSave={handleSave} />
      )}

      {editingFornecedor && (
        <FornecedorFormModal
          key={editingFornecedor.id}
          open
          fornecedor={editingFornecedor}
          onClose={() => setEditingFornecedorId(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
