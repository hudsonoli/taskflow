"use client";

import { Clock } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { textosForaDoExpediente, type BloqueioExpediente } from "@/lib/expediente-acesso";

/**
 * "Fora do horário de expediente" (Fase Expediente 2). A SESSÃO é válida — por isso não é o login: a política da empresa recusa o uso agora. Os horários vêm do servidor
 * (fuso da empresa); quando o acesso volta, o próprio guarda (polling único de `/expediente/estado`) devolve o app, sem novo login.
 */
export function ForaDoExpedienteView({ bloqueio, onSair, saindo }: { bloqueio: BloqueioExpediente; onSair: () => void; saindo: boolean }) {
  const textos = textosForaDoExpediente(bloqueio);
  return (
    <div className="flex h-screen items-center justify-center bg-app px-4" role="status" aria-live="polite">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 text-center shadow-sm">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <Clock className="h-5 w-5" />
        </div>
        <h1 className="text-lg font-semibold tracking-tight text-fg">{textos.titulo}</h1>
        {textos.proximoAcesso && <p className="mt-2 text-sm text-fg-muted">{textos.proximoAcesso}</p>}
        {textos.proximoTrabalho && <p className="mt-1 text-xs text-fg-muted">{textos.proximoTrabalho}</p>}
        {!textos.proximoAcesso && !textos.proximoTrabalho && <p className="mt-2 text-sm text-fg-muted">O acesso ao sistema está fora do horário definido pela sua empresa.</p>}
        <div className="mt-5 flex justify-center">
          <Button type="button" variant="secondary" onClick={onSair} disabled={saindo}>
            {saindo ? "Saindo…" : "Sair"}
          </Button>
        </div>
      </div>
    </div>
  );
}
