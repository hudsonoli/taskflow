"use client";

import { useCallback, useEffect, useState } from "react";
import { Truck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  arquivarFornecedorReal,
  atualizarFornecedorReal,
  criarFornecedorReal,
  listFornecedoresReais,
  restaurarFornecedorReal,
} from "@/lib/api-backend";
import type {
  Fornecedor,
  FornecedorFormDraft,
  PossivelDuplicidadeFornecedor,
} from "@/types/fornecedor";
import { ArquivarFornecedorModal } from "./ArquivarFornecedorModal";
import { FornecedorFormModal } from "./FornecedorFormModal";
import { FornecedoresStats } from "./FornecedoresStats";
import { FornecedoresTable } from "./FornecedoresTable";
import { PossiveisDuplicidadesFornecedorAviso } from "./PossiveisDuplicidadesFornecedorAviso";
import { type FornecedorStatusFiltro, FornecedoresToolbar } from "./FornecedoresToolbar";

export function FornecedoresView() {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<FornecedorStatusFiltro>("todos");
  const [mostrarArquivados, setMostrarArquivados] = useState(false);
  const [creatingFornecedor, setCreatingFornecedor] = useState(false);
  const [editingFornecedorId, setEditingFornecedorId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [arquivarFornecedorId, setArquivarFornecedorId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);
  // Devolvido pela API na criação/alteração — informativo, nunca bloqueia.
  const [possiveisDuplicidades, setPossiveisDuplicidades] = useState<PossivelDuplicidadeFornecedor[]>([]);

  const editingFornecedor = fornecedores.find((item) => item.id === editingFornecedorId);
  const arquivarFornecedor = fornecedores.find((item) => item.id === arquivarFornecedorId);

  // A busca vai para o backend: assim `codigoReferencia` (F26000001), `codigoInterno` e o
  // documento sem pontuação também são pesquisáveis, não só o que está na tela. A regra de
  // interpretação do termo é única e mora em backend/app/core/busca.py.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const data = await listFornecedoresReais({
        search: query.trim() || undefined,
        status: mostrarArquivados ? "arquivado" : statusFilter === "todos" ? undefined : statusFilter,
      });
      setFornecedores(data);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os fornecedores.");
    } finally {
      setCarregando(false);
    }
  }, [query, statusFilter, mostrarArquivados]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 250); // debounce da busca
    return () => clearTimeout(timeout);
  }, [carregar]);

  async function handleSave(draft: FornecedorFormDraft, fornecedorId?: string) {
    setSalvando(true);
    setErro(null);
    try {
      const salvo = fornecedorId
        ? await atualizarFornecedorReal(fornecedorId, draft)
        : await criarFornecedorReal(draft);

      // Coincidência de nome/documento NÃO impede o cadastro — só avisa. Ver
      // docs/padrao-entidades-externas.md.
      setPossiveisDuplicidades(salvo.possiveisDuplicidades);

      await carregar();
      setCreatingFornecedor(false);
      setEditingFornecedorId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível salvar o fornecedor.");
    } finally {
      setSalvando(false);
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarFornecedorId) return;
    setArquivando(true);
    setErro(null);
    try {
      await arquivarFornecedorReal(arquivarFornecedorId, motivo);
      await carregar();
      setArquivarFornecedorId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar o fornecedor.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(fornecedorId: string) {
    setErro(null);
    try {
      await restaurarFornecedorReal(fornecedorId);
      await carregar();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar o fornecedor.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Truck className="h-5 w-5" />}
        title="Fornecedores"
        description="Gráficas, produtoras, freelancers, mídia — vincule-os aos custos das demandas."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {erro && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      {possiveisDuplicidades.length > 0 && (
        <PossiveisDuplicidadesFornecedorAviso
          duplicidades={possiveisDuplicidades}
          onDispensar={() => setPossiveisDuplicidades([])}
        />
      )}

      <FornecedoresStats fornecedores={fornecedores} />

      <FornecedoresToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onNewFornecedor={() => setCreatingFornecedor(true)}
        mostrarArquivados={mostrarArquivados}
        onMostrarArquivadosChange={setMostrarArquivados}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && fornecedores.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <FornecedoresTable
          fornecedores={fornecedores}
          onEdit={setEditingFornecedorId}
          onArquivar={setArquivarFornecedorId}
          onRestaurar={handleRestaurar}
        />
      )}

      {creatingFornecedor && (
        <FornecedorFormModal
          open
          salvando={salvando}
          onClose={() => setCreatingFornecedor(false)}
          onSave={handleSave}
        />
      )}

      {editingFornecedor && (
        <FornecedorFormModal
          key={editingFornecedor.id}
          open
          fornecedor={editingFornecedor}
          salvando={salvando}
          onClose={() => setEditingFornecedorId(null)}
          onSave={handleSave}
        />
      )}

      {arquivarFornecedor && (
        <ArquivarFornecedorModal
          open
          nome={arquivarFornecedor.nome}
          arquivando={arquivando}
          onClose={() => setArquivarFornecedorId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
