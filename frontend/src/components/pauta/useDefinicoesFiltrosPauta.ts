"use client";

import { useMemo } from "react";
import { Building2, Flag, FolderKanban, Network, User } from "lucide-react";
import type { MemberOption } from "@/components/ui/MemberSelector";
import type { ClienteDiretorioItem, DepartamentoDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import { prioridadeDemandaLabels } from "@/lib/demandas";
import { CAMPO_PAUTA } from "@/lib/filtros-pauta";
import { useUsuariosSelector } from "@/lib/useResponsaveisSelector";
import type { DefinicaoFiltro, OpcaoFiltro } from "@/types/filtros";

function opcaoDeUsuario(membro: MemberOption): OpcaoFiltro {
  return { value: membro.id, label: membro.nome, avatar: { nome: membro.nome, corIdentificacao: membro.corIdentificacao, fotoUrl: membro.fotoUrl } };
}

/**
 * Filtros avançados da Pauta operacional por etapa: Colaborador, Departamento, Cliente, Projeto e Prioridade. Colaborador e Departamento se aplicam à responsabilidade
 * EFETIVA da etapa (não ao responsável geral bruto nem ao departamento cadastral da pessoa). O servidor só executa "é"/"é um de" — sem "não é". Colaborador busca no
 * servidor, em qualquer status de usuário (para localizar o trabalho de quem já saiu).
 */
export function useDefinicoesFiltrosPauta({
  departamentos,
  clientes,
  projetos,
  diretoriosProntos,
}: {
  departamentos: DepartamentoDiretorioItem[];
  clientes: ClienteDiretorioItem[];
  projetos: ProjetoDiretorioItem[];
  diretoriosProntos: boolean;
}): DefinicaoFiltro[] {
  const { buscarOpcoes, resolverSelecionados } = useUsuariosSelector({ todosStatus: true });

  return useMemo<DefinicaoFiltro[]>(
    () => [
      {
        id: CAMPO_PAUTA.responsavel,
        label: "Colaborador",
        icone: User,
        tipo: "enum",
        permiteExcluir: false,
        valoresAbertos: true,
        buscarOpcoes: async (parametros) => (await buscarOpcoes(parametros)).map(opcaoDeUsuario),
        resolverOpcoes: async (ids) => (await resolverSelecionados(ids)).map(opcaoDeUsuario),
        placeholderBusca: "Buscar pessoa…",
        mensagemVazio: "Nenhum usuário encontrado",
      },
      {
        id: CAMPO_PAUTA.departamento,
        label: "Departamento",
        icone: Network,
        tipo: "enum",
        permiteExcluir: false,
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        // Filtro sobre etapas existentes: inclui departamento arquivado (etapas antigas ainda o referenciam).
        opcoes: departamentos.map((departamento) => ({
          value: departamento.id,
          label: departamento.status === "arquivado" ? `${departamento.nome} (arquivado)` : departamento.nome,
        })),
      },
      {
        id: CAMPO_PAUTA.cliente,
        label: "Cliente",
        icone: Building2,
        tipo: "enum",
        permiteExcluir: false,
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome })),
        placeholderBusca: "Buscar cliente…",
        buscavel: true,
      },
      {
        id: CAMPO_PAUTA.projeto,
        label: "Projeto",
        icone: FolderKanban,
        tipo: "enum",
        permiteExcluir: false,
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome })),
        placeholderBusca: "Buscar projeto…",
        buscavel: true,
      },
      {
        id: CAMPO_PAUTA.prioridade,
        label: "Prioridade",
        icone: Flag,
        tipo: "enum",
        permiteExcluir: false,
        opcoes: Object.entries(prioridadeDemandaLabels).map(([value, label]) => ({ value, label })),
      },
    ],
    [departamentos, clientes, projetos, diretoriosProntos, buscarOpcoes, resolverSelecionados],
  );
}
