"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { PeriodosDoDia } from "@/components/regra-expediente/PeriodosDoDia";
import { salvarJornadaUsuario, usarExpedienteDaEmpresa } from "@/lib/api-backend";
import {
  DIAS_ORDEM,
  TEXTO_CONFIRMAR_VOLTAR_EMPRESA,
  TEXTO_JORNADA_EMPRESA,
  TEXTO_JORNADA_PERSONALIZADA,
  TEXTO_JORNADA_TODA_FECHADA,
  corpoDaJornada,
  errosDaJornada,
  grade,
  horasDaSemana,
  jornadaPendente,
  jornadaTodaFechada,
  mensagemDeErroCapacidade,
  podeSalvarJornada,
  resumoDaSemana,
  type ModoJornada,
} from "@/lib/usuario-capacidade";
import type { PeriodoExpediente } from "@/types/regra-expediente";
import type { JornadaUsuario } from "@/types/usuario-capacidade";
import { ConfirmacaoCurta } from "./ConfirmacaoCurta";

/**
 * Bloco A — Jornada de trabalho. Dois estados: "Expediente da empresa" (padrão; só um resumo de leitura — nada é copiado para o usuário) e "Jornada personalizada" (grade semanal
 * própria, 0..n períodos por dia, que SUBSTITUI a semana da empresa). Escolher "personalizada" só pré-preenche a tela com o expediente atual como sugestão: nada é gravado até Salvar.
 * Voltar ao padrão remove a jornada (DELETE) depois de uma confirmação curta. Validação dos períodos = a mesma do Horário de expediente (`lib/expediente-periodos`); o backend repete.
 */
export function UsuarioJornadaEditor({ usuarioId, jornada, somenteLeitura, onChange }: { usuarioId: string; jornada: JornadaUsuario; somenteLeitura: boolean; onChange: (jornada: JornadaUsuario) => void }) {
  const [modo, setModo] = useState<ModoJornada>(jornada.personalizada ? "personalizada" : "empresa");
  const [dias, setDias] = useState(() => grade(jornada.dias));
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvoEm, setSalvoEm] = useState<string | null>(null);
  const [confirmarVoltar, setConfirmarVoltar] = useState(false);
  const [removendo, setRemovendo] = useState(false);
  const [erroRemover, setErroRemover] = useState<string | null>(null);

  const erros = errosDaJornada(dias);
  const pendente = jornadaPendente(jornada, modo, dias);
  const podeSalvar = podeSalvarJornada({ servidor: jornada, modo, dias, somenteLeitura, salvando });
  const ocupado = salvando || removendo;

  function escolherEmpresa() {
    if (somenteLeitura || ocupado) return;
    if (jornada.personalizada) {
      setErroRemover(null);
      setConfirmarVoltar(true);
      return;
    }
    setModo("empresa");
    setDias(grade(jornada.dias));
    setErro(null);
  }

  function escolherPersonalizada() {
    if (somenteLeitura || ocupado) return;
    setModo("personalizada");
    setSalvoEm(null);
  }

  function descartar() {
    setErro(null);
    setDias(grade(jornada.dias));
    if (!jornada.personalizada) setModo("empresa");
  }

  function atualizarDia(diaSemana: number, periodos: PeriodoExpediente[]) {
    setDias((atual) => atual.map((dia) => (dia.diaSemana === diaSemana ? { ...dia, periodos } : dia)));
    setSalvoEm(null);
  }

  async function salvar() {
    if (!podeSalvar) return;
    setSalvando(true);
    setErro(null);
    try {
      const salva = await salvarJornadaUsuario(usuarioId, corpoDaJornada(dias));
      onChange(salva);
      setModo("personalizada");
      setDias(grade(salva.dias));
      setSalvoEm(new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }));
    } catch (e) {
      setErro(mensagemDeErroCapacidade(e, "Não foi possível salvar a jornada."));
    } finally {
      setSalvando(false);
    }
  }

  async function voltarAoExpediente() {
    setRemovendo(true);
    setErroRemover(null);
    try {
      const fallback = await usarExpedienteDaEmpresa(usuarioId);
      onChange(fallback);
      setModo("empresa");
      setDias(grade(fallback.dias));
      setConfirmarVoltar(false);
      setErro(null);
      setSalvoEm(null);
    } catch (e) {
      setErroRemover(mensagemDeErroCapacidade(e, "Não foi possível remover a jornada personalizada."));
    } finally {
      setRemovendo(false);
    }
  }

  const opcao = "flex cursor-pointer items-start gap-2 rounded-xl border px-3 py-2.5 text-sm transition";
  return (
    <section aria-label="Jornada de trabalho" className="rounded-2xl border border-line bg-surface p-4">
      <h3 className="text-base font-semibold text-fg">Jornada de trabalho</h3>

      <div role="radiogroup" aria-label="Origem da jornada" className="mt-3 grid gap-2 sm:grid-cols-2">
        <label className={`${opcao} ${modo === "empresa" ? "border-indigo-400 bg-indigo-50/50 dark:bg-indigo-500/10" : "border-line"} ${somenteLeitura ? "cursor-default" : ""}`}>
          <input type="radio" name={`jornada-${usuarioId}`} checked={modo === "empresa"} onChange={escolherEmpresa} disabled={somenteLeitura || ocupado} className="mt-0.5" />
          <span>
            <span className="block font-medium text-fg">Usar expediente da empresa</span>
            <span className="block text-xs text-fg-subtle">Padrão</span>
          </span>
        </label>
        <label className={`${opcao} ${modo === "personalizada" ? "border-indigo-400 bg-indigo-50/50 dark:bg-indigo-500/10" : "border-line"} ${somenteLeitura ? "cursor-default" : ""}`}>
          <input type="radio" name={`jornada-${usuarioId}`} checked={modo === "personalizada"} onChange={escolherPersonalizada} disabled={somenteLeitura || ocupado} className="mt-0.5" />
          <span>
            <span className="block font-medium text-fg">Jornada personalizada</span>
            <span className="block text-xs text-fg-subtle">Horários próprios por dia da semana</span>
          </span>
        </label>
      </div>

      {modo === "empresa" ? (
        <div className="mt-3">
          <p className="text-sm text-fg-muted">{TEXTO_JORNADA_EMPRESA}</p>
          <ul aria-label="Expediente da empresa (somente leitura)" className="mt-2 flex flex-col gap-0.5 text-xs text-fg-subtle">
            {resumoDaSemana(jornada.dias).map((linha) => (
              <li key={linha.dias}>
                <span className="inline-block w-16 font-medium text-fg-muted">{linha.dias}</span>
                {linha.texto}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="mt-3">
          <p className="text-xs text-fg-muted">{TEXTO_JORNADA_PERSONALIZADA}</p>
          {!jornada.personalizada && !somenteLeitura && (
            <p className="mt-1 text-xs text-fg-subtle">Os horários abaixo são uma sugestão a partir do expediente da empresa. Nada é gravado até você salvar.</p>
          )}
          <div className="mt-2">
            {DIAS_ORDEM.map((diaSemana) => (
              <PeriodosDoDia
                key={diaSemana}
                dia={diaSemana}
                periodos={dias.find((d) => d.diaSemana === diaSemana)?.periodos ?? []}
                erro={erros[diaSemana]}
                onChange={(periodos) => atualizarDia(diaSemana, periodos)}
                somenteLeitura={somenteLeitura || ocupado}
              />
            ))}
          </div>
          <p className="mt-2 text-xs text-fg-subtle">Total na semana: {horasDaSemana(dias)} h</p>
          {jornadaTodaFechada(dias) && <p className="mt-1 text-xs text-amber-700 dark:text-amber-400">{TEXTO_JORNADA_TODA_FECHADA}</p>}
        </div>
      )}

      {!somenteLeitura && (modo === "personalizada" || erro) && (
        <div className="mt-4 flex flex-wrap items-center justify-end gap-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
          {erro && (
            <p role="alert" className="mr-auto text-xs text-red-600 dark:text-red-400">
              {erro}
            </p>
          )}
          {!erro && Object.keys(erros).length > 0 && <p className="mr-auto text-xs text-amber-700 dark:text-amber-400">Corrija os horários destacados para salvar.</p>}
          {!erro && Object.keys(erros).length === 0 && salvoEm && !pendente && (
            <p role="status" className="mr-auto text-xs text-emerald-700 dark:text-emerald-400">
              Salvo às {salvoEm}.
            </p>
          )}
          {jornada.personalizada && (
            <Button type="button" variant="ghost" onClick={escolherEmpresa} disabled={ocupado}>
              Usar expediente da empresa
            </Button>
          )}
          {pendente && (
            <Button type="button" variant="secondary" onClick={descartar} disabled={ocupado}>
              {jornada.personalizada ? "Descartar alterações" : "Cancelar"}
            </Button>
          )}
          <Button type="button" onClick={salvar} disabled={!podeSalvar}>
            {salvando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            {salvando ? "Salvando…" : "Salvar jornada"}
          </Button>
        </div>
      )}

      {confirmarVoltar && (
        <ConfirmacaoCurta
          titulo="Usar expediente da empresa"
          texto={TEXTO_CONFIRMAR_VOLTAR_EMPRESA}
          confirmar="Remover jornada"
          ocupado={removendo}
          erro={erroRemover}
          onConfirm={voltarAoExpediente}
          onClose={() => setConfirmarVoltar(false)}
        />
      )}
    </section>
  );
}
