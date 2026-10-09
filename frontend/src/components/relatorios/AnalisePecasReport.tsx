"use client";

import { rotuloDemanda } from "@/lib/referencias";
import { useState } from "react";
import { Inbox } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ContagemAjustes } from "@/lib/api-backend";
import { useAjustesProjeto } from "@/lib/useAjustesProjeto";
import { usePecasProjeto } from "@/lib/usePecasProjeto";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";

const AJUSTES_ZERADOS: ContagemAjustes = { ajustesInternos: 0, ajustesCliente: 0, refacoes: 0 };

export function AnalisePecasReport() {
  const { projetos } = useDiretorioProjetos();
  const [projetoIdSelecionado, setProjetoIdSelecionado] = useState("");
  // Diretório carrega assíncrono: `useState(projetos[0]?.id)` capturaria sempre "" no mount.
  // Mesmo padrão derivado de RelatoriosView/AnaliseProjetoReport/PerformanceColaboradorReport.
  const projetoId = projetoIdSelecionado || projetos[0]?.id || "";

  // D4A — as peças (Demandas do Projeto) vêm paginadas do servidor, já com o redator resolvido e
  // o tempo em pauta calculado. Antes: `analisarPecasPorProjeto` sobre `AppDataContext.demandas`
  // (as 200 mais recentes da empresa) + diretório de usuários.
  const { linhas: pecas, total, carregando, erro, carregandoMais, erroMais, carregarMais } = usePecasProjeto(
    projetoId || null,
  );

  // Ajustes internos/Ajustes cliente/Refações por Demanda (Fase 2F.4) — mesma agregação real
  // usada por AnaliseProjetoReport, uma request por Projeto selecionado (não por peça). Cobre
  // todas as Demandas do Projeto, então vale para qualquer página carregada.
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

      {erro ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          Não foi possível carregar as peças do projeto: {erro}
        </div>
      ) : carregando ? (
        <EmptyState title="Carregando…" description="Buscando as peças do projeto no servidor." icon={<Inbox size={16} />} />
      ) : pecas.length === 0 ? (
        <EmptyState title="Nenhuma peça encontrada" description="Este projeto ainda não tem demandas cadastradas." />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-semibold uppercase tracking-[0.12em] text-fg-subtle">
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
                      <p className="font-medium text-fg">{peca.nome}</p>
                      <p className="text-xs text-fg-subtle">{rotuloDemanda(peca)}</p>
                    </td>
                    <td className="py-2 text-fg-muted">{peca.redatorNome ?? "Sem responsável"}</td>
                    <td className="py-2 text-right text-fg-muted">
                      {peca.emAndamento ? "Em andamento" : `${peca.tempoEmPautaDias?.toFixed(1)}d`}
                    </td>
                    <td className="py-2 text-right text-fg-muted">
                      {valorAjuste(peca.demandaId, "ajustesInternos")}
                    </td>
                    <td className="py-2 text-right text-fg-muted">
                      {valorAjuste(peca.demandaId, "ajustesCliente")}
                    </td>
                    <td className="py-2 text-right text-fg-muted">
                      {valorAjuste(peca.demandaId, "refacoes")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pecas.length < total && (
            <div className="flex flex-col items-center gap-2">
              <Button type="button" variant="secondary" onClick={carregarMais} disabled={carregandoMais}>
                {carregandoMais ? "Carregando…" : "Carregar mais"}
              </Button>
              <p className="text-xs text-fg-subtle">
                Mostrando {pecas.length} de {total}
              </p>
              {erroMais && <p className="text-xs text-red-600 dark:text-red-400">{erroMais}</p>}
            </div>
          )}
        </>
      )}
    </div>
  );
}
