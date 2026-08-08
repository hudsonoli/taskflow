"use client";

import { useMemo, useState } from "react";
import { Select } from "@/components/ui/Select";
import { EmptyState } from "@/components/ui/EmptyState";
import { analisarPecasPorProjeto } from "@/lib/relatorios";
import { useAppData } from "@/lib/AppDataContext";

export function AnalisePecasReport() {
  const { demandas, projetos } = useAppData();
  const [projetoId, setProjetoId] = useState(projetos[0]?.id ?? "");
  const pecas = useMemo(() => analisarPecasPorProjeto(projetoId, demandas), [projetoId, demandas]);

  return (
    <div className="flex flex-col gap-4">
      <div className="max-w-xs">
        <Select
          label="Projeto"
          value={projetoId}
          onChange={(event) => setProjetoId(event.target.value)}
          options={projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome }))}
        />
      </div>

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
                  <td className="py-2 text-right text-zinc-600 dark:text-zinc-400">{peca.ajustesInternos}</td>
                  <td className="py-2 text-right text-zinc-600 dark:text-zinc-400">{peca.ajustesCliente}</td>
                  <td className="py-2 text-right text-zinc-600 dark:text-zinc-400">{peca.refacoes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
