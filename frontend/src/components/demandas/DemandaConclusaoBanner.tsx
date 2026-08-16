"use client";

import { useState } from "react";
import { CheckCircle2, Mail, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { registrarConclusaoEmailDemanda } from "@/lib/api-backend";
import type { Demanda } from "@/types/demanda";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { resolverClientePorReferencia } from "@/lib/referencias";

/**
 * Aviso de conclusão (Fase 2E.4) — `emailConclusaoEnviado`/`emailConclusaoData` já eram
 * campos reais, mas até esta fase só chegavam a `setDemandas(...)` local (ver instrução da
 * fase, item 1). Agora vai por `POST /demandas/{id}/conclusao-email`: enviar e dispensar
 * gravam os MESMOS campos reais, só o evento de domínio publicado muda — é o único jeito de
 * diferenciar as duas intenções na timeline depois (ver DemandaConclusaoEmailRegistrar).
 */
export function DemandaConclusaoBanner({
  demanda,
  onChange,
}: {
  demanda: Demanda;
  onChange: (demanda: Demanda) => void;
}) {
  const { clientes } = useDiretorioClientes();
  const cliente = resolverClientePorReferencia(demanda.clienteId, clientes);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  if (demanda.status !== "concluida" || demanda.emailConclusaoEnviado) return null;
  if (!cliente || !cliente.avisarConclusaoPorEmail) return null;

  const destinatarios = cliente.contatos.filter((contato) => contato.recebeEntregas).map((contato) => contato.email);
  const destinatariosFinais = destinatarios.length > 0 ? destinatarios : cliente.email ? [cliente.email] : [];

  async function registrar(enviado: boolean) {
    setProcessando(true);
    setErro(null);
    try {
      const atualizada = await registrarConclusaoEmailDemanda(demanda.id, enviado);
      onChange(atualizada);
    } catch {
      setErro("Não foi possível registrar a conclusão.");
    } finally {
      setProcessando(false);
    }
  }

  function handleEnviar() {
    void registrar(true);
  }

  function handleDispensar() {
    void registrar(false);
  }

  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-500/30 dark:bg-emerald-500/10">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-600 ring-1 ring-emerald-100 dark:bg-zinc-900 dark:text-emerald-400 dark:ring-emerald-500/20">
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Trabalho concluído</p>
            <p className="mt-1 text-sm leading-6 text-emerald-700 dark:text-emerald-400">
              Enviar um e-mail para o cliente avisando que o trabalho final foi concluído?
            </p>
            <p className="mt-1 text-xs text-emerald-600/80 dark:text-emerald-400/70">
              {destinatariosFinais.length > 0
                ? `Destinatário(s): ${destinatariosFinais.join(", ")}`
                : "Nenhum contato cadastrado para este cliente — cadastre um contato para receber entregas."}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button type="button" variant="secondary" onClick={handleDispensar} disabled={processando} className="px-3 py-1.5 text-xs">
            <X className="h-3.5 w-3.5" />
            Agora não
          </Button>
          <Button
            type="button"
            onClick={handleEnviar}
            className="px-3 py-1.5 text-xs"
            disabled={processando || destinatariosFinais.length === 0}
          >
            <Mail className="h-3.5 w-3.5" />
            Enviar e-mail
          </Button>
        </div>
      </div>
      {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}
    </div>
  );
}
