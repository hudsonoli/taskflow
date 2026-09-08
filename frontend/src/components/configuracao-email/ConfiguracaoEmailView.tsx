"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Loader2, Mail, ShieldCheck, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Switch } from "@/components/ui/Switch";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import {
  atualizarConfiguracaoEmailReal,
  obterConfiguracaoEmailReal,
  testarConfiguracaoEmailReal,
} from "@/lib/api-backend";
import type {
  ConfiguracaoEmailFormDraft,
  ConfiguracaoEmailRead,
  ConfiguracaoEmailTesteMotivo,
  ConfiguracaoEmailTesteResultado,
} from "@/types/configuracao-email";

/**
 * Fase 2G.7B2 — substitui por completo o mock/local state de Configuração de e-mail. V1 é
 * SMTP manual apenas: as simulações de OAuth Google/M365 do protótipo (login falso via
 * `setTimeout`, "conta conectada" fake) foram removidas — não existiam de verdade, e
 * mantê-las ao lado da configuração real sugeriria uma integração que não existe.
 */

const toneResultado: Record<ConfiguracaoEmailTesteMotivo, "green" | "amber" | "red"> = {
  sucesso: "green",
  configuracao_incompleta: "amber",
  dns_falhou: "red",
  host_bloqueado: "red",
  timeout: "red",
  autenticacao_invalida: "red",
  tls_invalido: "red",
  conexao_recusada: "red",
  erro_smtp: "red",
  erro_desconhecido: "red",
};

function createInitialDraft(configuracao?: ConfiguracaoEmailRead | null): ConfiguracaoEmailFormDraft {
  return {
    smtpHost: configuracao?.smtpHost ?? "",
    smtpPort: configuracao?.smtpPort != null ? String(configuracao.smtpPort) : "",
    smtpUsuario: configuracao?.smtpUsuario ?? "",
    // Nasce SEMPRE vazio — o GET nunca devolve a senha (nem mascarada, nem ciphertext). Ver
    // kickoff 2G.7B2, item 10.
    smtpSenha: "",
    removerSenha: false,
    remetenteEmail: configuracao?.remetenteEmail ?? "",
    remetenteNome: configuracao?.remetenteNome ?? "",
    usarTls: configuracao?.usarTls ?? true,
    usarSsl: configuracao?.usarSsl ?? false,
    ativo: configuracao?.ativo ?? false,
  };
}

export function ConfiguracaoEmailView() {
  const [configuracao, setConfiguracao] = useState<ConfiguracaoEmailRead | null>(null);
  const [draft, setDraft] = useState<ConfiguracaoEmailFormDraft>(() => createInitialDraft());
  const [draftInicial, setDraftInicial] = useState<ConfiguracaoEmailFormDraft>(() => createInitialDraft());
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);
  const [testando, setTestando] = useState(false);
  const [resultadoTeste, setResultadoTeste] = useState<ConfiguracaoEmailTesteResultado | null>(null);

  async function carregar() {
    setCarregando(true);
    setErro(null);
    try {
      const dados = await obterConfiguracaoEmailReal();
      // `id`/`createdAt`/`updatedAt` nulos é o DTO virtual (Empresa ainda não salvou nada) —
      // estado normal, nunca um erro.
      setConfiguracao(dados);
      setDraft(createInitialDraft(dados));
      setDraftInicial(createInitialDraft(dados));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar a configuração de e-mail.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    // setTimeout(0) tira o setState síncrono de dentro do corpo do efeito — mesmo padrão já
    // usado em AppDataContext.tsx (recarregarSessao/recarregarDemandas).
    const timeout = setTimeout(() => {
      void carregar();
    }, 0);
    return () => clearTimeout(timeout);
  }, []);

  // Dirty state simples: compara o draft inteiro (inclusive smtpSenha/removerSenha — digitar
  // uma senha nova ou marcar "remover" já conta como alteração pendente) contra o baseline
  // reconstruído no último load/save bem-sucedido.
  const alteracoesPendentes = useMemo(() => JSON.stringify(draft) !== JSON.stringify(draftInicial), [draft, draftInicial]);

  function updateDraft(patch: Partial<ConfiguracaoEmailFormDraft>) {
    setDraft((atual) => ({ ...atual, ...patch }));
    setResultadoTeste(null); // qualquer edição invalida o resultado do teste anterior
  }

  function handleUsarTls(checked: boolean) {
    updateDraft({
      usarTls: checked,
      usarSsl: checked ? false : draft.usarSsl,
      // Só sugere a porta padrão quando o campo está vazio — nunca sobrescreve uma porta já
      // informada (kickoff 2G.7B2, item 18).
      smtpPort: checked && draft.smtpPort.trim() === "" ? "587" : draft.smtpPort,
    });
  }

  function handleUsarSsl(checked: boolean) {
    updateDraft({
      usarSsl: checked,
      usarTls: checked ? false : draft.usarTls,
      smtpPort: checked && draft.smtpPort.trim() === "" ? "465" : draft.smtpPort,
    });
  }

  function handleRemoverSenha() {
    updateDraft({ removerSenha: true, smtpSenha: "" });
  }

  function cancelarRemocaoSenha() {
    updateDraft({ removerSenha: false });
  }

  function validarAntesDeSalvar(): string | null {
    if (draft.smtpPort.trim()) {
      const porta = Number(draft.smtpPort);
      if (!Number.isInteger(porta) || porta < 1 || porta > 65535) {
        return "A porta SMTP deve ser um número entre 1 e 65535.";
      }
    }
    if (draft.usarTls && draft.usarSsl) {
      return "TLS e SSL não podem estar ativos ao mesmo tempo.";
    }
    if (draft.ativo) {
      if (!draft.smtpHost.trim()) return "Informe o servidor SMTP para ativar a configuração.";
      if (!draft.remetenteEmail.trim()) return "Informe o e-mail do remetente para ativar a configuração.";
      const senhaResultanteExiste = draft.removerSenha
        ? false
        : draft.smtpSenha.trim() !== ""
          ? true
          : Boolean(configuracao?.smtpSenhaConfigurada);
      if (draft.smtpUsuario.trim() && !senhaResultanteExiste) {
        return "Informe a senha SMTP — o usuário foi preenchido, mas a configuração ficaria sem senha.";
      }
    }
    return null;
  }

  async function handleSalvar() {
    const mensagemInvalida = validarAntesDeSalvar();
    if (mensagemInvalida) {
      setErroSalvar(mensagemInvalida);
      return;
    }

    setSalvando(true);
    setErroSalvar(null);
    setResultadoTeste(null);
    try {
      await atualizarConfiguracaoEmailReal(draft);
      // Refetch explícito (não a resposta do PATCH otimisticamente) — zero optimistic update
      // estrutural, mesmo padrão real já adotado em SLA/ModeloCampanha.
      await carregar();
    } catch (error) {
      setErroSalvar(
        error instanceof Error ? error.message : "Não foi possível salvar a configuração de e-mail.",
      );
      // Nunca mantém a senha digitada no estado além do necessário — falhou, limpa e pede
      // reentrada (kickoff 2G.7B2, item 14).
      setDraft((atual) => ({ ...atual, smtpSenha: "", removerSenha: false }));
    } finally {
      setSalvando(false);
    }
  }

  async function handleTestar() {
    setTestando(true);
    setResultadoTeste(null);
    try {
      const resultado = await testarConfiguracaoEmailReal();
      setResultadoTeste(resultado);
    } catch (error) {
      setResultadoTeste({
        sucesso: false,
        motivo: "erro_desconhecido",
        mensagem: error instanceof Error ? error.message : "Não foi possível testar a conexão.",
      });
    } finally {
      setTestando(false);
    }
  }

  if (carregando) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-zinc-200 bg-white p-10 text-sm text-zinc-500 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando configuração de e-mail…
      </div>
    );
  }

  if (erro) {
    return <EstadoErro mensagem={erro} onRetry={carregar} />;
  }

  const podeTestar =
    configuracao?.id != null &&
    Boolean(configuracao.smtpHost) &&
    configuracao.smtpPort != null &&
    !alteracoesPendentes &&
    !salvando &&
    !testando;

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
              <Mail className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Configuração de e-mail</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Servidor SMTP usado para disparar e-mails do sistema, como o aviso de conclusão de tarefa ao cliente.
              </p>
            </div>
          </div>
          <Badge tone="green">Banco real</Badge>
        </div>
      </motion.div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Servidor SMTP</p>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
              Integrações OAuth com Google e Microsoft poderão ser adicionadas futuramente — por enquanto, configuração
              manual apenas.
            </p>
          </div>
          <Switch
            checked={draft.ativo}
            onChange={(checked) => updateDraft({ ativo: checked })}
            label="Ativar configuração de e-mail"
          />
        </div>

        {erroSalvar && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erroSalvar}
          </div>
        )}

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Input
            label="Nome do remetente"
            placeholder="Ex: Taskfloww Agência"
            value={draft.remetenteNome}
            onChange={(event) => updateDraft({ remetenteNome: event.target.value })}
          />
          <Input
            label="E-mail do remetente"
            type="email"
            placeholder="disparo@agencia.com.br"
            value={draft.remetenteEmail}
            onChange={(event) => updateDraft({ remetenteEmail: event.target.value })}
          />
          <Input
            label="Servidor SMTP"
            placeholder="smtp.agencia.com.br"
            value={draft.smtpHost}
            onChange={(event) => updateDraft({ smtpHost: event.target.value })}
          />
          <Input
            label="Porta SMTP"
            type="number"
            placeholder="587"
            value={draft.smtpPort}
            onChange={(event) => updateDraft({ smtpPort: event.target.value })}
          />
          <Input
            label="Usuário SMTP"
            placeholder="usuario@agencia.com.br"
            value={draft.smtpUsuario}
            onChange={(event) => updateDraft({ smtpUsuario: event.target.value })}
          />
          <div>
            <Input
              label="Senha SMTP"
              type="password"
              placeholder="Deixe em branco para manter a senha atual"
              value={draft.smtpSenha}
              disabled={draft.removerSenha}
              onChange={(event) => updateDraft({ smtpSenha: event.target.value, removerSenha: false })}
            />
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              {configuracao?.smtpSenhaConfigurada && !draft.removerSenha && (
                <Badge tone="blue">Senha configurada</Badge>
              )}
              {draft.removerSenha ? (
                <button
                  type="button"
                  onClick={cancelarRemocaoSenha}
                  className="text-xs font-medium text-indigo-600 underline-offset-2 hover:underline dark:text-indigo-400"
                >
                  Cancelar remoção da senha
                </button>
              ) : (
                configuracao?.smtpSenhaConfigurada && (
                  <button
                    type="button"
                    onClick={handleRemoverSenha}
                    className="text-xs font-medium text-red-600 underline-offset-2 hover:underline dark:text-red-400"
                  >
                    Remover senha salva
                  </button>
                )
              )}
            </div>
            {draft.removerSenha && (
              <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                A senha salva será removida ao salvar as alterações.
              </p>
            )}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-x-8 gap-y-3">
          <Switch checked={draft.usarTls} onChange={handleUsarTls} label="Usar STARTTLS" />
          <Switch checked={draft.usarSsl} onChange={handleUsarSsl} label="Usar SSL implícito" />
        </div>

        <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-zinc-100 bg-zinc-50/70 p-3.5 text-xs text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950/30 dark:text-zinc-400">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          A senha nunca é exibida depois de salva — só é possível confirmar que existe ou substituí-la.
        </div>

        <div className="mt-5 flex flex-col gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-1">
            <Button type="button" variant="secondary" onClick={handleTestar} disabled={!podeTestar}>
              {testando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              {testando ? "Testando…" : "Testar conexão"}
            </Button>
            {configuracao?.id != null && alteracoesPendentes && (
              <p className="text-xs text-amber-600 dark:text-amber-400">Salve as alterações antes de testar.</p>
            )}
            {configuracao?.id == null && (
              <p className="text-xs text-zinc-400">Salve a configuração pelo menos uma vez para poder testá-la.</p>
            )}
          </div>
          <Button type="button" onClick={handleSalvar} disabled={salvando}>
            {salvando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            {salvando ? "Salvando…" : "Salvar alterações"}
          </Button>
        </div>

        {resultadoTeste && (
          <div
            className={`mt-4 flex items-start gap-2.5 rounded-xl border p-3.5 text-xs ${
              toneResultado[resultadoTeste.motivo] === "green"
                ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
                : toneResultado[resultadoTeste.motivo] === "amber"
                  ? "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300"
                  : "border-red-200 bg-red-50 text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
            }`}
          >
            {resultadoTeste.sucesso ? (
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            ) : toneResultado[resultadoTeste.motivo] === "amber" ? (
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            ) : (
              <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            )}
            <span>{resultadoTeste.sucesso ? "Conexão SMTP validada com sucesso." : resultadoTeste.mensagem}</span>
          </div>
        )}
      </div>
    </div>
  );
}
