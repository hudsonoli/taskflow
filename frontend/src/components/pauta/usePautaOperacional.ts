"use client";

import { useEffect, useReducer } from "react";
import { getPautaOperacional, PautaOperacionalErro } from "@/lib/api";
import { estadoRemotoInicial, reduzirRemoto, type EstadoRemoto } from "@/lib/trafego-operacional";
import type { ParametrosPautaOperacional, PautaOperacional } from "@/types/pauta-operacional";

/**
 * PAUTA: UMA requisição por consulta (`GET /pauta/operacional`), refeita ao mudar período, filtro ou busca e após uma mutação no detalhe (`versao`) — sem polling.
 * Uma consulta nova cancela a anterior em voo; com dados na tela o conteúdo é mantido (`atualizando`). `parametros === null` não consulta (acesso ainda não resolvido ou negado).
 */
export function usePautaOperacional(parametros: ParametrosPautaOperacional | null, versao = 0): EstadoRemoto<PautaOperacional> {
  const [estado, despachar] = useReducer(reduzirRemoto<PautaOperacional>, undefined, () => estadoRemotoInicial<PautaOperacional>());
  const chave = parametros ? JSON.stringify({ parametros, versao }) : null;

  useEffect(() => {
    if (chave === null) return;
    const { parametros: consulta } = JSON.parse(chave) as { parametros: ParametrosPautaOperacional };
    const controlador = new AbortController();
    despachar({ tipo: "buscar" });
    getPautaOperacional(consulta, controlador.signal)
      .then((dados) => {
        if (!controlador.signal.aborted) despachar({ tipo: "sucesso", dados, emMs: Date.now() });
      })
      .catch((erro) => {
        if (controlador.signal.aborted) return;
        despachar({ tipo: "falha", mensagem: erro instanceof PautaOperacionalErro || erro instanceof Error ? erro.message : "Não foi possível carregar a pauta." });
      });
    return () => controlador.abort();
  }, [chave]);

  return estado;
}
