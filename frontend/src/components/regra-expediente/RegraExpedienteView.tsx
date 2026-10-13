"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Clock, Loader2, MinusCircle } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { atualizarRegraExpedienteReal, getEmAndamentoOperacional, getRegraExpedienteReal } from "@/lib/api-backend";
import { useEstadoExpediente } from "@/lib/estadoExpediente";
import { DIAS_ORDEM, diasNormalizados, diasParaEnvio, errosDaSemana, opcoesDeFuso } from "@/lib/expediente-periodos";
import type { DiaEspecial, DiaSemana, PeriodoExpediente, RegraExpediente } from "@/types/regra-expediente";
import { DiasEspeciaisSection } from "./DiasEspeciaisSection";
import { PeriodosDoDia } from "./PeriodosDoDia";

// Fase Expediente 1 — fundação. A tela configura períodos por dia (0, 1, 2 ou mais), antecedência de acesso, fuso e dias especiais. O QUE TEM EFEITO HOJE: o
// interruptor "Controle de expediente" (o gate que já existia: iniciar a execução de uma demanda só é aceito dentro dos períodos). Os interruptores de BLOQUEIO de
// acesso e de PAUSA automática existem mas ficam desligados e travados — nenhum bloqueio nem pausa automática acontece nesta etapa (o servidor também recusa ligá-los).

function normalizarRegra(dados: RegraExpediente): RegraExpediente {
  const normalizados = diasNormalizados(dados.dias);
  return {
    ...dados,
    dias: normalizados.map((dia) => ({ diaSemana: dia.diaSemana, ativo: dia.periodos.length > 0, periodos: dia.periodos })),
  };
}

export function RegraExpedienteView() {
  const { estado } = useEstadoExpediente();
  const [regra, setRegra] = useState<RegraExpediente | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);
  const [salvoEm, setSalvoEm] = useState<string | null>(null);
  // D2-D3A — endpoint dedicado (`GET /demandas/operacional/em-andamento`, admin/gestor), agregado no servidor sobre o universo INTEGRAL. `null` distingue
  // "carregando" de "zero confirmado".
  const [emAndamento, setEmAndamento] = useState<number | null>(null);
  const [erroEmAndamento, setErroEmAndamento] = useState(false);

  function buscar() {
    getRegraExpedienteReal()
      .then((dados) => {
        setRegra(normalizarRegra(dados));
        setErro(false);
      })
      .catch(() => setErro(true))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    buscar();
    getEmAndamentoOperacional()
      .then((resultado) => setEmAndamento(resultado.emAndamento))
      .catch(() => setErroEmAndamento(true));
  }, []);

  function tentarNovamente() {
    setCarregando(true);
    setErro(false);
    buscar();
  }

  if (carregando) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-sm text-fg-muted shadow-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando regra de expediente…
      </div>
    );
  }

  if (erro || !regra) {
    return <EstadoErro mensagem="Não foi possível carregar a regra de expediente." onRetry={tentarNovamente} />;
  }

  function updateRegra(patch: Partial<Pick<RegraExpediente, "ativo" | "toleranciaRetomadaMinutos" | "antecedenciaAcessoMinutos" | "timezone">>) {
    setSalvoEm(null);
    setRegra((current) => (current ? { ...current, ...patch } : current));
  }

  function updatePeriodos(diaSemana: DiaSemana, periodos: PeriodoExpediente[]) {
    setSalvoEm(null);
    setRegra((current) =>
      current ? { ...current, dias: current.dias.map((dia) => (dia.diaSemana === diaSemana ? { ...dia, periodos, ativo: periodos.length > 0 } : dia)) } : current,
    );
  }

  function updateDiasEspeciais(diasEspeciais: DiaEspecial[]) {
    setRegra((current) => (current ? { ...current, diasEspeciais } : current));
  }

  const errosPorDia = errosDaSemana(regra.dias);
  const haErros = Object.keys(errosPorDia).length > 0;

  async function salvar() {
    if (!regra || haErros) return;
    setSalvando(true);
    setErroSalvar(null);
    try {
      const atualizada = await atualizarRegraExpedienteReal({
        ativo: regra.ativo,
        toleranciaRetomadaMinutos: regra.toleranciaRetomadaMinutos,
        antecedenciaAcessoMinutos: regra.antecedenciaAcessoMinutos,
        timezone: regra.timezone,
        dias: diasParaEnvio(regra.dias),
      });
      setRegra(normalizarRegra(atualizada));
      setSalvoEm(new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }));
    } catch (error) {
      setErroSalvar(error instanceof Error && error.message ? error.message : "Não foi possível salvar a regra de expediente.");
    } finally {
      setSalvando(false);
    }
  }

  const dentroDoExpediente = estado?.dentroExpediente ?? true;
  const agoraFormatado = estado ? new Date(estado.agora).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : null;
  const emExecucaoAgoraTexto = emAndamento === null && !erroEmAndamento ? "…" : erroEmAndamento ? "—" : emAndamento;

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-line bg-surface p-4 shadow-sm"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Clock className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h1 className="text-lg font-semibold tracking-tight text-fg">Horário de expediente</h1>
            <p className="mt-0.5 max-w-3xl text-xs leading-5 text-fg-muted">
              Defina os períodos de trabalho de cada dia da semana, a antecedência de acesso e os dias especiais. Nesta etapa a configuração é registrada e já
              vale para <strong>iniciar a execução</strong> de uma demanda; o bloqueio de acesso fora do horário e a pausa automática ainda não estão ativos.
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
          <CheckCircle2 className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
        ) : (
          <MinusCircle className="h-5 w-5 text-amber-700 dark:text-amber-400" />
        )}
        <div>
          <p className={`text-sm font-semibold ${dentroDoExpediente ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300"}`}>
            {dentroDoExpediente ? "Agora: dentro do expediente" : "Agora: fora do expediente"}
          </p>
          <p className="mt-0.5 text-xs text-fg-muted">
            {agoraFormatado ?? "—"} · {emExecucaoAgoraTexto} demanda(s) em execução agora
          </p>
        </div>
      </div>

      <section aria-labelledby="controle-titulo" className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <h2 id="controle-titulo" className="text-sm font-semibold text-fg">
          Controle
        </h2>
        <div className="mt-3 grid gap-3 lg:grid-cols-3">
          <div className="rounded-xl border border-zinc-200 bg-surface px-3.5 py-2.5 dark:border-zinc-700">
            <Switch
              checked={regra.ativo}
              onChange={(checked) => updateRegra({ ativo: checked })}
              label="Ativar controle de expediente"
              description="Quando ativo, iniciar a execução de uma demanda só é aceito dentro dos períodos. Desativado, nada é restringido por dia ou horário."
            />
          </div>
          <div className="rounded-xl border border-zinc-200 bg-surface px-3.5 py-2.5 dark:border-zinc-700">
            <Switch
              checked={false}
              disabled
              onChange={() => undefined}
              label="Bloquear usuários fora do expediente"
              description="Será ativado em uma próxima etapa."
            />
            <div className="mt-1.5">
              <Badge>Em breve</Badge>
            </div>
          </div>
          <div className="rounded-xl border border-zinc-200 bg-surface px-3.5 py-2.5 dark:border-zinc-700">
            <Switch
              checked={false}
              disabled
              onChange={() => undefined}
              label="Pausar atividades ao final dos períodos"
              description="Será ativado em uma próxima etapa."
            />
            <div className="mt-1.5">
              <Badge>Em breve</Badge>
            </div>
          </div>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <Input
              label="Antecedência para acesso (minutos)"
              type="number"
              min={0}
              max={720}
              value={regra.antecedenciaAcessoMinutos}
              onChange={(event) => updateRegra({ antecedenciaAcessoMinutos: Math.min(720, Math.max(0, Number(event.target.value) || 0)) })}
            />
            <p className="mt-1.5 text-xs text-fg-muted">
              Só libera o <strong>acesso</strong> antes de cada período. Não conta como horário trabalhado e não muda os períodos abaixo.
            </p>
          </div>
          <div>
            <Select
              label="Fuso horário da empresa"
              value={regra.timezone}
              onChange={(event) => updateRegra({ timezone: event.target.value })}
              options={opcoesDeFuso(regra.timezone)}
            />
            <p className="mt-1.5 text-xs text-fg-muted">Os horários valem neste fuso — nunca no relógio do navegador.</p>
          </div>
        </div>
      </section>

      <section aria-labelledby="semana-titulo" className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <h2 id="semana-titulo" className="text-sm font-semibold text-fg">
          Horário semanal
        </h2>
        <p className="mt-0.5 text-xs text-fg-muted">
          Um dia pode ter um ou vários períodos (ex.: 08:00–12:00 e 13:00–18:00). Sem períodos, o dia fica fechado. Um período não atravessa a meia-noite.
        </p>
        <div className="mt-2">
          {DIAS_ORDEM.map((diaSemana) => {
            const dia = regra.dias.find((item) => item.diaSemana === diaSemana);
            return (
              <PeriodosDoDia
                key={diaSemana}
                dia={diaSemana}
                periodos={dia?.periodos ?? []}
                erro={errosPorDia[diaSemana]}
                onChange={(periodos) => updatePeriodos(diaSemana, periodos)}
              />
            );
          })}
        </div>

        <details className="mt-4 rounded-xl border border-zinc-100 bg-zinc-50/70 p-3 dark:border-zinc-800 dark:bg-zinc-950/30">
          <summary className="cursor-pointer text-xs font-semibold text-fg-muted">Avançado — tolerância de retomada (legado)</summary>
          <div className="mt-3 max-w-xs">
            <Input
              label="Tolerância de retomada (minutos)"
              type="number"
              min={0}
              max={120}
              value={regra.toleranciaRetomadaMinutos}
              onChange={(event) => updateRegra({ toleranciaRetomadaMinutos: Math.max(0, Number(event.target.value) || 0) })}
            />
          </div>
          <p className="mt-2 text-xs text-fg-muted">
            Regra antiga, mantida como era: <strong>iniciar a execução</strong> já é aceito esta quantidade de minutos antes do início do 2º período do dia
            (ex.: com 30 min, depois do almoço a execução pode começar 30 min antes). Não é a antecedência de acesso e não altera prazos nem SLA.
          </p>
        </details>

        <div className="mt-5 flex flex-wrap items-center justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800">
          {erroSalvar && (
            <p role="alert" className="mr-auto text-xs text-red-600 dark:text-red-400">
              {erroSalvar}
            </p>
          )}
          {!erroSalvar && haErros && <p className="mr-auto text-xs text-amber-700 dark:text-amber-400">Corrija os períodos destacados para salvar.</p>}
          {!erroSalvar && !haErros && salvoEm && (
            <p role="status" className="mr-auto text-xs text-emerald-700 dark:text-emerald-400">
              Salvo às {salvoEm}.
            </p>
          )}
          <Button type="button" onClick={salvar} disabled={salvando || haErros}>
            {salvando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            {salvando ? "Salvando…" : "Salvar alterações"}
          </Button>
        </div>
      </section>

      <DiasEspeciaisSection dias={regra.diasEspeciais} onChange={updateDiasEspeciais} />
    </div>
  );
}
