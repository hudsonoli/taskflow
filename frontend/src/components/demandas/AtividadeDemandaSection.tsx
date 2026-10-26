"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { MessageSquare, Pencil, Send, Trash2, X } from "lucide-react";
import {
  criarComentarioDemanda,
  editarComentarioDemanda,
  excluirComentarioDemanda,
  listarMencionaveisDemanda,
  listComentariosDemanda,
} from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { podeAcessarAreaAdministrativa } from "@/lib/escopo-operacional";
import { idsDasMencoes, reconciliarSelecionadas, segmentarComMencoes, type Mencionavel } from "@/lib/mencoes";
import { useUsuariosComIds } from "@/lib/useUsuariosComIds";
import type { Demanda, DemandaComentario } from "@/types/demanda";
import { MencaoTextarea } from "./MencaoTextarea";
import { useEscopoLeituraDemanda } from "./leituraDemanda";

function SectionShell({ children }: { children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <MessageSquare className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-fg">Atividade</h3>
          <p className="mt-0.5 text-xs text-fg-muted">
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
 * @menções (V1): "@" abre a lista de pessoas elegíveis; escolher grava "@Nome" no texto e a identidade (id) à parte. O servidor revalida e notifica só os mencionados novos.
 * Sem anexo, reação ou thread — ver docstring de `DemandaComentario`.
 */
export function AtividadeDemandaSection({ demanda }: { demanda: Demanda }) {
  const { usuarioAtual } = useAppData();
  // Leitura pela Pauta global: só consulta (com `escopo=pauta`); sem comentar, editar nem excluir. No ACOMPANHAMENTO (o solicitante) lê com `escopo=acompanhamento` e PODE
  // comentar — e editar/excluir o próprio comentário; o servidor decide (autor-só edita) e nada além de comentar é liberado.
  const escopoLeitura = useEscopoLeituraDemanda();
  const somenteLeitura = escopoLeitura === "pauta";
  const [comentarios, setComentarios] = useState<DemandaComentario[]>([]);
  const { usuarios, resolvendo } = useUsuariosComIds(comentarios.map((comentario) => comentario.autorUsuarioId));
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [textoEdicao, setTextoEdicao] = useState("");
  const [processandoId, setProcessandoId] = useState<string | null>(null);
  const [selecionadas, setSelecionadas] = useState<Mencionavel[]>([]);
  const [selecionadasEdicao, setSelecionadasEdicao] = useState<Mencionavel[]>([]);
  const [publicando, setPublicando] = useState(false);

  const buscarMencionaveis = useCallback(
    (consulta: string, sinal: AbortSignal) => listarMencionaveisDemanda(demanda.id, consulta, sinal),
    [demanda.id],
  );

  const podeModerar = usuarioAtual ? podeAcessarAreaAdministrativa(usuarioAtual) : false;

  useEffect(() => {
    let cancelado = false;
    listComentariosDemanda(demanda.id, escopoLeitura)
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
  }, [demanda.id, escopoLeitura]);

  function nomeAutor(autorUsuarioId: string | null, autorSistema?: boolean): string {
    if (autorSistema) return "Sistema";
    if (!autorUsuarioId) return "Usuário removido";
    return usuarios.find((usuario) => usuario.id === autorUsuarioId)?.nome ?? (resolvendo ? "Carregando…" : "Usuário removido");
  }

  async function comentar() {
    const conteudo = texto.trim();
    if (!conteudo || publicando) return; // trava o duplo envio: um clique = um comentário = no máximo uma notificação por pessoa
    setErro(null);
    setPublicando(true);
    try {
      const criado = await criarComentarioDemanda(demanda.id, conteudo, idsDasMencoes(reconciliarSelecionadas(conteudo, selecionadas)));
      setComentarios((atual) => [criado, ...atual]);
      setTexto("");
      setSelecionadas([]);
    } catch (error) {
      setErro(error instanceof Error && error.message ? error.message : "Não foi possível publicar o comentário.");
    } finally {
      setPublicando(false);
    }
  }

  function iniciarEdicao(comentario: DemandaComentario) {
    setEditandoId(comentario.id);
    setTextoEdicao(comentario.texto);
    // as menções já guardadas voltam como selecionadas: reenviar o mesmo conjunto não notifica ninguém de novo
    setSelecionadasEdicao((comentario.mencoes ?? []).map((m) => ({ id: m.usuarioId, nome: m.nome })));
  }

  async function salvarEdicao(comentarioId: string) {
    const conteudo = textoEdicao.trim();
    if (!conteudo) return;
    setProcessandoId(comentarioId);
    setErro(null);
    try {
      const atualizado = await editarComentarioDemanda(demanda.id, comentarioId, conteudo, idsDasMencoes(reconciliarSelecionadas(conteudo, selecionadasEdicao)));
      setComentarios((atual) => atual.map((item) => (item.id === comentarioId ? atualizado : item)));
      setEditandoId(null);
    } catch (error) {
      setErro(error instanceof Error && error.message ? error.message : "Não foi possível salvar a edição.");
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
      {!somenteLeitura && (
      <div className="flex items-start gap-2">
        <MencaoTextarea
          className="flex-1"
          value={texto}
          onValueChange={setTexto}
          selecionadas={selecionadas}
          onSelecionadasChange={setSelecionadas}
          buscar={buscarMencionaveis}
          onKeyDownExtra={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              void comentar();
            }
          }}
          placeholder="Comentar sobre a tarefa… use @ para mencionar alguém"
          ariaLabel="Novo comentário"
          rows={2}
        />
        <button
          type="button"
          onClick={() => void comentar()}
          disabled={!texto.trim() || publicando}
          className="inline-flex shrink-0 items-center justify-center rounded-xl bg-indigo-600 p-2.5 text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Comentar"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      )}

      {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}

      <div className="mt-4 space-y-3">
        {carregando ? (
          <p className="text-sm text-fg-subtle">Carregando comentários…</p>
        ) : comentarios.length === 0 ? (
          <p className="text-sm text-fg-subtle">Nenhum comentário registrado ainda.</p>
        ) : (
          comentarios.map((comentario) => {
            const ehAutor = !somenteLeitura && usuarioAtual != null && comentario.autorUsuarioId === usuarioAtual.id;
            const podeExcluir = !somenteLeitura && (ehAutor || podeModerar);
            return (
              <div
                key={comentario.id}
                className="rounded-2xl border border-zinc-100 bg-zinc-50/60 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/30"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-fg">
                      {nomeAutor(comentario.autorUsuarioId, comentario.autorSistema)}
                    </p>
                    <p className="text-xs text-fg-subtle">
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
                          className="rounded-lg p-1 text-fg-subtle transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
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
                          className="rounded-lg p-1 text-fg-subtle transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {editandoId === comentario.id ? (
                  <div className="mt-1.5 flex items-start gap-2">
                    <MencaoTextarea
                      className="flex-1"
                      autoFocus
                      value={textoEdicao}
                      onValueChange={setTextoEdicao}
                      selecionadas={selecionadasEdicao}
                      onSelecionadasChange={setSelecionadasEdicao}
                      buscar={buscarMencionaveis}
                      onKeyDownExtra={(event) => {
                        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                          event.preventDefault();
                          void salvarEdicao(comentario.id);
                        }
                        if (event.key === "Escape") setEditandoId(null);
                      }}
                      ariaLabel="Editar comentário"
                      rows={2}
                      inputClassName="w-full resize-none rounded-xl border border-indigo-300 bg-surface px-3 py-2 text-sm text-fg outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => setEditandoId(null)}
                      aria-label="Cancelar edição"
                      className="shrink-0 rounded-lg p-1.5 text-fg-subtle transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => void salvarEdicao(comentario.id)}
                      disabled={!textoEdicao.trim() || processandoId === comentario.id}
                      aria-label="Salvar edição"
                      className="shrink-0 rounded-lg bg-indigo-600 p-1.5 text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Send className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ) : (
                  <p className="mt-1.5 whitespace-pre-wrap break-words text-sm leading-6 text-zinc-600 dark:text-zinc-300">
                    {segmentarComMencoes(comentario.texto, comentario.mencoes ?? []).map((trecho, posicao) =>
                      trecho.tipo === "mencao" ? (
                        <span key={posicao} className="rounded bg-indigo-50 px-1 font-medium text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300">
                          {trecho.valor}
                        </span>
                      ) : (
                        <span key={posicao}>{trecho.valor}</span>
                      ),
                    )}
                  </p>
                )}
              </div>
            );
          })
        )}
      </div>
    </SectionShell>
  );
}
