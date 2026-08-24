"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Pencil, Plus, Tag } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  arquivarCategoriaPecaReal,
  atualizarCategoriaPecaReal,
  CategoriaPecaArquivadaConflictError,
  criarCategoriaPecaReal,
  listCategoriasPecaReais,
  listPecasReais,
  restaurarCategoriaPecaReal,
} from "@/lib/api-backend";
import { invalidarDiretorioCategoriasPeca } from "@/lib/diretorioCategoriasPeca";
import type { CategoriaPeca, CategoriaPecaFormDraft } from "@/types/categoria-peca";
import { ArquivarCategoriaPecaModal } from "./ArquivarCategoriaPecaModal";
import { CategoriaPecaFormModal } from "./CategoriaPecaFormModal";

type Filtro = "todas" | "ativas" | "arquivadas";

export function CategoriasPecaView() {
  const [categorias, setCategorias] = useState<CategoriaPeca[]>([]);
  const [contagemPorCategoria, setContagemPorCategoria] = useState<Record<string, number>>({});
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroForm, setErroForm] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<Filtro>("ativas");
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [arquivandoId, setArquivandoId] = useState<string | null>(null);
  const [restaurandoId, setRestaurandoId] = useState<string | null>(null);

  const editingCategoria = categorias.find((categoria) => categoria.id === editingId);
  const arquivandoCategoria = categorias.find((categoria) => categoria.id === arquivandoId);

  // Duas chamadas fixas (ativo + arquivado), nunca uma por categoria — sem N+1. A contagem de
  // Peças por Categoria vem do mesmo GET /pecas que a aba "Peças" já usa, agregado no
  // cliente: pedir um endpoint novo só para isso não se paga no tamanho atual do catálogo.
  const buscar = useCallback(() => {
    return Promise.all([
      listCategoriasPecaReais({ status: "ativo" }),
      listCategoriasPecaReais({ status: "arquivado" }),
      listPecasReais(),
    ])
      .then(([ativas, arquivadas, pecas]) => {
        setCategorias([...ativas, ...arquivadas]);
        const contagem: Record<string, number> = {};
        pecas.forEach((peca) => {
          if (peca.categoriaId) contagem[peca.categoriaId] = (contagem[peca.categoriaId] ?? 0) + 1;
        });
        setContagemPorCategoria(contagem);
        setErro(null);
      })
      .catch((error) => {
        setErro(error instanceof Error ? error.message : "Não foi possível carregar as categorias.");
      })
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    buscar();
  }, [buscar]);

  function recarregar() {
    setCarregando(true);
    setErro(null);
    return buscar();
  }

  const categoriasFiltradas = useMemo(
    () =>
      categorias
        .filter((categoria) => {
          if (filtro === "ativas" && categoria.status !== "ativo") return false;
          if (filtro === "arquivadas" && categoria.status !== "arquivado") return false;
          if (query.trim() && !categoria.nome.toLowerCase().includes(query.trim().toLowerCase())) return false;
          return true;
        })
        .sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome)),
    [categorias, filtro, query],
  );

  async function handleSave(draft: CategoriaPecaFormDraft, categoriaId?: string) {
    setSalvando(true);
    setErroForm(null);
    try {
      if (!categoriaId) {
        await criarCategoriaPecaReal(draft);
      } else {
        await atualizarCategoriaPecaReal(categoriaId, draft);
      }
      await recarregar();
      invalidarDiretorioCategoriasPeca();
      setCreating(false);
      setEditingId(null);
    } catch (error) {
      if (error instanceof CategoriaPecaArquivadaConflictError) {
        setErroForm("Já existe uma categoria arquivada com este nome. Restaure-a em vez de criar uma nova.");
      } else {
        setErroForm(error instanceof Error ? error.message : "Não foi possível salvar a categoria.");
      }
    } finally {
      setSalvando(false);
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivandoCategoria) return;
    setSalvando(true);
    try {
      await arquivarCategoriaPecaReal(arquivandoCategoria.id, motivo);
      await recarregar();
      invalidarDiretorioCategoriasPeca();
      setArquivandoId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar a categoria.");
    } finally {
      setSalvando(false);
    }
  }

  async function handleRestaurar(categoriaId: string) {
    setRestaurandoId(categoriaId);
    try {
      await restaurarCategoriaPecaReal(categoriaId);
      await recarregar();
      invalidarDiretorioCategoriasPeca();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar a categoria.");
    } finally {
      setRestaurandoId(null);
    }
  }

  if (carregando) return <EstadoCarregando cards={0} />;
  if (erro && categorias.length === 0) return <EstadoErro mensagem={erro} onRetry={recarregar} />;

  return (
    <div className="flex flex-col gap-4">
      {erro && categorias.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="grid flex-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
            <label className="block text-sm">
              <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
                Busca
              </span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar por nome"
                className="w-full rounded-xl border border-zinc-200/80 bg-zinc-50/70 px-3 py-2.5 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
              />
            </label>

            <div className="flex items-end gap-1 rounded-xl bg-zinc-100 p-1 dark:bg-zinc-800">
              {(
                [
                  { id: "todas", label: "Todas" },
                  { id: "ativas", label: "Ativas" },
                  { id: "arquivadas", label: "Arquivadas" },
                ] as const
              ).map((opcao) => (
                <button
                  key={opcao.id}
                  type="button"
                  onClick={() => setFiltro(opcao.id)}
                  className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    filtro === opcao.id
                      ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-950 dark:text-zinc-50"
                      : "text-zinc-500 dark:text-zinc-400"
                  }`}
                >
                  {opcao.label}
                </button>
              ))}
            </div>
          </div>

          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" />
            Nova categoria
          </Button>
        </div>
      </div>

      {categoriasFiltradas.length === 0 ? (
        <EmptyState
          title="Nenhuma categoria encontrada"
          description="Ajuste a busca/filtro ou crie a primeira categoria."
          icon={<Tag size={18} />}
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
                <tr>
                  <th className="px-4 py-2.5">Nome</th>
                  <th className="px-4 py-2.5 text-right">Ordem</th>
                  <th className="px-4 py-2.5 text-right">Peças vinculadas</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {categoriasFiltradas.map((categoria) => (
                  <tr
                    key={categoria.id}
                    className={`group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 ${
                      categoria.status === "ativo" ? "" : "opacity-60"
                    }`}
                  >
                    <td className="px-4 py-3 font-semibold text-zinc-900 dark:text-zinc-100">{categoria.nome}</td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-400">
                      {categoria.ordem}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-400">
                      {contagemPorCategoria[categoria.id] ?? 0}
                    </td>
                    <td className="px-4 py-3">
                      {categoria.status === "ativo" ? (
                        <Badge tone="green">Ativa</Badge>
                      ) : (
                        <Badge tone="neutral">Arquivada</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        {categoria.status === "ativo" ? (
                          <>
                            <Button
                              variant="secondary"
                              onClick={() => setEditingId(categoria.id)}
                              className="px-3 py-1.5 text-xs"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                              Editar
                            </Button>
                            <Button
                              variant="secondary"
                              onClick={() => setArquivandoId(categoria.id)}
                              className="px-3 py-1.5 text-xs"
                            >
                              Arquivar
                            </Button>
                          </>
                        ) : (
                          <Button
                            variant="secondary"
                            disabled={restaurandoId === categoria.id}
                            onClick={() => handleRestaurar(categoria.id)}
                            className="px-3 py-1.5 text-xs"
                          >
                            {restaurandoId === categoria.id ? "Restaurando…" : "Restaurar"}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {creating && (
        <CategoriaPecaFormModal
          open
          salvando={salvando}
          erro={erroForm}
          onClose={() => {
            setCreating(false);
            setErroForm(null);
          }}
          onSave={handleSave}
        />
      )}

      {editingCategoria && (
        <CategoriaPecaFormModal
          key={editingCategoria.id}
          open
          categoria={editingCategoria}
          salvando={salvando}
          erro={erroForm}
          onClose={() => {
            setEditingId(null);
            setErroForm(null);
          }}
          onSave={handleSave}
        />
      )}

      {arquivandoCategoria && (
        <ArquivarCategoriaPecaModal
          open
          nome={arquivandoCategoria.nome}
          arquivando={salvando}
          onClose={() => setArquivandoId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
