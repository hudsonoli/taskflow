"use client";

import { useEffect, useState } from "react";
import { listDiretorioDepartamentos, type DepartamentoDiretorioItem } from "@/lib/api-backend";

/**
 * Cache remoto deduplicado do diretório de departamentos — mesmo padrão de
 * lib/diretorioUsuarios.ts. Inclui arquivados (resolução histórica de referências antigas);
 * quem monta lista de opções nova filtra `status === "ativo"` no consumidor.
 *
 * Sem localStorage, sem fallback mock. `invalidarDiretorioDepartamentos()` limpa e refaz a
 * busca, atualizando todos os assinantes após uma mutação.
 */

type Estado = {
  departamentos: DepartamentoDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: DepartamentoDiretorioItem[] | null = null;
let emVoo: Promise<DepartamentoDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<DepartamentoDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioDepartamentos()
    .then((departamentos) => {
      cache = departamentos;
      emVoo = null;
      notificar();
      return departamentos;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioDepartamentos(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioDepartamentos(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    departamentos: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () => setEstado({ departamentos: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((departamentos) => setEstado({ departamentos, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            departamentos: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar os departamentos.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
