"use client";

import { useEffect, useRef, useState } from "react";
import { ClipboardList } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { listDemandasReais } from "@/lib/api-backend";
import { formatPrazo, statusDemandaLabels, statusDemandaTone } from "@/lib/demandas";
import { rotuloDemanda } from "@/lib/referencias";
import type { Demanda } from "@/types/demanda";

// D2-B2: mesma razão do D2-B1 (ver DemandasView.tsx) — AppDataContext.demandas vem limitado a
// 200 itens carregados uma única vez no login. Uma demanda deste projeto podia estar fora dessa
// janela e a seção parecia vazia sem nenhum aviso. A seção passa a buscar direto do servidor
// por projetoId, sem depender desse array global. Aba somente-leitura dentro de um painel de
// inspeção (ver docstring de ProjetoDetailsDrawer) — sem mutation, sem necessidade de refetch
// por sucesso de escrita.
const TAMANHO_PAGINA = 50;

export function ProjetoDemandasSection({ projetoId }: { projetoId: string }) {
  const [demandas, setDemandas] = useState<Demanda[]>([]);
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [temMais, setTemMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // projetoId consultado — comparado durante o RENDER, mesmo padrão de DemandasView.tsx e
  // lib/useAjustesProjeto.ts: evita setState síncrono no corpo do efeito, que
  // react-hooks/set-state-in-effect rejeita neste projeto.
  const [projetoConsultado, setProjetoConsultado] = useState<string | null>(null);
  if (projetoId !== projetoConsultado) {
    setProjetoConsultado(projetoId);
    setDemandas([]);
    setTemMais(false);
    setErro(null);
    setCarregandoInicial(true);
  }

  // Hoje o único consumidor (ProjetoDetailsDrawer) sempre desmonta esta seção antes de trocar
  // de projeto — o backdrop do DetailsModal bloqueia clique em outra linha enquanto está aberto.
  // Mesmo assim, `carregarMais` roda fora do useEffect (é um handler de clique, não pode usar o
  // flag `cancelado` de cleanup) e não tinha nenhuma proteção própria: se um consumidor futuro
  // permitir trocar projetoId sem desmontar, uma resposta tardia da página 2 do projeto anterior
  // se concatenaria na lista do projeto novo. Ref sempre atualizada no render guarda contra isso.
  const projetoIdAtualRef = useRef(projetoId);
  useEffect(() => {
    projetoIdAtualRef.current = projetoId;
  }, [projetoId]);

  useEffect(() => {
    let cancelado = false;
    listDemandasReais({ projetoId, limit: TAMANHO_PAGINA, offset: 0 })
      .then((resultado) => {
        if (cancelado) return; // resposta obsoleta — projetoId já mudou de novo
        setDemandas(resultado);
        setTemMais(resultado.length === TAMANHO_PAGINA);
        setErro(null);
        setCarregandoInicial(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setErro(error instanceof Error ? error.message : "Não foi possível carregar as demandas deste projeto.");
        setCarregandoInicial(false);
      });
    return () => {
      cancelado = true;
    };
  }, [projetoId]);

  function carregarMais() {
    const projetoDoClique = projetoId;
    setCarregandoMais(true);
    listDemandasReais({ projetoId, limit: TAMANHO_PAGINA, offset: demandas.length })
      .then((resultado) => {
        if (projetoIdAtualRef.current !== projetoDoClique) return; // projeto mudou enquanto a página carregava
        setDemandas((atual) => [...atual, ...resultado]);
        setTemMais(resultado.length === TAMANHO_PAGINA);
        setErro(null);
      })
      .catch((error) => {
        if (projetoIdAtualRef.current !== projetoDoClique) return;
        // Não corrompe a lista já exibida — mantém o que já veio, com o erro sinalizado abaixo.
        setErro(error instanceof Error ? error.message : "Não foi possível carregar mais demandas.");
      })
      .finally(() => {
        if (projetoIdAtualRef.current === projetoDoClique) setCarregandoMais(false);
      });
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <ClipboardList className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">Demandas do projeto</h3>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">Ativas, concluídas e demais status, todas em um lugar.</p>
        </div>
      </div>

      <div className="mt-4">
        {carregandoInicial ? (
          <p className="text-sm text-zinc-400">Carregando demandas…</p>
        ) : erro && demandas.length === 0 ? (
          <EmptyState title="Não foi possível carregar" description={erro} icon={<ClipboardList size={16} />} />
        ) : demandas.length === 0 ? (
          <EmptyState title="Nenhuma demanda vinculada" description="As demandas criadas para este projeto vão aparecer aqui." icon={<ClipboardList size={16} />} />
        ) : (
          <>
            <ul className="flex flex-col gap-2.5">
              {demandas.map((demanda) => (
                <li
                  key={demanda.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-zinc-100 bg-zinc-50/60 px-3.5 py-2.5 dark:border-zinc-800 dark:bg-zinc-950/30"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">{demanda.nome}</p>
                    <p className="text-xs text-zinc-400">
                      {rotuloDemanda(demanda)} · prazo {formatPrazo(demanda.prazoEtapaAtual)}
                    </p>
                  </div>
                  <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                </li>
              ))}
            </ul>
            {erro && demandas.length > 0 && <p className="mt-2 text-xs text-red-500">{erro}</p>}
            {temMais && (
              <div className="mt-3 flex justify-center">
                <Button type="button" variant="secondary" onClick={carregarMais} disabled={carregandoMais}>
                  {carregandoMais ? "Carregando…" : "Carregar mais"}
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
