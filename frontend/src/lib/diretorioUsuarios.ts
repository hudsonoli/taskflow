"use client";

import { useEffect, useState } from "react";
import { listDiretorioUsuarios, type UsuarioDiretorioItem } from "@/lib/api-backend";

/**
 * Cache remoto deduplicado do diretório de usuários — usado pelos seletores de
 * responsável/membro em todo o app (ver docs/padrao-arquivamento.md e lib/referencias.ts).
 *
 * Sem localStorage/sessionStorage: é um cache em memória (módulo), válido só durante a
 * sessão do navegador. Sem fallback pra mock — se a busca falhar, `erro` fica preenchido e
 * `usuarios` fica vazio, nunca dado fictício. Requisições concorrentes reaproveitam a mesma
 * promise em voo (dedup). `invalidarDiretorioUsuarios()` limpa o cache e já dispara um
 * refetch, pra todo componente assinante atualizar sozinho após uma mutação (criar/editar/
 * excluir/restaurar usuário).
 */

type Estado = {
  usuarios: UsuarioDiretorioItem[];
  carregando: boolean;
  erro: string | null;
};

let cache: UsuarioDiretorioItem[] | null = null;
let emVoo: Promise<UsuarioDiretorioItem[]> | null = null;
const assinantes = new Set<() => void>();

function notificar() {
  assinantes.forEach((assinante) => assinante());
}

function buscar(): Promise<UsuarioDiretorioItem[]> {
  if (emVoo) return emVoo;
  emVoo = listDiretorioUsuarios()
    .then((usuarios) => {
      cache = usuarios;
      emVoo = null;
      notificar();
      return usuarios;
    })
    .catch((error) => {
      emVoo = null;
      throw error;
    });
  return emVoo;
}

export function invalidarDiretorioUsuarios(): void {
  cache = null;
  emVoo = null;
  notificar();
  void buscar();
}

export function useDiretorioUsuarios(): Estado {
  const [estado, setEstado] = useState<Estado>(() => ({
    usuarios: cache ?? [],
    carregando: cache === null,
    erro: null,
  }));

  useEffect(() => {
    const assinante = () => setEstado({ usuarios: cache ?? [], carregando: cache === null, erro: null });
    assinantes.add(assinante);

    if (cache === null) {
      buscar()
        .then((usuarios) => setEstado({ usuarios, carregando: false, erro: null }))
        .catch((error) => {
          setEstado({
            usuarios: [],
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar o diretório de usuários.",
          });
        });
    }

    return () => {
      assinantes.delete(assinante);
    };
  }, []);

  return estado;
}
