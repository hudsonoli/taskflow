"use client";

import { useEffect, useState } from "react";
import { getEstadoExpedienteReal } from "@/lib/api-backend";
import type { EstadoExpediente } from "@/types/regra-expediente";

/**
 * Estado operacional de expediente (Fase 2G.3), calculado no servidor — nunca no relógio do
 * navegador (ver GET /expediente/estado). Poll simples por componente, sem cache
 * compartilhado: diferente dos diretórios (Cliente/Projeto/TipoTarefa/...), este dado muda
 * sozinho com o tempo, então cada consumidor já precisa de um intervalo próprio — um cache
 * compartilhado só adicionaria complexidade sem remover nenhum poll.
 */

const INTERVALO_MS = 30_000;

type Resultado = {
  estado: EstadoExpediente | null;
  carregando: boolean;
};

export function useEstadoExpediente(): Resultado {
  const [estado, setEstado] = useState<EstadoExpediente | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let cancelado = false;

    function buscar() {
      getEstadoExpedienteReal()
        .then((novo) => {
          if (!cancelado) {
            setEstado(novo);
            setCarregando(false);
          }
        })
        .catch(() => {
          if (!cancelado) setCarregando(false);
        });
    }

    buscar();
    const intervalId = setInterval(buscar, INTERVALO_MS);
    return () => {
      cancelado = true;
      clearInterval(intervalId);
    };
  }, []);

  return { estado, carregando };
}
