"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Building2, Headset, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { listarEmpresasPlataforma } from "@/lib/plataforma-api";
import type { PlataformaEmpresa } from "@/types/plataforma";

export function PlataformaHomeView() {
  const [empresas, setEmpresas] = useState<PlataformaEmpresa[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function carregar() {
    setErro(null);
    try {
      setEmpresas(await listarEmpresasPlataforma());
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar as empresas.");
    }
  }

  useEffect(() => {
    const timeout = setTimeout(() => void carregar(), 0);
    return () => clearTimeout(timeout);
  }, []);

  if (erro) return <EstadoErro mensagem={erro} onRetry={carregar} />;
  if (!empresas) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-sm text-fg-muted shadow-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando…
      </div>
    );
  }

  const ativas = empresas.filter((empresa) => empresa.status === "ativa").length;
  const semGestor = empresas.filter((empresa) => empresa.status === "ativa" && empresa.gestoresAtivos === 0).length;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Link
        href="/plataforma/empresas"
        className="group flex flex-col gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm transition hover:border-line-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        <div className="flex items-center justify-between">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Building2 className="h-5 w-5" />
          </span>
          <ArrowRight className="h-4 w-4 text-fg-subtle transition group-hover:translate-x-0.5" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-fg">Empresas</h2>
          <p className="mt-0.5 text-xs text-fg-muted">
            {empresas.length} {empresas.length === 1 ? "empresa cadastrada" : "empresas cadastradas"} · {ativas}{" "}
            {ativas === 1 ? "ativa" : "ativas"}
          </p>
        </div>
        {semGestor > 0 && (
          <Badge tone="amber">
            {semGestor} {semGestor === 1 ? "empresa ativa sem Gestor" : "empresas ativas sem Gestor"}
          </Badge>
        )}
      </Link>

      <div aria-disabled="true" className="flex flex-col gap-3 rounded-xl border border-dashed border-line bg-surface-2 p-4 opacity-80">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-zinc-100 text-fg-subtle dark:bg-zinc-800">
          <Headset className="h-5 w-5" />
        </span>
        <div>
          <h2 className="flex items-center gap-2 text-base font-semibold text-fg">
            Suporte <Badge>Em breve</Badge>
          </h2>
          <p className="mt-0.5 text-xs text-fg-muted">Atendimento às empresas, em uma fase futura.</p>
        </div>
      </div>
    </div>
  );
}
