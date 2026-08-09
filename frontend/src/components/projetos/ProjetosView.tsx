"use client";

import { useCallback, useEffect, useState } from "react";
import { FolderKanban } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  ProjetoArquivadoConflictError,
  arquivarProjetoReal,
  atualizarProjetoReal,
  criarProjetoReal,
  listProjetosReais,
  restaurarProjetoReal,
} from "@/lib/api-backend";
import type { Projeto, ProjetoFormDraft } from "@/types/projeto";
import { ArquivarProjetoModal } from "./ArquivarProjetoModal";
import { NovoProjetoModal } from "./NovoProjetoModal";
import { ProjetoDetailsDrawer } from "./ProjetoDetailsDrawer";
import { ProjetosStats } from "./ProjetosStats";
import { ProjetosTable } from "./ProjetosTable";
import { type ProjetoStatusFiltro, ProjetosToolbar } from "./ProjetosToolbar";

export function ProjetosView() {
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<ProjetoStatusFiltro>("todos");
  const [mostrarArquivados, setMostrarArquivados] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [arquivarProjetoId, setArquivarProjetoId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);
  // Conflito com projeto arquivado: guarda o id para oferecer "restaurar" em vez de só
  // mostrar erro de duplicidade (ver docs/padrao-arquivamento.md).
  const [conflitoArquivadoId, setConflitoArquivadoId] = useState<string | null>(null);

  const selectedProject = projetos.find((projeto) => projeto.id === selectedProjectId);
  const editingProject = projetos.find((projeto) => projeto.id === editingProjectId);
  const arquivarProjeto = projetos.find((projeto) => projeto.id === arquivarProjetoId);

  // A busca vai para o backend: assim `codigoReferencia` (P26000001) e a campanha também
  // são pesquisáveis, não só o que está na tela.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const data = await listProjetosReais({
        search: query.trim() || undefined,
        status: mostrarArquivados ? "arquivado" : statusFilter === "todos" ? undefined : statusFilter,
      });
      setProjetos(data);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os projetos.");
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

  async function salvar(draft: ProjetoFormDraft, projetoId?: string): Promise<string | null> {
    setSalvando(true);
    setErro(null);
    setConflitoArquivadoId(null);
    try {
      const salvo = projetoId
        ? await atualizarProjetoReal(projetoId, draft)
        : await criarProjetoReal(draft);
      await carregar();
      setCreatingProject(false);
      setEditingProjectId(null);
      return salvo.id;
    } catch (error) {
      if (error instanceof ProjetoArquivadoConflictError) {
        setConflitoArquivadoId(error.projetoArquivadoId);
        setErro(error.message);
      } else {
        setErro(error instanceof Error ? error.message : "Não foi possível salvar o projeto.");
      }
      return null;
    } finally {
      setSalvando(false);
    }
  }

  async function handleSaveAndClose(draft: ProjetoFormDraft, projetoId?: string) {
    await salvar(draft, projetoId);
  }

  async function handleSaveAndContinue(draft: ProjetoFormDraft, projetoId?: string) {
    const id = await salvar(draft, projetoId);
    if (id) setSelectedProjectId(id);
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarProjetoId) return;
    setArquivando(true);
    setErro(null);
    try {
      await arquivarProjetoReal(arquivarProjetoId, motivo);
      await carregar();
      setArquivarProjetoId(null);
      setSelectedProjectId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar o projeto.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(projetoId: string) {
    setErro(null);
    setConflitoArquivadoId(null);
    try {
      await restaurarProjetoReal(projetoId);
      await carregar();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar o projeto.");
    }
  }

  function openEdit(projetoId: string) {
    setSelectedProjectId(null);
    setEditingProjectId(projetoId);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<FolderKanban className="h-5 w-5" />}
        title="Projetos"
        description="Raiz de cada empreendimento/campanha — as demandas se organizam a partir de um projeto."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {erro && (
        <div className="flex flex-col gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          <span>{erro}</span>
          {conflitoArquivadoId && (
            <button
              type="button"
              onClick={() => handleRestaurar(conflitoArquivadoId)}
              className="self-start rounded-lg border border-red-300 px-2 py-1 font-medium transition hover:bg-red-100 dark:border-red-500/40 dark:hover:bg-red-500/20"
            >
              Restaurar o projeto arquivado
            </button>
          )}
        </div>
      )}

      <ProjetosStats projetos={projetos} />

      <ProjetosToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onNewProject={() => setCreatingProject(true)}
        mostrarArquivados={mostrarArquivados}
        onMostrarArquivadosChange={setMostrarArquivados}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && projetos.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : projetos.length === 0 ? (
        <EmptyState
          title={query.trim() ? "Nenhum projeto encontrado" : "Nenhum projeto cadastrado"}
          description={
            query.trim()
              ? "Ajuste a busca ou os filtros para visualizar os projetos cadastrados."
              : "Crie o primeiro projeto para começar a organizar as demandas."
          }
        />
      ) : (
        <ProjetosTable
          projetos={projetos}
          onOpenDetails={setSelectedProjectId}
          onEdit={openEdit}
          onArquivar={setArquivarProjetoId}
          onRestaurar={handleRestaurar}
        />
      )}

      {creatingProject && (
        <NovoProjetoModal
          open
          salvando={salvando}
          onClose={() => setCreatingProject(false)}
          onSaveAndClose={handleSaveAndClose}
          onSaveAndContinue={handleSaveAndContinue}
        />
      )}

      {editingProject && (
        <NovoProjetoModal
          key={editingProject.id}
          open
          projeto={editingProject}
          salvando={salvando}
          onClose={() => setEditingProjectId(null)}
          onSaveAndClose={handleSaveAndClose}
          onSaveAndContinue={handleSaveAndContinue}
        />
      )}

      {arquivarProjeto && (
        <ArquivarProjetoModal
          open
          nome={arquivarProjeto.nome}
          arquivando={arquivando}
          onClose={() => setArquivarProjetoId(null)}
          onConfirm={handleArquivar}
        />
      )}

      <ProjetoDetailsDrawer
        projeto={selectedProject}
        onClose={() => setSelectedProjectId(null)}
        onEdit={openEdit}
      />
    </div>
  );
}
