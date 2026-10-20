"use client";

import { useEffect, useReducer } from "react";
import { getTrafegoCarga } from "@/lib/api";
import { estadoRemotoInicial, reduzirRemoto, type EstadoRemoto } from "@/lib/trafego-operacional";
import { mensagemDeErroCarga } from "@/lib/trafego-carga";
import type { CargaSemanal, ParametrosCarga } from "@/types/trafego-carga";

/**
 * CARGA: UMA requisição principal por consulta (`GET /trafego/operacional/carga`), refeita ao entrar na aba, ao mudar semana ou filtro e no botão Atualizar — sem polling, sem websocket.
 * Uma consulta nova cancela a anterior em voo; ao trocar semana/filtro o conteúdo anterior continua na tela (`atualizando`) até a resposta chegar. `versao` força a releitura (Atualizar).
 * `parametros === null` não consulta nada (drill-down fechado).
 */
export function useTrafegoCarga(parametros: ParametrosCarga | null, versao = 0): EstadoRemoto<CargaSemanal> {
  const [estado, despachar] = useReducer(reduzirRemoto<CargaSemanal>, undefined, () => estadoRemotoInicial<CargaSemanal>());
  const chave = parametros ? JSON.stringify({ parametros, versao }) : null;

  useEffect(() => {
    if (chave === null) return;
    const { parametros: consulta } = JSON.parse(chave) as { parametros: ParametrosCarga };
    const controlador = new AbortController();
    despachar({ tipo: "buscar" });
    getTrafegoCarga(consulta, controlador.signal)
      .then((dados) => {
        if (!controlador.signal.aborted) despachar({ tipo: "sucesso", dados, emMs: Date.now() });
      })
      .catch((erro) => {
        if (!controlador.signal.aborted) despachar({ tipo: "falha", mensagem: mensagemDeErroCarga(erro) });
      });
    return () => controlador.abort();
  }, [chave]);

  return estado;
}
