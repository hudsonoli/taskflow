"use client";

import { useState } from "react";
import { Check, Copy, MailCheck, MailWarning } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { absolutizarLink, descreverConvite } from "@/lib/plataforma";
import { useOrigem } from "@/lib/useOrigem";
import type { PlataformaConvite } from "@/types/plataforma";

function formatarValidade(iso: string): string {
  const data = new Date(iso);
  return Number.isNaN(data.getTime())
    ? ""
    : data.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/**
 * Estado do convite de primeiro acesso do Gestor. NUNCA há senha aqui (o Gestor define a própria). Enviado: só confirma. Não enviado (ex.: a empresa nova ainda
 * não tem SMTP): mostra o MOTIVO e o link de primeiro acesso para entrega manual — exibido uma única vez (o servidor guarda só o hash), com validade e aviso.
 * Fechar a tela descarta o link da memória.
 */
export function ConviteGestorAviso({ convite }: { convite: PlataformaConvite }) {
  const origem = useOrigem();
  const [copiado, setCopiado] = useState(false);
  const estado = descreverConvite(convite);
  const link = convite.linkAcesso ? absolutizarLink(origem, convite.linkAcesso) : null;
  const Icone = convite.enviado ? MailCheck : MailWarning;

  async function copiar() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
    } catch {
      setCopiado(false);
    }
  }

  return (
    <div
      role="status"
      className={
        convite.enviado
          ? "rounded-xl border border-emerald-300/60 bg-emerald-50 p-3 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200"
          : "rounded-xl border border-amber-300/60 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200"
      }
    >
      <p className="flex items-center gap-2 text-sm font-semibold">
        <Icone size={16} /> {estado.titulo}
      </p>
      <p className="mt-1 text-xs">{estado.detalhe}</p>

      {link && (
        <div className="mt-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide">Link de primeiro acesso</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <code data-testid="link-convite" className="min-w-0 flex-1 select-all break-all rounded-lg border border-field-line bg-field px-3 py-2 font-mono text-xs text-fg">
              {link}
            </code>
            <Button type="button" variant="secondary" onClick={() => void copiar()} aria-label="Copiar link de primeiro acesso">
              {copiado ? <Check size={14} /> : <Copy size={14} />} {copiado ? "Copiado" : "Copiar link"}
            </Button>
          </div>
          <p className="mt-2 text-xs">
            Este link é exibido <strong>uma única vez</strong> e vale até {formatarValidade(convite.expiraEm)}. Entregue-o por um canal seguro: quem o abrir define a
            senha desta conta. Para gerar outro, use <strong>Reenviar convite</strong> na página da empresa.
          </p>
        </div>
      )}
    </div>
  );
}
