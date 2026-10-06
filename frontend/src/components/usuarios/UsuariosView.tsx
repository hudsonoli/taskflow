"use client";

import { useEffect, useRef, useState } from "react";
import { Users } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  atualizarUsuarioReal,
  criarUsuarioReal,
  excluirUsuarioReal,
  getResumoUsuarios,
  listUsuariosPagina,
  restaurarUsuarioReal,
  UsuarioArquivadoConflictError,
  type UsuarioResumo,
} from "@/lib/api-backend";
import { invalidarDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import type { Usuario, UsuarioFormDraft } from "@/types/usuario";
import { ExcluirUsuarioModal } from "./ExcluirUsuarioModal";
import { UsuarioFormModal } from "./UsuarioFormModal";
import { UsuariosStats } from "./UsuariosStats";
import { UsuariosTable } from "./UsuariosTable";
import { type UsuarioSituacaoFiltro, UsuariosToolbar } from "./UsuariosToolbar";

const TAMANHO_PAGINA = 50;
const DEBOUNCE_BUSCA_MS = 300;

export function UsuariosView() {
  const { usuarioAtual } = useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [erroMais, setErroMais] = useState<string | null>(null);
  const [temMais, setTemMais] = useState(false);
  const [resumo, setResumo] = useState<UsuarioResumo | null>(null);
  const [query, setQuery] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [situacaoFilter, setSituacaoFilter] = useState<UsuarioSituacaoFiltro>("todos");
  const [departamentoFilter, setDepartamentoFilter] = useState("");
  // Incrementado após mutation: reconcilia a listagem E o resumo com o servidor.
  const [refetchTick, setRefetchTick] = useState(0);
  const [creatingUsuario, setCreatingUsuario] = useState(false);
  const [editingUsuarioId, setEditingUsuarioId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [excluirUsuarioId, setExcluirUsuarioId] = useState<string | null>(null);
  const [excluindo, setExcluindo] = useState(false);

  const editingUsuario = usuarios.find((usuario) => usuario.id === editingUsuarioId);
  const excluirUsuario = usuarios.find((usuario) => usuario.id === excluirUsuarioId);
  const empresaId = usuarioAtual?.empresaId;

  // Espelha a chave vigente para descartar respostas de "Carregar mais" de uma consulta anterior.
  const chaveRef = useRef<string | null>(null);

  // Debounce da digitação: só o texto "assentado" vira consulta no servidor.
  useEffect(() => {
    const timeout = setTimeout(() => setBuscaAplicada(query.trim()), DEBOUNCE_BUSCA_MS);
    return () => clearTimeout(timeout);
  }, [query]);

  // Chave da consulta vigente (filtros + empresa + reconciliação). Comparada durante o RENDER, não
  // dentro do efeito (regra react-hooks/set-state-in-effect do projeto — mesmo padrão do MemberSelector).
  const situacaoServidor = situacaoFilter === "todos" ? undefined : situacaoFilter;
  const chave = empresaId ? JSON.stringify([empresaId, buscaAplicada, situacaoServidor, departamentoFilter, refetchTick]) : null;
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  useEffect(() => {
    chaveRef.current = chave;
  });
  if (chave !== chaveConsultada) {
    setChaveConsultada(chave);
    setCarregandoMais(false);
    setErroMais(null);
    if (chave !== null) {
      setCarregando(true);
      setErro(null);
    }
  }

  // Primeira página da consulta vigente. Resposta de uma consulta já abandonada (digitou outra busca,
  // trocou filtro) é descartada pelo `cancelado` do cleanup.
  useEffect(() => {
    if (!empresaId) return;
    let cancelado = false;
    listUsuariosPagina({
      empresaId,
      search: buscaAplicada || undefined,
      situacao: situacaoServidor,
      departamentoId: departamentoFilter || undefined,
      limit: TAMANHO_PAGINA,
      offset: 0,
    })
      .then((pagina) => {
        if (cancelado) return;
        setUsuarios(pagina);
        setTemMais(pagina.length === TAMANHO_PAGINA);
        setErro(null);
        setCarregando(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setErro(error instanceof Error ? error.message : "Não foi possível carregar os usuários.");
        setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [empresaId, buscaAplicada, situacaoServidor, departamentoFilter, refetchTick]);

  // Cards: agregados da empresa inteira, independentes de filtros e de página.
  useEffect(() => {
    if (!empresaId) return;
    let cancelado = false;
    getResumoUsuarios(empresaId)
      .then((dados) => {
        if (!cancelado) setResumo(dados);
      })
      .catch(() => {
        if (!cancelado) setResumo(null);
      });
    return () => {
      cancelado = true;
    };
  }, [empresaId, refetchTick]);

  function carregarMais() {
    if (!empresaId || carregandoMais) return;
    const chaveDaPagina = chave;
    setCarregandoMais(true);
    setErroMais(null);
    listUsuariosPagina({
      empresaId,
      search: buscaAplicada || undefined,
      situacao: situacaoServidor,
      departamentoId: departamentoFilter || undefined,
      limit: TAMANHO_PAGINA,
      offset: usuarios.length,
    })
      .then((pagina) => {
        // A consulta mudou enquanto esta página vinha: não mistura resultados de filtros diferentes.
        if (chaveRef.current !== chaveDaPagina) return;
        setUsuarios((atual) => {
          const jaNaTela = new Set(atual.map((usuario) => usuario.id));
          return [...atual, ...pagina.filter((usuario) => !jaNaTela.has(usuario.id))];
        });
        setTemMais(pagina.length === TAMANHO_PAGINA);
      })
      .catch((error) => {
        if (chaveRef.current !== chaveDaPagina) return;
        setErroMais(error instanceof Error ? error.message : "Não foi possível carregar mais usuários.");
      })
      .finally(() => {
        if (chaveRef.current === chaveDaPagina) setCarregandoMais(false);
      });
  }

  function reconciliar() {
    setRefetchTick((tick) => tick + 1);
  }

  async function handleSave(draft: UsuarioFormDraft, usuarioId?: string) {
    if (!empresaId) return;
    setSalvando(true);
    try {
      if (!usuarioId) {
        await criarUsuarioReal(draft, empresaId);
      } else {
        const anterior = usuarios.find((usuario) => usuario.id === usuarioId);
        await atualizarUsuarioReal(usuarioId, draft, anterior?.ativo ?? true);
      }
      reconciliar();
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
            reconciliar();
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
      reconciliar();
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

      <UsuariosStats resumo={resumo} />

      {carregando && usuarios.length === 0 ? (
        <EstadoCarregando />
      ) : erro && usuarios.length === 0 ? (
        <EstadoErro mensagem={erro} onRetry={reconciliar} />
      ) : (
        <>

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

          <div className={carregando ? "opacity-60 transition-opacity" : "transition-opacity"}>
            <UsuariosTable
              usuarios={usuarios}
              departamentos={departamentos}
              temMais={temMais}
              onEdit={setEditingUsuarioId}
              onExcluir={setExcluirUsuarioId}
            />
          </div>

          {erro && <p className="text-xs text-red-600">{erro}</p>}

          {temMais && !carregando && (
            <div className="flex flex-col items-center gap-1">
              <Button type="button" variant="secondary" onClick={carregarMais} disabled={carregandoMais}>
                {carregandoMais ? "Carregando…" : "Carregar mais"}
              </Button>
              {erroMais && <p className="text-xs text-red-600">{erroMais}</p>}
            </div>
          )}
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
