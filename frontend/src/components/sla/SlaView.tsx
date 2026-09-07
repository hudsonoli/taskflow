"use client";

import { useCallback, useEffect, useState } from "react";
import { Timer } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  arquivarSlaRegraReal,
  atualizarSlaRegraReal,
  criarSlaRegraReal,
  listSlaRegrasReais,
  restaurarSlaRegraReal,
  SlaRegraArquivadaConflictError,
} from "@/lib/api-backend";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import type { SlaRegra, SlaRegraFormDraft } from "@/types/sla";
import { ArquivarSlaRegraModal } from "./ArquivarSlaRegraModal";
import { SlaFormModal } from "./SlaFormModal";
import { SlaStats } from "./SlaStats";
import { SlaTable } from "./SlaTable";
import { SlaToolbar, type FiltroStatus } from "./SlaToolbar";

export function SlaView() {
  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();

  const [regras, setRegras] = useState<SlaRegra[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filtro, setFiltro] = useState<FiltroStatus>("todos");
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);
  const [arquivarId, setArquivarId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);

  const editingRegra = regras.find((regra) => regra.id === editingId);
  const arquivarRegra = regras.find((regra) => regra.id === arquivarId);

  // GET /slas sem `status` OCULTA arquivado (mesmo comportamento de /modelos-campanha) — não
  // existe forma de trazer os 3 status numa única chamada. Pra "Todos" sustentar as 4 abas
  // sem reload a cada troca, buscamos os 3 status fixos em paralelo e mesclamos client-side;
  // com um status específico selecionado, uma única chamada já filtrada no backend. Busca por
  // nome/descrição vai para o backend nos dois casos.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const search = query.trim() || undefined;
      if (filtro === "todos") {
        const [ativas, inativas, arquivadas] = await Promise.all([
          listSlaRegrasReais({ status: "ativo", search }),
          listSlaRegrasReais({ status: "inativo", search }),
          listSlaRegrasReais({ status: "arquivado", search }),
        ]);
        setRegras([...ativas, ...inativas, ...arquivadas]);
      } else {
        setRegras(await listSlaRegrasReais({ status: filtro, search }));
      }
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar as regras de SLA.");
    } finally {
      setCarregando(false);
    }
  }, [query, filtro]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 250); // debounce da busca — mesmo padrão de ModelosCampanhaView
    return () => clearTimeout(timeout);
  }, [carregar]);

  async function handleSave(draft: SlaRegraFormDraft, slaRegraId?: string) {
    setSalvando(true);
    setErroSalvar(null);
    try {
      if (!slaRegraId) {
        await criarSlaRegraReal(draft);
      } else {
        await atualizarSlaRegraReal(slaRegraId, draft);
      }
      await carregar();
      setCreating(false);
      setEditingId(null);
    } catch (error) {
      if (error instanceof SlaRegraArquivadaConflictError) {
        setErroSalvar("Já existe uma regra de SLA arquivada com este nome. Restaure-a em vez de criar uma nova.");
      } else {
        setErroSalvar(error instanceof Error ? error.message : "Não foi possível salvar a regra de SLA.");
      }
    } finally {
      setSalvando(false);
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarId) return;
    setArquivando(true);
    setErro(null);
    try {
      await arquivarSlaRegraReal(arquivarId, motivo);
      await carregar();
      setArquivarId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar a regra de SLA.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(slaRegraId: string) {
    setErro(null);
    try {
      await restaurarSlaRegraReal(slaRegraId);
      await carregar();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar a regra de SLA.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Timer className="h-5 w-5" />}
        title="SLA"
        description="Prazos de resposta e resolução, por prioridade, departamento ou cliente."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {erro && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      <SlaStats slaRegras={regras} />

      <SlaToolbar query={query} onQueryChange={setQuery} filtro={filtro} onFiltroChange={setFiltro} onNewRegra={() => setCreating(true)} />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && regras.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <SlaTable
          slaRegras={regras}
          departamentos={departamentos}
          clientes={clientes}
          onEdit={setEditingId}
          onArquivar={setArquivarId}
          onRestaurar={handleRestaurar}
        />
      )}

      {creating && (
        <SlaFormModal
          open
          departamentos={departamentos}
          clientes={clientes}
          salvando={salvando}
          erro={erroSalvar}
          onClose={() => {
            setCreating(false);
            setErroSalvar(null);
          }}
          onSave={handleSave}
        />
      )}

      {editingRegra && (
        <SlaFormModal
          key={editingRegra.id}
          open
          regra={editingRegra}
          departamentos={departamentos}
          clientes={clientes}
          salvando={salvando}
          erro={erroSalvar}
          onClose={() => {
            setEditingId(null);
            setErroSalvar(null);
          }}
          onSave={handleSave}
        />
      )}

      {arquivarRegra && (
        <ArquivarSlaRegraModal
          open
          nome={arquivarRegra.nome}
          arquivando={arquivando}
          onClose={() => setArquivarId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
