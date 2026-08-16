"use client";

import { useEffect, useState } from "react";
import { listDiretorioWorkflowModelos } from "@/lib/api-backend";
import type { WorkflowModeloDiretorioItem } from "@/types/workflow-modelo";

/**
 * Cache remoto deduplicado do diretório de workflows ativos — mesmo padrão de
 * lib/diretorioDepartamentos.ts. Diferente dos outros diretórios, o backend já filtra só
 * `ativo` (não há referência histórica a resolver aqui — seleção é sempre pra frente).
 *
 * Sem localStorage, sem fallback mock. `invalidarDiretorioWorkflowModelos()` limpa e refaz a
 * busca, atualizando todos os assinantes após uma mutação (ex.: arquivar um workflow).
 */

type Estado = {
  workflowModelos: WorkflowModeloDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: WorkflowModeloDiretorioItem[] | null = null;
let emVoo: Promise<WorkflowModeloDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<WorkflowModeloDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioWorkflowModelos()
    .then((workflowModelos) => {
      cache = workflowModelos;
      emVoo = null;
      notificar();
      return workflowModelos;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioWorkflowModelos(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioWorkflowModelos(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    workflowModelos: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () =>
      setEstado({ workflowModelos: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((workflowModelos) => setEstado({ workflowModelos, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            workflowModelos: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar os workflows.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
