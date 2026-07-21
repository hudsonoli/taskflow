"use client";

import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { ToolbarCard } from "@/components/ui/ToolbarCard";
import {
  trafegoDepartamentosMock,
  trafegoEmpresasMock,
  trafegoUsuariosMock,
} from "@/lib/trafego-mock";
import type { TrafegoFiltersState } from "@/types/trafego";

type TrafegoFiltersProps = {
  filters: TrafegoFiltersState;
  onChange: (filters: TrafegoFiltersState) => void;
};

export function TrafegoFilters({ filters, onChange }: TrafegoFiltersProps) {
  function updateFilter<Key extends keyof TrafegoFiltersState>(
    key: Key,
    value: TrafegoFiltersState[Key]
  ) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <ToolbarCard>
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-zinc-950 text-white">
            <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-semibold text-zinc-950">Filtros operacionais</p>
            <p className="text-xs text-zinc-500">Ajuste a visão sem alterar dados.</p>
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
              size="xs"
              onClick={() =>
                updateFilter(
                  "periodo",
                  periodo.value as TrafegoFiltersState["periodo"]
                )
              }
            >
              {periodo.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.9fr_1.15fr_1.15fr_1fr_0.85fr]">
        <Select
          label="Empresa"
          value={filters.empresaId}
          onChange={(event) => updateFilter("empresaId", event.target.value)}
          options={trafegoEmpresasMock.map((empresa) => ({
            value: empresa.id,
            label: empresa.nome,
          }))}
        />

        <MultiSelect
          label="Usuário"
          placeholder="Todos os usuários"
          values={filters.usuarioIds}
          onChange={(values) => updateFilter("usuarioIds", values)}
          options={trafegoUsuariosMock.map((usuario) => ({
            value: usuario.id,
            label: usuario.nome,
          }))}
        />

        <MultiSelect
          label="Departamento"
          placeholder="Todos os departamentos"
          values={filters.departamentoIds}
          onChange={(values) => updateFilter("departamentoIds", values)}
          options={trafegoDepartamentosMock.map((departamento) => ({
            value: departamento.id,
            label: departamento.nome,
          }))}
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
          onChange={(event) =>
            updateFilter(
              "status",
              event.target.value as TrafegoFiltersState["status"]
            )
          }
          options={[
            { value: "todos", label: "Todos" },
            { value: "ativa", label: "Em execução" },
            { value: "pausada", label: "Pausada" },
            { value: "bloqueada", label: "Bloqueada" },
            { value: "aguardando_cliente", label: "Aguardando cliente" },
          ]}
        />
      </div>
    </ToolbarCard>
  );
}
