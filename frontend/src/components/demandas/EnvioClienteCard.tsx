"use client";

import { useState } from "react";
import { CheckCircle2, Clock, Send } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { patchDemandaReal } from "@/lib/api-backend";
import { formatPrazo } from "@/lib/demandas";
import type { Demanda } from "@/types/demanda";

function defaultPrazoRetorno(): string {
  const date = new Date(Date.now() + 2 * 24 * 60 * 60 * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

/**
 * Envio ao cliente (Fase 2E.4) — `status`/`enviadoClienteEm`/`prazoRetornoCliente`/
 * `retornoRecebidoEm` já eram campos reais e persistidos (`DemandaUpdate`), mas até esta
 * fase só chegavam a `setDemandas(...)` local — nunca ao `PATCH /demandas/{id}` real.
 * Sobrevivia até o próximo F5, quando revertia sem aviso (ver instrução da fase, item 1).
 *
 * Sem endpoint dedicado: é PATCH comum. "Enviar" já gera `demanda.status_alterado`
 * automaticamente; "Registrar retorno" publica `demanda.retorno_cliente_registrado` (ver
 * DemandaService.update_demanda) — os dois já aparecem na timeline sem nada extra aqui.
 */
export function EnvioClienteCard({ demanda, onChange }: { demanda: Demanda; onChange: (demanda: Demanda) => void }) {
  const [prazoRetorno, setPrazoRetorno] = useState(defaultPrazoRetorno());
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const aguardandoCliente =
    demanda.status === "aguardando_cliente" && Boolean(demanda.enviadoClienteEm) && !demanda.retornoRecebidoEm;

  async function enviarParaCliente() {
    setProcessando(true);
    setErro(null);
    try {
      const atualizada = await patchDemandaReal(demanda.id, {
        status: "aguardando_cliente",
        enviadoClienteEm: new Date().toISOString(),
        prazoRetornoCliente: prazoRetorno,
      });
      onChange(atualizada);
    } catch {
      setErro("Não foi possível enviar para o cliente.");
    } finally {
      setProcessando(false);
    }
  }

  async function marcarRetornoRecebido() {
    setProcessando(true);
    setErro(null);
    try {
      const atualizada = await patchDemandaReal(demanda.id, {
        retornoRecebidoEm: new Date().toISOString(),
      });
      onChange(atualizada);
    } catch {
      setErro("Não foi possível registrar o retorno do cliente.");
    } finally {
      setProcessando(false);
    }
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
          <Button
            type="button"
            variant="secondary"
            onClick={() => void marcarRetornoRecebido()}
            disabled={processando}
            className="px-3 py-1.5 text-xs"
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            Registrar retorno
          </Button>
        </div>
        {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}
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
          <Button type="button" onClick={() => void enviarParaCliente()} disabled={processando} className="px-3 py-2.5 text-xs">
            <Send className="h-3.5 w-3.5" />
            Enviar
          </Button>
        </div>
      </div>
      {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}
      {demanda.status === "aguardando_cliente" && !demanda.enviadoClienteEm && (
        <Badge tone="amber">Status já está como aguardando cliente</Badge>
      )}
    </div>
  );
}
