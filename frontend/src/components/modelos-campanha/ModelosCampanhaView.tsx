"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Layers3 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  arquivarModeloCampanhaReal,
  atualizarModeloCampanhaReal,
  criarModeloCampanhaReal,
  listModelosCampanhaReais,
  ModeloCampanhaArquivadoConflictError,
  restaurarModeloCampanhaReal,
} from "@/lib/api-backend";
import type { ModeloCampanha, ModeloCampanhaFormDraft } from "@/types/modelo-campanha";
import { ArquivarModeloCampanhaModal } from "./ArquivarModeloCampanhaModal";
import { ModeloCampanhaFormModal } from "./ModeloCampanhaFormModal";
import { ModelosCampanhaStats } from "./ModelosCampanhaStats";
import { ModelosCampanhaTable } from "./ModelosCampanhaTable";
import { ModelosCampanhaToolbar, type FiltroStatus } from "./ModelosCampanhaToolbar";

export function ModelosCampanhaView() {
  const [modelos, setModelos] = useState<ModeloCampanha[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filtro, setFiltro] = useState<FiltroStatus>("todos");
  const [creatingModelo, setCreatingModelo] = useState(false);
  const [editingModeloId, setEditingModeloId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);
  const [arquivarModeloId, setArquivarModeloId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);

  const editingModelo = modelos.find((item) => item.id === editingModeloId);
  const arquivarModelo = modelos.find((item) => item.id === arquivarModeloId);

  // A listagem padrão do backend só exclui arquivado por padrão (ativo+inativo juntos) — pra
  // sustentar os 4 filtros (Todos/Ativos/Inativos/Arquivados) sobre os MESMOS dados sem
  // reload a cada troca de aba, buscamos os 3 status fixos em paralelo (3 chamadas, nunca
  // uma por linha) e filtramos client-side. Busca por nome vai para o backend.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const search = query.trim() || undefined;
      const [ativos, inativos, arquivados] = await Promise.all([
        listModelosCampanhaReais({ status: "ativo", search }),
        listModelosCampanhaReais({ status: "inativo", search }),
        listModelosCampanhaReais({ status: "arquivado", search }),
      ]);
      setModelos([...ativos, ...inativos, ...arquivados]);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os modelos de campanha.");
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

  const modelosFiltrados = useMemo(() => {
    if (filtro === "todos") return modelos;
    return modelos.filter((modelo) => modelo.status === filtro);
  }, [modelos, filtro]);

  async function handleSave(draft: ModeloCampanhaFormDraft, modeloId?: string) {
    setSalvando(true);
    setErroSalvar(null);
    try {
      if (!modeloId) {
        await criarModeloCampanhaReal(draft);
      } else {
        await atualizarModeloCampanhaReal(modeloId, draft);
      }
      await carregar();
      setCreatingModelo(false);
      setEditingModeloId(null);
    } catch (error) {
      if (error instanceof ModeloCampanhaArquivadoConflictError) {
        const restaurar = window.confirm(
          "Já existe um modelo de campanha arquivado com este nome. Deseja restaurá-lo em vez de criar um novo?",
        );
        if (restaurar) {
          try {
            await restaurarModeloCampanhaReal(error.modeloCampanhaArquivadoId);
            await carregar();
            setCreatingModelo(false);
            setEditingModeloId(null);
          } catch (restoreError) {
            setErroSalvar(restoreError instanceof Error ? restoreError.message : "Não foi possível restaurar o modelo.");
          }
        }
      } else {
        setErroSalvar(error instanceof Error ? error.message : "Não foi possível salvar o modelo de campanha.");
      }
    } finally {
      setSalvando(false);
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarModeloId) return;
    setArquivando(true);
    setErro(null);
    try {
      await arquivarModeloCampanhaReal(arquivarModeloId, motivo);
      await carregar();
      setArquivarModeloId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar o modelo de campanha.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(modeloId: string) {
    setErro(null);
    try {
      await restaurarModeloCampanhaReal(modeloId);
      await carregar();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar o modelo de campanha.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Layers3 className="h-5 w-5" />}
        title="Modelos de campanha"
        description="Biblioteca reutilizável de estruturas de campanha — ainda sem integração com Projeto."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {erro && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      <ModelosCampanhaStats modelos={modelos} />

      <ModelosCampanhaToolbar
        query={query}
        onQueryChange={setQuery}
        filtro={filtro}
        onFiltroChange={setFiltro}
        onNewModelo={() => setCreatingModelo(true)}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && modelos.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <ModelosCampanhaTable
          modelos={modelosFiltrados}
          onEdit={setEditingModeloId}
          onArquivar={setArquivarModeloId}
          onRestaurar={handleRestaurar}
        />
      )}

      {creatingModelo && (
        <ModeloCampanhaFormModal
          open
          salvando={salvando}
          erro={erroSalvar}
          onClose={() => {
            setCreatingModelo(false);
            setErroSalvar(null);
          }}
          onSave={handleSave}
        />
      )}

      {editingModelo && (
        <ModeloCampanhaFormModal
          key={editingModelo.id}
          open
          modelo={editingModelo}
          salvando={salvando}
          erro={erroSalvar}
          onClose={() => {
            setEditingModeloId(null);
            setErroSalvar(null);
          }}
          onSave={handleSave}
        />
      )}

      {arquivarModelo && (
        <ArquivarModeloCampanhaModal
          open
          nome={arquivarModelo.nome}
          arquivando={arquivando}
          onClose={() => setArquivarModeloId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
