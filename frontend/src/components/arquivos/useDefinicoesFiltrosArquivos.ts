"use client";

import { useMemo } from "react";
import { Building2, CalendarDays, CircleDot, FileType, FolderKanban, ListTodo, User } from "lucide-react";
import type { MemberOption } from "@/components/ui/MemberSelector";
import type { ClienteDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import { STATUS_LAYOUT_OPTIONS } from "@/lib/arquivo-status-layout";
import { PRESETS_DATA } from "@/lib/filtros-avancados";
import { CAMPO_ARQUIVOS } from "@/lib/filtros-arquivos";
import { useUsuariosSelector } from "@/lib/useResponsaveisSelector";
import type { DemandaDiretorio } from "@/types/demanda";
import type { DefinicaoFiltro, OpcaoFiltro } from "@/types/filtros";

const TIPOS: OpcaoFiltro[] = [
  { value: "anexo", label: "Anexo" },
  { value: "layout", label: "Layout" },
  { value: "link", label: "Link" },
];

function opcaoDeUsuario(membro: MemberOption): OpcaoFiltro {
  return {
    value: membro.id,
    label: membro.nome,
    avatar: { nome: membro.nome, corIdentificacao: membro.corIdentificacao, fotoUrl: membro.fotoUrl },
  };
}

/**
 * Definições dos filtros avançados de Arquivos, só com os campos que o domínio realmente tem (arquivo → demanda → cliente/
 * projeto; remetente; tipo; status do layout; data de envio). Cliente e Projeto somem quando o recorte já é fixo (aba de
 * Cliente/Projeto). Memoizado: a identidade só muda quando as listas mudam.
 */
export function useDefinicoesFiltrosArquivos({
  clientes,
  projetos,
  demandas,
  ocultarCliente,
  ocultarProjeto,
  diretoriosProntos,
}: {
  clientes: ClienteDiretorioItem[];
  projetos: ProjetoDiretorioItem[];
  demandas: DemandaDiretorio[];
  ocultarCliente: boolean;
  ocultarProjeto: boolean;
  diretoriosProntos: boolean;
}): DefinicaoFiltro[] {
  const { buscarOpcoes, resolverSelecionados } = useUsuariosSelector({ todosStatus: true });

  return useMemo(() => {
    const definicoes: DefinicaoFiltro[] = [];
    if (!ocultarCliente) {
      definicoes.push({
        id: CAMPO_ARQUIVOS.cliente,
        label: "Cliente",
        icone: Building2,
        tipo: "enum",
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome })),
        placeholderBusca: "Buscar cliente…",
        buscavel: true,
      });
    }
    if (!ocultarProjeto) {
      definicoes.push({
        id: CAMPO_ARQUIVOS.projeto,
        label: "Projeto",
        icone: FolderKanban,
        tipo: "enum",
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome })),
        placeholderBusca: "Buscar projeto…",
        buscavel: true,
      });
    }
    definicoes.push(
      {
        id: CAMPO_ARQUIVOS.demanda,
        label: "Demanda",
        icone: ListTodo,
        tipo: "enum",
        valoresAbertos: true,
        opcoesCarregadas: diretoriosProntos,
        opcoes: demandas.map((demanda) => ({ value: demanda.id, label: `#${demanda.numeroOperacional} — ${demanda.nome}` })),
        placeholderBusca: "Buscar demanda…",
        buscavel: true,
      },
      { id: CAMPO_ARQUIVOS.tipo, label: "Tipo", icone: FileType, tipo: "enum", opcoes: TIPOS },
      {
        id: CAMPO_ARQUIVOS.status,
        label: "Status do layout",
        icone: CircleDot,
        tipo: "enum",
        opcoes: STATUS_LAYOUT_OPTIONS.map(({ value, label }) => ({ value, label })),
      },
      {
        id: CAMPO_ARQUIVOS.enviadoPor,
        label: "Enviado por",
        icone: User,
        tipo: "enum",
        valoresAbertos: true,
        buscarOpcoes: async (parametros) => (await buscarOpcoes(parametros)).map(opcaoDeUsuario),
        resolverOpcoes: async (ids) => (await resolverSelecionados(ids)).map(opcaoDeUsuario),
        placeholderBusca: "Buscar pessoa…",
        mensagemVazio: "Nenhum usuário encontrado",
      },
      {
        id: CAMPO_ARQUIVOS.dataEnvio,
        label: "Data de envio",
        icone: CalendarDays,
        tipo: "data",
        presets: [PRESETS_DATA.hoje, PRESETS_DATA.ontem, PRESETS_DATA.esta_semana, PRESETS_DATA.este_mes],
      },
    );
    return definicoes;
  }, [clientes, projetos, demandas, ocultarCliente, ocultarProjeto, diretoriosProntos, buscarOpcoes, resolverSelecionados]);
}
