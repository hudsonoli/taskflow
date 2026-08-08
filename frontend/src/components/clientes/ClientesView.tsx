"use client";

import { useCallback, useEffect, useState } from "react";
import { Building2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  arquivarClienteReal,
  atualizarClienteReal,
  criarClienteReal,
  listClientesReais,
  restaurarClienteReal,
} from "@/lib/api-backend";
import { invalidarDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioGruposCliente } from "@/lib/diretorioGruposCliente";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { useAppData } from "@/lib/AppDataContext";
import type { Cliente, ClienteFormDraft, PossivelDuplicidadeCliente } from "@/types/cliente";
import { ArquivarClienteModal } from "./ArquivarClienteModal";
import { ClienteFormModal } from "./ClienteFormModal";
import { ClientesStats } from "./ClientesStats";
import { ClientesTable } from "./ClientesTable";
import { PossiveisDuplicidadesAviso } from "./PossiveisDuplicidadesAviso";
import { type ClienteStatusFiltro, ClientesToolbar } from "./ClientesToolbar";

export function ClientesView() {
  const { perfilAtual } = useAppData();
  const { grupos: gruposCliente } = useDiretorioGruposCliente();
  const { usuarios } = useDiretorioUsuarios();

  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<ClienteStatusFiltro>("todos");
  const [mostrarArquivados, setMostrarArquivados] = useState(false);
  const [creatingCliente, setCreatingCliente] = useState(false);
  const [editingClienteId, setEditingClienteId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [arquivarClienteId, setArquivarClienteId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);
  // Devolvido pela API na criação/alteração — informativo, nunca bloqueia.
  const [possiveisDuplicidades, setPossiveisDuplicidades] = useState<PossivelDuplicidadeCliente[]>([]);

  const editingCliente = clientes.find((item) => item.id === editingClienteId);
  const arquivarCliente = clientes.find((item) => item.id === arquivarClienteId);

  // A busca vai para o backend: assim `codigoReferencia` (C26000001), `codigoInterno` e o
  // documento sem pontuação também são pesquisáveis, não só o que está na tela.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const data = await listClientesReais({
        search: query.trim() || undefined,
        status: mostrarArquivados ? "arquivado" : statusFilter === "todos" ? undefined : statusFilter,
      });
      setClientes(data);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os clientes.");
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

  async function handleSave(draft: ClienteFormDraft, clienteId?: string) {
    setSalvando(true);
    setErro(null);
    try {
      const salvo = clienteId
        ? await atualizarClienteReal(clienteId, draft)
        : await criarClienteReal(draft);

      // Coincidência de nome/documento NÃO impede o cadastro — só avisa. Ver
      // docs/padrao-entidades-externas.md.
      setPossiveisDuplicidades(salvo.possiveisDuplicidades);

      await carregar();
      invalidarDiretorioClientes();
      setCreatingCliente(false);
      setEditingClienteId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível salvar o cliente.");
    } finally {
      setSalvando(false);
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarClienteId) return;
    setArquivando(true);
    setErro(null);
    try {
      await arquivarClienteReal(arquivarClienteId, motivo);
      await carregar();
      invalidarDiretorioClientes();
      setArquivarClienteId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar o cliente.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(clienteId: string) {
    setErro(null);
    try {
      await restaurarClienteReal(clienteId);
      await carregar();
      invalidarDiretorioClientes();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar o cliente.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Building2 className="h-5 w-5" />}
        title="Clientes"
        description="Cadastro de clientes usados por projetos e demandas."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {erro && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      {possiveisDuplicidades.length > 0 && (
        <PossiveisDuplicidadesAviso
          duplicidades={possiveisDuplicidades}
          onDispensar={() => setPossiveisDuplicidades([])}
        />
      )}

      <ClientesStats clientes={clientes} perfilAtual={perfilAtual} />

      <ClientesToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onNewCliente={() => setCreatingCliente(true)}
        mostrarArquivados={mostrarArquivados}
        onMostrarArquivadosChange={setMostrarArquivados}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && clientes.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <ClientesTable
          clientes={clientes}
          grupos={gruposCliente}
          usuarios={usuarios}
          onEdit={setEditingClienteId}
          onArquivar={setArquivarClienteId}
          onRestaurar={handleRestaurar}
        />
      )}

      {creatingCliente && (
        <ClienteFormModal
          open
          grupos={gruposCliente}
          usuarios={usuarios}
          salvando={salvando}
          onClose={() => setCreatingCliente(false)}
          onSave={handleSave}
        />
      )}

      {editingCliente && (
        <ClienteFormModal
          key={editingCliente.id}
          open
          cliente={editingCliente}
          grupos={gruposCliente}
          usuarios={usuarios}
          salvando={salvando}
          onClose={() => setEditingClienteId(null)}
          onSave={handleSave}
        />
      )}

      {arquivarCliente && (
        <ArquivarClienteModal
          open
          nome={arquivarCliente.nome}
          arquivando={arquivando}
          onClose={() => setArquivarClienteId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
