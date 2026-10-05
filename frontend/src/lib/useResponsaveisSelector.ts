"use client";

import { useCallback, useEffect, useState } from "react";
import type { BuscarOpcoesMembros, MemberOption, ResolverSelecionadosMembros } from "@/components/ui/MemberSelector";
import { buscarDiretorioUsuarios, type DepartamentoDiretorioItem, type UsuarioDiretorioItem } from "@/lib/api-backend";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { resolverUsuariosPorIds } from "@/lib/usuariosPorIds";

type OpcoesSeletor = {
  /** Subtítulo = nome do departamento do usuário (Demandas). Sem isso, a opção só tem nome/avatar. */
  comSubtitulo?: boolean;
  /** Restringe as opções a um departamento (filtro exato do servidor). */
  departamentoId?: string;
  /** Selecionado que não está `ativo` aparece como "<nome> (indisponível)". */
  marcarIndisponiveis?: boolean;
  /**
   * Oferece usuários de QUALQUER status (inclusive inativo/bloqueado/arquivado) — para filtros e telas
   * administrativas que consultam registros históricos. Padrão: só `ativo` (novo vínculo).
   */
  todosStatus?: boolean;
};

function paraOpcao(
  usuario: UsuarioDiretorioItem,
  departamentos: DepartamentoDiretorioItem[],
  { comSubtitulo, marcarIndisponiveis }: OpcoesSeletor,
): MemberOption {
  return {
    id: usuario.id,
    nome: marcarIndisponiveis && usuario.status !== "ativo" ? `${usuario.nome} (indisponível)` : usuario.nome,
    subtitulo:
      comSubtitulo && usuario.departamentoId
        ? departamentos.find((departamento) => departamento.id === usuario.departamentoId)?.nome
        : undefined,
    corIdentificacao: usuario.corIdentificacao,
    fotoUrl: usuario.fotoUrl,
  };
}

/**
 * Fonte dos seletores de USUÁRIO no modo servidor do `MemberSelector` (identidade = UUID):
 * responsáveis de Demanda, de Departamento, líder/membros de Equipe, responsáveis padrão de etapa de
 * Workflow, responsável sugerido de Modelo de Campanha, responsáveis de Projeto e filtro de
 * colaborador. Sem o corte do diretório de 200.
 *
 * Mesma regra de todos eles (usuário `ativo` para NOVO vínculo; quem já está selecionado aparece
 * mesmo se arquivado/inativo/bloqueado):
 * - `buscarOpcoes`: página do diretório filtrada no servidor por nome e por `status=ativo`;
 * - `resolverSelecionados`: nome (qualquer status) de quem já está selecionado, via
 *   `resolverUsuariosPorIds` (cache por id + lote único) — é o que faz o usuário nº 201+ aparecer com
 *   nome ao abrir um registro existente, mesmo com vários seletores/etapas na mesma tela.
 */
export function useUsuariosSelector(opcoes: OpcoesSeletor = {}): { buscarOpcoes: BuscarOpcoesMembros; resolverSelecionados: ResolverSelecionadosMembros } {
  const { departamentos } = useDiretorioDepartamentos();
  const { comSubtitulo = false, departamentoId, marcarIndisponiveis = false, todosStatus = false } = opcoes;

  const buscarOpcoes = useCallback<BuscarOpcoesMembros>(
    async ({ busca, limit, offset }) => {
      const usuarios = await buscarDiretorioUsuarios({
        search: busca,
        status: todosStatus ? undefined : "ativo",
        departamentoId,
        limit,
        offset,
      });
      return usuarios.map((usuario) => paraOpcao(usuario, departamentos, { comSubtitulo }));
    },
    [departamentos, comSubtitulo, departamentoId, todosStatus],
  );

  const resolverSelecionados = useCallback<ResolverSelecionadosMembros>(
    async (ids) => (await resolverUsuariosPorIds(ids)).map((usuario) => paraOpcao(usuario, departamentos, { comSubtitulo, marcarIndisponiveis })),
    [departamentos, comSubtitulo, marcarIndisponiveis],
  );

  return { buscarOpcoes, resolverSelecionados };
}

/** Responsáveis de Demanda: o seletor genérico, com o departamento como subtítulo. */
export function useResponsaveisSelector() {
  return useUsuariosSelector({ comSubtitulo: true });
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
