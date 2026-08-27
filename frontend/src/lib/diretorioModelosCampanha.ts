"use client";

import { useEffect, useState } from "react";
import { listDiretorioModelosCampanha } from "@/lib/api-backend";
import type { ModeloCampanhaDiretorioItem } from "@/types/modelo-campanha";

/**
 * Cache remoto deduplicado do diretório de Modelos de Campanha ativos (GET
 * /modelos-campanha/diretorio) — mesmo padrão de lib/diretorioTiposTarefa.ts. Backend já
 * filtra só `ativo` — sem referência histórica a resolver aqui, seleção é sempre pra frente
 * (aplicar/substituir Modelo num Projeto, Fase 2G.5C3).
 */

type Estado = {
  modelosCampanha: ModeloCampanhaDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: ModeloCampanhaDiretorioItem[] | null = null;
let emVoo: Promise<ModeloCampanhaDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<ModeloCampanhaDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioModelosCampanha()
    .then((modelosCampanha) => {
      cache = modelosCampanha;
      emVoo = null;
      notificar();
      return modelosCampanha;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioModelosCampanha(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioModelosCampanha(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    modelosCampanha: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () =>
      setEstado({ modelosCampanha: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((modelosCampanha) => setEstado({ modelosCampanha, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            modelosCampanha: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar os modelos de campanha.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
