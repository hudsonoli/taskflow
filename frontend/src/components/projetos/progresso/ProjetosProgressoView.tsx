"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronsDownUp, ChevronsUpDown, RotateCw, Search, X } from "lucide-react";
import { DemandaDetailsDrawer } from "@/components/demandas/DemandaDetailsDrawer";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { Select } from "@/components/ui/Select";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { statusDemandaLabels } from "@/lib/demandas";
import { classificarTarefa } from "@/lib/escopo-operacional";
import { carregarProgressoProjetos, MAX_TAREFAS_CARREGADAS, type DadosProgresso } from "@/lib/progresso-projetos-dados";
import {
  aplicarFiltros,
  FILTROS_PROGRESSO_VAZIOS,
  filtroDeTarefaAtivo,
  montarProjetos,
  responsaveisDaTarefa,
  type FiltrosProgresso,
} from "@/lib/projetos-progresso";
import { useTenantPath } from "@/lib/useTenantPath";
import { useUsuariosPorIds, useUsuariosSelector } from "@/lib/useResponsaveisSelector";
import type { Demanda, DemandaStatus } from "@/types/demanda";
import { ProjetoProgressoGrupo } from "./ProjetoProgressoGrupo";

/** Quantos projetos já chegam abertos quando o usuário ainda não expandiu/recolheu nada. */
const ABERTOS_POR_PADRAO = 3;

const STATUS_FILTRAVEIS: DemandaStatus[] = ["bloqueada", "em_execucao", "aguardando_cliente", "pausada", "planejada", "rascunho", "concluida"];

type Estado = { dados: DadosProgresso; instante: Date };

/**
 * Progresso de Projetos — leitura operacional agrupada por projeto. NADA se edita aqui: status, responsáveis e prazo mudam nas telas de sempre (a linha abre o painel
 * de detalhes existente). O percentual do projeto é só "tarefas concluídas / total"; o andamento do workflow aparece por tarefa, separado, como "etapas concluídas / total".
 */
export function ProjetosProgressoView() {
  const router = useRouter();
  const tp = useTenantPath();
  const [estado, setEstado] = useState<Estado | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [filtros, setFiltros] = useState<FiltrosProgresso>(FILTROS_PROGRESSO_VAZIOS);
  // null = padrão (primeiros projetos abertos); depois do primeiro clique vira o conjunto explícito.
  const [expandidos, setExpandidos] = useState<Set<string> | null>(null);
  const [selecionadaId, setSelecionadaId] = useState<string | null>(null);

  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();
  const seletorUsuarios = useUsuariosSelector({ todosStatus: true });

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const dados = await carregarProgressoProjetos();
      setEstado({ dados, instante: new Date() });
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar o progresso dos projetos.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 0);
    return () => clearTimeout(timeout);
  }, [carregar]);

  const instante = estado?.instante;
  const estaAtrasada = useCallback((demanda: Demanda) => (instante ? classificarTarefa(demanda, instante).atrasada : false), [instante]);

  const grupos = useMemo(() => (estado ? montarProjetos(estado.dados.projetos, estado.dados.tarefas, estaAtrasada) : []), [estado, estaAtrasada]);
  const visiveis = useMemo(() => aplicarFiltros(grupos, filtros), [grupos, filtros]);
  const totalPorProjeto = useMemo(() => new Map(grupos.map((grupo) => [grupo.projeto.id, grupo.resumo.total])), [grupos]);

  // Todos os usuários que aparecem nas linhas (responsáveis da etapa atual + quem trabalha agora): UMA resolução em lote, nunca uma por linha.
  const idsUsuarios = useMemo(() => {
    const ids = new Set<string>();
    for (const grupo of visiveis) {
      for (const demanda of grupo.tarefas) {
        responsaveisDaTarefa(demanda).usuarioIds.forEach((id) => ids.add(id));
      }
    }
    if (estado?.dados.agora.fonte === "pessoas") Object.values(estado.dados.agora.porDemanda).forEach((lista) => lista.forEach((id) => ids.add(id)));
    return [...ids].sort();
  }, [visiveis, estado]);
  const usuarios = useUsuariosPorIds(idsUsuarios);

  const clientesDosProjetos = useMemo(() => {
    const ids = new Set((estado?.dados.projetos ?? []).map((projeto) => projeto.clienteId).filter(Boolean));
    return clientes.filter((cliente) => ids.has(cliente.id)).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  }, [clientes, estado]);
  const nomeDoCliente = (clienteId: string) => (clienteId ? (clientes.find((cliente) => cliente.id === clienteId)?.nome ?? "Cliente") : "Projeto interno");

  const filtrando = filtroDeTarefaAtivo(filtros) || filtros.clienteId !== "";
  const todosIds = visiveis.map((grupo) => grupo.projeto.id);
  const abertos = expandidos ?? new Set(filtroDeTarefaAtivo(filtros) ? todosIds : todosIds.slice(0, ABERTOS_POR_PADRAO));

  function alternar(id: string) {
    const proximo = new Set(abertos);
    if (!proximo.delete(id)) proximo.add(id);
    setExpandidos(proximo);
  }

  const selecionada = estado?.dados.tarefas.find((demanda) => demanda.id === selecionadaId);

  // O painel de detalhes devolve a tarefa já atualizada: o resumo do projeto e as linhas refletem o servidor sem recarregar tudo.
  function aoMudarTarefa(proxima: Demanda) {
    setEstado((atual) => (atual ? { ...atual, dados: { ...atual.dados, tarefas: atual.dados.tarefas.map((demanda) => (demanda.id === proxima.id ? proxima : demanda)) } } : atual));
  }

  function atualizar(campo: Partial<FiltrosProgresso>) {
    setFiltros((atual) => ({ ...atual, ...campo }));
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(4,minmax(0,1fr))]">
          <label className="block text-sm md:col-span-2 lg:col-span-1">
            <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Busca</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
              <input
                value={filtros.busca}
                onChange={(event) => atualizar({ busca: event.target.value })}
                placeholder="Projeto, campanha, código ou tarefa"
                className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
              />
            </span>
          </label>
          <Select
            label="Cliente"
            value={filtros.clienteId}
            onChange={(event) => atualizar({ clienteId: event.target.value })}
            options={[{ value: "", label: "Todos" }, ...clientesDosProjetos.map((cliente) => ({ value: cliente.id, label: cliente.nome }))]}
          />
          <div className="block text-sm">
            <MemberSelector
              label="Responsável"
              variant="compact"
              multiple={false}
              values={filtros.responsavelId ? [filtros.responsavelId] : []}
              onChange={(ids) => atualizar({ responsavelId: ids[0] ?? "" })}
              buscarOpcoes={seletorUsuarios.buscarOpcoes}
              resolverSelecionados={seletorUsuarios.resolverSelecionados}
              placeholder="Todos"
            />
          </div>
          <Select
            label="Departamento"
            value={filtros.departamentoId}
            onChange={(event) => atualizar({ departamentoId: event.target.value })}
            options={[{ value: "", label: "Todos" }, ...departamentos.filter((departamento) => departamento.status === "ativo").map((departamento) => ({ value: departamento.id, label: departamento.nome }))]}
          />
          <Select
            label="Status"
            value={filtros.status}
            onChange={(event) => atualizar({ status: event.target.value as DemandaStatus | "" })}
            options={[{ value: "", label: "Todos" }, ...STATUS_FILTRAVEIS.map((status) => ({ value: status, label: statusDemandaLabels[status] }))]}
          />
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-fg-muted">
            {estado ? `${visiveis.length} de ${grupos.length} projeto(s)` : ""}
            {filtrando && " — filtros ativos; o resumo de cada projeto sempre considera todas as tarefas dele."}
          </p>
          <div className="flex flex-wrap gap-2">
            {filtrando && (
              <Button type="button" variant="ghost" className="px-3 py-1.5" onClick={() => setFiltros(FILTROS_PROGRESSO_VAZIOS)}>
                <X className="h-3.5 w-3.5" />
                Limpar filtros
              </Button>
            )}
            <Button type="button" variant="secondary" className="px-3 py-1.5" onClick={() => setExpandidos(new Set(todosIds))} disabled={visiveis.length === 0}>
              <ChevronsUpDown className="h-3.5 w-3.5" />
              Expandir tudo
            </Button>
            <Button type="button" variant="secondary" className="px-3 py-1.5" onClick={() => setExpandidos(new Set())} disabled={visiveis.length === 0}>
              <ChevronsDownUp className="h-3.5 w-3.5" />
              Recolher tudo
            </Button>
            <Button type="button" variant="secondary" className="px-3 py-1.5" onClick={() => void carregar()} disabled={carregando}>
              <RotateCw className="h-3.5 w-3.5" />
              Atualizar
            </Button>
          </div>
        </div>
      </div>

      {estado?.dados.truncado && (
        <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
          Há mais de {MAX_TAREFAS_CARREGADAS} tarefas nestes projetos: esta visão carregou as primeiras {estado.dados.tarefas.length}, então os totais e percentuais de alguns projetos podem estar incompletos.
        </div>
      )}

      {carregando && !estado ? (
        <EstadoCarregando cards={0} />
      ) : erro && !estado ? (
        <EstadoErro mensagem={erro} onRetry={() => void carregar()} />
      ) : visiveis.length === 0 ? (
        <EmptyState
          title={grupos.length === 0 ? "Nenhum projeto para acompanhar" : "Nenhum projeto corresponde aos filtros"}
          description={grupos.length === 0 ? "Quando houver projetos com tarefas, o progresso de cada um aparece aqui." : "Ajuste ou limpe os filtros para ver os projetos."}
        />
      ) : (
        <div className={carregando ? "flex flex-col gap-3 opacity-60 transition-opacity" : "flex flex-col gap-3"} aria-busy={carregando}>
          {visiveis.map((grupo) => (
            <ProjetoProgressoGrupo
              key={grupo.projeto.id}
              grupo={grupo}
              clienteNome={nomeDoCliente(grupo.projeto.clienteId)}
              aberto={abertos.has(grupo.projeto.id)}
              onAlternar={() => alternar(grupo.projeto.id)}
              tarefasTotal={totalPorProjeto.get(grupo.projeto.id) ?? 0}
              estaAtrasada={estaAtrasada}
              usuarios={usuarios}
              departamentos={departamentos}
              agora={estado?.dados.agora ?? { fonte: "nenhuma" }}
              onAbrirTarefa={(demanda) => setSelecionadaId(demanda.id)}
            />
          ))}
        </div>
      )}

      <DemandaDetailsDrawer
        key={selecionada?.id}
        demanda={selecionada}
        onClose={() => setSelecionadaId(null)}
        onChange={aoMudarTarefa}
        onEdit={() => router.push(tp("tarefas"))}
      />
    </div>
  );
}
