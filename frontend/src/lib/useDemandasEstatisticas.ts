"use client";

import { useEffect, useState } from "react";
import { getDemandasEstatisticas } from "@/lib/api-backend";
import type { DemandaEstatisticas } from "@/types/demanda";

type Estado = {
  estatisticas: DemandaEstatisticas | null;
  /** Só até a PRIMEIRA resposta (ou falha): num refresh os números anteriores continuam na tela. */
  carregando: boolean;
  erro: string | null;
};

/**
 * Cards de `DemandasStats` vindos do servidor. `versao` é o gatilho de refresh: quem muda Demandas
 * (criar, editar, mudar status) incrementa e os números são reconciliados com o servidor — nunca
 * por atualização otimista de um array local.
 *
 * - primeira carga: `carregando` => os cards mostram "…";
 * - refresh: o último valor bom permanece até a nova resposta chegar (sem piscar);
 * - falha: `estatisticas` vira `null` e `erro` aparece — os cards mostram "—", nunca um número
 *   parcial ou antigo ao lado de uma mensagem de erro;
 * - resposta obsoleta (um refresh mais novo já foi disparado, ou a tela desmontou) é descartada
 *   pelo `cancelado` do efeito.
 */
export function useDemandasEstatisticas(versao: number): Estado {
  const [estado, setEstado] = useState<Estado>({ estatisticas: null, carregando: true, erro: null });

  useEffect(() => {
    let cancelado = false;
    getDemandasEstatisticas()
      .then((estatisticas) => {
        if (!cancelado) setEstado({ estatisticas, carregando: false, erro: null });
      })
      .catch((error) => {
        if (!cancelado) {
          setEstado({
            estatisticas: null,
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar as estatísticas.",
          });
        }
      });
    return () => {
      cancelado = true;
    };
  }, [versao]);

  return estado;
}
