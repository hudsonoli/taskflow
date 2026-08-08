"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Mail, Shield, Unplug } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Switch } from "@/components/ui/Switch";
import { useAppData } from "@/lib/AppDataContext";
import type { ProvedorEmail } from "@/types/configuracao-email";

const provedorLabels: Record<Exclude<ProvedorEmail, "manual">, string> = {
  google: "Google",
  m365: "Microsoft 365",
};

export function ConfiguracaoEmailView() {
  const { configuracaoEmail, setConfiguracaoEmail, usuarioAtual } = useAppData();
  const [conectando, setConectando] = useState<ProvedorEmail | null>(null);

  const contaConectadaViaOAuth = configuracaoEmail.provedor !== "manual" && Boolean(configuracaoEmail.contaConectada);

  function updateConfig(patch: Partial<typeof configuracaoEmail>) {
    setConfiguracaoEmail((current) => ({ ...current, ...patch, updatedAt: new Date().toISOString() }));
  }

  function conectarConta(provedor: Exclude<ProvedorEmail, "manual">) {
    setConectando(provedor);
    // Login simulado — sem OAuth real nesta fase de prototipação (ver CLAUDE.md).
    setTimeout(() => {
      const contaSimulada = usuarioAtual?.email || `contato@${provedor === "google" ? "gmail.com" : "empresa.onmicrosoft.com"}`;
      updateConfig({
        provedor,
        contaConectada: contaSimulada,
        emailDisparo: contaSimulada,
        ativo: true,
      });
      setConectando(null);
    }, 600);
  }

  function desconectarConta() {
    updateConfig({ provedor: "manual", contaConectada: undefined, ativo: false });
  }

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
                Conta usada para disparar e-mails do sistema, como o aviso de conclusão de tarefa ao cliente.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Conectar conta</p>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
          Autentique com um provedor para disparar e-mails a partir da conta conectada (simulado nesta fase).
        </p>

        {contaConectadaViaOAuth ? (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 dark:border-emerald-500/30 dark:bg-emerald-500/10">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <div>
                <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                  Conectado via {provedorLabels[configuracaoEmail.provedor as Exclude<ProvedorEmail, "manual">]}
                </p>
                <p className="text-xs text-emerald-700/80 dark:text-emerald-400/80">{configuracaoEmail.contaConectada}</p>
              </div>
            </div>
            <Button type="button" variant="secondary" onClick={desconectarConta} className="px-3 py-1.5 text-xs">
              <Unplug className="h-3.5 w-3.5" />
              Desconectar
            </Button>
          </div>
        ) : (
          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => conectarConta("google")}
              disabled={conectando !== null}
              className="px-4 py-2.5 text-sm"
            >
              {conectando === "google" ? "Conectando…" : "Conectar com Google"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => conectarConta("m365")}
              disabled={conectando !== null}
              className="px-4 py-2.5 text-sm"
            >
              {conectando === "m365" ? "Conectando…" : "Conectar com Microsoft 365"}
            </Button>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Configuração manual (SMTP)</p>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
              Use quando o disparo não passar por Google/M365 — servidor SMTP próprio ou de terceiros.
            </p>
          </div>
          <Switch
            checked={configuracaoEmail.ativo}
            onChange={(checked) => updateConfig({ ativo: checked })}
            label={configuracaoEmail.ativo ? "Disparo ativo" : "Disparo desativado"}
          />
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Input
            label="Nome de exibição"
            placeholder="Ex: Taskfloww Agência"
            value={configuracaoEmail.nomeExibicao}
            onChange={(event) => updateConfig({ nomeExibicao: event.target.value })}
          />
          <Input
            label="E-mail de disparo"
            type="email"
            placeholder="disparo@agencia.com.br"
            value={configuracaoEmail.emailDisparo}
            onChange={(event) => updateConfig({ emailDisparo: event.target.value, provedor: "manual", contaConectada: undefined })}
          />
          <Input
            label="Servidor SMTP"
            placeholder="smtp.agencia.com.br"
            value={configuracaoEmail.servidorSmtp}
            onChange={(event) => updateConfig({ servidorSmtp: event.target.value })}
          />
          <Input
            label="Porta"
            type="number"
            placeholder="587"
            value={configuracaoEmail.portaSmtp ?? ""}
            onChange={(event) => updateConfig({ portaSmtp: event.target.value ? Number(event.target.value) : null })}
          />
          <Input
            label="Usuário SMTP"
            placeholder="usuario@agencia.com.br"
            value={configuracaoEmail.usuarioSmtp}
            onChange={(event) => updateConfig({ usuarioSmtp: event.target.value })}
          />
          <Input
            label="Senha"
            type="password"
            placeholder="••••••••"
            value={configuracaoEmail.senhaSmtp}
            onChange={(event) => updateConfig({ senhaSmtp: event.target.value })}
          />
        </div>

        <div className="mt-4 max-w-xs">
          <Switch
            checked={configuracaoEmail.usarSsl}
            onChange={(checked) => updateConfig({ usarSsl: checked })}
            label="Conexão segura (SSL/TLS)"
          />
        </div>

        <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-zinc-100 bg-zinc-50/70 p-3.5 text-xs text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950/30 dark:text-zinc-400">
          <Shield className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Dados locais desta fase de prototipação — sem envio real de e-mails nem integração externa.
        </div>
      </div>
    </div>
  );
}
