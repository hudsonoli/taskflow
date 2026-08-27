"use client";

import { useEffect, useState } from "react";
import { Layers3, RotateCw } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ModeloCampanhaItensEditor } from "@/components/modelos-campanha/ModeloCampanhaItensEditor";
import {
  aplicarModeloCampanhaAoProjetoReal,
  atualizarProjetoModeloCampanhaSnapshotReal,
  getProjetoModeloCampanhaSnapshot,
} from "@/lib/api-backend";
import type { ModeloCampanhaItemFormDraft } from "@/types/modelo-campanha";
import type { Projeto } from "@/types/projeto";
import type { ProjetoModeloCampanhaSnapshot, ProjetoModeloCampanhaSnapshotItem } from "@/types/projeto-modelo-campanha";
import { ProjetoAplicarModeloCampanhaModal } from "./ProjetoAplicarModeloCampanhaModal";

/**
 * Seção de Modelo de Campanha do Projeto (Fase 2G.5C3) — consome o snapshot relacional
 * (`GET/POST.../aplicar/PATCH /projetos/{id}/modelo-campanha`), nunca mais o JSONB legado
 * (`projetos.modelo_campanha`/`modelo_campanha_id`, ver types/projeto.ts). Autocontida: busca
 * seu próprio estado (não participa do `onChange` de rascunho genérico das outras seções de
 * ProjetoFormSections.tsx) porque salva através de endpoints dedicados, não do PATCH
 * genérico de Projeto.
 */

function snapshotItemParaDraft(item: ProjetoModeloCampanhaSnapshotItem): ModeloCampanhaItemFormDraft {
  return {
    id: item.id,
    // O id do snapshot já é uma chave única e estável — reaproveitado como clientKey.
    clientKey: item.id,
    nome: item.nome,
    briefingPadrao: item.briefingPadrao ?? "",
    prioridadePadrao: item.prioridadePadrao,
    pecaId: item.pecaId,
    // O nome exibido vem do campo *NomeSnapshot — histórico, nunca recalculado. O editor
    // compartilhado só troca esse nome quando o próprio usuário troca a referência.
    pecaNome: item.pecaNomeSnapshot,
    tipoTarefaId: item.tipoTarefaId,
    tipoTarefaNome: item.tipoTarefaNomeSnapshot,
    workflowModeloId: item.workflowModeloId,
    workflowModeloNome: item.workflowModeloNomeSnapshot,
    responsavelUsuarioId: item.responsavelUsuarioId,
    responsavelUsuarioNome: item.responsavelUsuarioNomeSnapshot,
    responsavelDepartamentoId: item.responsavelDepartamentoId,
    responsavelDepartamentoNome: item.responsavelDepartamentoNomeSnapshot,
  };
}

function formatarDataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function ModeloCampanhaSection({ projeto, somenteLeitura }: { projeto: Projeto; somenteLeitura?: boolean }) {
  const [snapshot, setSnapshot] = useState<ProjetoModeloCampanhaSnapshot | null>(null);
  const [carregandoSnapshot, setCarregandoSnapshot] = useState(true);
  const [erroSnapshot, setErroSnapshot] = useState<string | null>(null);

  const [draftItens, setDraftItens] = useState<ModeloCampanhaItemFormDraft[]>([]);
  const [salvandoEdicao, setSalvandoEdicao] = useState(false);
  const [erroEdicao, setErroEdicao] = useState<string | null>(null);

  const [mostrarModalAplicar, setMostrarModalAplicar] = useState(false);
  const [aplicando, setAplicando] = useState(false);
  const [erroAplicar, setErroAplicar] = useState<string | null>(null);

  // Token incrementado só pelo botão "Tentar novamente" — reaproveita o mesmo efeito de
  // busca sem precisar de uma função `carregarSnapshot` separada chamada de dentro do
  // efeito (isso disparava o aviso de setState-em-efeito do react-hooks; mesmo padrão de
  // AtividadeDemandaSection.tsx: promise encadeada direto no corpo do efeito, com guarda de
  // cancelamento).
  const [tentativaRecarregar, setTentativaRecarregar] = useState(0);

  useEffect(() => {
    let cancelado = false;
    // Nada de setState síncrono aqui no topo do efeito (dispara o aviso de
    // react-hooks/set-state-in-effect) — o estado inicial já nasce "carregando" via
    // `useState(true)`, e o botão "Tentar novamente" reseta carregando/erro ele mesmo antes
    // de incrementar `tentativaRecarregar`.
    getProjetoModeloCampanhaSnapshot(projeto.id)
      .then((dados) => {
        if (cancelado) return;
        setSnapshot(dados);
        setDraftItens(dados ? dados.itens.map(snapshotItemParaDraft) : []);
        setErroSnapshot(null);
      })
      .catch((error) => {
        if (cancelado) return;
        setErroSnapshot(
          error instanceof Error ? error.message : "Não foi possível carregar o Modelo de Campanha do projeto.",
        );
      })
      .finally(() => {
        if (!cancelado) setCarregandoSnapshot(false);
      });
    return () => {
      cancelado = true;
    };
  }, [projeto.id, tentativaRecarregar]);

  async function handleConfirmarAplicar(modeloCampanhaId: string) {
    setAplicando(true);
    setErroAplicar(null);
    try {
      const novoSnapshot = await aplicarModeloCampanhaAoProjetoReal(projeto.id, modeloCampanhaId);
      setSnapshot(novoSnapshot);
      setDraftItens(novoSnapshot.itens.map(snapshotItemParaDraft));
      setErroEdicao(null);
      setMostrarModalAplicar(false);
    } catch (error) {
      setErroAplicar(error instanceof Error ? error.message : "Não foi possível aplicar o Modelo de Campanha.");
    } finally {
      setAplicando(false);
    }
  }

  async function handleSalvarEdicao() {
    setSalvandoEdicao(true);
    setErroEdicao(null);
    try {
      const atualizado = await atualizarProjetoModeloCampanhaSnapshotReal(projeto.id, { itens: draftItens });
      setSnapshot(atualizado);
      setDraftItens(atualizado.itens.map(snapshotItemParaDraft));
    } catch (error) {
      // Draft local preservado de propósito — o usuário não perde o que editou por causa de
      // uma referência inválida num só item (ver item 22 da Fase 2G.5C3).
      setErroEdicao(error instanceof Error ? error.message : "Não foi possível salvar as alterações.");
    } finally {
      setSalvandoEdicao(false);
    }
  }

  const botaoAplicarLabel = snapshot ? "Substituir Modelo" : "Aplicar Modelo";

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Layers3 className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">Modelo de campanha</h3>
            <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
              Estrutura de itens aplicada a partir da biblioteca de Modelos de Campanha.
            </p>
          </div>
        </div>
        {!somenteLeitura && !carregandoSnapshot && !erroSnapshot && (
          <Button type="button" onClick={() => setMostrarModalAplicar(true)} className="px-3 py-1.5 text-xs">
            {botaoAplicarLabel}
          </Button>
        )}
      </div>

      <div className="mt-4">
        {carregandoSnapshot ? (
          <div className="h-32 animate-pulse rounded-2xl border border-zinc-200 bg-zinc-100/70 dark:border-zinc-800 dark:bg-zinc-900/60" />
        ) : erroSnapshot ? (
          <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-8 text-center dark:border-red-500/30 dark:bg-red-500/10">
            <p className="max-w-sm text-sm text-red-600 dark:text-red-400">{erroSnapshot}</p>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setCarregandoSnapshot(true);
                setErroSnapshot(null);
                setTentativaRecarregar((t) => t + 1);
              }}
              className="px-3 py-1.5 text-xs"
            >
              <RotateCw className="h-3.5 w-3.5" />
              Tentar novamente
            </Button>
          </div>
        ) : snapshot === null ? (
          <EmptyState
            title="Nenhum Modelo de Campanha aplicado"
            description="Aplique um modelo da biblioteca para materializar os itens padrão neste projeto."
            icon={<Layers3 size={16} />}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2 rounded-xl border border-zinc-100 bg-zinc-50/70 px-3.5 py-2.5 text-xs dark:border-zinc-800 dark:bg-zinc-950/30">
              <Badge tone="blue">{snapshot.modeloCampanhaNomeSnapshot ?? "Modelo removido da biblioteca"}</Badge>
              {snapshot.aplicadoAt && (
                <span className="text-zinc-500 dark:text-zinc-400">Aplicado em {formatarDataHora(snapshot.aplicadoAt)}</span>
              )}
            </div>

            {erroEdicao && (
              <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
                {erroEdicao}
              </p>
            )}

            <ModeloCampanhaItensEditor itens={draftItens} onItensChange={setDraftItens} somenteLeitura={somenteLeitura} />

            {!somenteLeitura && (
              <div className="flex justify-end">
                <Button type="button" disabled={salvandoEdicao} onClick={handleSalvarEdicao} className="px-3 py-1.5 text-xs">
                  {salvandoEdicao ? "Salvando…" : "Salvar alterações"}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      <ProjetoAplicarModeloCampanhaModal
        open={mostrarModalAplicar}
        temSnapshotAtual={snapshot !== null}
        aplicando={aplicando}
        erro={erroAplicar}
        onClose={() => {
          setMostrarModalAplicar(false);
          setErroAplicar(null);
        }}
        onConfirm={handleConfirmarAplicar}
      />
    </section>
  );
}
