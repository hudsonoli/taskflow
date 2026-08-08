"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Layers3 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EMPRESA_PADRAO_ID, generateId } from "@/lib/pecas-mock";
import { useAppData } from "@/lib/AppDataContext";
import { podeVerDadosFinanceiros } from "@/types/usuario";
import type { Peca, PecaFormDraft } from "@/types/peca";
import { PecaFormModal } from "./PecaFormModal";
import { PecasStats } from "./PecasStats";
import { PecasTable } from "./PecasTable";
import { PecasToolbar } from "./PecasToolbar";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesPeca(peca: Peca, query: string) {
  const haystack = [peca.nome, peca.categoria, peca.briefingPadrao].join(" ");
  return normalize(haystack).includes(normalize(query));
}

function createPecaFromDraft(draft: PecaFormDraft): Peca {
  const now = new Date().toISOString();
  return {
    id: generateId("peca"),
    empresaId: EMPRESA_PADRAO_ID,
    ...draft,
    createdAt: now,
    updatedAt: now,
  };
}

function updatePecaFromDraft(peca: Peca, draft: PecaFormDraft): Peca {
  return { ...peca, ...draft, updatedAt: new Date().toISOString() };
}

export function PecasView() {
  const { pecas, setPecas, perfilAtual } = useAppData();
  const [query, setQuery] = useState("");
  const [categoria, setCategoria] = useState("");
  const [onlyActive, setOnlyActive] = useState(true);
  const [creatingPeca, setCreatingPeca] = useState(false);
  const [editingPecaId, setEditingPecaId] = useState<string | null>(null);

  const editingPeca = pecas.find((peca) => peca.id === editingPecaId);
  const podeVerValor = podeVerDadosFinanceiros(perfilAtual);

  const categorias = useMemo(() => {
    const unique = new Set<string>();
    pecas.forEach((peca) => peca.categoria && unique.add(peca.categoria));
    return Array.from(unique).sort();
  }, [pecas]);

  const filteredPecas = useMemo(
    () =>
      pecas.filter((peca) => {
        if (onlyActive && !peca.ativa) return false;
        if (categoria && peca.categoria !== categoria) return false;
        if (query.trim() && !matchesPeca(peca, query)) return false;
        return true;
      }),
    [pecas, query, categoria, onlyActive],
  );

  function handleSave(draft: PecaFormDraft, pecaId?: string) {
    if (!pecaId) {
      setPecas((current) => [createPecaFromDraft(draft), ...current]);
    } else {
      setPecas((current) => current.map((peca) => (peca.id === pecaId ? updatePecaFromDraft(peca, draft) : peca)));
    }
    setCreatingPeca(false);
    setEditingPecaId(null);
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
              <Layers3 className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Peças</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Modelos reutilizáveis de peças/serviços — tempo estimado, valor de tabela e briefing padrão.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <PecasStats pecas={pecas} />

      <PecasToolbar
        query={query}
        onQueryChange={setQuery}
        categoria={categoria}
        onCategoriaChange={setCategoria}
        categorias={categorias}
        onlyActive={onlyActive}
        onToggleOnlyActive={() => setOnlyActive((current) => !current)}
        onNewPeca={() => setCreatingPeca(true)}
      />

      <PecasTable pecas={filteredPecas} podeVerValor={podeVerValor} onEdit={setEditingPecaId} />

      {creatingPeca && <PecaFormModal open onClose={() => setCreatingPeca(false)} onSave={handleSave} />}

      {editingPeca && (
        <PecaFormModal key={editingPeca.id} open peca={editingPeca} onClose={() => setEditingPecaId(null)} onSave={handleSave} />
      )}
    </div>
  );
}
