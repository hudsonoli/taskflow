"use client";

import { useEffect, useState } from "react";
import { listDiretorioCategoriasPeca } from "@/lib/api-backend";
import type { CategoriaPecaDiretorioItem } from "@/types/categoria-peca";

/**
 * Cache remoto deduplicado do diretório de Categorias de Peça ativas — mesmo padrão de
 * lib/diretorioTiposTarefa.ts. Sem localStorage, sem fallback mock.
 * `invalidarDiretorioCategoriasPeca()` limpa e refaz a busca, atualizando todos os
 * assinantes após uma mutação (ex.: criar/arquivar uma Categoria).
 */

type Estado = {
  categorias: CategoriaPecaDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: CategoriaPecaDiretorioItem[] | null = null;
let emVoo: Promise<CategoriaPecaDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<CategoriaPecaDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioCategoriasPeca()
    .then((categorias) => {
      cache = categorias;
      emVoo = null;
      notificar();
      return categorias;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioCategoriasPeca(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioCategoriasPeca(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    categorias: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () =>
      setEstado({ categorias: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((categorias) => setEstado({ categorias, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            categorias: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar as categorias de peça.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
