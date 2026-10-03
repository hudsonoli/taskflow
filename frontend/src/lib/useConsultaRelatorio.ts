"use client";

import { useEffect, useState } from "react";

type Estado<T> = {
  resultado: T | null;
  carregando: boolean;
  erro: string | null;
};

const ESTADO_VAZIO = { resultado: null, carregando: false, erro: null };

/**
 * D4B — consulta de Relatório ao servidor com loading/erro e proteção contra resposta antiga.
 *
 * `buscar` identifica a consulta: quem chama o estabiliza com `useCallback` (as entradas da
 * consulta — Colaborador, Cliente — entram nas dependências), ou usa uma função de módulo.
 * `null` = nada a buscar (ainda sem seleção): sem requisição e sem "carregando".
 *
 * Mesmo desenho de `useAnaliseProjeto`: o reset ao trocar de consulta acontece durante o render
 * (nunca `setState` síncrono no efeito) e o `cancelado` do efeito descarta a resposta de uma
 * consulta anterior, então um resultado antigo nunca aparece como se fosse da seleção atual.
 */
export function useConsultaRelatorio<T>(buscar: (() => Promise<T>) | null): Estado<T> {
  // Embrulhada num objeto: guardar a função direto no `useState` a trataria como "updater".
  const [consultada, setConsultada] = useState<{ buscar: (() => Promise<T>) | null }>({ buscar: null });
  const [estado, setEstado] = useState<Estado<T>>(ESTADO_VAZIO);

  if (buscar !== consultada.buscar) {
    setConsultada({ buscar });
    setEstado(buscar ? { resultado: null, carregando: true, erro: null } : ESTADO_VAZIO);
  }

  useEffect(() => {
    if (!buscar) return;

    let cancelado = false;
    buscar()
      .then((resultado) => {
        if (!cancelado) setEstado({ resultado, carregando: false, erro: null });
      })
      .catch((error) => {
        if (!cancelado) {
          setEstado({
            resultado: null,
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar o relatório.",
          });
        }
      });

    return () => {
      cancelado = true;
    };
  }, [buscar]);

  return estado;
}
