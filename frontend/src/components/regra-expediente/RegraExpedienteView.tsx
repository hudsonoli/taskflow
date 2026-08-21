"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Clock, Loader2, PauseCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Switch } from "@/components/ui/Switch";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { atualizarRegraExpedienteReal, getRegraExpedienteReal } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useEstadoExpediente } from "@/lib/estadoExpediente";
import type { DiaSemana, JanelaDia, RegraExpediente } from "@/types/regra-expediente";

// Fase 2G.3 — regra real por Empresa (antes: só estado local/mock). A UI original tinha uma
// única janela global; a única mudança estrutural aqui é a linha de dias da semana abaixo do
// switch — o restante (turnos, tolerância, cartão "agora") segue o mesmo layout de antes,
// com a janela compartilhada entre todos os dias marcados como úteis (o backend já suporta
// horários distintos por dia — não expor isso na UI ainda é decisão deliberada de manter o
// menor impacto visual possível, ver relatório da Fase 2G.3).

const ORDEM_DIAS: DiaSemana[] = [0, 1, 2, 3, 4, 5, 6];
const DIAS_LABEL: Record<DiaSemana, string> = { 0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom" };

function paraMinutos(horaMinuto: string): number {
  const [horas, minutos] = horaMinuto.split(":").map(Number);
  return horas * 60 + minutos;
}

function formatarMinutos(totalMinutos: number): string {
  const normalizado = ((totalMinutos % 1440) + 1440) % 1440;
  const horas = Math.floor(normalizado / 60);
  const minutos = normalizado % 60;
  return `${String(horas).padStart(2, "0")}:${String(minutos).padStart(2, "0")}`;
}

/** Início efetivo do turno da tarde (com tolerância) do dia usado como referência da janela
 * compartilhada — `null` quando nenhum dia ativo tem horário de tarde definido ainda. */
function tardeInicioEfetivo(diaReferencia: JanelaDia | null, toleranciaRetomadaMinutos: number): string | null {
  if (!diaReferencia?.tardeInicio) return null;
  return formatarMinutos(paraMinutos(diaReferencia.tardeInicio) - toleranciaRetomadaMinutos);
}

export function RegraExpedienteView() {
  const { demandas } = useAppData();
  const { estado } = useEstadoExpediente();
  const [regra, setRegra] = useState<RegraExpediente | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);

  function buscar() {
    getRegraExpedienteReal()
      .then((dados) => {
        setRegra(dados);
        setErro(false);
      })
      .catch(() => setErro(true))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    buscar();
  }, []);

  function tentarNovamente() {
    setCarregando(true);
    setErro(false);
    buscar();
  }

  if (carregando) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-zinc-200 bg-white p-10 text-sm text-zinc-500 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando regra de expediente…
      </div>
    );
  }

  if (erro || !regra) {
    return <EstadoErro mensagem="Não foi possível carregar a regra de expediente." onRetry={tentarNovamente} />;
  }

  function updateRegra(patch: Partial<Pick<RegraExpediente, "ativo" | "toleranciaRetomadaMinutos">>) {
    setRegra((current) => (current ? { ...current, ...patch } : current));
  }

  /** Aplica o novo horário a todos os dias marcados como úteis — janela compartilhada, ver
   * comentário no topo do arquivo. */
  function updateJanelaDosDiasAtivos(patch: Partial<Pick<JanelaDia, "manhaInicio" | "manhaFim" | "tardeInicio" | "tardeFim">>) {
    setRegra((current) =>
      current ? { ...current, dias: current.dias.map((dia) => (dia.ativo ? { ...dia, ...patch } : dia)) } : current,
    );
  }

  function toggleDia(diaSemana: DiaSemana) {
    setRegra((current) => {
      if (!current) return current;
      const referencia = current.dias.find((dia) => dia.ativo) ?? {
        manhaInicio: "09:00",
        manhaFim: "12:00",
        tardeInicio: "14:00",
        tardeFim: "19:00",
      };
      return {
        ...current,
        dias: current.dias.map((dia) => {
          if (dia.diaSemana !== diaSemana) return dia;
          if (dia.ativo) {
            return { ...dia, ativo: false, manhaInicio: null, manhaFim: null, tardeInicio: null, tardeFim: null };
          }
          return {
            ...dia,
            ativo: true,
            manhaInicio: referencia.manhaInicio,
            manhaFim: referencia.manhaFim,
            tardeInicio: referencia.tardeInicio,
            tardeFim: referencia.tardeFim,
          };
        }),
      };
    });
  }

  async function salvar() {
    if (!regra) return;
    setSalvando(true);
    setErroSalvar(null);
    try {
      const atualizada = await atualizarRegraExpedienteReal({
        ativo: regra.ativo,
        toleranciaRetomadaMinutos: regra.toleranciaRetomadaMinutos,
        dias: regra.dias,
      });
      setRegra(atualizada);
    } catch (error) {
      setErroSalvar(error instanceof Error ? error.message : "Não foi possível salvar a regra de expediente.");
    } finally {
      setSalvando(false);
    }
  }

  const diaReferencia = regra.dias.find((dia) => dia.ativo) ?? null;
  const dentroDoExpediente = estado?.dentroExpediente ?? true;
  const agoraFormatado = estado
    ? new Date(estado.agora).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : null;
  const emExecucaoAgora = demandas.filter((demanda) => demanda.status === "em_execucao").length;
  const inicioTarde = tardeInicioEfetivo(diaReferencia, regra.toleranciaRetomadaMinutos);

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
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
            {agoraFormatado ?? "—"} · {emExecucaoAgora} demanda(s) em execução agora
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="max-w-sm rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch
            checked={regra.ativo}
            onChange={(checked) => updateRegra({ ativo: checked })}
            label="Controle de expediente ativo"
            description="Quando desativado, o sistema não bloqueia a operação por dia ou horário."
          />
        </div>

        <div className="mt-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Dias úteis</p>
          <div className="flex flex-wrap gap-2">
            {ORDEM_DIAS.map((diaSemana) => {
              const dia = regra.dias.find((item) => item.diaSemana === diaSemana);
              const ativo = dia?.ativo ?? false;
              return (
                <button
                  key={diaSemana}
                  type="button"
                  onClick={() => toggleDia(diaSemana)}
                  aria-pressed={ativo}
                  className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                    ativo
                      ? "border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-500/40 dark:bg-indigo-500/10 dark:text-indigo-300"
                      : "border-zinc-200 bg-zinc-50 text-zinc-400 hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-950/30 dark:text-zinc-500"
                  }`}
                >
                  {DIAS_LABEL[diaSemana]}
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Turno da manhã</p>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Início"
                type="time"
                value={diaReferencia?.manhaInicio ?? ""}
                disabled={!diaReferencia}
                onChange={(event) => updateJanelaDosDiasAtivos({ manhaInicio: event.target.value })}
              />
              <Input
                label="Fim"
                type="time"
                value={diaReferencia?.manhaFim ?? ""}
                disabled={!diaReferencia}
                onChange={(event) => updateJanelaDosDiasAtivos({ manhaFim: event.target.value })}
              />
            </div>
          </div>

          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Turno da tarde</p>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Início"
                type="time"
                value={diaReferencia?.tardeInicio ?? ""}
                disabled={!diaReferencia}
                onChange={(event) => updateJanelaDosDiasAtivos({ tardeInicio: event.target.value })}
              />
              <Input
                label="Fim"
                type="time"
                value={diaReferencia?.tardeFim ?? ""}
                disabled={!diaReferencia}
                onChange={(event) => updateJanelaDosDiasAtivos({ tardeFim: event.target.value })}
              />
            </div>
          </div>
        </div>

        {!diaReferencia && (
          <p className="mt-3 text-xs text-amber-600 dark:text-amber-400">
            Selecione ao menos um dia útil acima para definir os turnos.
          </p>
        )}

        <div className="mt-5">
          <Input
            label="Tolerância de retomada antecipada (minutos)"
            type="number"
            min={0}
            max={120}
            value={regra.toleranciaRetomadaMinutos}
            onChange={(event) => updateRegra({ toleranciaRetomadaMinutos: Number(event.target.value) || 0 })}
          />
          {inicioTarde && diaReferencia?.tardeFim && (
            <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
              A partir das <span className="font-semibold text-zinc-700 dark:text-zinc-300">{inicioTarde}</span>, o
              usuário já pode arrastar o card de volta para &quot;Em execução&quot; sem que a regra pause de novo — mesmo o
              turno da tarde começando oficialmente às {diaReferencia.tardeInicio}.
            </p>
          )}
        </div>

        {diaReferencia?.manhaFim && inicioTarde && diaReferencia.tardeFim && (
          <p className="mt-5 border-t border-zinc-100 pt-4 text-xs text-zinc-400 dark:border-zinc-800">
            Fora dos turnos configurados (ex.: {diaReferencia.manhaFim}–{inicioTarde}, e após {diaReferencia.tardeFim}), nos
            dias úteis marcados acima, toda demanda com status &quot;Em execução&quot; é movida automaticamente para
            &quot;Pausada&quot;.
          </p>
        )}

        <div className="mt-5 flex items-center justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800">
          {erroSalvar && <p className="mr-auto text-xs text-red-600 dark:text-red-400">{erroSalvar}</p>}
          <Button type="button" onClick={salvar} disabled={salvando}>
            {salvando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            {salvando ? "Salvando…" : "Salvar alterações"}
          </Button>
        </div>
      </div>
    </div>
  );
}
