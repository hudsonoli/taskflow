"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { ClienteDiretorioItem, ProjetoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import type { ArquivosCentralFiltros } from "@/types/arquivo";
import type { DemandaDiretorio } from "@/types/demanda";

const TIPO_LABELS: Record<NonNullable<ArquivosCentralFiltros["tipo"]>, string> = {
  anexo: "Anexo",
  layout: "Layout",
  link: "Link",
};

const STATUS_LABELS: Record<NonNullable<ArquivosCentralFiltros["status"]>, string> = {
  novo: "Novo",
  aprovado: "Aprovado",
  reprovado: "Reprovado",
  solicitar_alteracao: "Solicitar alteração",
};

export function ArquivosFiltros({
  filtros,
  onChange,
  clientes,
  projetos,
  demandas,
  usuarios,
  ocultarCliente = false,
  ocultarProjeto = false,
  compacto = false,
}: {
  filtros: ArquivosCentralFiltros;
  onChange: (filtros: ArquivosCentralFiltros) => void;
  clientes: ClienteDiretorioItem[];
  projetos: ProjetoDiretorioItem[];
  demandas: DemandaDiretorio[];
  usuarios: UsuarioDiretorioItem[];
  // Contexto fixo (aba de Projeto/Cliente): o recorte já vem definido por quem monta a tela.
  ocultarCliente?: boolean;
  ocultarProjeto?: boolean;
  // Dentro de modal/drawer: menos colunas (a largura útil é a do painel, não a da viewport).
  compacto?: boolean;
}) {
  function atualizar<K extends keyof ArquivosCentralFiltros>(chave: K, valor: ArquivosCentralFiltros[K]) {
    // Trocar Cliente/Projeto limpa o filtro de Demanda se ela não pertencer mais ao recorte
    // — evita um filtro "fantasma" que a UI mostra selecionado mas que já não bate com nada.
    const proximo: ArquivosCentralFiltros = { ...filtros, [chave]: valor || undefined, offset: 0 };
    if (chave === "clienteId" || chave === "projetoId") {
      const demanda = demandas.find((item) => item.id === proximo.demandaId);
      const aindaValida =
        demanda &&
        (!proximo.clienteId || demanda.clienteId === proximo.clienteId) &&
        (!proximo.projetoId || demanda.projetoId === proximo.projetoId);
      if (!aindaValida) proximo.demandaId = undefined;
    }
    onChange(proximo);
  }

  const projetosFiltrados = filtros.clienteId ? projetos.filter((projeto) => projeto.clienteId === filtros.clienteId) : projetos;
  const demandasFiltradas = demandas.filter(
    (demanda) =>
      (!filtros.clienteId || demanda.clienteId === filtros.clienteId) &&
      (!filtros.projetoId || demanda.projetoId === filtros.projetoId),
  );

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
          <SlidersHorizontal className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">Filtros</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">Busca e filtros rodam no servidor — nunca sobre tudo já carregado.</p>
        </div>
      </div>

      <div className="relative mb-3">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
        <input
          value={filtros.search ?? ""}
          onChange={(event) => atualizar("search", event.target.value)}
          placeholder="Buscar por nome, demanda, cliente ou projeto…"
          className="w-full rounded-xl border border-zinc-200 bg-zinc-50/70 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
        />
      </div>

      <div className={compacto ? "grid gap-3 sm:grid-cols-2" : "grid gap-3 sm:grid-cols-2 lg:grid-cols-4"}>
        {!ocultarCliente && (
          <Select
            label="Cliente"
            value={filtros.clienteId ?? ""}
            onChange={(event) => atualizar("clienteId", event.target.value)}
            options={[{ value: "", label: "Todos" }, ...clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome }))]}
          />
        )}
        {!ocultarProjeto && (
          <Select
            label="Projeto"
            value={filtros.projetoId ?? ""}
            onChange={(event) => atualizar("projetoId", event.target.value)}
            options={[{ value: "", label: "Todos" }, ...projetosFiltrados.map((projeto) => ({ value: projeto.id, label: projeto.nome }))]}
          />
        )}
        <Select
          label="Demanda"
          value={filtros.demandaId ?? ""}
          onChange={(event) => atualizar("demandaId", event.target.value)}
          options={[
            { value: "", label: "Todas" },
            ...demandasFiltradas.map((demanda) => ({ value: demanda.id, label: `#${demanda.numeroOperacional} — ${demanda.nome}` })),
          ]}
        />
        <Select
          label="Usuário"
          value={filtros.usuarioId ?? ""}
          onChange={(event) => atualizar("usuarioId", event.target.value)}
          options={[{ value: "", label: "Todos" }, ...usuarios.map((usuario) => ({ value: usuario.id, label: usuario.nome }))]}
        />
        <Select
          label="Tipo"
          value={filtros.tipo ?? ""}
          onChange={(event) => atualizar("tipo", (event.target.value || undefined) as ArquivosCentralFiltros["tipo"])}
          options={[{ value: "", label: "Todos" }, ...Object.entries(TIPO_LABELS).map(([value, label]) => ({ value, label }))]}
        />
        <Select
          label="Status (layout)"
          value={filtros.status ?? ""}
          onChange={(event) => atualizar("status", (event.target.value || undefined) as ArquivosCentralFiltros["status"])}
          options={[{ value: "", label: "Todos" }, ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))]}
        />
        <Input
          label="De"
          type="date"
          value={filtros.dataInicio ? filtros.dataInicio.slice(0, 10) : ""}
          onChange={(event) => atualizar("dataInicio", event.target.value ? `${event.target.value}T00:00:00Z` : undefined)}
        />
        <Input
          label="Até"
          type="date"
          value={filtros.dataFim ? filtros.dataFim.slice(0, 10) : ""}
          onChange={(event) => atualizar("dataFim", event.target.value ? `${event.target.value}T23:59:59Z` : undefined)}
        />
      </div>
    </div>
  );
}
