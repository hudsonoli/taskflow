"use client";

import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { buscarDiretorioUsuarios, type DepartamentoDiretorioItem } from "@/lib/api-backend";
import type { TrafegoFiltersState } from "@/types/trafego";

/**
 * O filtro de usuário pesquisa NO SERVIDOR (uma página por busca, "Carregar mais") em vez de
 * receber o diretório inteiro — esse terminava no usuário nº 200 por nome, e quem vinha depois
 * nem aparecia para ser filtrado. O que sai do filtro continua sendo `usuarioIds` (UUIDs), os
 * mesmos parâmetros de `/trafego/indicadores|carga|agora`.
 */
async function buscarUsuarios({ busca, limit, offset }: { busca: string; limit: number; offset: number }) {
  const usuarios = await buscarDiretorioUsuarios({ search: busca, limit, offset });
  return usuarios.map((usuario) => ({ id: usuario.id, nome: usuario.nome }));
}

export function TrafegoFilters({
  filters,
  onChange,
  departamentos,
}: {
  filters: TrafegoFiltersState;
  onChange: (filters: TrafegoFiltersState) => void;
  departamentos: DepartamentoDiretorioItem[];
}) {
  function updateFilter<Key extends keyof TrafegoFiltersState>(key: Key, value: TrafegoFiltersState[Key]) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <span className="bg-brand-gradient flex h-9 w-9 items-center justify-center rounded-xl">
            <SlidersHorizontal className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold text-fg">Filtros operacionais</p>
            <p className="text-xs text-fg-muted">Ajuste a visão sem alterar dados.</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {[
            { value: "hoje", label: "Hoje" },
            { value: "24h", label: "24h" },
            { value: "7d", label: "7 dias" },
            { value: "30d", label: "30 dias" },
          ].map((periodo) => (
            <Button
              key={periodo.value}
              type="button"
              variant={filters.periodo === periodo.value ? "primary" : "secondary"}
              onClick={() => updateFilter("periodo", periodo.value as TrafegoFiltersState["periodo"])}
              className="px-3 py-1.5 text-xs"
            >
              {periodo.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.15fr_1.15fr_1fr_0.85fr]">
        <MemberSelector
          label="Usuário"
          values={filters.usuarioIds}
          onChange={(values) => updateFilter("usuarioIds", values)}
          placeholder="Selecionar usuários…"
          buscarOpcoes={buscarUsuarios}
          emptyLabel="Nenhum usuário encontrado"
        />
        <MultiSelect
          label="Departamento"
          values={filters.departamentoIds}
          onChange={(values) => updateFilter("departamentoIds", values)}
          options={departamentos.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
        />
        <Input
          label="Demanda"
          placeholder="Buscar demanda"
          value={filters.demandaQuery}
          onChange={(event) => updateFilter("demandaQuery", event.target.value)}
        />
        <Select
          label="Status"
          value={filters.status}
          onChange={(event) => updateFilter("status", event.target.value as TrafegoFiltersState["status"])}
          options={[
            { value: "todos", label: "Todos" },
            { value: "ativa", label: "Em execução" },
            { value: "encerrada", label: "Encerradas" },
          ]}
        />
      </div>
    </div>
  );
}
