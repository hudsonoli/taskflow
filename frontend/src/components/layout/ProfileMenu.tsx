"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { LogOut, UserCog } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { useAppData } from "@/lib/AppDataContext";
import { perfilUsuarioLabels } from "@/types/usuario";

export function ProfileMenu() {
  const { usuarioAtual, logout } = useAppData();
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
            className="absolute right-0 z-30 mt-2 w-64 overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-lg dark:border-zinc-800 dark:bg-zinc-900"
          >
            {saindo ? (
              <p className="px-4 py-5 text-center text-sm text-zinc-500 dark:text-zinc-400">Saindo…</p>
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
                    <p className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">{usuarioAtual.nome}</p>
                    <Badge tone="blue">{perfilUsuarioLabels[usuarioAtual.perfil]}</Badge>
                  </div>
                </div>

                <nav className="flex flex-col p-1.5">
                  <Link
                    href="/minha-conta"
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-50 dark:text-zinc-200 dark:hover:bg-zinc-800"
                  >
                    <UserCog className="h-4 w-4 text-zinc-400" />
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
