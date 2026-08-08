"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Timer } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EMPRESA_PADRAO_ID, generateId } from "@/lib/sla-mock";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import type { SlaRegra, SlaRegraFormDraft } from "@/types/sla";
import { SlaFormModal } from "./SlaFormModal";
import { SlaStats } from "./SlaStats";
import { SlaTable } from "./SlaTable";
import { SlaToolbar } from "./SlaToolbar";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesRegra(regra: SlaRegra, query: string) {
  return normalize([regra.nome, regra.descricao].join(" ")).includes(normalize(query));
}

function createRegraFromDraft(draft: SlaRegraFormDraft): SlaRegra {
  const now = new Date().toISOString();
  return {
    id: generateId("sla"),
    empresaId: EMPRESA_PADRAO_ID,
    ...draft,
    createdAt: now,
    updatedAt: now,
  };
}

function updateRegraFromDraft(regra: SlaRegra, draft: SlaRegraFormDraft): SlaRegra {
  return { ...regra, ...draft, updatedAt: new Date().toISOString() };
}

export function SlaView() {
  const { slaRegras, setSlaRegras, clientes } = useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const editingRegra = slaRegras.find((regra) => regra.id === editingId);

  const filteredRegras = useMemo(
    () => slaRegras.filter((regra) => (query.trim() ? matchesRegra(regra, query) : true)),
    [slaRegras, query],
  );

  function handleSave(draft: SlaRegraFormDraft, slaRegraId?: string) {
    if (!slaRegraId) {
      setSlaRegras((current) => [createRegraFromDraft(draft), ...current]);
    } else {
      setSlaRegras((current) => current.map((regra) => (regra.id === slaRegraId ? updateRegraFromDraft(regra, draft) : regra)));
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
              <Timer className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">SLA</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Prazos de resposta e resolução, por prioridade, departamento ou cliente.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <SlaStats slaRegras={slaRegras} />

      <SlaToolbar query={query} onQueryChange={setQuery} onNewRegra={() => setCreating(true)} />

      <SlaTable slaRegras={filteredRegras} departamentos={departamentos} clientes={clientes} onEdit={setEditingId} />

      {creating && (
        <SlaFormModal open departamentos={departamentos} clientes={clientes} onClose={() => setCreating(false)} onSave={handleSave} />
      )}

      {editingRegra && (
        <SlaFormModal
          key={editingRegra.id}
          open
          regra={editingRegra}
          departamentos={departamentos}
          clientes={clientes}
          onClose={() => setEditingId(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
