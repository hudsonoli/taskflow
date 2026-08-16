"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, ChevronDown, ChevronUp, Circle, ListChecks, Pencil, Send, Trash2, X } from "lucide-react";
import {
  alternarConclusaoItemChecklist,
  criarItemChecklist,
  editarTextoItemChecklist,
  excluirItemChecklist,
  listChecklistDemanda,
  reordenarChecklist,
} from "@/lib/api-backend";
import type { DemandaChecklistItem } from "@/types/demanda";

/**
 * Checklist de Demanda — primeira versão (Fase 2E.3). Sem responsável, departamento, prazo
 * ou dependência entre itens: essas regras não estão definidas ainda (ver instrução da fase).
 *
 * Substitui o placeholder `RecursoIndisponivel` — checklist agora tem tabela e endpoint
 * dedicado (`/demandas/{id}/checklist`), buscado ao montar este card.
 */
export function DemandaChecklistCard({ demandaId }: { demandaId: string }) {
  const [itens, setItens] = useState<DemandaChecklistItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [novoTexto, setNovoTexto] = useState("");
  const [processandoId, setProcessandoId] = useState<string | null>(null);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [textoEdicao, setTextoEdicao] = useState("");

  useEffect(() => {
    let cancelado = false;
    listChecklistDemanda(demandaId)
      .then((dados) => {
        if (!cancelado) setItens(dados);
      })
      .catch(() => {
        if (!cancelado) setErro("Não foi possível carregar o checklist.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [demandaId]);

  async function adicionarItem() {
    const texto = novoTexto.trim();
    if (!texto) return;
    setErro(null);
    try {
      const item = await criarItemChecklist(demandaId, texto);
      setItens((atual) => [...atual, item]);
      setNovoTexto("");
    } catch {
      setErro("Não foi possível adicionar o item.");
    }
  }

  async function alternarConcluido(item: DemandaChecklistItem) {
    setProcessandoId(item.id);
    setErro(null);
    try {
      const atualizado = await alternarConclusaoItemChecklist(demandaId, item.id, !item.concluido);
      setItens((atual) => atual.map((existente) => (existente.id === item.id ? atualizado : existente)));
    } catch {
      setErro("Não foi possível atualizar o item.");
    } finally {
      setProcessandoId(null);
    }
  }

  function iniciarEdicao(item: DemandaChecklistItem) {
    setEditandoId(item.id);
    setTextoEdicao(item.texto);
  }

  async function salvarEdicao(itemId: string) {
    const texto = textoEdicao.trim();
    if (!texto) return;
    setProcessandoId(itemId);
    setErro(null);
    try {
      const atualizado = await editarTextoItemChecklist(demandaId, itemId, texto);
      setItens((atual) => atual.map((existente) => (existente.id === itemId ? atualizado : existente)));
      setEditandoId(null);
    } catch {
      setErro("Não foi possível salvar a edição.");
    } finally {
      setProcessandoId(null);
    }
  }

  async function excluir(itemId: string) {
    setProcessandoId(itemId);
    setErro(null);
    try {
      await excluirItemChecklist(demandaId, itemId);
      setItens((atual) => atual.filter((existente) => existente.id !== itemId));
    } catch {
      setErro("Não foi possível excluir o item.");
    } finally {
      setProcessandoId(null);
    }
  }

  async function mover(index: number, direcao: -1 | 1) {
    const alvo = index + direcao;
    if (alvo < 0 || alvo >= itens.length) return;
    const reordenados = [...itens];
    [reordenados[index], reordenados[alvo]] = [reordenados[alvo], reordenados[index]];
    setItens(reordenados);
    setErro(null);
    try {
      const confirmados = await reordenarChecklist(demandaId, reordenados.map((item) => item.id));
      setItens(confirmados);
    } catch {
      setErro("Não foi possível reordenar o checklist.");
      setItens(itens);
    }
  }

  const concluidos = itens.filter((item) => item.concluido).length;

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-zinc-50">
          <ListChecks className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          Checklist
        </div>
        {itens.length > 0 && (
          <span className="text-xs font-medium text-zinc-400">
            {concluidos}/{itens.length} concluídos
          </span>
        )}
      </div>

      {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}

      <div className="mt-3 flex items-center gap-2">
        <input
          value={novoTexto}
          onChange={(event) => setNovoTexto(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void adicionarItem();
            }
          }}
          placeholder="Adicionar item…"
          className="w-full rounded-xl border border-zinc-200/80 bg-zinc-50/70 px-3 py-2 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
        />
        <button
          type="button"
          onClick={() => void adicionarItem()}
          disabled={!novoTexto.trim()}
          className="inline-flex shrink-0 items-center justify-center rounded-xl bg-indigo-600 p-2.5 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Adicionar item"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-3 flex flex-col gap-1.5">
        {carregando ? (
          <p className="text-sm text-zinc-400">Carregando checklist…</p>
        ) : itens.length === 0 ? (
          <p className="text-sm text-zinc-400">Nenhum item no checklist ainda.</p>
        ) : (
          itens.map((item, index) => (
            <div
              key={item.id}
              className="flex items-center gap-2 rounded-xl border border-zinc-100 bg-zinc-50/60 px-3 py-2 dark:border-zinc-800 dark:bg-zinc-950/30"
            >
              <button
                type="button"
                onClick={() => void alternarConcluido(item)}
                disabled={processandoId === item.id}
                aria-label={item.concluido ? "Reabrir item" : "Concluir item"}
                className="shrink-0 text-zinc-400 transition hover:text-indigo-600 disabled:opacity-40 dark:hover:text-indigo-400"
              >
                {item.concluido ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                ) : (
                  <Circle className="h-5 w-5" />
                )}
              </button>

              {editandoId === item.id ? (
                <input
                  autoFocus
                  value={textoEdicao}
                  onChange={(event) => setTextoEdicao(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void salvarEdicao(item.id);
                    if (event.key === "Escape") setEditandoId(null);
                  }}
                  onBlur={() => void salvarEdicao(item.id)}
                  className="min-w-0 flex-1 rounded-lg border border-indigo-300 bg-white px-2 py-1 text-sm text-zinc-900 outline-none dark:bg-zinc-900 dark:text-zinc-100"
                />
              ) : (
                <span
                  className={`min-w-0 flex-1 truncate text-sm ${
                    item.concluido
                      ? "text-zinc-400 line-through"
                      : "text-zinc-700 dark:text-zinc-200"
                  }`}
                >
                  {item.texto}
                </span>
              )}

              <div className="flex shrink-0 items-center gap-0.5">
                <button
                  type="button"
                  onClick={() => mover(index, -1)}
                  disabled={index === 0}
                  aria-label="Mover para cima"
                  className="rounded-lg p-1 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-30 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                >
                  <ChevronUp className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => mover(index, 1)}
                  disabled={index === itens.length - 1}
                  aria-label="Mover para baixo"
                  className="rounded-lg p-1 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-30 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                >
                  <ChevronDown className="h-3.5 w-3.5" />
                </button>
                {editandoId === item.id ? (
                  <button
                    type="button"
                    onClick={() => setEditandoId(null)}
                    aria-label="Cancelar edição"
                    className="rounded-lg p-1 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => iniciarEdicao(item)}
                    aria-label="Editar texto"
                    className="rounded-lg p-1 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => void excluir(item.id)}
                  disabled={processandoId === item.id}
                  aria-label="Excluir item"
                  className="rounded-lg p-1 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
