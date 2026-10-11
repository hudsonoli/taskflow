"use client";

import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { caminhoDoTenant } from "@/lib/tenant";

/**
 * A sessão aberta pertence a OUTRA empresa que a da URL (`/e/<slug>/...`). Nada da empresa da URL é carregado nem exibido, e a URL nunca troca
 * a empresa da sessão: a pessoa volta à própria empresa ou sai. A mensagem não nomeia nenhuma das duas empresas.
 */
export function SessaoOutraEmpresaView({ slugDaSessao, onSair, saindo }: { slugDaSessao: string; onSair: () => void; saindo: boolean }) {
  return (
    <div className="flex h-screen items-center justify-center bg-app px-4">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 text-center shadow-sm">
        <div className="mb-3 flex justify-center text-amber-600 dark:text-amber-400">
          <ShieldAlert size={24} />
        </div>
        <h1 className="text-lg font-semibold tracking-tight text-fg">Esta sessão é de outra empresa</h1>
        <p className="mt-2 text-sm text-fg-muted">
          Você está conectado em outra empresa e não tem acesso a este endereço. Volte para a sua empresa ou saia para entrar de novo.
        </p>
        <div className="mt-4 flex flex-col gap-2">
          <Link
            href={caminhoDoTenant(slugDaSessao, "meu-dia")}
            className="rounded-xl bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            Ir para a minha empresa
          </Link>
          <button
            type="button"
            onClick={onSair}
            disabled={saindo}
            className="rounded-xl border border-line px-3 py-2 text-sm font-medium text-fg hover:bg-surface-hover disabled:opacity-60"
          >
            Sair
          </button>
        </div>
      </div>
    </div>
  );
}
