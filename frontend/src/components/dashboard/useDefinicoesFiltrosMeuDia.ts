"use client";

import { useMemo } from "react";
import { Building2, CalendarClock, CircleDot, Flag, FolderKanban } from "lucide-react";
import type { ClienteDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import { prioridadeDemandaLabels, statusDemandaLabels } from "@/lib/demandas";
import { PRESETS_DATA } from "@/lib/filtros-avancados";
import { CAMPO_MEU_DEPARTAMENTO } from "@/lib/filtros-meu-departamento";
import { STATUS_DA_FILA } from "@/lib/meu-dia";
import type { DefinicaoFiltro } from "@/types/filtros";
import type { DemandaStatus } from "@/types/demanda";

/**
 * Filtros avançados do Meu Dia: só refinam a fila PESSOAL (Status, Cliente, Projeto, Prioridade, Prazo). NÃO há "Responsável": o Meu
 * Dia é fixo no próprio usuário (derivado do token no servidor). Mesmos ids de campo e mesmo mapeamento para a API que o Meu
 * Departamento (`filtrosMeuDepartamentoParaApi`); o status oferece só os da fila (concluída/cancelada/arquivada não fazem parte).
 */
export function useDefinicoesFiltrosMeuDia({
  clientes,
  projetos,
  diretoriosProntos,
}: {
  clientes: ClienteDiretorioItem[];
  projetos: ProjetoDiretorioItem[];
  diretoriosProntos: boolean;
}): DefinicaoFiltro[] {
  return useMemo<DefinicaoFiltro[]>(
    () => [
      {
        id: CAMPO_MEU_DEPARTAMENTO.status,
        label: "Status",
        icone: CircleDot,
        tipo: "enum",
        opcoes: STATUS_DA_FILA.map((valor) => ({ value: valor, label: statusDemandaLabels[valor as DemandaStatus] })),
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
        presets: [PRESETS_DATA.hoje, PRESETS_DATA.amanha, PRESETS_DATA.esta_semana, PRESETS_DATA.atrasado],
      },
    ],
    [clientes, projetos, diretoriosProntos],
  );
}
