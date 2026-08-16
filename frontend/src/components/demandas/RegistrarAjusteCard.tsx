"use client";

import { useState } from "react";
import { RotateCcw, UserCog, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { registrarAjusteDemanda, type TipoAjusteDemanda } from "@/lib/api-backend";
import type { Demanda } from "@/types/demanda";

const TIPOS: { tipo: TipoAjusteDemanda; label: string; icon: typeof UserCog }[] = [
  { tipo: "ajuste_interno", label: "Ajuste interno", icon: UserCog },
  { tipo: "ajuste_cliente", label: "Ajuste de cliente", icon: Users },
  { tipo: "refacao", label: "Refação", icon: RotateCcw },
];

/**
 * Registrar ajuste (Fase 2E.4) — não muda nenhum campo da Demanda, só publica um evento real
 * na timeline (ver POST /demandas/{id}/ajustes). Até esta fase, o clique só gravava em
 * `historico[]` local (`setDemandas(...)`) e nunca chegava ao servidor — sobrevivia até o
 * próximo F5, quando desaparecia (ver instrução da fase, item 1).
 *
 * As contagens por tipo que este card mostrava (derivadas do `historico[]` embutido na
 * Demanda) saíram: manter isso exigiria buscar o histórico completo só para contar botão,
 * e Histórico já tem tela própria para consultar o que foi registrado.
 */
export function RegistrarAjusteCard({ demanda }: { demanda: Demanda }) {
  const [processando, setProcessando] = useState<TipoAjusteDemanda | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function registrar(tipo: TipoAjusteDemanda) {
    setProcessando(tipo);
    setErro(null);
    try {
      await registrarAjusteDemanda(demanda.id, tipo);
    } catch {
      setErro("Não foi possível registrar o ajuste.");
    } finally {
      setProcessando(null);
    }
  }

  return (
    <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/40">
      <p className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Registrar movimentação</p>
      <div className="flex flex-wrap gap-2">
        {TIPOS.map(({ tipo, label, icon: Icon }) => (
          <Button
            key={tipo}
            type="button"
            variant="secondary"
            onClick={() => void registrar(tipo)}
            disabled={processando !== null}
            className="px-3 py-1.5 text-xs"
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </Button>
        ))}
      </div>
      {erro && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{erro}</p>}
    </div>
  );
}
