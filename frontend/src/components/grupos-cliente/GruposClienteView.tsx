"use client";

import { useState } from "react";
import { Archive, ArchiveRestore, Plus, Tag } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { coresIdentificacaoDisponiveis, resolveCorIdentificacaoHex } from "@/lib/cores";
import {
  atualizarGrupoClienteReal,
  arquivarGrupoClienteReal,
  criarGrupoClienteReal,
  GrupoClienteArquivadoConflictError,
  restaurarGrupoClienteReal,
} from "@/lib/api-backend";
import { invalidarDiretorioGruposCliente, useDiretorioGruposCliente } from "@/lib/diretorioGruposCliente";
import { correspondeGrupoCliente } from "@/lib/referencias";
import { useAppData } from "@/lib/AppDataContext";
import { ExcluirGrupoClienteModal } from "./ExcluirGrupoClienteModal";

export function GruposClienteView() {
  const { clientes } = useAppData();
  const { grupos, carregando, erro } = useDiretorioGruposCliente();
  const [novoNome, setNovoNome] = useState("");
  const [criando, setCriando] = useState(false);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [mostrarArquivados, setMostrarArquivados] = useState(false);
  const [arquivarGrupoId, setArquivarGrupoId] = useState<string | null>(null);
  const [arquivando, setArquivando] = useState(false);
  const [restaurandoId, setRestaurandoId] = useState<string | null>(null);

  const arquivarGrupo = grupos.find((grupo) => grupo.id === arquivarGrupoId);
  const gruposVisiveis = mostrarArquivados ? grupos : grupos.filter((grupo) => grupo.status === "ativo");

  async function handleCriar() {
    const nome = novoNome.trim();
    if (!nome) return;
    setCriando(true);
    setErroAcao(null);
    try {
      await criarGrupoClienteReal(nome, coresIdentificacaoDisponiveis[0].id);
      invalidarDiretorioGruposCliente();
      setNovoNome("");
    } catch (error) {
      if (error instanceof GrupoClienteArquivadoConflictError) {
        const restaurar = window.confirm(
          "Já existe um grupo arquivado com este nome. Deseja restaurá-lo em vez de criar um novo?",
        );
        if (restaurar) {
          try {
            await restaurarGrupoClienteReal(error.grupoClienteArquivadoId);
            invalidarDiretorioGruposCliente();
            setNovoNome("");
          } catch (restoreError) {
            setErroAcao(restoreError instanceof Error ? restoreError.message : "Não foi possível restaurar o grupo.");
          }
        }
      } else {
        setErroAcao(error instanceof Error ? error.message : "Não foi possível criar o grupo.");
      }
    } finally {
      setCriando(false);
    }
  }

  async function handleCorChange(grupoId: string, corIdentificacao: string) {
    setErroAcao(null);
    try {
      await atualizarGrupoClienteReal(grupoId, { corIdentificacao });
      invalidarDiretorioGruposCliente();
    } catch (error) {
      setErroAcao(error instanceof Error ? error.message : "Não foi possível atualizar a cor.");
    }
  }

  async function handleArquivar(motivo: string) {
    if (!arquivarGrupoId) return;
    setArquivando(true);
    setErroAcao(null);
    try {
      await arquivarGrupoClienteReal(arquivarGrupoId, motivo);
      invalidarDiretorioGruposCliente();
      setArquivarGrupoId(null);
    } catch (error) {
      setErroAcao(error instanceof Error ? error.message : "Não foi possível arquivar o grupo.");
    } finally {
      setArquivando(false);
    }
  }

  async function handleRestaurar(grupoId: string) {
    setRestaurandoId(grupoId);
    setErroAcao(null);
    try {
      await restaurarGrupoClienteReal(grupoId);
      invalidarDiretorioGruposCliente();
    } catch (error) {
      setErroAcao(error instanceof Error ? error.message : "Não foi possível restaurar o grupo.");
    } finally {
      setRestaurandoId(null);
    }
  }

  function contarClientes(grupo: (typeof grupos)[number]) {
    return clientes.filter((cliente) => cliente.tagIds.some((referencia) => correspondeGrupoCliente(referencia, grupo)))
      .length;
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Tag className="h-5 w-5" />}
        title="Grupos de clientes"
        description="Etiquetas para organizar os clientes — grupos econômicos, redes, carteiras. Aplique-as no cadastro do cliente; na grid de Clientes dá para agrupar por grupo."
        action={<Badge tone="green">Banco real</Badge>}
      />

      {carregando ? (
        <EstadoCarregando />
      ) : erro ? (
        <EstadoErro mensagem={erro} onRetry={invalidarDiretorioGruposCliente} />
      ) : (
        <>
          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                value={novoNome}
                onChange={(event) => setNovoNome(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && handleCriar()}
                placeholder="Nome do novo grupo (ex.: GRUPO BRETAS)"
                className="w-full flex-1 rounded-xl border border-zinc-200/80 bg-zinc-50/70 px-3 py-2.5 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
              />
              <Button onClick={handleCriar} disabled={!novoNome.trim() || criando}>
                <Plus className="h-4 w-4" />
                {criando ? "Criando…" : "Criar grupo"}
              </Button>
            </div>
            {erroAcao && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{erroAcao}</p>}
          </div>

          <div className="flex items-center justify-end">
            <button
              type="button"
              onClick={() => setMostrarArquivados((current) => !current)}
              className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            >
              {mostrarArquivados ? "Ocultar arquivados" : "Mostrar arquivados"}
            </button>
          </div>

          {gruposVisiveis.length === 0 ? (
            <EmptyState title="Nenhum grupo cadastrado" description="Crie um grupo para começar a organizar seus clientes." icon={<Tag size={16} />} />
          ) : (
            <div className="flex flex-col gap-3">
              {gruposVisiveis.map((grupo) => {
                const arquivado = grupo.status === "arquivado";
                return (
                  <div
                    key={grupo.id}
                    className={`flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:flex-row sm:items-center sm:justify-between ${arquivado ? "opacity-60" : ""}`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white"
                        style={{ backgroundColor: resolveCorIdentificacaoHex(grupo.corIdentificacao) }}
                      >
                        <Tag className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="font-semibold text-zinc-950 dark:text-zinc-50">
                          {grupo.nome}
                          {arquivado && <span className="ml-2 text-xs font-normal text-zinc-400">(arquivado)</span>}
                        </p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400">
                          {contarClientes(grupo)} cliente(s) na base
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {!arquivado && (
                        <div className="flex flex-wrap gap-1.5">
                          {coresIdentificacaoDisponiveis.map((cor) => (
                            <button
                              key={cor.id}
                              type="button"
                              aria-label={cor.id}
                              onClick={() => handleCorChange(grupo.id, cor.id)}
                              className={
                                grupo.corIdentificacao === cor.id
                                  ? "h-6 w-6 rounded-full ring-2 ring-offset-2 ring-zinc-900 dark:ring-offset-zinc-900 dark:ring-zinc-100"
                                  : "h-6 w-6 rounded-full"
                              }
                              style={{ backgroundColor: cor.hex }}
                            />
                          ))}
                        </div>
                      )}
                      {arquivado ? (
                        <button
                          type="button"
                          onClick={() => handleRestaurar(grupo.id)}
                          disabled={restaurandoId === grupo.id}
                          aria-label={`Restaurar ${grupo.nome}`}
                          className="rounded-full p-2 text-zinc-400 transition hover:bg-emerald-50 hover:text-emerald-600 dark:hover:bg-emerald-500/10 dark:hover:text-emerald-400"
                        >
                          <ArchiveRestore className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setArquivarGrupoId(grupo.id)}
                          aria-label={`Arquivar ${grupo.nome}`}
                          className="rounded-full p-2 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                        >
                          <Archive className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <p className="text-xs text-zinc-400">
            Os grupos são compartilhados entre os módulos — a contagem acima considera todos os clientes cadastrados.
          </p>
        </>
      )}

      {arquivarGrupo && (
        <ExcluirGrupoClienteModal
          open
          nome={arquivarGrupo.nome}
          arquivando={arquivando}
          onClose={() => setArquivarGrupoId(null)}
          onConfirm={handleArquivar}
        />
      )}
    </div>
  );
}
