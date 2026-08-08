"use client";

import { useEffect, useState } from "react";
import { listDiretorioGruposCliente, type GrupoClienteDiretorioItem } from "@/lib/api-backend";

/**
 * Cache remoto deduplicado do diretório de grupos de cliente — mesmo padrão de
 * lib/diretorioUsuarios.ts. Inclui ativos e arquivados (resolução histórica de
 * Cliente.tagIds — ver lib/referencias.ts); quem monta uma lista de opções selecionáveis
 * nova filtra `status === "ativo"` no consumidor.
 *
 * Sem localStorage/sessionStorage, sem fallback mock. `invalidarDiretorioGruposCliente()`
 * limpa o cache e já dispara um refetch, pra todo assinante atualizar sozinho após
 * criar/editar/arquivar/restaurar um grupo.
 */

type Estado = {
  grupos: GrupoClienteDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: GrupoClienteDiretorioItem[] | null = null;
let emVoo: Promise<GrupoClienteDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<GrupoClienteDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioGruposCliente()
    .then((grupos) => {
      cache = grupos;
      emVoo = null;
      notificar();
      return grupos;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioGruposCliente(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioGruposCliente(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    grupos: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () => setEstado({ grupos: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((grupos) => setEstado({ grupos, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            grupos: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar o diretório de grupos de cliente.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
