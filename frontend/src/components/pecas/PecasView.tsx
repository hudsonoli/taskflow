"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Layers3 } from "lucide-react";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { Tabs } from "@/components/ui/Tabs";
import { atualizarPecaReal, criarPecaReal, listPecasReais } from "@/lib/api-backend";
import { podeVerDadosFinanceiros } from "@/types/usuario";
import { useAppData } from "@/lib/AppDataContext";
import type { Peca, PecaFormDraft } from "@/types/peca";
import { CategoriasPecaView } from "./CategoriasPecaView";
import { PecaFormModal } from "./PecaFormModal";
import { PecasStats } from "./PecasStats";
import { PecasTable } from "./PecasTable";
import { PecasToolbar } from "./PecasToolbar";

const abas = [
  { id: "pecas", label: "Peças" },
  { id: "categorias", label: "Categorias" },
];

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesPeca(peca: Peca, query: string) {
  const haystack = [peca.nome, peca.categoriaNome ?? "", peca.briefingPadrao].join(" ");
  return normalize(haystack).includes(normalize(query));
}

export function PecasView() {
  const { perfilAtual } = useAppData();
  const [pecas, setPecas] = useState<Peca[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [query, setQuery] = useState("");
  const [categoria, setCategoria] = useState("");
  const [onlyActive, setOnlyActive] = useState(true);
  const [creatingPeca, setCreatingPeca] = useState(false);
  const [editingPecaId, setEditingPecaId] = useState<string | null>(null);
  const [abaAtiva, setAbaAtiva] = useState("pecas");

  const editingPeca = pecas.find((peca) => peca.id === editingPecaId);
  const podeVerValor = podeVerDadosFinanceiros(perfilAtual);

  // Sem `status`: backend devolve ativo+inativo (exclui arquivado, que esta tela não mostra —
  // sem ação de arquivar na UI ainda). Filtro "só ativas" é local, pra alternar sem nova ida
  // ao servidor (catálogo é pequeno o bastante — ver item 24 da instrução).
  const buscar = useCallback(() => {
    return listPecasReais()
      .then((todas) => {
        setPecas(todas);
        setErro(null);
      })
      .catch((error) => {
        setErro(error instanceof Error ? error.message : "Não foi possível carregar as peças.");
      })
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    buscar();
  }, [buscar]);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    await buscar();
  }, [buscar]);

  const categorias = useMemo(() => {
    const unique = new Set<string>();
    pecas.forEach((peca) => peca.categoriaNome && unique.add(peca.categoriaNome));
    return Array.from(unique).sort();
  }, [pecas]);

  const filteredPecas = useMemo(
    () =>
      pecas.filter((peca) => {
        if (onlyActive && peca.status !== "ativo") return false;
        if (categoria && peca.categoriaNome !== categoria) return false;
        if (query.trim() && !matchesPeca(peca, query)) return false;
        return true;
      }),
    [pecas, query, categoria, onlyActive],
  );

  async function handleSave(draft: PecaFormDraft, pecaId?: string) {
    setSalvando(true);
    setErro(null);
    try {
      if (!pecaId) {
        await criarPecaReal(draft);
      } else {
        await atualizarPecaReal(pecaId, draft);
      }
      await carregar();
      setCreatingPeca(false);
      setEditingPecaId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível salvar a peça.");
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
              <Layers3 className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Peças</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Modelos reutilizáveis de peças/serviços — tempo estimado, valor de tabela e briefing padrão.
              </p>
            </div>
          </div>
          <Badge tone="green">Banco real</Badge>
        </div>
      </motion.div>

      <Tabs tabs={abas} activeTab={abaAtiva} onChange={setAbaAtiva} />

      {abaAtiva === "categorias" ? (
        <CategoriasPecaView />
      ) : (
        <>
          {erro && pecas.length > 0 && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
              {erro}
            </div>
          )}

          {carregando ? (
            <EstadoCarregando />
          ) : erro && pecas.length === 0 ? (
            <EstadoErro mensagem={erro} onRetry={carregar} />
          ) : (
            <>
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
            </>
          )}
        </>
      )}

      {creatingPeca && (
        <PecaFormModal open salvando={salvando} onClose={() => setCreatingPeca(false)} onSave={handleSave} />
      )}

      {editingPeca && (
        <PecaFormModal
          key={editingPeca.id}
          open
          peca={editingPeca}
          salvando={salvando}
          onClose={() => setEditingPecaId(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
