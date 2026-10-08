"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, KeyRound, LogOut, Monitor, Moon, ShieldCheck, Sun, UserRound } from "lucide-react";
import clsx from "clsx";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { useAppData } from "@/lib/AppDataContext";
import { useBranding } from "@/lib/BrandingContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { formatarBadge } from "@/lib/notificacoes";
import { useNotificacoes } from "@/lib/NotificacoesContext";
import type { TemaPreferencia } from "@/lib/tema";
import { usePlataformaAcesso } from "@/lib/usePlataformaAcesso";
import { perfilUsuarioLabels } from "@/types/usuario";

const OPCOES_TEMA = [
  { valor: "claro", rotulo: "Claro", icone: Sun },
  { valor: "escuro", rotulo: "Escuro", icone: Moon },
  { valor: "sistema", rotulo: "Sistema", icone: Monitor },
] as const;

const itemClassName =
  "flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm font-medium text-fg transition hover:bg-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-focus";

function Secao({ id, titulo }: { id: string; titulo: string }) {
  return (
    <p id={id} className="mb-1.5 px-1 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
      {titulo}
    </p>
  );
}

function formatarUltimoAcesso(em: string): string {
  const data = new Date(em);
  return Number.isNaN(data.getTime())
    ? ""
    : data.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function ProfileMenu() {
  const { usuarioAtual, logout } = useAppData();
  const { branding, preferenciaTema, definirPreferenciaTema, loginHref } = useBranding();
  const { resumo, recarregar } = useNotificacoes();
  const { departamentos } = useDiretorioDepartamentos();
  const [erroTema, setErroTema] = useState<string | null>(null);
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [saindo, setSaindo] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  // Entrada "Administração da Plataforma": só aparece se o backend confirmar a autoridade (nunca por e-mail/perfil).
  const administradorPlataforma = usePlataformaAcesso(usuarioAtual?.id);

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

  const badge = formatarBadge(resumo.naoLidas.total);
  const departamento = usuarioAtual.departamentoId ? departamentos.find((item) => item.id === usuarioAtual.departamentoId) : undefined;
  const ultimoAcesso = usuarioAtual.ultimoAcesso ? formatarUltimoAcesso(usuarioAtual.ultimoAcesso.em) : "";

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
    const destino = loginHref; // login da empresa da sessão (capturado antes de o contexto ser limpo)
    await logout();
    router.replace(destino);
    router.refresh();
  }

  function alternar() {
    if (!open) void recarregar(); // badge fresco no momento em que é consultado (sem polling)
    setOpen(!open);
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={alternar}
        aria-label="Menu do perfil"
        aria-expanded={open}
        className="relative rounded-full transition hover:ring-2 hover:ring-indigo-200 dark:hover:ring-indigo-500/30"
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
            className="absolute right-0 z-30 mt-2 max-h-[calc(100vh-5rem)] w-72 max-w-[calc(100vw-1rem)] overflow-y-auto rounded-2xl border border-line bg-surface shadow-lg"
          >
            {saindo ? (
              <p className="px-4 py-5 text-center text-sm text-fg-muted">Saindo…</p>
            ) : (
              <>
                <div className="flex items-center gap-3 border-b border-line px-4 py-3.5">
                  <Avatar
                    nome={usuarioAtual.nome}
                    corIdentificacao={usuarioAtual.corIdentificacao}
                    fotoUrl={usuarioAtual.fotoUrl}
                    className="h-11 w-11 shrink-0 rounded-full text-sm"
                  />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-fg">{usuarioAtual.nome}</p>
                    {(usuarioAtual.cargo || departamento) && (
                      <p className="truncate text-xs text-fg-muted">{[usuarioAtual.cargo, departamento?.nome].filter(Boolean).join(" · ")}</p>
                    )}
                    <p className="truncate text-xs text-fg-subtle">{usuarioAtual.email}</p>
                    <div className="mt-1">
                      <Badge tone="blue">{perfilUsuarioLabels[usuarioAtual.perfil]}</Badge>
                    </div>
                  </div>
                </div>

                <nav aria-label="Conta" className="border-b border-line p-1.5">
                  <Link href="/minha-conta" onClick={() => setOpen(false)} className={itemClassName}>
                    <UserRound className="h-4 w-4 text-fg-subtle" />
                    Perfil
                  </Link>
                  <Link href="/notificacoes" onClick={() => setOpen(false)} className={itemClassName}>
                    <Bell className="h-4 w-4 text-fg-subtle" />
                    <span className="flex-1">Notificações</span>
                    {badge && (
                      <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-indigo-600 px-1.5 text-[11px] font-bold leading-none text-white">
                        {badge}
                        <span className="sr-only"> não lidas</span>
                      </span>
                    )}
                  </Link>
                  <Link href="/minha-conta#seguranca" onClick={() => setOpen(false)} className={itemClassName}>
                    <KeyRound className="h-4 w-4 text-fg-subtle" />
                    Alterar senha
                  </Link>
                  {administradorPlataforma && (
                    <Link href="/plataforma" onClick={() => setOpen(false)} className={itemClassName}>
                      <ShieldCheck className="h-4 w-4 text-fg-subtle" />
                      Administração da Plataforma
                    </Link>
                  )}
                </nav>

                <div className="border-b border-line px-4 py-3">
                  <Secao id="menu-tema-rotulo" titulo="Tema" />
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

                <div className="p-1.5">
                  <button
                    type="button"
                    onClick={handleSair}
                    className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm font-medium text-red-700 transition hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-red-400 dark:hover:bg-red-500/10"
                  >
                    <LogOut className="h-4 w-4" />
                    Sair
                  </button>
                </div>

                {ultimoAcesso && (
                  <p className="border-t border-line bg-surface-2 px-4 py-2 text-[11px] leading-4 text-fg-muted">
                    Último acesso: {ultimoAcesso}
                    {usuarioAtual.ultimoAcesso?.ip ? ` · IP ${usuarioAtual.ultimoAcesso.ip}` : ""}
                  </p>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
