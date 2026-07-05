"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  createAcessoPadrao,
  departamentos,
  EMPRESA_PADRAO_ID,
  responsaveisDisponiveis,
} from "@/lib/equipe-mock";
import type { EquipeDraft } from "@/types/equipe";
import { NovaEquipeButton } from "./NovaEquipeButton";

function resolveDepartamentoNome(departamentoId: string): string {
  return (
    departamentos.find((departamento) => departamento.id === departamentoId)
      ?.nome ?? departamentoId
  );
}

function resolveResponsavelNome(responsavelId: string): string {
  return (
    responsaveisDisponiveis.find((usuario) => usuario.id === responsavelId)
      ?.nome ?? responsavelId
  );
}

function criarMembrosMock(quantidade: number) {
  return Array.from({ length: quantidade }, (_, index) => ({
    membroId: `membro-mock-${index}`,
    usuarioId: "",
    nome: "",
    papel: "",
  }));
}

const initialEquipes: EquipeDraft[] = [
  {
    equipeId: "equipe-1",
    codigoInterno: "#1001",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Atendimento",
    sigla: "ATD",
    descricao: "",
    departamentoId: "dep-atendimento",
    responsavelId: "user-4",
    ativa: true,
    membros: criarMembrosMock(5),
    acesso: createAcessoPadrao(),
    historico: [],
  },
  {
    equipeId: "equipe-2",
    codigoInterno: "#1002",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Criação",
    sigla: "CRI",
    descricao: "",
    departamentoId: "dep-criacao",
    responsavelId: "user-5",
    ativa: true,
    membros: criarMembrosMock(8),
    acesso: createAcessoPadrao(),
    historico: [],
  },
  {
    equipeId: "equipe-3",
    codigoInterno: "#1003",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Mídia",
    sigla: "MID",
    descricao: "",
    departamentoId: "dep-midia",
    responsavelId: "user-6",
    ativa: true,
    membros: criarMembrosMock(3),
    acesso: createAcessoPadrao(),
    historico: [],
  },
  {
    equipeId: "equipe-4",
    codigoInterno: "#1004",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Produção",
    sigla: "PRD",
    descricao: "",
    departamentoId: "dep-orcamento-producao",
    responsavelId: "user-2",
    ativa: true,
    membros: criarMembrosMock(6),
    acesso: createAcessoPadrao(),
    historico: [],
  },
  {
    equipeId: "equipe-5",
    codigoInterno: "#1005",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Financeiro",
    sigla: "FIN",
    descricao: "",
    departamentoId: "dep-financeiro",
    responsavelId: "user-3",
    ativa: true,
    membros: criarMembrosMock(2),
    acesso: createAcessoPadrao(),
    historico: [],
  },
  {
    equipeId: "equipe-6",
    codigoInterno: "#1006",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "TI",
    sigla: "TI",
    descricao: "",
    departamentoId: "dep-ti",
    responsavelId: "user-1",
    ativa: true,
    membros: criarMembrosMock(1),
    acesso: createAcessoPadrao(),
    historico: [],
  },
];

export function EquipesView() {
  const [equipes, setEquipes] = useState<EquipeDraft[]>(initialEquipes);

  const totalMembros = equipes.reduce(
    (total, equipe) => total + equipe.membros.length,
    0
  );
  const equipesAtivas = equipes.filter((equipe) => equipe.ativa).length;

  function handleUpsert(draft: EquipeDraft) {
    setEquipes((current) => {
      const exists = current.some(
        (equipe) => equipe.equipeId === draft.equipeId
      );

      if (exists) {
        return current.map((equipe) =>
          equipe.equipeId === draft.equipeId ? draft : equipe
        );
      }

      return [draft, ...current];
    });
  }

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Equipes"
          description="Organização de departamentos, líderes e colaboradores."
        />

        <NovaEquipeButton onUpsert={handleUpsert} />
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total Equipes</p>
          <p className="mt-3 text-3xl font-bold">{equipes.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Colaboradores</p>
          <p className="mt-3 text-3xl font-bold">{totalMembros}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Ativas</p>
          <p className="mt-3 text-3xl font-bold">{equipesAtivas}</p>
        </Card>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Equipe</th>
              <th className="px-6 py-4 font-medium">Departamento</th>
              <th className="px-6 py-4 font-medium">Responsável</th>
              <th className="px-6 py-4 font-medium">Membros</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {equipes.map((equipe) => (
              <tr
                key={equipe.equipeId}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {equipe.nome}
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {resolveDepartamentoNome(equipe.departamentoId)}
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {resolveResponsavelNome(equipe.responsavelId)}
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {equipe.membros.length}
                </td>
                <td className="px-6 py-4">
                  <Badge>{equipe.ativa ? "Ativa" : "Inativa"}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
