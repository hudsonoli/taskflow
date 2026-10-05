"use client";

import { useEffect, useMemo, useSyncExternalStore } from "react";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import {
  assinarUsuariosPorIds,
  ehIdDeUsuario,
  falhouRecentemente,
  resolverUsuariosPorIds,
  usuarioEmCache,
  versaoUsuariosPorIds,
} from "@/lib/usuariosPorIds";

type Resultado = {
  /** Diretório global + os usuários dos `referencias` que ficaram fora da janela de 200. */
  usuarios: UsuarioDiretorioItem[];
  /** Ainda há nome sendo resolvido (diretório carregando ou consulta por ids em curso). */
  resolvendo: boolean;
};

/**
 * Para telas que só TRADUZEM id -> nome/avatar: devolve o diretório global acrescido dos usuários
 * citados em `referencias` que o diretório (limitado a 200) não trouxe, buscados numa única
 * chamada em lote (`GET /usuarios/diretorio/por-ids`, com cache por id e agrupamento entre
 * componentes — ver `usuariosPorIds.ts`).
 *
 * Com até 200 usuários na empresa nada é pedido além do diretório. Quem consome continua usando
 * `usuarios.find(...)` como antes; enquanto `resolvendo` for verdadeiro, deve mostrar um
 * placeholder ("Carregando…") em vez de UUID ou "Usuário removido".
 *
 * Se a consulta por ids falhar, `usuarios` fica só com o diretório (o fallback seguro de sempre) e
 * a tela segue funcionando; nova tentativa só depois de alguns segundos.
 *
 * Não serve para montar opções de seleção (isso é o modo servidor do `MemberSelector`).
 */
export function useUsuariosComIds(referencias: ReadonlyArray<string | null | undefined>): Resultado {
  const { usuarios: diretorio, carregando } = useDiretorioUsuarios();
  // Muda quando o cache/as falhas mudam; é o que reexecuta os memos abaixo.
  const versao = useSyncExternalStore(assinarUsuariosPorIds, versaoUsuariosPorIds, versaoUsuariosPorIds);

  const chave = referencias.filter((id): id is string => typeof id === "string" && ehIdDeUsuario(id)).join(",");

  const foraDoDiretorio = useMemo(() => {
    if (carregando || !chave) return [];
    const conhecidos = new Set(diretorio.map((usuario) => usuario.id));
    return [...new Set(chave.split(",").map((id) => id.toLowerCase()))].filter((id) => !conhecidos.has(id));
  }, [chave, diretorio, carregando]);

  const { extras, pendentes } = useMemo(() => {
    void versao;
    const encontrados: UsuarioDiretorioItem[] = [];
    const faltando: string[] = [];
    for (const id of foraDoDiretorio) {
      const doCache = usuarioEmCache(id);
      if (doCache) encontrados.push(doCache);
      else if (doCache === undefined && !falhouRecentemente(id)) faltando.push(id);
    }
    return { extras: encontrados, pendentes: faltando };
  }, [foraDoDiretorio, versao]);

  const chavePendentes = pendentes.join(",");
  useEffect(() => {
    if (!chavePendentes) return;
    // O resultado chega pelo cache (`versao`); falha vira marca de falha e o fallback seguro.
    resolverUsuariosPorIds(chavePendentes.split(",")).catch(() => undefined);
  }, [chavePendentes]);

  const usuarios = useMemo(() => (extras.length > 0 ? [...diretorio, ...extras] : diretorio), [diretorio, extras]);
  return { usuarios, resolvendo: carregando || pendentes.length > 0 };
}
