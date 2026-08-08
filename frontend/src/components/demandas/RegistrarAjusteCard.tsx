"use client";

import { RotateCcw, UserCog, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { generateId } from "@/lib/demandas-mock";
import type { Demanda, DemandaHistoricoTipo } from "@/types/demanda";

const TIPOS: { tipo: DemandaHistoricoTipo; label: string; acao: string; icon: typeof UserCog }[] = [
  { tipo: "ajuste_interno", label: "Ajuste interno", acao: "Ajuste interno registrado", icon: UserCog },
  { tipo: "ajuste_cliente", label: "Ajuste de cliente", acao: "Ajuste solicitado pelo cliente", icon: Users },
  { tipo: "refacao", label: "Refação", acao: "Refação registrada", icon: RotateCcw },
];

export function RegistrarAjusteCard({ demanda, onChange }: { demanda: Demanda; onChange: (demanda: Demanda) => void }) {
  function registrar(tipo: DemandaHistoricoTipo, acao: string) {
    const now = new Date().toISOString();
    onChange({
      ...demanda,
      updatedAt: now,
      historico: [
        {
          id: generateId("hist-demanda"),
          usuarioId: "user-1",
          usuario: "Você",
          acao,
          tipo,
          dataHora: new Date().toLocaleString("pt-BR"),
          ip: "127.0.0.1",
          dispositivo: "Workspace local",
        },
        ...demanda.historico,
      ],
    });
  }

  const contagens = TIPOS.map(({ tipo }) => demanda.historico.filter((evento) => evento.tipo === tipo).length);

  return (
    <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/40">
      <p className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Registrar movimentação</p>
      <div className="flex flex-wrap gap-2">
        {TIPOS.map(({ tipo, label, acao, icon: Icon }, index) => (
          <Button key={tipo} type="button" variant="secondary" onClick={() => registrar(tipo, acao)} className="px-3 py-1.5 text-xs">
            <Icon className="h-3.5 w-3.5" />
            {label}
            {contagens[index] > 0 && (
              <span className="ml-1 rounded-full bg-zinc-200 px-1.5 text-[10px] font-semibold text-zinc-700 dark:bg-zinc-700 dark:text-zinc-200">
                {contagens[index]}
              </span>
            )}
          </Button>
        ))}
      </div>
    </div>
  );
}
