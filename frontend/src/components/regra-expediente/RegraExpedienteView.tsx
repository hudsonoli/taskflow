"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Clock, PauseCircle } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Switch } from "@/components/ui/Switch";
import { isDentroExpediente, tardeInicioEfetivo } from "@/lib/regra-expediente-mock";
import { useAppData } from "@/lib/AppDataContext";

export function RegraExpedienteView() {
  const { regraExpediente, setRegraExpediente, demandas } = useAppData();
  const [agora, setAgora] = useState<Date | null>(null);

  useEffect(() => {
    const timeoutId = setTimeout(() => setAgora(new Date()), 0);
    const intervalId = setInterval(() => setAgora(new Date()), 1000);
    return () => {
      clearTimeout(timeoutId);
      clearInterval(intervalId);
    };
  }, []);

  function updateRegra(patch: Partial<typeof regraExpediente>) {
    setRegraExpediente((current) => ({ ...current, ...patch, updatedAt: new Date().toISOString() }));
  }

  const dentroDoExpediente = agora ? isDentroExpediente(agora, regraExpediente) : true;
  const emExecucaoAgora = demandas.filter((demanda) => demanda.status === "em_execucao").length;

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <Clock className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Horário de expediente</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Fora do horário configurado, demandas &quot;Em execução&quot; são pausadas automaticamente — o
                usuário precisa arrastar o card de volta para retomar.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <div
        className={`flex flex-wrap items-center gap-3 rounded-2xl border p-4 shadow-sm ${
          dentroDoExpediente
            ? "border-emerald-200 bg-emerald-50 dark:border-emerald-500/30 dark:bg-emerald-500/10"
            : "border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10"
        }`}
      >
        {dentroDoExpediente ? (
          <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        ) : (
          <PauseCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        )}
        <div>
          <p className={`text-sm font-semibold ${dentroDoExpediente ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300"}`}>
            {dentroDoExpediente ? "Agora: dentro do expediente" : "Agora: fora do expediente — pausas automáticas ativas"}
          </p>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            {agora?.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })} · {emExecucaoAgora} demanda(s) em execução agora
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="max-w-xs rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch
            checked={regraExpediente.ativo}
            onChange={(checked) => updateRegra({ ativo: checked })}
            label={regraExpediente.ativo ? "Regra ativa" : "Regra desativada"}
          />
        </div>

        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Turno da manhã</p>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Início"
                type="time"
                value={regraExpediente.manhaInicio}
                onChange={(event) => updateRegra({ manhaInicio: event.target.value })}
              />
              <Input
                label="Fim"
                type="time"
                value={regraExpediente.manhaFim}
                onChange={(event) => updateRegra({ manhaFim: event.target.value })}
              />
            </div>
          </div>

          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Turno da tarde</p>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Início"
                type="time"
                value={regraExpediente.tardeInicio}
                onChange={(event) => updateRegra({ tardeInicio: event.target.value })}
              />
              <Input
                label="Fim"
                type="time"
                value={regraExpediente.tardeFim}
                onChange={(event) => updateRegra({ tardeFim: event.target.value })}
              />
            </div>
          </div>
        </div>

        <div className="mt-5">
          <Input
            label="Tolerância de retomada antecipada (minutos)"
            type="number"
            min={0}
            max={120}
            value={regraExpediente.toleranciaRetomadaMinutos}
            onChange={(event) => updateRegra({ toleranciaRetomadaMinutos: Number(event.target.value) || 0 })}
          />
          <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
            A partir das <span className="font-semibold text-zinc-700 dark:text-zinc-300">{tardeInicioEfetivo(regraExpediente)}</span>, o
            usuário já pode arrastar o card de volta para &quot;Em execução&quot; sem que a regra pause de novo — mesmo o
            turno da tarde começando oficialmente às {regraExpediente.tardeInicio}.
          </p>
        </div>

        <p className="mt-5 border-t border-zinc-100 pt-4 text-xs text-zinc-400 dark:border-zinc-800">
          Fora dos turnos configurados (ex.: 12:01–{tardeInicioEfetivo(regraExpediente)}, e após {regraExpediente.tardeFim}), toda
          demanda com status &quot;Em execução&quot; é movida automaticamente para &quot;Pausada&quot;.
        </p>
      </div>
    </div>
  );
}
