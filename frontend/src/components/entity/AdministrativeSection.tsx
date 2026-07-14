import { Lock } from "lucide-react";
import type { ReactNode } from "react";

type AdministrativeSectionProps = {
  children: ReactNode;
};

/**
 * Envelope visual para conteúdo administrativo/sensível (financeiro, dados
 * bancários — e, futuramente, Salário em Usuários). Não verifica permissão
 * nem conhece perfis de acesso: quem chama decide se este componente é
 * renderizado (ver hasAdministrativeAccess em lib/access-control.ts e
 * entity-component-api.md, seção "Guia Administrativa"). Puramente
 * apresentacional — sem lógica de negócio.
 */
export function AdministrativeSection({ children }: AdministrativeSectionProps) {
  return (
    <div className="space-y-5">
      <div className="flex items-start gap-2 rounded-2xl bg-zinc-50 p-3">
        <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-400" strokeWidth={2} aria-hidden="true" />
        <p className="text-[11px] text-zinc-500">
          Conteúdo restrito a perfis autorizados. Nunca é exibido em tabela,
          Peek ou busca — visível apenas aqui, no modo de edição.
        </p>
      </div>

      {children}
    </div>
  );
}
