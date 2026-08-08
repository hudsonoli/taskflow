"use client";

import { AlertTriangle, X } from "lucide-react";
import { formatarReferenciaVisual } from "@/lib/formatarReferencia";
import type { MotivoPossivelDuplicidade, PossivelDuplicidadeCliente } from "@/types/cliente";

const rotuloMotivo: Record<MotivoPossivelDuplicidade, string> = {
  nome: "mesmo nome",
  documento: "mesmo documento",
  nome_documento: "mesmo nome e documento",
};

/**
 * Sinaliza cadastros parecidos com o que acabou de ser salvo.
 *
 * O cadastro **já foi criado** — isto é informativo. Em Cliente, nome e documento não são
 * identidade: filiais homônimas com CNPJ distinto e empreendimentos distintos sob o mesmo
 * CNPJ são cadastros legítimos (ver docs/padrao-entidades-externas.md).
 *
 * Por isso o texto evita afirmar que são duplicados, não oferece merge e não altera nada:
 * quem decide é a pessoa. Deduplicação é funcionalidade futura, com revisão humana.
 */
export function PossiveisDuplicidadesAviso({
  duplicidades,
  onDispensar,
}: {
  duplicidades: PossivelDuplicidadeCliente[];
  onDispensar: () => void;
}) {
  return (
    <div
      role="status"
      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="text-sm font-medium">Encontramos clientes com dados semelhantes.</p>
            <p className="mt-0.5 text-xs opacity-80">
              O cadastro foi salvo normalmente. Confira se não é o mesmo cliente já registrado.
            </p>

            <ul className="mt-2.5 flex flex-col gap-1.5">
              {duplicidades.map((item) => (
                <li key={item.id} className="text-xs">
                  <span className="font-medium">
                    {formatarReferenciaVisual({
                      entidade: "cliente",
                      sequencialReferencia: Number(item.codigoReferencia.slice(3)),
                      nome: item.nome,
                    })}
                  </span>
                  {item.documento && <span className="opacity-80"> · {item.documento}</span>}
                  <span className="opacity-80"> · {rotuloMotivo[item.motivo]}</span>
                  {item.status === "arquivado" && <span className="opacity-80"> · arquivado</span>}
                  <span className="ml-1.5 font-mono text-[11px] opacity-60">{item.codigoReferencia}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <button
          type="button"
          onClick={onDispensar}
          aria-label="Dispensar aviso"
          className="rounded-lg p-1 transition hover:bg-amber-100 dark:hover:bg-amber-500/20"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
