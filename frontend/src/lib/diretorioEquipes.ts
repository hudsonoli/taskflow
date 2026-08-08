"use client";

import { useEffect, useState } from "react";
import { listDiretorioEquipes, type EquipeDiretorioItem } from "@/lib/api-backend";

/**
 * Cache remoto deduplicado do diretório de equipes — mesmo padrão de
 * lib/diretorioUsuarios.ts. Inclui arquivados (resolução histórica de referências antigas);
 * quem monta lista de opções nova filtra `status === "ativo"` no consumidor.
 *
 * Sem localStorage, sem fallback mock. `invalidarDiretorioEquipes()` limpa e refaz a
 * busca, atualizando todos os assinantes após uma mutação.
 */

type Estado = {
  equipes: EquipeDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: EquipeDiretorioItem[] | null = null;
let emVoo: Promise<EquipeDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<EquipeDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioEquipes()
    .then((equipes) => {
      cache = equipes;
      emVoo = null;
      notificar();
      return equipes;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioEquipes(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioEquipes(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    equipes: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () => setEstado({ equipes: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((equipes) => setEstado({ equipes, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            equipes: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar as equipes.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
