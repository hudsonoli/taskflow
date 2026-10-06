"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { LogOut, Monitor, Moon, Sun, UserCog } from "lucide-react";
import clsx from "clsx";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { useAppData } from "@/lib/AppDataContext";
import { useBranding } from "@/lib/BrandingContext";
import type { TemaPreferencia } from "@/lib/tema";
import { perfilUsuarioLabels } from "@/types/usuario";

const OPCOES_TEMA = [
  { valor: "claro", rotulo: "Claro", icone: Sun },
  { valor: "escuro", rotulo: "Escuro", icone: Moon },
  { valor: "sistema", rotulo: "Sistema", icone: Monitor },
] as const;

export function ProfileMenu() {
  const { usuarioAtual, logout } = useAppData();
  const { branding, preferenciaTema, definirPreferenciaTema } = useBranding();
  const [erroTema, setErroTema] = useState<string | null>(null);
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [saindo, setSaindo] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
        setSaindo(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!usuarioAtual) return null;

  // Troca imediata (otimista); se o servidor recusar, o provider já restaurou o tema anterior — só avisamos.
  async function escolherTema(nova: TemaPreferencia) {
    if (nova === preferenciaTema) return;
    setErroTema(null);
    try {
      await definirPreferenciaTema(nova);
    } catch {
      setErroTema("Não foi possível salvar o tema. A preferência anterior foi restaurada.");
    }
  }

  async function handleSair() {
    setSaindo(true);
    await logout();
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label="Menu do perfil"
        className="rounded-full transition hover:ring-2 hover:ring-indigo-200 dark:hover:ring-indigo-500/30"
      >
        <Avatar
          nome={usuarioAtual.nome}
          corIdentificacao={usuarioAtual.corIdentificacao}
          fotoUrl={usuarioAtual.fotoUrl}
          className="h-9 w-9 rounded-full"
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-30 mt-2 w-64 overflow-hidden rounded-2xl border border-line bg-surface shadow-lg"
          >
            {saindo ? (
              <p className="px-4 py-5 text-center text-sm text-fg-muted">Saindo…</p>
            ) : (
              <>
                <div className="flex items-center gap-3 border-b border-zinc-100 px-4 py-3.5 dark:border-zinc-800">
                  <Avatar
                    nome={usuarioAtual.nome}
                    corIdentificacao={usuarioAtual.corIdentificacao}
                    fotoUrl={usuarioAtual.fotoUrl}
                    className="h-10 w-10 shrink-0 rounded-full text-sm"
                  />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-fg">{usuarioAtual.nome}</p>
                    <Badge tone="blue">{perfilUsuarioLabels[usuarioAtual.perfil]}</Badge>
                  </div>
                </div>

                <div className="border-b border-line px-4 py-3">
                  <p id="menu-tema-rotulo" className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
                    Tema
                  </p>
                  <div role="radiogroup" aria-labelledby="menu-tema-rotulo" className="flex flex-col gap-0.5">
                    {OPCOES_TEMA.map(({ valor, rotulo, icone: Icone }) => {
                      const ativo = preferenciaTema === valor;
                      return (
                        <button
                          key={valor}
                          type="button"
                          role="radio"
                          aria-checked={ativo}
                          onClick={() => void escolherTema(valor)}
                          className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-sm font-medium text-fg transition hover:bg-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                        >
                          <span
                            aria-hidden
                            className={clsx(
                              "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2",
                              ativo ? "border-indigo-600 dark:border-indigo-400" : "border-field-line",
                            )}
                          >
                            {ativo && <span className="h-2 w-2 rounded-full bg-indigo-600 dark:bg-indigo-400" />}
                          </span>
                          <Icone className="h-4 w-4 text-fg-subtle" />
                          {rotulo}
                        </button>
                      );
                    })}
                  </div>
                  {preferenciaTema === null ? (
                    <p className="mt-1.5 px-2 text-xs text-fg-muted">
                      Padrão da empresa · {branding.tema === "escuro" ? "Escuro" : "Claro"}
                    </p>
                  ) : (
                    <button
                      type="button"
                      onClick={() => void escolherTema(null)}
                      className="mt-1.5 rounded px-2 text-left text-xs font-medium text-indigo-600 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-indigo-400"
                    >
                      Usar padrão da empresa ({branding.tema === "escuro" ? "Escuro" : "Claro"})
                    </button>
                  )}
                  {erroTema && (
                    <p role="alert" className="mt-1.5 px-2 text-xs font-medium text-danger">
                      {erroTema}
                    </p>
                  )}
                </div>

                <nav className="flex flex-col p-1.5">
                  <Link
                    href="/minha-conta"
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-50 dark:text-zinc-200 dark:hover:bg-zinc-800"
                  >
                    <UserCog className="h-4 w-4 text-fg-subtle" />
                    Conta
                  </Link>
                  <button
                    type="button"
                    onClick={handleSair}
                    className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm font-medium text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
                  >
                    <LogOut className="h-4 w-4" />
                    Sair
                  </button>
                </nav>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
