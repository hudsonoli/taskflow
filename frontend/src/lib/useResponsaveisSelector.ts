"use client";

import { useCallback, useEffect, useState } from "react";
import type { BuscarOpcoesMembros, MemberOption, ResolverSelecionadosMembros } from "@/components/ui/MemberSelector";
import { buscarDiretorioUsuarios, type DepartamentoDiretorioItem, type UsuarioDiretorioItem } from "@/lib/api-backend";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { resolverUsuariosPorIds } from "@/lib/usuariosPorIds";

function paraOpcao(usuario: UsuarioDiretorioItem, departamentos: DepartamentoDiretorioItem[]): MemberOption {
  return {
    id: usuario.id,
    nome: usuario.nome,
    subtitulo: usuario.departamentoId
      ? departamentos.find((departamento) => departamento.id === usuario.departamentoId)?.nome
      : undefined,
    corIdentificacao: usuario.corIdentificacao,
    fotoUrl: usuario.fotoUrl,
  };
}

/**
 * Fonte do seletor de "Usuários responsáveis" de uma Demanda (criação, edição e aba Responsáveis),
 * no modo servidor do `MemberSelector`.
 *
 * Mesma semântica de antes (usuário `ativo` para NOVO vínculo; quem já é responsável aparece mesmo
 * se arquivado/inativo/bloqueado), agora sem o corte do diretório de 200:
 * - `buscarOpcoes`: página do diretório filtrada no servidor por nome e por `status=ativo`;
 * - `resolverSelecionados`: nome (qualquer status) de quem já está selecionado, onde quer que esteja
 *   no diretório — é o que faz um responsável nº 201+ aparecer com nome ao abrir a Demanda.
 */
export function useResponsaveisSelector(): { buscarOpcoes: BuscarOpcoesMembros; resolverSelecionados: ResolverSelecionadosMembros } {
  const { departamentos } = useDiretorioDepartamentos();

  const buscarOpcoes = useCallback<BuscarOpcoesMembros>(
    async ({ busca, limit, offset }) => {
      const usuarios = await buscarDiretorioUsuarios({ search: busca, status: "ativo", limit, offset });
      return usuarios.map((usuario) => paraOpcao(usuario, departamentos));
    },
    [departamentos],
  );

  const resolverSelecionados = useCallback<ResolverSelecionadosMembros>(
    async (ids) => (await resolverUsuariosPorIds(ids)).map((usuario) => paraOpcao(usuario, departamentos)),
    [departamentos],
  );

  return { buscarOpcoes, resolverSelecionados };
}

/** Nomes (só leitura) dos ids dados, resolvidos como acima. `null` enquanto carrega ou se a consulta falhar. */
export function useUsuariosPorIds(ids: string[]): Record<string, UsuarioDiretorioItem> | null {
  const chave = ids.join(",");
  const [estado, setEstado] = useState<{ chave: string; usuarios: Record<string, UsuarioDiretorioItem> } | null>(null);

  useEffect(() => {
    if (!chave) return;
    let cancelado = false;
    resolverUsuariosPorIds(chave.split(","))
      .then((usuarios) => {
        if (!cancelado) setEstado({ chave, usuarios: Object.fromEntries(usuarios.map((usuario) => [usuario.id, usuario])) });
      })
      .catch(() => {
        if (!cancelado) setEstado(null);
      });
    return () => {
      cancelado = true;
    };
  }, [chave]);

  // Só vale para a lista de ids ATUAL: resultado de uma lista anterior não é mostrado.
  return estado && estado.chave === chave ? estado.usuarios : null;
}
