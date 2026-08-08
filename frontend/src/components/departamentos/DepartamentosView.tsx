"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Building2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  arquivarDepartamentoReal,
  atualizarDepartamentoReal,
  criarDepartamentoReal,
  DepartamentoArquivadoConflictError,
  listDepartamentosReais,
  restaurarDepartamentoReal,
} from "@/lib/api-backend";
import { invalidarDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import type { Departamento, DepartamentoFormDraft } from "@/types/departamento";
import { ArquivarDepartamentoModal } from "./ArquivarDepartamentoModal";
import { DepartamentoFormModal } from "./DepartamentoFormModal";
import { DepartamentosStats } from "./DepartamentosStats";
import { DepartamentosTable } from "./DepartamentosTable";
import { DepartamentosToolbar } from "./DepartamentosToolbar";

export function DepartamentosView() {
  const { usuarios } = useDiretorioUsuarios();
  const [departamentos, setDepartamentos] = useState<Departamento[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [mostrarArquivados, setMostrarArquivados] = useState(false);
  const [creatingDepartamento, setCreatingDepartamento] = useState(false);
  const [editingDepartamentoId, setEditingDepartamentoId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [arquivarDepartamentoId, setArquivarDepartamentoId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);

  const editingDepartamento = departamentos.find((item) => item.id === editingDepartamentoId);
  const arquivarDepartamento = departamentos.find((item) => item.id === arquivarDepartamentoId);

  // A busca vai para o backend: assim `codigoReferencia` (D26000001) e `codigoInterno`
  // também são pesquisáveis, não só o que está carregado na tela.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const data = await listDepartamentosReais({
        search: query.trim() || undefined,
        status: mostrarArquivados ? "arquivado" : undefined,
      });
      setDepartamentos(data);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os departamentos.");
    } finally {
      setCarregando(false);
    }
  }, [query, mostrarArquivados]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 250); // debounce da busca
    return () => clearTimeout(timeout);
  }, [carregar]);

  const filteredDepartamentos = useMemo(() => departamentos, [departamentos]);

  async function handleSave(draft: DepartamentoFormDraft, departamentoId?: string) {
    setSalvando(true);
    setErro(null);
    try {
      if (!departamentoId) {
        await criarDepartamentoReal(draft);
      } else {
        await atualizarDepartamentoReal(departamentoId, draft);
      }
      await carregar();
      invalidarDiretorioDepartamentos();
      setCreatingDepartamento(false);
      setEditingDepartamentoId(null);
    } catch (error) {
      if (error instanceof DepartamentoArquivadoConflictError) {
        const restaurar = window.confirm(
          "Já existe um departamento arquivado com este nome. Deseja restaurá-lo em vez de criar um novo?",
        );
        if (restaurar) {
          try {
            await restaurarDepartamentoReal(error.departamentoArquivadoId);
            await carregar();
            invalidarDiretorioDepartamentos();
            setCreatingDepartamento(false);
            setEditingDepartamentoId(null);
          } catch (restoreError) {
            setErro(
              restoreError instanceof Error ? restoreError.message : "Não foi possível restaurar o departamento.",
            );
          }
        }
      } else {
        setErro(error instanceof Error ? error.message : "Não foi possível salvar o departamento.");
      }
    } finally {
      setSalvando(false);
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarDepartamentoId) return;
    setArquivando(true);
    setErro(null);
    try {
      await arquivarDepartamentoReal(arquivarDepartamentoId, motivo);
      await carregar();
      invalidarDiretorioDepartamentos();
      setArquivarDepartamentoId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar o departamento.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(departamentoId: string) {
    setErro(null);
    try {
      await restaurarDepartamentoReal(departamentoId);
      await carregar();
      invalidarDiretorioDepartamentos();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar o departamento.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Building2 className="h-5 w-5" />}
        title="Departamentos"
        description="Setores da operação, usados nos filtros de Usuários e Projetos."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {erro && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      <DepartamentosStats departamentos={departamentos} usuarios={usuarios} />

      <DepartamentosToolbar
        query={query}
        onQueryChange={setQuery}
        onNewDepartamento={() => setCreatingDepartamento(true)}
        mostrarArquivados={mostrarArquivados}
        onMostrarArquivadosChange={setMostrarArquivados}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && departamentos.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <DepartamentosTable
          departamentos={filteredDepartamentos}
          usuarios={usuarios}
          onEdit={setEditingDepartamentoId}
          onArquivar={setArquivarDepartamentoId}
          onRestaurar={handleRestaurar}
        />
      )}

      {creatingDepartamento && (
        <DepartamentoFormModal
          open
          usuarios={usuarios}
          salvando={salvando}
          onClose={() => setCreatingDepartamento(false)}
          onSave={handleSave}
        />
      )}

      {editingDepartamento && (
        <DepartamentoFormModal
          key={editingDepartamento.id}
          open
          departamento={editingDepartamento}
          usuarios={usuarios}
          salvando={salvando}
          onClose={() => setEditingDepartamentoId(null)}
          onSave={handleSave}
        />
      )}

      {arquivarDepartamento && (
        <ArquivarDepartamentoModal
          open
          nome={arquivarDepartamento.nome}
          arquivando={arquivando}
          onClose={() => setArquivarDepartamentoId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
