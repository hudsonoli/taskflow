"use client";

import { useEffect, useState } from "react";
import { getRelatorioAnaliseProjeto } from "@/lib/api-backend";
import type { RelatorioAnaliseProjeto } from "@/types/relatorios";

type Estado = {
  resultado: RelatorioAnaliseProjeto | null;
  carregando: boolean;
  erro: string | null;
};

const ESTADO_VAZIO: Estado = { resultado: null, carregando: false, erro: null };

/**
 * D4A — "Análise de projeto" calculada no servidor, uma request por Projeto selecionado.
 * `null` enquanto o diretório de Projetos ainda não resolveu `projetoId` (nada é buscado com id
 * vazio). Mesmo desenho de `useAjustesProjeto`: o reset ao trocar de Projeto acontece durante o
 * render (nunca `setState` síncrono no efeito) e o `cancelado` do efeito descarta a resposta de
 * um Projeto anterior — o resultado antigo nunca aparece como se fosse do selecionado.
 */
export function useAnaliseProjeto(projetoId: string | null): Estado {
  const [projetoIdConsultado, setProjetoIdConsultado] = useState<string | null>(null);
  const [estado, setEstado] = useState<Estado>(ESTADO_VAZIO);

  if (projetoId !== projetoIdConsultado) {
    setProjetoIdConsultado(projetoId);
    setEstado(projetoId ? { resultado: null, carregando: true, erro: null } : ESTADO_VAZIO);
  }

  useEffect(() => {
    if (!projetoId) return;

    let cancelado = false;
    getRelatorioAnaliseProjeto(projetoId)
      .then((resultado) => {
        if (!cancelado) setEstado({ resultado, carregando: false, erro: null });
      })
      .catch((error) => {
        if (!cancelado) {
          setEstado({
            resultado: null,
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar a análise do projeto.",
          });
        }
      });

    return () => {
      cancelado = true;
    };
  }, [projetoId]);

  return estado;
}
