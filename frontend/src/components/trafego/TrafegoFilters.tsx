"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
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
    <div className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm">
      <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr_1.2fr_1fr_0.8fr]">
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

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {[
          { value: "hoje", label: "Hoje" },
          { value: "24h", label: "Últimas 24 horas" },
          { value: "7d", label: "7 dias" },
          { value: "30d", label: "30 dias" },
        ].map((periodo) => (
          <Button
            key={periodo.value}
            type="button"
            variant={filters.periodo === periodo.value ? "primary" : "secondary"}
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
  );
}
