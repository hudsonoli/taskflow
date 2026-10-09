"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Hash, Info, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Switch } from "@/components/ui/Switch";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { atualizarNumeracaoTarefaReal, obterNumeracaoTarefaReal } from "@/lib/api-backend";
import {
  type CampoConfiguracaoNumeracao,
  DIGITOS_MAX,
  DIGITOS_MIN,
  PREFIXO_MAX,
  SEPARADOR_MAX,
  diferencaParaPatch,
  exigeConfirmacao,
  formatarIdentificador,
  validarFormato,
  validarProximoNumero,
} from "@/lib/numeracao-tarefas";
import type { ConfiguracaoNumeracaoTarefaRead } from "@/types/configuracao-numeracao-tarefa";

/**
 * Numeração de tarefas — estado do contador (Fase 2G.8B) + configuração do formato das PRÓXIMAS tarefas (Fase 7D.1).
 *
 * O que muda aqui vale só para tarefas novas: cada tarefa guarda o identificador que recebeu na emissão e nunca o perde
 * (`#845` continua `#845`). Não existe "reiniciar a cada ano" — o número é contínuo (fase futura). A prévia é calculada no
 * navegador só para dar retorno imediato; não consome número e o servidor revalida tudo ao salvar.
 */

const AVISO_HISTORICO = "As alterações serão aplicadas somente às novas tarefas. Tarefas já emitidas mantêm sua identificação.";

function paraDraft(dados: ConfiguracaoNumeracaoTarefaRead): CampoConfiguracaoNumeracao {
  return {
    prefixo: dados.prefixo,
    separador: dados.separador,
    incluirAno: dados.incluirAno,
    digitos: dados.digitos,
    proximoNumero: dados.proximoNumero,
  };
}

export function ConfiguracaoNumeracaoTarefaView() {
  const [dados, setDados] = useState<ConfiguracaoNumeracaoTarefaRead | null>(null);
  const [draft, setDraft] = useState<CampoConfiguracaoNumeracao | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);
  const [salvoEm, setSalvoEm] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);

  async function carregar() {
    setCarregando(true);
    setErro(null);
    try {
      const lido = await obterNumeracaoTarefaReal();
      setDados(lido);
      setDraft(paraDraft(lido));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar a numeração de tarefas.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    // setTimeout(0) tira o setState síncrono de dentro do corpo do efeito — mesmo padrão já
    // usado em ConfiguracaoEmailView/AppDataContext.
    const timeout = setTimeout(() => {
      void carregar();
    }, 0);
    return () => clearTimeout(timeout);
  }, []);

  const atual = useMemo(() => (dados ? paraDraft(dados) : null), [dados]);
  const patch = useMemo(() => (atual && draft ? diferencaParaPatch(atual, draft) : {}), [atual, draft]);
  const alterado = Object.keys(patch).length > 0;

  const erroFormato = draft ? validarFormato(draft) : null;
  const erroProximo = draft && dados ? validarProximoNumero(draft.proximoNumero, dados.maiorNumeroEmitido) : null;
  const preview =
    draft && !erroFormato && !erroProximo ? formatarIdentificador(draft, draft.proximoNumero, new Date().getFullYear()) : null;

  function atualizar(parcial: Partial<CampoConfiguracaoNumeracao>) {
    setDraft((anterior) => (anterior ? { ...anterior, ...parcial } : anterior));
    setSalvoEm(null);
    setErroSalvar(null);
    setConfirmando(false);
  }

  async function salvar() {
    if (!alterado || erroFormato || erroProximo) return;
    if (exigeConfirmacao(patch) && !confirmando) {
      setConfirmando(true); // confirmação leve, no próprio card — só para a mudança do próximo número
      return;
    }
    setSalvando(true);
    setErroSalvar(null);
    try {
      const salvo = await atualizarNumeracaoTarefaReal(patch);
      setDados(salvo);
      setDraft(paraDraft(salvo));
      setSalvoEm(salvo.preview);
      setConfirmando(false);
    } catch (error) {
      setErroSalvar(error instanceof Error ? error.message : "Não foi possível salvar a configuração.");
      setConfirmando(false);
    } finally {
      setSalvando(false);
    }
  }

  if (carregando) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-sm text-fg-muted shadow-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando numeração de tarefas…
      </div>
    );
  }

  if (erro || !dados || !draft) {
    return <EstadoErro mensagem={erro ?? "Não foi possível carregar a numeração de tarefas."} onRetry={carregar} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-line bg-surface p-4 shadow-sm"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <Hash className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-fg">Numeração de tarefas</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-fg-muted">
                Defina como as próximas tarefas serão identificadas. O número é contínuo e as tarefas já emitidas não mudam.
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-fg-subtle">Entidade</p>
            <p className="mt-1 text-lg font-semibold text-fg">{dados.rotuloEntidade}</p>
          </div>
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-fg-subtle">Status</p>
            <p className="mt-1 flex items-center gap-1.5 text-lg font-semibold">
              {dados.consistente ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-700 dark:text-emerald-400" />
                  <span className="text-emerald-700 dark:text-emerald-400">Consistente</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="h-4 w-4 text-amber-700 dark:text-amber-400" />
                  <span className="text-amber-700 dark:text-amber-400">Atenção necessária</span>
                </>
              )}
            </p>
          </div>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-500/20 dark:bg-indigo-500/5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-600 dark:text-indigo-400">Contador atual</p>
            <p className="mt-1 text-lg font-semibold text-fg">{dados.contadorAtual}</p>
          </div>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-500/20 dark:bg-indigo-500/5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-600 dark:text-indigo-400">Próximo número</p>
            <p className="mt-1 text-lg font-semibold text-fg">{dados.proximoNumero}</p>
          </div>
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30 sm:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-fg-subtle">Maior número emitido no TaskFloww</p>
            <p className="mt-1 text-lg font-semibold text-fg">{dados.maiorNumeroEmitido != null ? dados.maiorNumeroEmitido : "—"}</p>
          </div>
        </div>

        {!dados.consistente && (
          <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-400">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {dados.motivoInconsistencia ?? "A numeração precisa de verificação administrativa."}
          </div>
        )}
      </div>

      <section aria-labelledby="formato-numeracao" className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <h2 id="formato-numeracao" className="text-sm font-semibold text-fg">
          Formato das próximas tarefas
        </h2>
        <p className="mt-0.5 text-xs text-fg-muted">{AVISO_HISTORICO}</p>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Input
            label="Prefixo"
            value={draft.prefixo}
            maxLength={PREFIXO_MAX}
            placeholder="Ex.: BOX"
            onChange={(evento) => atualizar({ prefixo: evento.target.value })}
          />
          <Input
            label="Separador"
            value={draft.separador}
            maxLength={SEPARADOR_MAX}
            placeholder="Ex.: -"
            onChange={(evento) => atualizar({ separador: evento.target.value })}
          />
          <Input
            label="Quantidade mínima de dígitos"
            type="number"
            min={DIGITOS_MIN}
            max={DIGITOS_MAX}
            value={Number.isNaN(draft.digitos) ? "" : draft.digitos}
            onChange={(evento) => atualizar({ digitos: evento.target.value === "" ? Number.NaN : Number(evento.target.value) })}
          />
          <Input
            label="Próximo número"
            type="number"
            min={1}
            value={Number.isNaN(draft.proximoNumero) ? "" : draft.proximoNumero}
            onChange={(evento) =>
              atualizar({ proximoNumero: evento.target.value === "" ? Number.NaN : Number(evento.target.value) })
            }
          />
          <div className="flex items-end sm:col-span-2 lg:col-span-1">
            <Switch
              checked={draft.incluirAno}
              onChange={(checked) => atualizar({ incluirAno: checked })}
              label="Incluir ano"
              description="Escreve o ano da emissão no identificador. Não reinicia o número."
            />
          </div>
        </div>

        <div className="mt-5 rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-500/20 dark:bg-indigo-500/5" aria-live="polite">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-600 dark:text-indigo-400">
            Prévia da próxima tarefa
          </p>
          <p className="mt-1 text-lg font-semibold text-fg" data-testid="preview-numeracao">
            {preview ?? "—"}
          </p>
          <p className="mt-0.5 text-xs text-fg-muted">A prévia não consome número.</p>
        </div>

        {(erroFormato || erroProximo) && (
          <p role="alert" className="mt-3 text-xs text-red-600 dark:text-red-400">
            {erroFormato ?? erroProximo}
          </p>
        )}
        {erroSalvar && (
          <p role="alert" className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erroSalvar}
          </p>
        )}
        {salvoEm && (
          <p role="status" className="mt-3 flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" /> Configuração salva. A próxima tarefa será {salvoEm}.
          </p>
        )}

        {confirmando && (
          <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              Confirmar o próximo número {draft.proximoNumero}? {AVISO_HISTORICO}
            </span>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button type="button" onClick={() => void salvar()} disabled={!alterado || salvando || Boolean(erroFormato) || Boolean(erroProximo)}>
            {salvando ? "Salvando…" : confirmando ? "Confirmar e salvar" : "Salvar configuração"}
          </Button>
          {confirmando && (
            <Button type="button" variant="secondary" onClick={() => setConfirmando(false)} disabled={salvando}>
              Cancelar
            </Button>
          )}
        </div>
      </section>
    </div>
  );
}
