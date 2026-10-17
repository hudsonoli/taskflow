"use client";

import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { Tabs } from "@/components/ui/Tabs";
import { useAppData } from "@/lib/AppDataContext";
import { podeAcessarCentralTrafego } from "@/lib/escopo-operacional";
import { VISAO_PADRAO, VISOES_TRAFEGO, visaoDaUrl } from "@/lib/trafego-operacional";
import { TrafegoAgoraVisao } from "./TrafegoAgoraVisao";
import { TrafegoGargalosVisao } from "./TrafegoGargalosVisao";
import { TrafegoHeader } from "./TrafegoHeader";
import { TrafegoTempoPessoalView } from "./TrafegoTempoPessoalView";

/**
 * Central de Tráfego — Tráfego V2. Gestão OPERACIONAL: [Agora] "o que precisa da atenção do gestor agora?" e [Gargalos] "onde o fluxo está travando?", ambos sobre os intervalos de estado das
 * tarefas (tempo operacional). A antiga tela de sessões manuais continua disponível, rebaixada para a aba secundária [Tempo pessoal] — tempo PESSOAL, que não alimenta as duas primeiras.
 * A visão vive na URL (`?visao=gargalos`); sem parâmetro, ou com valor desconhecido, abre AGORA. O backend é a autoridade de acesso; aqui só se reaproveita o mesmo gate da tela.
 * A visão é lida do ROUTER (`useSearchParams`) e trocada com `router.replace` — assim as visões filhas, que guardam os próprios filtros na URL (`useFiltrosNaUrl`), já montam vendo `visao` e nunca
 * a apagam ao gravar um filtro.
 */
export function TrafegoView() {
  const { usuarioAtual } = useAppData();
  const router = useRouter();
  const pathname = usePathname();
  const parametrosDaUrl = useSearchParams();
  const visao = visaoDaUrl(parametrosDaUrl.get("visao"));
  // Etapa escolhida numa linha do AGORA ("Ver gargalos"): uma etapa materializada, que a API expande para a definição inteira.
  const [etapa, setEtapa] = useState<{ id: string; nome: string } | null>(null);

  if (!usuarioAtual) return null;

  if (!podeAcessarCentralTrafego(usuarioAtual)) {
    return (
      <div className="flex flex-col gap-6">
        <TrafegoHeader />
        <AcessoNegado
          titulo="Central de Tráfego restrita à gestão autorizada"
          descricao="Esta visão reúne o estado operacional de toda a empresa — disponível apenas para perfis de gestão autorizados nesta fase."
        />
      </div>
    );
  }

  // Parte da URL REAL do navegador (onde as visões filhas gravam os filtros) e muda só `visao`; o resto é preservado.
  const irPara = (id: string) => {
    const proximo = new URLSearchParams(window.location.search);
    if (id === VISAO_PADRAO) proximo.delete("visao");
    else proximo.set("visao", id);
    const consulta = proximo.toString();
    router.replace(consulta ? `${pathname}?${consulta}` : pathname, { scroll: false });
  };

  return (
    <div className="flex flex-col gap-4">
      <TrafegoHeader />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs tabs={VISOES_TRAFEGO.map((item) => ({ id: item.id, label: item.label }))} activeTab={visao} onChange={irPara} />
      </div>

      {visao === "agora" && (
        <TrafegoAgoraVisao
          onVerGargalosDaEtapa={(escolhida) => {
            setEtapa(escolhida);
            irPara("gargalos");
          }}
        />
      )}
      {visao === "gargalos" && <TrafegoGargalosVisao etapa={etapa} onLimparEtapa={() => setEtapa(null)} />}
      {visao === "pessoal" && <TrafegoTempoPessoalView />}
    </div>
  );
}
