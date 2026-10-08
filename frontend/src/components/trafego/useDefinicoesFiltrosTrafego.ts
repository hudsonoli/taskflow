"use client";

import { useMemo } from "react";
import { Building2, CalendarClock, CircleDot, FolderKanban, Flag, User, Users } from "lucide-react";
import type { MemberOption } from "@/components/ui/MemberSelector";
import type { ClienteDiretorioItem, DepartamentoDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import { prioridadeDemandaLabels } from "@/lib/demandas";
import { PRESETS_DATA } from "@/lib/filtros-avancados";
import { CAMPO_TRAFEGO } from "@/lib/filtros-trafego";
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
 * Definições dos filtros avançados de Tráfego. O domínio é a SESSÃO DE TRABALHO: usuário e departamento são da sessão;
 * cliente, projeto, prioridade e prazo são atributos da Demanda em que ela acontece (o servidor os resolve por junção).
 * "Status da sessão" só distingue em execução/encerradas (sem "não é": o servidor mantém a semântica dos indicadores).
 */
export function useDefinicoesFiltrosTrafego({
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
        id: CAMPO_TRAFEGO.usuario,
        label: "Usuário",
        icone: User,
        tipo: "enum",
        valoresAbertos: true,
        buscarOpcoes: async (parametros) => (await buscarOpcoes(parametros)).map(opcaoDeUsuario),
        resolverOpcoes: async (ids) => (await resolverSelecionados(ids)).map(opcaoDeUsuario),
        placeholderBusca: "Buscar pessoa…",
        mensagemVazio: "Nenhum usuário encontrado",
      },
      {
        id: CAMPO_TRAFEGO.departamento,
        label: "Departamento",
        icone: Users,
        tipo: "enum",
        valoresAbertos: true,
        opcoesCarregadas: departamentos.length > 0 || diretoriosProntos,
        opcoes: departamentos.map((departamento) => ({ value: departamento.id, label: departamento.nome })),
      },
      {
        id: CAMPO_TRAFEGO.cliente,
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
        id: CAMPO_TRAFEGO.projeto,
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
        id: CAMPO_TRAFEGO.prioridade,
        label: "Prioridade",
        icone: Flag,
        tipo: "enum",
        opcoes: Object.entries(prioridadeDemandaLabels).map(([value, label]) => ({ value, label })),
      },
      {
        id: CAMPO_TRAFEGO.prazo,
        label: "Prazo da demanda",
        icone: CalendarClock,
        tipo: "data",
        presets: [PRESETS_DATA.hoje, PRESETS_DATA.amanha, PRESETS_DATA.esta_semana, PRESETS_DATA.atrasado],
      },
      {
        id: CAMPO_TRAFEGO.status,
        label: "Status da sessão",
        icone: CircleDot,
        tipo: "enum",
        multiplo: false,
        permiteExcluir: false,
        opcoes: [
          { value: "ativa", label: "Em execução" },
          { value: "encerrada", label: "Encerradas" },
        ],
      },
    ],
    [departamentos, clientes, projetos, diretoriosProntos, buscarOpcoes, resolverSelecionados],
  );
}
