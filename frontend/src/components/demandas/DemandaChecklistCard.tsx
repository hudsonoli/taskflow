"use client";

import { useState } from "react";
import { CheckSquare, Plus, Trash2 } from "lucide-react";
import { generateId } from "@/lib/demandas-mock";
import type { Demanda, DemandaChecklistItem } from "@/types/demanda";

export function DemandaChecklistCard({ demanda, onChange }: { demanda: Demanda; onChange: (demanda: Demanda) => void }) {
  const [novoItem, setNovoItem] = useState("");
  const total = demanda.checklist.length;
  const concluidos = demanda.checklist.filter((item) => item.concluido).length;

  function updateChecklist(checklist: DemandaChecklistItem[]) {
    onChange({ ...demanda, checklist, updatedAt: new Date().toISOString() });
  }

  function adicionarItem() {
    const texto = novoItem.trim();
    if (!texto) return;
    updateChecklist([...demanda.checklist, { id: generateId("checklist"), texto, concluido: false }]);
    setNovoItem("");
  }

  function alternarItem(itemId: string) {
    updateChecklist(
      demanda.checklist.map((item) => (item.id === itemId ? { ...item, concluido: !item.concluido } : item)),
    );
  }

  function removerItem(itemId: string) {
    updateChecklist(demanda.checklist.filter((item) => item.id !== itemId));
  }

  return (
    <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/40">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CheckSquare className="h-4 w-4 text-zinc-400" />
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Checklist</p>
        </div>
        {total > 0 && (
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
            {concluidos}/{total} concluídos
          </span>
        )}
      </div>

      <div className="mt-3 space-y-1.5">
        {demanda.checklist.map((item) => (
          <label
            key={item.id}
            className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition hover:bg-white dark:hover:bg-zinc-900"
          >
            <input
              type="checkbox"
              checked={item.concluido}
              onChange={() => alternarItem(item.id)}
              className="h-4 w-4 rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500 dark:border-zinc-600"
            />
            <span
              className={
                item.concluido
                  ? "flex-1 text-sm text-zinc-400 line-through dark:text-zinc-500"
                  : "flex-1 text-sm text-zinc-700 dark:text-zinc-200"
              }
            >
              {item.texto}
            </span>
            <button
              type="button"
              onClick={() => removerItem(item.id)}
              aria-label="Remover item"
              className="text-zinc-300 transition hover:text-red-500 dark:text-zinc-600"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </label>
        ))}
        {total === 0 && <p className="px-2 py-1 text-sm text-zinc-400">Nenhum item na checklist.</p>}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <input
          value={novoItem}
          onChange={(event) => setNovoItem(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              adicionarItem();
            }
          }}
          placeholder="Adicionar item…"
          className="w-full rounded-xl border border-zinc-200 bg-white py-2 px-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        />
        <button
          type="button"
          onClick={adicionarItem}
          disabled={!novoItem.trim()}
          className="inline-flex shrink-0 items-center justify-center rounded-xl bg-indigo-600 p-2 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Adicionar item"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
