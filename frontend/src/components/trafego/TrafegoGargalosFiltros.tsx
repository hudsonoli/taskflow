"use client";

import { X } from "lucide-react";
import { Combobox } from "@/components/ui/Combobox";
import { Select } from "@/components/ui/Select";
import { PERIODOS_GARGALOS, type PeriodoGargalosId } from "@/lib/trafego-operacional";

type Opcao = { value: string; label: string };

/**
 * Filtros dos GARGALOS: período (máx. 90 dias, como o backend), departamento, cliente e projeto — seletores já existentes do app —, mais a etapa escolhida a partir de uma linha do AGORA
 * (a etapa é filtrada por UMA etapa materializada, que o AGORA expõe como `etapaAtual.id`; a API a expande para a definição inteira: nome + tipo + departamentos).
 * Todos os valores são ids/identificadores estáveis, nunca rótulos.
 */
export function TrafegoGargalosFiltros({
  periodo,
  onPeriodo,
  departamentoId,
  onDepartamento,
  departamentos,
  clienteId,
  onCliente,
  clientes,
  projetoId,
  onProjeto,
  projetos,
  etapa,
  onLimparEtapa,
}: {
  periodo: PeriodoGargalosId;
  onPeriodo: (periodo: PeriodoGargalosId) => void;
  departamentoId: string;
  onDepartamento: (id: string) => void;
  departamentos: Opcao[];
  clienteId: string;
  onCliente: (id: string) => void;
  clientes: Opcao[];
  projetoId: string;
  onProjeto: (id: string) => void;
  projetos: Opcao[];
  etapa: { id: string; nome: string } | null;
  onLimparEtapa: () => void;
}) {
  return (
    <div role="search" aria-label="Filtros dos gargalos" className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Select
          label="Período"
          value={periodo}
          onChange={(evento) => onPeriodo(evento.target.value as PeriodoGargalosId)}
          options={PERIODOS_GARGALOS.map((item) => ({ value: item.id, label: item.label }))}
        />
        <Select
          label="Departamento"
          value={departamentoId}
          onChange={(evento) => onDepartamento(evento.target.value)}
          options={[{ value: "", label: "Todos os departamentos" }, ...departamentos]}
        />
        <Combobox label="Cliente" value={clienteId} onChange={onCliente} options={clientes} placeholder="Todos os clientes" />
        <Combobox label="Projeto" value={projetoId} onChange={onProjeto} options={projetos} placeholder="Todos os projetos" />
      </div>
      {etapa && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-fg-muted">
          <span>Etapa:</span>
          <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-1 font-semibold text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400">
            {etapa.nome}
            <button type="button" onClick={onLimparEtapa} aria-label="Remover filtro de etapa" className="rounded-full hover:text-indigo-900 dark:hover:text-indigo-200">
              <X className="h-3 w-3" />
            </button>
          </span>
        </div>
      )}
    </div>
  );
}
