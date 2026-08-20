"use client";

import { useEffect, useState } from "react";
import { listDiretorioTiposTarefa } from "@/lib/api-backend";
import type { TipoTarefaDiretorioItem } from "@/types/tipo-tarefa";

/**
 * Cache remoto deduplicado do diretório de Tipos de Tarefa ativos — mesmo padrão de
 * lib/diretorioWorkflowModelos.ts (Fase 2G.1). Diferente dos diretórios de Cliente/Projeto/
 * Departamento, o backend já filtra só `ativo` — não há referência histórica a resolver
 * aqui, seleção é sempre pra frente.
 *
 * Sem localStorage, sem fallback mock. `invalidarDiretorioTiposTarefa()` limpa e refaz a
 * busca, atualizando todos os assinantes após uma mutação (ex.: arquivar um Tipo de Tarefa).
 */

type Estado = {
  tiposTarefa: TipoTarefaDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: TipoTarefaDiretorioItem[] | null = null;
let emVoo: Promise<TipoTarefaDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<TipoTarefaDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioTiposTarefa()
    .then((tiposTarefa) => {
      cache = tiposTarefa;
      emVoo = null;
      notificar();
      return tiposTarefa;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioTiposTarefa(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioTiposTarefa(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    tiposTarefa: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () =>
      setEstado({ tiposTarefa: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((tiposTarefa) => setEstado({ tiposTarefa, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            tiposTarefa: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar os tipos de tarefa.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
