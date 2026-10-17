"use client";

import { useNow } from "@/lib/useNow";
import { avisoSemEtapaAtual } from "@/lib/trafego-operacional";
import { TrafegoAgoraKpis } from "./TrafegoAgoraKpis";
import { TrafegoAgoraLista } from "./TrafegoAgoraLista";
import { BotaoAtualizar, TrafegoAvisoAtualizacao, TrafegoErroLocal, TrafegoSkeleton } from "./TrafegoEstados";
import { useTrafegoAgora } from "./useTrafegoOperacional";

const ATUALIZACAO_RELOGIO_MS = 30_000;

/**
 * AGORA — "o que precisa da atenção do gestor agora?". UMA requisição (`/trafego/operacional/agora`) com polling silencioso de 30 s; os tempos "há quanto tempo" avançam localmente a partir
 * da idade que o servidor mediu (sem refetch por segundo). Tempo operacional ≠ pessoal: nenhum dado de sessão entra aqui.
 */
export function TrafegoAgoraVisao({ onVerGargalosDaEtapa }: { onVerGargalosDaEtapa?: (etapa: { id: string; nome: string }) => void }) {
  const { estado, atualizar } = useTrafegoAgora();
  const agora = useNow(ATUALIZACAO_RELOGIO_MS);
  const { dados, recebidoEmMs, carregando, atualizando, erro } = estado;
  const aviso = dados ? avisoSemEtapaAtual(dados.kpis.semEtapaAtual) : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-fg-muted">Estado atual das tarefas abertas. Atualiza sozinho a cada 30 segundos.</p>
        <BotaoAtualizar onClick={atualizar} atualizando={atualizando} />
      </div>

      {carregando && dados === null ? (
        <TrafegoSkeleton kpis={5} linhas={3} />
      ) : dados === null || recebidoEmMs === null ? (
        <TrafegoErroLocal mensagem={erro ?? "Não foi possível carregar as métricas operacionais."} onTentarNovamente={atualizar} />
      ) : (
        <>
          {erro && <TrafegoAvisoAtualizacao mensagem={erro} onTentarNovamente={atualizar} />}
          <TrafegoAgoraKpis kpis={dados.kpis} />
          {aviso && <p className="text-xs text-fg-subtle">{aviso}</p>}
          <TrafegoAgoraLista dados={dados} recebidoEmMs={recebidoEmMs} agoraMs={agora.getTime()} onVerGargalosDaEtapa={onVerGargalosDaEtapa} />
        </>
      )}
    </div>
  );
}
