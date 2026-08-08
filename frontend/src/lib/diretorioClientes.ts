"use client";

import { useEffect, useState } from "react";
import { listDiretorioClientes, type ClienteDiretorioItem } from "@/lib/api-backend";

/**
 * Cache remoto deduplicado do diretório de clientes — mesmo padrão de
 * lib/diretorioUsuarios.ts e lib/diretorioGruposCliente.ts. Inclui ativos e arquivados
 * (resolução histórica de `Demanda.clienteId` e `Projeto.clienteId`, que ainda são mock —
 * ver lib/referencias.ts); quem monta uma lista de opções selecionáveis nova filtra
 * `status === "ativo"` no consumidor.
 *
 * Sem localStorage/sessionStorage, sem fallback mock. `invalidarDiretorioClientes()` limpa
 * o cache e já dispara um refetch, pra todo assinante atualizar sozinho após
 * criar/editar/arquivar/restaurar um cliente.
 */

type Estado = {
  clientes: ClienteDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: ClienteDiretorioItem[] | null = null;
let emVoo: Promise<ClienteDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<ClienteDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioClientes()
    .then((clientes) => {
      cache = clientes;
      emVoo = null;
      notificar();
      return clientes;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioClientes(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioClientes(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    clientes: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () => setEstado({ clientes: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((clientes) => setEstado({ clientes, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            clientes: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar o diretório de clientes.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
