"use client";

import { useMemo } from "react";
import { Building2, CalendarClock, CircleDot, Flag, FolderKanban, Inbox, Network, User, Users } from "lucide-react";
import type { MemberOption } from "@/components/ui/MemberSelector";
import type { ClienteDiretorioItem, DepartamentoDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import { prioridadeDemandaLabels, statusDemandaLabels } from "@/lib/demandas";
import { PRESETS_DATA } from "@/lib/filtros-avancados";
import { CAMPO_PAUTA } from "@/lib/filtros-pauta";
import { STATUS_DA_FILA } from "@/lib/meu-dia";
import { useUsuariosSelector } from "@/lib/useResponsaveisSelector";
import type { DemandaStatus } from "@/types/demanda";
import type { DefinicaoFiltro, OpcaoFiltro } from "@/types/filtros";

function opcaoDeUsuario(membro: MemberOption): OpcaoFiltro {
  return { value: membro.id, label: membro.nome, avatar: { nome: membro.nome, corIdentificacao: membro.corIdentificacao, fotoUrl: membro.fotoUrl } };
}

/**
 * Filtros avançados da Pauta GLOBAL. Aqui o Departamento É um filtro (o escopo é a empresa inteira). Status oferece só os da fila
 * operacional (a Pauta mostra o que está em andamento, não o que já terminou). Responsável busca no servidor, em qualquer status
 * de usuário (para localizar o trabalho de quem já saiu).
 */
export function useDefinicoesFiltrosPauta({
  departamentos,
  equipes,
  clientes,
  projetos,
  diretoriosProntos,
}: {
  departamentos: DepartamentoDiretorioItem[];
  equipes: Array<{ id: string; nome: string }>;
  clientes: ClienteDiretorioItem[];
  projetos: ProjetoDiretorioItem[];
  diretoriosProntos: boolean;
}): DefinicaoFiltro[] {
  const { buscarOpcoes, resolverSelecionados } = useUsuariosSelector({ todosStatus: true });

  return useMemo<DefinicaoFiltro[]>(
    () => [
      {
        id: CAMPO_PAUTA.departamento,
        label: "Departamento",
        icone: Network,
        tipo: "enum",
        permiteExcluir: false,
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        // Filtro sobre demandas existentes: inclui departamento arquivado (demandas antigas ainda o referenciam).
        opcoes: departamentos.map((departamento) => ({
          value: departamento.id,
          label: departamento.status === "arquivado" ? `${departamento.nome} (arquivado)` : departamento.nome,
        })),
      },
      {
        id: CAMPO_PAUTA.responsavel,
        label: "Responsável",
        icone: User,
        tipo: "enum",
        valoresAbertos: true,
        buscarOpcoes: async (parametros) => (await buscarOpcoes(parametros)).map(opcaoDeUsuario),
        resolverOpcoes: async (ids) => (await resolverSelecionados(ids)).map(opcaoDeUsuario),
        placeholderBusca: "Buscar pessoa…",
        mensagemVazio: "Nenhum usuário encontrado",
      },
      {
        id: CAMPO_PAUTA.equipe,
        label: "Equipe",
        icone: Users,
        tipo: "enum",
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: equipes.map((equipe) => ({ value: equipe.id, label: equipe.nome })),
      },
      {
        id: CAMPO_PAUTA.cliente,
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
        id: CAMPO_PAUTA.projeto,
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
        id: CAMPO_PAUTA.status,
        label: "Status",
        icone: CircleDot,
        tipo: "enum",
        opcoes: STATUS_DA_FILA.map((valor) => ({ value: valor, label: statusDemandaLabels[valor as DemandaStatus] })),
      },
      {
        id: CAMPO_PAUTA.prioridade,
        label: "Prioridade",
        icone: Flag,
        tipo: "enum",
        opcoes: Object.entries(prioridadeDemandaLabels).map(([value, label]) => ({ value, label })),
      },
      {
        id: CAMPO_PAUTA.prazo,
        label: "Prazo",
        icone: CalendarClock,
        tipo: "data",
        presets: [PRESETS_DATA.hoje, PRESETS_DATA.amanha, PRESETS_DATA.esta_semana, PRESETS_DATA.atrasado],
      },
      {
        id: CAMPO_PAUTA.origem,
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
    [departamentos, equipes, clientes, projetos, diretoriosProntos, buscarOpcoes, resolverSelecionados],
  );
}
