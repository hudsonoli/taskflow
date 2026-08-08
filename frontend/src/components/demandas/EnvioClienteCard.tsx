"use client";

import { useState } from "react";
import { CheckCircle2, Clock, Send } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { formatPrazo, generateId } from "@/lib/demandas-mock";
import type { Demanda } from "@/types/demanda";

function defaultPrazoRetorno(): string {
  const date = new Date(Date.now() + 2 * 24 * 60 * 60 * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

function registrarHistorico(demanda: Demanda, acao: string): Demanda {
  const now = new Date().toISOString();
  return {
    ...demanda,
    updatedAt: now,
    historico: [
      {
        id: generateId("hist-demanda"),
        usuarioId: "user-1",
        usuario: "Você",
        acao,
        dataHora: new Date().toLocaleString("pt-BR"),
        ip: "127.0.0.1",
        dispositivo: "Workspace local",
      },
      ...demanda.historico,
    ],
  };
}

export function EnvioClienteCard({ demanda, onChange }: { demanda: Demanda; onChange: (demanda: Demanda) => void }) {
  const [prazoRetorno, setPrazoRetorno] = useState(defaultPrazoRetorno());
  const aguardandoCliente =
    demanda.status === "aguardando_cliente" && Boolean(demanda.enviadoClienteEm) && !demanda.retornoRecebidoEm;

  function enviarParaCliente() {
    const now = new Date().toISOString();
    onChange(
      registrarHistorico(
        {
          ...demanda,
          status: "aguardando_cliente",
          enviadoClienteEm: now,
          prazoRetornoCliente: prazoRetorno,
          retornoRecebidoEm: undefined,
        },
        `Enviado para aprovação do cliente — retorno até ${formatPrazo(prazoRetorno)}`,
      ),
    );
  }

  function marcarRetornoRecebido() {
    const now = new Date().toISOString();
    onChange(
      registrarHistorico(
        { ...demanda, retornoRecebidoEm: now, prazoRetornoCliente: undefined },
        "Retorno do cliente registrado",
      ),
    );
  }

  if (aguardandoCliente) {
    return (
      <div className="rounded-xl border border-amber-100 bg-amber-50/60 p-3.5 dark:border-amber-500/20 dark:bg-amber-500/5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
              <Clock className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Aguardando retorno do cliente</p>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Enviado em {formatPrazo(demanda.enviadoClienteEm ?? "")} · retorno até{" "}
                <strong>{formatPrazo(demanda.prazoRetornoCliente ?? "")}</strong>
              </p>
            </div>
          </div>
          <Button type="button" variant="secondary" onClick={marcarRetornoRecebido} className="px-3 py-1.5 text-xs">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Registrar retorno
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/40">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Enviar para o cliente</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">Marca o prazo de retorno para alteração/aprovação.</p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <Input
            label="Retorno até"
            type="datetime-local"
            value={prazoRetorno}
            onChange={(event) => setPrazoRetorno(event.target.value)}
            className="w-56"
          />
          <Button type="button" onClick={enviarParaCliente} className="px-3 py-2.5 text-xs">
            <Send className="h-3.5 w-3.5" />
            Enviar
          </Button>
        </div>
      </div>
      {demanda.status === "aguardando_cliente" && !demanda.enviadoClienteEm && (
        <Badge tone="amber">Status já está como aguardando cliente</Badge>
      )}
    </div>
  );
}
