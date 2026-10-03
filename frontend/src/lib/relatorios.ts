import type { ClienteDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import type { PontoLinha } from "@/types/relatorios";

// D4B — os cálculos de Relatórios (abertas por projeto, volume por colaborador, volume semanal,
// performance de colaborador) saíram daqui: rodavam sobre `AppDataContext.demandas`
// (`GET /demandas?limit=200`) e hoje vêm agregados do servidor (`GET /relatorios/**`). Sobram só
// helpers de apresentação/seleção que não tocam em Demanda.

/**
 * Consulta histórica, não seleção de vínculo novo — não filtra `status`. O diretório de
 * Cliente já inclui arquivado por padrão (`ClienteRepository.list_diretorio`), então um
 * cliente descontinuado com Demandas antigas continua aparecendo aqui em vez de sumir do
 * relatório.
 */
export function resolveClientesComProjeto(projetos: ProjetoDiretorioItem[], clientes: ClienteDiretorioItem[]) {
  return clientes.filter((cliente) => projetos.some((projeto) => projeto.clienteId === cliente.id));
}

/** Ponto do gráfico semanal a partir da segunda-feira ("YYYY-MM-DD") devolvida pelo servidor; o rótulo é `dd/MM`. */
export function pontoDaSemana(inicioSemana: string, value: number): PontoLinha {
  const [, mes, dia] = inicioSemana.split("-");
  return { semanaLabel: `${dia}/${mes}`, inicioSemana, value };
}
