"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import { getTrafegoOperacionalAgora, getTrafegoOperacionalGargalos } from "@/lib/api";
import {
  criarPoller,
  estadoRemotoInicial,
  mensagemDeErro,
  reduzirRemoto,
  type EstadoRemoto,
  type PollerAgora,
} from "@/lib/trafego-operacional";
import type { ParametrosGargalosOperacionais, TrafegoOperacionalAgora, TrafegoOperacionalGargalos } from "@/types/trafego-operacional";

const LIMITE_LISTA_AGORA = 50;

/**
 * AGORA: UMA requisição por atualização (`GET /trafego/operacional/agora`), com polling silencioso a cada 30 s (só com a aba visível, sem sobrepor requisições, sem websocket).
 * A primeira carga mostra skeleton; as seguintes MANTÊM o conteúdo e só ligam `atualizando` — a tela nunca pisca. Uma falha depois de haver dados mantém os dados e expõe `erro`.
 */
export function useTrafegoAgora(): { estado: EstadoRemoto<TrafegoOperacionalAgora>; atualizar: () => void } {
  const [estado, despachar] = useReducer(reduzirRemoto<TrafegoOperacionalAgora>, undefined, () => estadoRemotoInicial<TrafegoOperacionalAgora>());
  const pollerRef = useRef<PollerAgora | null>(null);

  useEffect(() => {
    let vivo = true;
    const controlador = new AbortController();
    const buscar = async () => {
      despachar({ tipo: "buscar" });
      try {
        const dados = await getTrafegoOperacionalAgora(LIMITE_LISTA_AGORA, controlador.signal);
        if (vivo) despachar({ tipo: "sucesso", dados, emMs: Date.now() });
      } catch (erro) {
        if (vivo) despachar({ tipo: "falha", mensagem: mensagemDeErro(erro) });
      }
    };
    const poller = criarPoller({ buscar, visivel: () => document.visibilityState === "visible" });
    pollerRef.current = poller;
    poller.iniciar();
    const aoMudarVisibilidade = () => poller.aoMudarVisibilidade();
    document.addEventListener("visibilitychange", aoMudarVisibilidade);
    return () => {
      vivo = false;
      controlador.abort(); // desmontar (ou o 2º efeito do StrictMode em dev) cancela a requisição em voo
      poller.parar();
      pollerRef.current = null;
      document.removeEventListener("visibilitychange", aoMudarVisibilidade);
    };
  }, []);

  const atualizar = useCallback(() => pollerRef.current?.atualizar(), []);
  return { estado, atualizar };
}

/**
 * GARGALOS: UMA requisição por consulta (`GET /trafego/operacional/gargalos`), refeita ao entrar na aba, ao mudar qualquer filtro e no botão Atualizar — sem polling.
 * Uma consulta nova cancela a anterior em voo; ao trocar filtro o conteúdo anterior continua na tela (`atualizando`) até a resposta chegar.
 */
export function useTrafegoGargalos(parametros: ParametrosGargalosOperacionais | null): EstadoRemoto<TrafegoOperacionalGargalos> {
  const [estado, despachar] = useReducer(reduzirRemoto<TrafegoOperacionalGargalos>, undefined, () => estadoRemotoInicial<TrafegoOperacionalGargalos>());
  const chave = parametros ? JSON.stringify(parametros) : null;

  useEffect(() => {
    if (chave === null) return;
    const consulta = JSON.parse(chave) as ParametrosGargalosOperacionais;
    const controlador = new AbortController();
    despachar({ tipo: "buscar" });
    getTrafegoOperacionalGargalos(consulta, controlador.signal)
      .then((dados) => {
        if (!controlador.signal.aborted) despachar({ tipo: "sucesso", dados, emMs: Date.now() });
      })
      .catch((erro) => {
        if (!controlador.signal.aborted) despachar({ tipo: "falha", mensagem: mensagemDeErro(erro) });
      });
    return () => controlador.abort();
  }, [chave]);

  return estado;
}
