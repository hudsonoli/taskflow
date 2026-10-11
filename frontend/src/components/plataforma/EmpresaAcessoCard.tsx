"use client";

import { useState } from "react";
import { Check, Copy, Link2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { urlDeAcessoDaEmpresa } from "@/lib/plataforma";
import { useOrigem } from "@/lib/useOrigem";

/**
 * Endereço de acesso de uma empresa: `<origem>/e/<slug>/login`. Só o endereço público (sem token, sem sessão): copiar não entra na empresa nem cria sessão tenant.
 * O slug é permanente depois da criação (faz parte de login, links e portal de aprovação).
 */
export function EmpresaAcessoCard({ slug, urlAcesso }: { slug: string; urlAcesso?: string }) {
  const origem = useOrigem();
  const [copiado, setCopiado] = useState(false);
  const url = urlAcesso && /^https?:\/\//i.test(urlAcesso) ? urlAcesso : urlDeAcessoDaEmpresa(origem, slug);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(url);
      setCopiado(true);
    } catch {
      setCopiado(false); // sem permissão da área de transferência: o endereço continua visível para cópia manual
    }
  }

  return (
    <div className="rounded-xl border border-line bg-surface-2 p-3">
      <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
        <Link2 size={12} /> Endereço de acesso da empresa
      </p>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        <code data-testid="url-acesso" className="min-w-0 flex-1 select-all break-all rounded-lg border border-field-line bg-field px-3 py-2 font-mono text-xs text-fg">
          {url}
        </code>
        <Button type="button" variant="secondary" onClick={() => void copiar()} aria-label="Copiar endereço de acesso">
          {copiado ? <Check size={14} /> : <Copy size={14} />} {copiado ? "Copiado" : "Copiar endereço"}
        </Button>
      </div>
    </div>
  );
}
