"use client";

import { useState } from "react";
import { Users } from "lucide-react";
import {
  CadastroAvatar,
  CadastroIndicators,
  CadastroPage,
  CadastroStatusBadge,
  CadastroTable,
  CadastroToolbar,
  cadastroTableCellClassName,
  cadastroTableHeaderCellClassName,
  cadastroTableHeaderClassName,
  cadastroTableRowClassName,
} from "@/components/cadastros";
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
  const [searchQuery, setSearchQuery] = useState("");

  const totalMembros = equipes.reduce(
    (total, equipe) => total + equipe.membros.length,
    0
  );
  const equipesAtivas = equipes.filter((equipe) => equipe.ativa).length;

  const equipesFiltradas = equipes.filter((equipe) =>
    [
      equipe.codigoInterno,
      equipe.nome,
      equipe.sigla,
      resolveDepartamentoNome(equipe.departamentoId),
      resolveResponsavelNome(equipe.responsavelId),
    ]
      .join(" ")
      .toLowerCase()
      .includes(searchQuery.trim().toLowerCase())
  );

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
    <CadastroPage
      title="Equipes"
      description="Organização de departamentos, líderes e colaboradores."
      toolbar={
        <CadastroToolbar
          searchValue={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Pesquisar equipes..."
          actions={<NovaEquipeButton onUpsert={handleUpsert} />}
        />
      }
      indicators={
        <CadastroIndicators
          items={[
            { label: "Total", value: equipes.length },
            { label: "Colaboradores", value: totalMembros },
            { label: "Ativas", value: equipesAtivas },
          ]}
        />
      }
    >
      <CadastroTable minWidth="780px">
        <thead className={cadastroTableHeaderClassName}>
          <tr>
            <th className={cadastroTableHeaderCellClassName}>Equipe</th>
            <th className={cadastroTableHeaderCellClassName}>Departamento</th>
            <th className={cadastroTableHeaderCellClassName}>Responsável</th>
            <th className={cadastroTableHeaderCellClassName}>Membros</th>
            <th className={cadastroTableHeaderCellClassName}>Status</th>
          </tr>
        </thead>

        <tbody>
          {equipesFiltradas.map((equipe) => (
            <tr key={equipe.equipeId} className={cadastroTableRowClassName}>
              <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                <div className="flex items-center gap-2.5">
                  <CadastroAvatar label={equipe.nome} icon={Users} />
                  <div className="min-w-0">
                    <p className="truncate font-medium text-zinc-900">{equipe.nome}</p>
                    <p className="text-xs text-zinc-400">{equipe.codigoInterno}</p>
                  </div>
                </div>
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                {resolveDepartamentoNome(equipe.departamentoId)}
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                {resolveResponsavelNome(equipe.responsavelId)}
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                {equipe.membros.length}
              </td>
              <td className={cadastroTableCellClassName}>
                <CadastroStatusBadge>{equipe.ativa ? "Ativa" : "Inativa"}</CadastroStatusBadge>
              </td>
            </tr>
          ))}
        </tbody>
      </CadastroTable>
    </CadastroPage>
  );
}
