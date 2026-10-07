"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, CheckCheck, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import clsx from "clsx";
import { useRouter } from "next/navigation";
import { PrazosEquipeLista } from "@/components/notificacoes/PrazosEquipeLista";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Tabs } from "@/components/ui/Tabs";
import { listarNotificacoes, listarPrazosEquipe, marcarNotificacaoLida, marcarTodasNotificacoesLidas } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { formatarBadge } from "@/lib/notificacoes";
import { useNotificacoes } from "@/lib/NotificacoesContext";
import type { Demanda } from "@/types/demanda";
import type { CategoriaNotificacao, GrupoPrazo, Notificacao } from "@/types/notificacoes";

/**
 * Central de Notificações (/notificacoes): Sistema · Prazos da equipe · Minhas notificações.
 * - Sistema/Minhas: visão tipada dos eventos das demandas do usuário (+ "lida" por usuário), paginada no servidor
 *   (50 por página), filtro Todas/Não lidas, marcar uma ou todas como lidas.
 * - Prazos da equipe: demandas derivadas no escopo REAL do usuário (nunca amplia o acesso), por grupo, paginadas no
 *   servidor.
 * A contagem de não lidas é o estado único (NotificacoesContext) — o sino e o menu do avatar reconciliam na hora.
 */

const POR_PAGINA = 50;
type Aba = "minhas" | "prazos" | "sistema";
type Filtro = "todas" | "nao_lidas";

const GRUPOS: { id: GrupoPrazo; rotulo: string }[] = [
  { id: "atrasadas", rotulo: "Atrasadas" },
  { id: "hoje", rotulo: "Vencem hoje" },
  { id: "proximas", rotulo: "Próximos 7 dias" },
];

const VAZIO_POR_ABA: Record<Aba, { titulo: string; descricao: string }> = {
  sistema: { titulo: "Nenhuma notificação do sistema.", descricao: "Avisos automáticos das suas tarefas aparecem aqui." },
  prazos: { titulo: "Nenhum prazo próximo ou atrasado.", descricao: "Tarefas abertas com prazo aparecem aqui." },
  minhas: { titulo: "Você não possui notificações.", descricao: "Atribuições e mudanças nas suas tarefas aparecem aqui." },
};

function formatarQuando(valor: string): string {
  const data = new Date(valor);
  return Number.isNaN(data.getTime())
    ? ""
    : data.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function Paginacao({ total, offset, onMudar }: { total: number; offset: number; onMudar: (offset: number) => void }) {
  if (total <= POR_PAGINA) return null;
  const pagina = Math.floor(offset / POR_PAGINA) + 1;
  const paginas = Math.ceil(total / POR_PAGINA);
  return (
    <div className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-xs text-fg-muted">
      <span>
        Página {pagina} de {paginas} · {total} registro(s)
      </span>
      <div className="flex gap-2">
        <Button type="button" variant="secondary" disabled={offset === 0} onClick={() => onMudar(Math.max(0, offset - POR_PAGINA))} className="px-3 py-1.5 text-xs">
          <ChevronLeft className="h-3.5 w-3.5" /> Anterior
        </Button>
        <Button type="button" variant="secondary" disabled={pagina >= paginas} onClick={() => onMudar(offset + POR_PAGINA)} className="px-3 py-1.5 text-xs">
          Próxima <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

export function NotificacoesView() {
  const router = useRouter();
  const { setDemandaParaAbrir } = useAppData();
  const { resumo, aplicarResumo, recarregar } = useNotificacoes();

  const [aba, setAba] = useState<Aba>("minhas");
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const [grupo, setGrupo] = useState<GrupoPrazo>("atrasadas");
  const [offset, setOffset] = useState(0);

  const [notificacoes, setNotificacoes] = useState<Notificacao[]>([]);
  const [demandas, setDemandas] = useState<Demanda[]>([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [marcandoTodas, setMarcandoTodas] = useState(false);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let cancelado = false;
    // setTimeout(0): mesmo padrão dos demais efeitos de carga (tira o setState síncrono do corpo do efeito).
    const timeout = setTimeout(() => {
      setCarregando(true);
      setErro(null);
      const consulta =
        aba === "prazos"
          ? listarPrazosEquipe(grupo, { limit: POR_PAGINA, offset }).then((pagina) => {
              if (cancelado) return;
              setDemandas(pagina.itens);
              setNotificacoes([]);
              setTotal(pagina.total);
            })
          : listarNotificacoes({ categoria: aba as CategoriaNotificacao, apenasNaoLidas: filtro === "nao_lidas", limit: POR_PAGINA, offset }).then((pagina) => {
              if (cancelado) return;
              setNotificacoes(pagina.itens);
              setDemandas([]);
              setTotal(pagina.total);
            });
      consulta
        .catch((error) => {
          if (!cancelado) setErro(error instanceof Error ? error.message : "Não foi possível carregar as notificações.");
        })
        .finally(() => {
          if (!cancelado) setCarregando(false);
        });
    }, 0);
    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
  }, [aba, filtro, grupo, offset, tentativa]);

  const abrirDemanda = useCallback(
    (demandaId: string) => {
      setDemandaParaAbrir({ demandaId, aba: "dados" });
      router.push("/tarefas");
    },
    [router, setDemandaParaAbrir],
  );

  async function marcarLida(notificacao: Notificacao) {
    if (notificacao.lida) return;
    // Otimista: marca na lista; o resumo devolvido pela API reconcilia sino e menu.
    setNotificacoes((atuais) =>
      filtro === "nao_lidas" ? atuais.filter((item) => item.id !== notificacao.id) : atuais.map((item) => (item.id === notificacao.id ? { ...item, lida: true } : item)),
    );
    if (filtro === "nao_lidas") setTotal((atual) => Math.max(0, atual - 1));
    try {
      aplicarResumo(await marcarNotificacaoLida(notificacao.id));
    } catch {
      void recarregar();
      setTentativa((n) => n + 1); // desfaz o otimismo relendo o servidor
    }
  }

  async function abrirNotificacao(notificacao: Notificacao) {
    void marcarLida(notificacao);
    if (notificacao.demandaId) abrirDemanda(notificacao.demandaId);
  }

  async function marcarTodas() {
    if (aba === "prazos") return;
    setMarcandoTodas(true);
    try {
      aplicarResumo(await marcarTodasNotificacoesLidas(aba as CategoriaNotificacao));
      setOffset(0);
      setTentativa((n) => n + 1);
    } catch {
      setErro("Não foi possível marcar como lidas.");
    } finally {
      setMarcandoTodas(false);
    }
  }

  function trocarAba(id: string) {
    setAba(id as Aba);
    setOffset(0);
    setFiltro("todas");
  }

  const naoLidasDaAba = aba === "sistema" ? resumo.naoLidas.sistema : aba === "minhas" ? resumo.naoLidas.minhas : 0;
  const prazosTotal = resumo.prazos.atrasadas + resumo.prazos.hoje + resumo.prazos.proximas;
  const comContagem = (rotulo: string, n: number) => (formatarBadge(n) ? `${rotulo} · ${formatarBadge(n)}` : rotulo);
  const vazio = VAZIO_POR_ABA[aba];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<Bell className="h-5 w-5" />}
        title="Notificações"
        description="Avisos das suas tarefas, notificações do sistema e os prazos da equipe — dentro do que você já tem acesso."
        action={
          resumo.naoLidas.total > 0 ? (
            <span role="status" className="rounded-full bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white">
              {formatarBadge(resumo.naoLidas.total)} não lida(s)
            </span>
          ) : undefined
        }
      />

      <Tabs
        tabs={[
          { id: "minhas", label: comContagem("Minhas notificações", resumo.naoLidas.minhas) },
          { id: "prazos", label: comContagem("Prazos da equipe", prazosTotal) },
          { id: "sistema", label: comContagem("Sistema", resumo.naoLidas.sistema) },
        ]}
        activeTab={aba}
        onChange={trocarAba}
      />

      <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
          {aba === "prazos" ? (
            <div role="radiogroup" aria-label="Grupo de prazo" className="inline-flex rounded-xl border border-field-line bg-field p-1">
              {GRUPOS.map(({ id, rotulo }) => {
                const ativo = grupo === id;
                const n = resumo.prazos[id];
                return (
                  <button
                    key={id}
                    type="button"
                    role="radio"
                    aria-checked={ativo}
                    onClick={() => {
                      setGrupo(id);
                      setOffset(0);
                    }}
                    className={clsx(
                      "rounded-lg px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                      ativo ? "bg-indigo-600 text-white" : "text-fg-muted hover:bg-surface-hover hover:text-fg",
                    )}
                  >
                    {rotulo}
                    {n > 0 && <span className="ml-1.5 opacity-90">{formatarBadge(n)}</span>}
                  </button>
                );
              })}
            </div>
          ) : (
            <>
              <div role="radiogroup" aria-label="Filtro" className="inline-flex rounded-xl border border-field-line bg-field p-1">
                {(
                  [
                    ["todas", "Todas"],
                    ["nao_lidas", "Não lidas"],
                  ] as const
                ).map(([id, rotulo]) => (
                  <button
                    key={id}
                    type="button"
                    role="radio"
                    aria-checked={filtro === id}
                    onClick={() => {
                      setFiltro(id);
                      setOffset(0);
                    }}
                    className={clsx(
                      "rounded-lg px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                      filtro === id ? "bg-indigo-600 text-white" : "text-fg-muted hover:bg-surface-hover hover:text-fg",
                    )}
                  >
                    {rotulo}
                  </button>
                ))}
              </div>
              <Button type="button" variant="secondary" disabled={naoLidasDaAba === 0 || marcandoTodas} onClick={() => void marcarTodas()} className="px-3 py-1.5 text-xs">
                {marcandoTodas ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCheck className="h-3.5 w-3.5" />}
                Marcar todas como lidas
              </Button>
            </>
          )}
        </div>

        {carregando && (
          <div className="flex items-center justify-center gap-2 p-10 text-sm text-fg-muted" role="status">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando…
          </div>
        )}

        {!carregando && erro && (
          <div className="p-4">
            <EstadoErro mensagem={erro} onRetry={() => setTentativa((n) => n + 1)} />
          </div>
        )}

        {!carregando && !erro && total === 0 && (
          <div className="p-4">
            <EmptyState title={vazio.titulo} description={vazio.descricao} icon={<Bell size={18} />} />
          </div>
        )}

        {!carregando && !erro && aba === "prazos" && demandas.length > 0 && <PrazosEquipeLista demandas={demandas} grupo={grupo} onAbrir={abrirDemanda} />}

        {!carregando && !erro && aba !== "prazos" && notificacoes.length > 0 && (
          <ul className="divide-y divide-line">
            {notificacoes.map((notificacao) => (
              <li key={notificacao.id} className="flex items-start gap-1 pr-2">
                <button
                  type="button"
                  onClick={() => void abrirNotificacao(notificacao)}
                  className="flex min-w-0 flex-1 items-start gap-3 px-4 py-3 text-left transition hover:bg-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
                >
                  <span
                    aria-hidden
                    className={clsx("mt-1.5 h-2 w-2 shrink-0 rounded-full", notificacao.lida ? "bg-transparent" : "bg-indigo-600 dark:bg-indigo-400")}
                  />
                  <div className="min-w-0 flex-1">
                    <p className={clsx("text-sm text-fg", notificacao.lida ? "font-normal" : "font-semibold")}>
                      {notificacao.titulo}
                      {!notificacao.lida && <span className="sr-only"> (não lida)</span>}
                    </p>
                    {notificacao.detalhe && <p className="mt-0.5 text-xs text-fg-muted">{notificacao.detalhe}</p>}
                    <p className="mt-0.5 truncate text-xs text-fg-muted">
                      {[notificacao.demandaReferencia, notificacao.demandaNome].filter(Boolean).join(" · ")}
                      {notificacao.autorNome ? ` — por ${notificacao.autorNome}` : ""}
                    </p>
                  </div>
                  <span className="shrink-0 whitespace-nowrap text-xs text-fg-subtle">{formatarQuando(notificacao.ocorridaEm)}</span>
                </button>
                {!notificacao.lida && (
                  <button
                    type="button"
                    onClick={() => void marcarLida(notificacao)}
                    aria-label="Marcar como lida"
                    title="Marcar como lida"
                    className="mt-2 shrink-0 rounded-full p-1.5 text-fg-subtle transition hover:bg-surface-hover hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  >
                    <CheckCheck className="h-4 w-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}

        {!carregando && !erro && <Paginacao total={total} offset={offset} onMudar={setOffset} />}
      </div>
    </div>
  );
}
