"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { History, MapPinOff } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { listEventos } from "@/lib/api";
import { useAppData } from "@/lib/AppDataContext";
import { podeAcessarAcessos } from "@/lib/escopo-operacional";
import { parseNavegador, parseSistemaOperacional } from "@/lib/user-agent";
import type { AcessoLoginEvento } from "@/types/acesso";

const TIPO_LOGIN_SUCESSO = "auth.login_sucesso";

function formatDataHora(iso: string): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "—";
  return data.toLocaleString("pt-BR");
}

export function AcessosView() {
  const { usuarioAtual } = useAppData();
  const [eventos, setEventos] = useState<AcessoLoginEvento[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const acessoLiberado = usuarioAtual ? podeAcessarAcessos(usuarioAtual) : false;

  const carregar = useCallback(async () => {
    setLoading(true);
    setErro(null);
    try {
      const resultado = await listEventos({ tipo: TIPO_LOGIN_SUCESSO, limit: 100 });
      const resolvidos: AcessoLoginEvento[] = resultado.map((evento) => {
        const payload = evento.payload ?? {};
        const userAgent = typeof payload.user_agent === "string" ? payload.user_agent : null;
        return {
          id: evento.id,
          usuarioId: evento.usuarioId,
          nome: typeof payload.nome === "string" ? payload.nome : "Usuário desconhecido",
          ip: typeof payload.ip_address === "string" ? payload.ip_address : null,
          userAgent,
          navegador: parseNavegador(userAgent),
          sistemaOperacional: parseSistemaOperacional(userAgent),
          ocorridoEm: evento.occurredAt,
        };
      });
      setEventos(resolvidos);
    } catch {
      setErro("Não foi possível carregar o histórico de acessos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!acessoLiberado) return;
    const timeout = setTimeout(() => {
      void carregar();
    }, 0);
    return () => clearTimeout(timeout);
  }, [acessoLiberado, carregar]);

  if (!usuarioAtual) return null;

  const header = (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <History className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Acesso</h1>
            <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
              Histórico de login ao sistema — hora, IP, navegador e sistema operacional. Área administrativa, restrita a
              Admin, Gestor e Diretoria.
            </p>
          </div>
        </div>
        <Badge tone="blue">Backend real</Badge>
      </div>
    </motion.div>
  );

  if (!acessoLiberado) {
    return (
      <div className="flex flex-col gap-6">
        {header}
        <AcessoNegado
          titulo="Acesso restrito à administração"
          descricao="Este histórico de login é visível apenas para Admin, Gestor e Diretoria."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {header}

      <div className="flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50/60 p-3.5 text-xs text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/5 dark:text-amber-400">
        <MapPinOff className="h-4 w-4 shrink-0" />
        <p>
          Região do IP indisponível nesta fase — exigiria um serviço externo de geolocalização, fora do escopo do
          protótipo. IP, navegador e sistema operacional são reais, capturados no login. A lista não filtra por
          empresa: o login real ainda não está integrado ao usuário simulado do cabeçalho.
        </p>
      </div>

      {loading ? (
        <EstadoCarregando cards={0} />
      ) : erro ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : eventos.length === 0 ? (
        <EmptyState
          title="Nenhum login registrado"
          description="Assim que houver um login real (via POST /auth/login), ele aparece aqui."
          icon={<History className="h-5 w-5" />}
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex items-center justify-between gap-3 border-b border-zinc-100 p-4 dark:border-zinc-800">
            <div>
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Logins recentes</h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">{eventos.length} registro(s)</p>
            </div>
            <Button type="button" variant="secondary" onClick={carregar} className="px-3 py-1.5 text-xs">
              Atualizar
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-100 text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:border-zinc-800 dark:text-zinc-500">
                  <th className="px-4 py-3">Usuário</th>
                  <th className="px-4 py-3">Data/hora</th>
                  <th className="px-4 py-3">IP</th>
                  <th className="px-4 py-3">Região do IP</th>
                  <th className="px-4 py-3">Navegador</th>
                  <th className="px-4 py-3">Sistema operacional</th>
                </tr>
              </thead>
              <tbody>
                {eventos.map((evento) => (
                  <tr key={evento.id} className="border-b border-zinc-50 last:border-0 dark:border-zinc-800/60">
                    <td className="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">{evento.nome}</td>
                    <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{formatDataHora(evento.ocorridoEm)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-zinc-600 dark:text-zinc-300">{evento.ip ?? "—"}</td>
                    <td className="px-4 py-3">
                      <Badge tone="neutral">Não disponível</Badge>
                    </td>
                    <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{evento.navegador}</td>
                    <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">{evento.sistemaOperacional}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
