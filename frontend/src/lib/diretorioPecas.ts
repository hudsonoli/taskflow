"use client";

import { useEffect, useState } from "react";
import { listDiretorioPecas } from "@/lib/api-backend";
import type { PecaDiretorioItem } from "@/types/peca";

/**
 * Cache remoto deduplicado do diretório de Peças ativas (GET /pecas/diretorio) — mesmo padrão
 * de lib/diretorioTiposTarefa.ts. Contrato pronto pra um futuro consumidor operacional (ex.:
 * seleção de Peça em Demanda); nenhuma tela usa isto ainda nesta fase.
 */

type Estado = {
  pecas: PecaDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: PecaDiretorioItem[] | null = null;
let emVoo: Promise<PecaDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<PecaDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioPecas()
    .then((pecas) => {
      cache = pecas;
      emVoo = null;
      notificar();
      return pecas;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioPecas(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioPecas(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    pecas: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () => setEstado({ pecas: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((pecas) => setEstado({ pecas, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            pecas: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar o diretório de peças.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
