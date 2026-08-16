"use client";

import { useEffect, useState } from "react";
import { listDiretorioProjetos, type ProjetoDiretorioItem } from "@/lib/api-backend";

/**
 * Cache remoto deduplicado do diretório de projetos — mesmo padrão de
 * lib/diretorioDepartamentos.ts. Inclui todos os status (resolução histórica de referências
 * antigas); quem monta lista de opções nova filtra no consumidor.
 *
 * Sem localStorage, sem fallback mock. `invalidarDiretorioProjetos()` limpa e refaz a busca,
 * atualizando todos os assinantes após uma mutação.
 */

type Estado = {
  projetos: ProjetoDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: ProjetoDiretorioItem[] | null = null;
let emVoo: Promise<ProjetoDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<ProjetoDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioProjetos()
    .then((projetos) => {
      cache = projetos;
      emVoo = null;
      notificar();
      return projetos;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioProjetos(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioProjetos(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    projetos: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () => setEstado({ projetos: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((projetos) => setEstado({ projetos, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            projetos: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar os projetos.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
