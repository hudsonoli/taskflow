"use client";

import Link from "next/link";
import { CalendarDays, ClipboardList } from "lucide-react";
import { CadastroIndicators } from "@/components/cadastros";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { StatusPill } from "@/components/ui/StatusPill";
import { statusDemandaLabels } from "@/lib/demandas-mock";
import type { Demanda, DemandaStatus } from "@/types/demanda";
import { ProjetoSectionShell } from "./ProjetoFormSections";

type ProjetoDemandasSectionProps = {
  demandas: Demanda[];
};

const statusTone: Record<DemandaStatus, "neutral" | "blue" | "green" | "amber" | "red"> = {
  rascunho: "neutral",
  planejada: "blue",
  em_execucao: "green",
  pausada: "amber",
  bloqueada: "red",
  aguardando_cliente: "amber",
  concluida: "green",
  cancelada: "neutral",
};

// Atraso é calculado por comparação de data (prazoEtapaAtual vs. hoje),
// não é um status próprio de Demanda — mesma lacuna já registrada em
// docs/arquitetura-taskfloww/02-modelo-dados-futuro.md (não há enum de
// atraso, só cálculo derivado).
function isDemandaAtrasada(demanda: Demanda) {
  if (demanda.status === "concluida" || demanda.status === "cancelada") return false;

  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  return new Date(demanda.prazoEtapaAtual) < hoje;
}

/**
 * Aba "Demandas" do drawer de Projeto — leitura de demandasMock filtrada
 * por projetoId (relação já existente em Demanda). Sem CRUD: apenas lista
 * e indicadores rápidos, com link para o módulo completo de Demandas.
 */
export function ProjetoDemandasSection({ demandas }: ProjetoDemandasSectionProps) {
  const emAndamento = demandas.filter((demanda) => demanda.status === "em_execucao").length;
  const concluidas = demandas.filter((demanda) => demanda.status === "concluida").length;
  const atrasadas = demandas.filter(isDemandaAtrasada).length;
  const bloqueadas = demandas.filter((demanda) => demanda.status === "bloqueada").length;
  const semResponsavel = demandas.filter(
    (demanda) => demanda.usuarioResponsavelIds.length === 0
  ).length;

  return (
    <ProjetoSectionShell
      eyebrow="Demandas"
      title="Demandas do projeto"
      description="Demandas vinculadas a este projeto, com indicadores rápidos de andamento."
      icon={<ClipboardList className="h-5 w-5" />}
    >
      <CadastroIndicators
        density="compact"
        columnsClassName="grid grid-cols-2 gap-3 sm:grid-cols-5"
        items={[
          { label: "Em andamento", value: emAndamento },
          { label: "Concluídas", value: concluidas },
          { label: "Atrasadas", value: atrasadas },
          { label: "Bloqueadas", value: bloqueadas },
          { label: "Sem responsável", value: semResponsavel },
        ]}
      />

      <div className="mt-4">
        {demandas.length === 0 ? (
          <EmptyStateIllustration
            title="Nenhuma demanda vinculada"
            description="As demandas criadas para este projeto aparecerão aqui."
            size="compact"
          />
        ) : (
          <div className="space-y-2">
            {demandas.map((demanda) => (
              <div
                key={demanda.id}
                className="flex items-center gap-3 rounded-2xl border border-zinc-100 px-3 py-2 transition hover:bg-zinc-50"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px] font-medium text-zinc-800">
                    {demanda.nome}
                  </p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-zinc-400">
                    <CalendarDays className="h-3 w-3" aria-hidden="true" />
                    {demanda.prazoEtapaAtual}
                  </p>
                </div>
                <StatusPill density="compact" tone={statusTone[demanda.status]}>
                  {statusDemandaLabels[demanda.status]}
                </StatusPill>
              </div>
            ))}
          </div>
        )}
      </div>

      <Link
        href="/tarefas"
        className="mt-3 inline-block text-[11px] font-medium text-primary hover:underline"
      >
        Ver todas as demandas
      </Link>
    </ProjetoSectionShell>
  );
}
