"use client";

import { AlertTriangle, X } from "lucide-react";
import { formatarReferenciaVisual } from "@/lib/formatarReferencia";
import type { MotivoPossivelDuplicidade, PossivelDuplicidadeFornecedor } from "@/types/fornecedor";

const rotuloMotivo: Record<MotivoPossivelDuplicidade, string> = {
  nome: "mesmo nome",
  documento: "mesmo documento",
  nome_documento: "mesmo nome e documento",
};

/**
 * Sinaliza cadastros parecidos com o que acabou de ser salvo.
 *
 * O cadastro **já foi criado** — isto é informativo. Em Fornecedor, como em Cliente, nome e
 * documento não são identidade (ver docs/padrao-entidades-externas.md): a base importada tem
 * registros sem documento e documento repetido entre cadastros distintos.
 *
 * Por isso o texto evita afirmar que são duplicados, não oferece merge e não altera nada:
 * quem decide é a pessoa. Deduplicação é funcionalidade futura, com revisão humana.
 */
export function PossiveisDuplicidadesFornecedorAviso({
  duplicidades,
  onDispensar,
}: {
  duplicidades: PossivelDuplicidadeFornecedor[];
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
            <p className="text-sm font-medium">Encontramos fornecedores com dados semelhantes.</p>
            <p className="mt-0.5 text-xs opacity-80">
              O cadastro foi salvo normalmente. Confira se não é o mesmo fornecedor já registrado.
            </p>
            <ul className="mt-2 flex flex-col gap-1">
              {duplicidades.map((duplicidade) => (
                <li key={duplicidade.id} className="text-xs">
                  <span className="font-medium">
                    {formatarReferenciaVisual({
                      entidade: "fornecedor",
                      sequencialReferencia: duplicidade.sequencialReferencia,
                      nome: duplicidade.nome,
                    })}
                  </span>
                  {duplicidade.documento && <span className="opacity-80"> · {duplicidade.documento}</span>}
                  <span className="opacity-80"> · {rotuloMotivo[duplicidade.motivo]}</span>
                  {duplicidade.status === "arquivado" && <span className="opacity-80"> · arquivado</span>}
                  <span className="ml-1.5 font-mono text-[11px] opacity-60">{duplicidade.codigoReferencia}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <button
          type="button"
          onClick={onDispensar}
          aria-label="Dispensar aviso"
          className="rounded-full p-1.5 transition hover:bg-amber-100 dark:hover:bg-amber-500/20"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
