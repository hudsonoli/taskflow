"use client";

import { useEffect, useState, type ReactNode } from "react";
import { MessageSquare, Pencil, Send, Trash2, X } from "lucide-react";
import {
  criarComentarioDemanda,
  editarComentarioDemanda,
  excluirComentarioDemanda,
  listComentariosDemanda,
} from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { podeAcessarAreaAdministrativa } from "@/lib/escopo-operacional";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import type { Demanda, DemandaComentario } from "@/types/demanda";

function SectionShell({ children }: { children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <MessageSquare className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">Atividade</h3>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            Histórico do que foi comentado sobre a tarefa pelas partes envolvidas.
          </p>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function formatarDataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR");
}

/**
 * Comentários de Demanda (Fase 2E.4) — real, com autoria e moderação decididas no backend.
 * Este componente só REFLETE a permissão (mostra/esconde botão) — quem barra de verdade é
 * `DemandaComentarioService`, que devolve 403 mesmo que a UI deixasse passar.
 *
 * Sem @mention, anexo, reação ou thread nesta fase — ver docstring de `DemandaComentario`.
 */
export function AtividadeDemandaSection({ demanda }: { demanda: Demanda }) {
  const { usuarioAtual } = useAppData();
  const { usuarios } = useDiretorioUsuarios();

  const [comentarios, setComentarios] = useState<DemandaComentario[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [textoEdicao, setTextoEdicao] = useState("");
  const [processandoId, setProcessandoId] = useState<string | null>(null);

  const podeModerar = usuarioAtual ? podeAcessarAreaAdministrativa(usuarioAtual) : false;

  useEffect(() => {
    let cancelado = false;
    listComentariosDemanda(demanda.id)
      .then((dados) => {
        if (!cancelado) setComentarios(dados);
      })
      .catch(() => {
        if (!cancelado) setErro("Não foi possível carregar os comentários.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [demanda.id]);

  function nomeAutor(autorUsuarioId: string | null): string {
    if (!autorUsuarioId) return "Usuário removido";
    return usuarios.find((usuario) => usuario.id === autorUsuarioId)?.nome ?? "Usuário removido";
  }

  async function comentar() {
    const conteudo = texto.trim();
    if (!conteudo) return;
    setErro(null);
    try {
      const criado = await criarComentarioDemanda(demanda.id, conteudo);
      setComentarios((atual) => [criado, ...atual]);
      setTexto("");
    } catch {
      setErro("Não foi possível publicar o comentário.");
    }
  }

  function iniciarEdicao(comentario: DemandaComentario) {
    setEditandoId(comentario.id);
    setTextoEdicao(comentario.texto);
  }

  async function salvarEdicao(comentarioId: string) {
    const conteudo = textoEdicao.trim();
    if (!conteudo) return;
    setProcessandoId(comentarioId);
    setErro(null);
    try {
      const atualizado = await editarComentarioDemanda(demanda.id, comentarioId, conteudo);
      setComentarios((atual) => atual.map((item) => (item.id === comentarioId ? atualizado : item)));
      setEditandoId(null);
    } catch {
      setErro("Não foi possível salvar a edição.");
    } finally {
      setProcessandoId(null);
    }
  }

  async function excluir(comentarioId: string) {
    setProcessandoId(comentarioId);
    setErro(null);
    try {
      await excluirComentarioDemanda(demanda.id, comentarioId);
      setComentarios((atual) => atual.filter((item) => item.id !== comentarioId));
    } catch {
      setErro("Não foi possível excluir o comentário.");
    } finally {
      setProcessandoId(null);
    }
  }

  return (
    <SectionShell>
      <div className="flex items-start gap-2">
        <textarea
          value={texto}
          onChange={(event) => setTexto(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              void comentar();
            }
          }}
          placeholder="Comentar sobre a tarefa…"
          rows={2}
          className="w-full resize-none rounded-xl border border-zinc-200 bg-zinc-50/70 py-2.5 px-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
        />
        <button
          type="button"
          onClick={() => void comentar()}
          disabled={!texto.trim()}
          className="inline-flex shrink-0 items-center justify-center rounded-xl bg-indigo-600 p-2.5 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Comentar"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>

      {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}

      <div className="mt-4 space-y-3">
        {carregando ? (
          <p className="text-sm text-zinc-400">Carregando comentários…</p>
        ) : comentarios.length === 0 ? (
          <p className="text-sm text-zinc-400">Nenhum comentário registrado ainda.</p>
        ) : (
          comentarios.map((comentario) => {
            const ehAutor = usuarioAtual != null && comentario.autorUsuarioId === usuarioAtual.id;
            const podeExcluir = ehAutor || podeModerar;
            return (
              <div
                key={comentario.id}
                className="rounded-2xl border border-zinc-100 bg-zinc-50/60 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/30"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {nomeAutor(comentario.autorUsuarioId)}
                    </p>
                    <p className="text-xs text-zinc-400">
                      {formatarDataHora(comentario.createdAt)}
                      {comentario.editadoEm && " · editado"}
                    </p>
                  </div>
                  {(ehAutor || podeExcluir) && editandoId !== comentario.id && (
                    <div className="flex shrink-0 items-center gap-0.5">
                      {ehAutor && (
                        <button
                          type="button"
                          onClick={() => iniciarEdicao(comentario)}
                          aria-label="Editar comentário"
                          className="rounded-lg p-1 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                      )}
                      {podeExcluir && (
                        <button
                          type="button"
                          onClick={() => void excluir(comentario.id)}
                          disabled={processandoId === comentario.id}
                          aria-label="Excluir comentário"
                          className="rounded-lg p-1 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {editandoId === comentario.id ? (
                  <div className="mt-1.5 flex items-start gap-2">
                    <textarea
                      autoFocus
                      value={textoEdicao}
                      onChange={(event) => setTextoEdicao(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                          event.preventDefault();
                          void salvarEdicao(comentario.id);
                        }
                        if (event.key === "Escape") setEditandoId(null);
                      }}
                      rows={2}
                      className="w-full resize-none rounded-xl border border-indigo-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none dark:bg-zinc-900 dark:text-zinc-100"
                    />
                    <button
                      type="button"
                      onClick={() => setEditandoId(null)}
                      aria-label="Cancelar edição"
                      className="shrink-0 rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => void salvarEdicao(comentario.id)}
                      disabled={!textoEdicao.trim() || processandoId === comentario.id}
                      aria-label="Salvar edição"
                      className="shrink-0 rounded-lg bg-indigo-600 p-1.5 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Send className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ) : (
                  <p className="mt-1.5 text-sm leading-6 text-zinc-600 dark:text-zinc-300">{comentario.texto}</p>
                )}
              </div>
            );
          })
        )}
      </div>
    </SectionShell>
  );
}
