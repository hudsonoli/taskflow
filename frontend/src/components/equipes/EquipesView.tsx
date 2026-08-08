"use client";

import { useCallback, useEffect, useState } from "react";
import { UsersRound } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  arquivarEquipeReal,
  atualizarEquipeReal,
  criarEquipeReal,
  listEquipesReais,
  restaurarEquipeReal,
} from "@/lib/api-backend";
import { invalidarDiretorioEquipes } from "@/lib/diretorioEquipes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import type { Equipe, EquipeFormDraft } from "@/types/equipe";
import { ArquivarEquipeModal } from "./ArquivarEquipeModal";
import { EquipeFormModal } from "./EquipeFormModal";
import { EquipesGrid } from "./EquipesGrid";
import { EquipesStats } from "./EquipesStats";
import { EquipesToolbar } from "./EquipesToolbar";

export function EquipesView() {
  const { usuarios } = useDiretorioUsuarios();
  const { departamentos } = useDiretorioDepartamentos();
  const [equipes, setEquipes] = useState<Equipe[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [mostrarArquivadas, setMostrarArquivadas] = useState(false);
  const [creatingEquipe, setCreatingEquipe] = useState(false);
  const [editingEquipeId, setEditingEquipeId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [arquivarEquipeId, setArquivarEquipeId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);

  const editingEquipe = equipes.find((equipe) => equipe.id === editingEquipeId);
  const arquivarEquipe = equipes.find((equipe) => equipe.id === arquivarEquipeId);

  // Busca no backend: `codigoReferencia` (E26000001) e `codigoInterno` também são
  // pesquisáveis, não só o que já está carregado na tela.
  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const data = await listEquipesReais({
        search: query.trim() || undefined,
        status: mostrarArquivadas ? "arquivado" : undefined,
      });
      setEquipes(data);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar as equipes.");
    } finally {
      setCarregando(false);
    }
  }, [query, mostrarArquivadas]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 250);
    return () => clearTimeout(timeout);
  }, [carregar]);

  async function handleSave(draft: EquipeFormDraft, equipeId?: string) {
    setSalvando(true);
    setErro(null);
    try {
      if (!equipeId) {
        await criarEquipeReal(draft);
      } else {
        await atualizarEquipeReal(equipeId, draft);
      }
      await carregar();
      invalidarDiretorioEquipes();
      setCreatingEquipe(false);
      setEditingEquipeId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível salvar a equipe.");
    } finally {
      setSalvando(false);
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarEquipeId) return;
    setArquivando(true);
    setErro(null);
    try {
      await arquivarEquipeReal(arquivarEquipeId, motivo);
      await carregar();
      invalidarDiretorioEquipes();
      setArquivarEquipeId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível arquivar a equipe.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(equipeId: string) {
    setErro(null);
    try {
      await restaurarEquipeReal(equipeId);
      await carregar();
      invalidarDiretorioEquipes();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível restaurar a equipe.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<UsersRound className="h-5 w-5" />}
        title="Equipes"
        description="Squads e times da operação, com líder e membros vinculados aos usuários reais."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {erro && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </div>
      )}

      <EquipesStats equipes={equipes} />

      <EquipesToolbar
        query={query}
        onQueryChange={setQuery}
        onNewEquipe={() => setCreatingEquipe(true)}
        mostrarArquivadas={mostrarArquivadas}
        onMostrarArquivadasChange={setMostrarArquivadas}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro && equipes.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <EquipesGrid
          equipes={equipes}
          usuarios={usuarios}
          departamentos={departamentos}
          onEdit={setEditingEquipeId}
          onArquivar={setArquivarEquipeId}
          onRestaurar={handleRestaurar}
        />
      )}

      {creatingEquipe && (
        <EquipeFormModal
          open
          usuarios={usuarios}
          departamentos={departamentos}
          salvando={salvando}
          onClose={() => setCreatingEquipe(false)}
          onSave={handleSave}
        />
      )}

      {editingEquipe && (
        <EquipeFormModal
          key={editingEquipe.id}
          open
          equipe={editingEquipe}
          usuarios={usuarios}
          departamentos={departamentos}
          salvando={salvando}
          onClose={() => setEditingEquipeId(null)}
          onSave={handleSave}
        />
      )}

      {arquivarEquipe && (
        <ArquivarEquipeModal
          open
          nome={arquivarEquipe.nome}
          arquivando={arquivando}
          onClose={() => setArquivarEquipeId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
