"use client";

import { useMemo, useState } from "react";
import { Select } from "@/components/ui/Select";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ContagemAjustes } from "@/lib/api-backend";
import { analisarPecasPorProjeto } from "@/lib/relatorios";
import { useAjustesProjeto } from "@/lib/useAjustesProjeto";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";

const AJUSTES_ZERADOS: ContagemAjustes = { ajustesInternos: 0, ajustesCliente: 0, refacoes: 0 };

export function AnalisePecasReport() {
  const { demandas } = useAppData();
  const { projetos } = useDiretorioProjetos();
  const { usuarios } = useDiretorioUsuarios();
  const [projetoIdSelecionado, setProjetoIdSelecionado] = useState("");
  // Diretório carrega assíncrono: `useState(projetos[0]?.id)` capturaria sempre "" no mount.
  // Mesmo padrão derivado de RelatoriosView/AnaliseProjetoReport/PerformanceColaboradorReport.
  const projetoId = projetoIdSelecionado || projetos[0]?.id || "";
  const pecas = useMemo(
    () => analisarPecasPorProjeto(projetoId, demandas, usuarios),
    [projetoId, demandas, usuarios],
  );

  // Ajustes internos/Ajustes cliente/Refações por Demanda (Fase 2F.4) — mesma agregação real
  // usada por AnaliseProjetoReport, uma request por Projeto selecionado (não por peça).
  const { resultado: ajustes, carregando: carregandoAjustes, erro: erroAjustes } = useAjustesProjeto(
    projetoId || null,
  );
  const valorAjuste = (demandaId: string, campo: keyof ContagemAjustes): string => {
    if (carregandoAjustes) return "…";
    if (erroAjustes || !ajustes) return "—";
    // Ausente em `porDemanda` = essa Demanda não teve nenhum dos três eventos — 0 real, não
    // falta de dado (ver contrato de GET /relatorios/demandas/ajustes).
    return String((ajustes.porDemanda[demandaId] ?? AJUSTES_ZERADOS)[campo]);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="max-w-xs">
        <Select
          label="Projeto"
          value={projetoId}
          onChange={(event) => setProjetoIdSelecionado(event.target.value)}
          options={projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome }))}
        />
      </div>

      {erroAjustes && (
        <p className="text-xs text-red-600 dark:text-red-400">
          Não foi possível carregar Ajustes internos/Ajustes de cliente/Refações: {erroAjustes}
        </p>
      )}

      {pecas.length === 0 ? (
        <EmptyState title="Nenhuma peça encontrada" description="Este projeto ainda não tem demandas cadastradas." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400">
              <tr>
                <th className="py-2">Demanda</th>
                <th className="py-2">Redator/DA</th>
                <th className="py-2 text-right">Tempo em pauta</th>
                <th className="py-2 text-right">Ajustes internos</th>
                <th className="py-2 text-right">Ajustes cliente</th>
                <th className="py-2 text-right">Refações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {pecas.map((peca) => (
                <tr key={peca.demandaId}>
                  <td className="py-2">
                    <p className="font-medium text-zinc-900 dark:text-zinc-100">{peca.nome}</p>
                    <p className="text-xs text-zinc-400">{peca.codigoInterno}</p>
                  </td>
                  <td className="py-2 text-zinc-600 dark:text-zinc-400">{peca.redator}</td>
                  <td className="py-2 text-right text-zinc-600 dark:text-zinc-400">
                    {peca.emAndamento ? "Em andamento" : `${peca.tempoEmPautaDias?.toFixed(1)}d`}
                  </td>
                  <td className="py-2 text-right text-zinc-600 dark:text-zinc-400">
                    {valorAjuste(peca.demandaId, "ajustesInternos")}
                  </td>
                  <td className="py-2 text-right text-zinc-600 dark:text-zinc-400">
                    {valorAjuste(peca.demandaId, "ajustesCliente")}
                  </td>
                  <td className="py-2 text-right text-zinc-600 dark:text-zinc-400">
                    {valorAjuste(peca.demandaId, "refacoes")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
