"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Users } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  atualizarUsuarioReal,
  criarUsuarioReal,
  excluirUsuarioReal,
  listUsuariosReais,
  restaurarUsuarioReal,
  UsuarioArquivadoConflictError,
} from "@/lib/api-backend";
import { generateId } from "@/lib/ids";
import { invalidarDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { resolverDepartamentoNome, resolverDepartamentoPorReferencia } from "@/lib/referencias";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import type { Usuario, UsuarioFormDraft } from "@/types/usuario";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";
import { ExcluirUsuarioModal } from "./ExcluirUsuarioModal";
import { UsuarioFormModal } from "./UsuarioFormModal";
import { UsuariosStats } from "./UsuariosStats";
import { UsuariosTable } from "./UsuariosTable";
import { type UsuarioSituacaoFiltro, UsuariosToolbar } from "./UsuariosToolbar";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesUsuario(usuario: Usuario, query: string, departamentos: DepartamentoDiretorioItem[]) {
  const haystack = [usuario.nome, usuario.email, resolverDepartamentoNome(usuario.departamentoId, departamentos)].join(" ");
  return normalize(haystack).includes(normalize(query));
}

export function UsuariosView() {
  const { usuarioAtual } = useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [situacaoFilter, setSituacaoFilter] = useState<UsuarioSituacaoFiltro>("todos");
  const [departamentoFilter, setDepartamentoFilter] = useState("");
  const [creatingUsuario, setCreatingUsuario] = useState(false);
  const [editingUsuarioId, setEditingUsuarioId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [excluirUsuarioId, setExcluirUsuarioId] = useState<string | null>(null);
  const [excluindo, setExcluindo] = useState(false);

  const editingUsuario = usuarios.find((usuario) => usuario.id === editingUsuarioId);
  const excluirUsuario = usuarios.find((usuario) => usuario.id === excluirUsuarioId);
  const empresaId = usuarioAtual?.empresaId;

  const carregar = useCallback(async () => {
    if (!empresaId) return;
    setCarregando(true);
    setErro(null);
    try {
      const data = await listUsuariosReais(empresaId);
      setUsuarios(data);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os usuários.");
    } finally {
      setCarregando(false);
    }
  }, [empresaId]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 0);
    return () => clearTimeout(timeout);
  }, [carregar]);

  // Filtro e vínculo do usuário são resolvidos pela camada central antes de comparar — a
  // igualdade acontece entre departamentos já resolvidos, nunca entre strings cruas.
  const departamentoFiltradoId = useMemo(
    () => (departamentoFilter ? resolverDepartamentoPorReferencia(departamentoFilter, departamentos)?.id : undefined),
    [departamentoFilter, departamentos],
  );

  const filteredUsuarios = useMemo(
    () =>
      usuarios.filter((usuario) => {
        const situacaoMatches =
          situacaoFilter === "todos" || (situacaoFilter === "ativo" ? usuario.ativo : !usuario.ativo);
        const departamentoMatches =
          !departamentoFilter ||
          (!!departamentoFiltradoId &&
            resolverDepartamentoPorReferencia(usuario.departamentoId, departamentos)?.id === departamentoFiltradoId);
        const queryMatches = query.trim() ? matchesUsuario(usuario, query, departamentos) : true;
        return situacaoMatches && departamentoMatches && queryMatches;
      }),
    [usuarios, query, situacaoFilter, departamentoFilter, departamentoFiltradoId, departamentos],
  );

  async function handleSave(draft: UsuarioFormDraft, usuarioId?: string) {
    if (!empresaId) return;
    setSalvando(true);
    try {
      if (!usuarioId) {
        await criarUsuarioReal(draft, empresaId, generateId("usuario"));
      } else {
        const anterior = usuarios.find((usuario) => usuario.id === usuarioId);
        await atualizarUsuarioReal(usuarioId, draft, anterior?.ativo ?? true);
      }
      await carregar();
      invalidarDiretorioUsuarios();
      setCreatingUsuario(false);
      setEditingUsuarioId(null);
    } catch (error) {
      if (error instanceof UsuarioArquivadoConflictError) {
        const restaurar = window.confirm(
          "Já existe um usuário com este e-mail (arquivado). Deseja restaurá-lo em vez de criar um novo? " +
            "Ele volta como inativo — reative depois se for o caso.",
        );
        if (restaurar) {
          try {
            await restaurarUsuarioReal(error.usuarioArquivadoId);
            await carregar();
            invalidarDiretorioUsuarios();
            setCreatingUsuario(false);
            setEditingUsuarioId(null);
          } catch (restoreError) {
            setErro(restoreError instanceof Error ? restoreError.message : "Não foi possível restaurar o usuário.");
          }
        }
      } else {
        setErro(error instanceof Error ? error.message : "Não foi possível salvar o usuário.");
      }
    } finally {
      setSalvando(false);
    }
  }

  async function handleExcluir(motivo: string) {
    if (!excluirUsuarioId) return;
    setExcluindo(true);
    try {
      await excluirUsuarioReal(excluirUsuarioId, motivo);
      await carregar();
      invalidarDiretorioUsuarios();
      setExcluirUsuarioId(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível excluir o usuário.");
    } finally {
      setExcluindo(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Users className="h-5 w-5" />}
        title="Usuários"
        description="Pessoas com acesso ao workspace, departamento e perfil de permissão."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : (
        <>
          <UsuariosStats usuarios={usuarios} />

          <UsuariosToolbar
            query={query}
            onQueryChange={setQuery}
            situacaoFilter={situacaoFilter}
            onSituacaoFilterChange={setSituacaoFilter}
            departamentoFilter={departamentoFilter}
            onDepartamentoFilterChange={setDepartamentoFilter}
            departamentos={departamentos}
            onNewUsuario={() => setCreatingUsuario(true)}
          />

          <UsuariosTable
            usuarios={filteredUsuarios}
            departamentos={departamentos}
            onEdit={setEditingUsuarioId}
            onExcluir={setExcluirUsuarioId}
          />
        </>
      )}

      {creatingUsuario && (
        <UsuarioFormModal
          open
          departamentos={departamentos}
          salvando={salvando}
          onClose={() => setCreatingUsuario(false)}
          onSave={handleSave}
        />
      )}

      {editingUsuario && (
        <UsuarioFormModal
          key={editingUsuario.id}
          open
          usuario={editingUsuario}
          departamentos={departamentos}
          salvando={salvando}
          onClose={() => setEditingUsuarioId(null)}
          onSave={handleSave}
        />
      )}

      {excluirUsuario && (
        <ExcluirUsuarioModal
          open
          nome={excluirUsuario.nome}
          excluindo={excluindo}
          onClose={() => setExcluirUsuarioId(null)}
          onConfirm={handleExcluir}
        />
      )}
    </div>
  );
}
