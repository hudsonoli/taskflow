"use client";

import { useMemo } from "react";
import { Building2, CalendarClock, CircleDot, Flag, FolderKanban, Inbox, User, Users } from "lucide-react";
import type { MemberOption } from "@/components/ui/MemberSelector";
import type { ClienteDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import { prioridadeDemandaLabels, statusDemandaLabels } from "@/lib/demandas";
import { PRESETS_DATA } from "@/lib/filtros-avancados";
import { CAMPO_MEU_DEPARTAMENTO } from "@/lib/filtros-meu-departamento";
import { useUsuariosSelector } from "@/lib/useResponsaveisSelector";
import type { DefinicaoFiltro, OpcaoFiltro } from "@/types/filtros";

function opcaoDeUsuario(membro: MemberOption): OpcaoFiltro {
  return {
    value: membro.id,
    label: membro.nome,
    avatar: { nome: membro.nome, corIdentificacao: membro.corIdentificacao, fotoUrl: membro.fotoUrl },
  };
}

/**
 * Definições dos filtros avançados de "Meu Departamento". NÃO há filtro de Departamento: o departamento é o escopo da tela
 * (o atual do usuário, resolvido no servidor) — os filtros só refinam. As opções de Responsável vêm do departamento ATUAL
 * (`departamentoId`): quando o contexto muda (Fase 5), a definição é recriada e a lista deixa de oferecer gente do anterior.
 */
export function useDefinicoesFiltrosMeuDepartamento({
  departamentoId,
  equipes,
  clientes,
  projetos,
  diretoriosProntos,
}: {
  departamentoId: string | undefined;
  equipes: Array<{ id: string; nome: string }>;
  clientes: ClienteDiretorioItem[];
  projetos: ProjetoDiretorioItem[];
  diretoriosProntos: boolean;
}): DefinicaoFiltro[] {
  const { buscarOpcoes, resolverSelecionados } = useUsuariosSelector({ departamentoId });

  return useMemo<DefinicaoFiltro[]>(
    () => [
      {
        id: CAMPO_MEU_DEPARTAMENTO.responsavel,
        label: "Responsável",
        icone: User,
        tipo: "enum",
        valoresAbertos: true,
        buscarOpcoes: async (parametros) => (await buscarOpcoes(parametros)).map(opcaoDeUsuario),
        resolverOpcoes: async (ids) => (await resolverSelecionados(ids)).map(opcaoDeUsuario),
        placeholderBusca: "Buscar colaborador…",
        mensagemVazio: "Nenhum colaborador encontrado",
      },
      {
        id: CAMPO_MEU_DEPARTAMENTO.equipe,
        label: "Equipe",
        icone: Users,
        tipo: "enum",
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: equipes.map((equipe) => ({ value: equipe.id, label: equipe.nome })),
      },
      {
        id: CAMPO_MEU_DEPARTAMENTO.cliente,
        label: "Cliente",
        icone: Building2,
        tipo: "enum",
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome })),
        placeholderBusca: "Buscar cliente…",
        buscavel: true,
      },
      {
        id: CAMPO_MEU_DEPARTAMENTO.projeto,
        label: "Projeto",
        icone: FolderKanban,
        tipo: "enum",
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome })),
        placeholderBusca: "Buscar projeto…",
        buscavel: true,
      },
      {
        id: CAMPO_MEU_DEPARTAMENTO.status,
        label: "Status",
        icone: CircleDot,
        tipo: "enum",
        opcoes: Object.entries(statusDemandaLabels).map(([value, label]) => ({ value, label })),
      },
      {
        id: CAMPO_MEU_DEPARTAMENTO.prioridade,
        label: "Prioridade",
        icone: Flag,
        tipo: "enum",
        opcoes: Object.entries(prioridadeDemandaLabels).map(([value, label]) => ({ value, label })),
      },
      {
        id: CAMPO_MEU_DEPARTAMENTO.prazo,
        label: "Prazo",
        icone: CalendarClock,
        tipo: "data",
        presets: [PRESETS_DATA.hoje, PRESETS_DATA.amanha, PRESETS_DATA.esta_semana, PRESETS_DATA.este_mes, PRESETS_DATA.atrasado],
      },
      {
        id: CAMPO_MEU_DEPARTAMENTO.origem,
        label: "Origem",
        icone: Inbox,
        tipo: "enum",
        multiplo: false,
        permiteExcluir: false,
        opcoes: [
          { value: "cliente", label: "Cliente" },
          { value: "interna", label: "Interna" },
        ],
      },
    ],
    [equipes, clientes, projetos, diretoriosProntos, buscarOpcoes, resolverSelecionados],
  );
}
