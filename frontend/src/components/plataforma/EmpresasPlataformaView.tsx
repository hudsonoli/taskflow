"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Building2, Loader2, Plus, Search } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { NovaEmpresaModal } from "@/components/plataforma/NovaEmpresaModal";
import { STATUS_EMPRESA_ROTULO } from "@/lib/plataforma";
import { listarEmpresasPlataforma } from "@/lib/plataforma-api";
import type { PlataformaEmpresa, PlataformaEmpresaStatus } from "@/types/plataforma";

const TOM_STATUS: Record<PlataformaEmpresaStatus, BadgeTone> = { ativa: "green", inativa: "amber", arquivada: "neutral" };

export function EmpresasPlataformaView() {
  const [empresas, setEmpresas] = useState<PlataformaEmpresa[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState("");
  const [status, setStatus] = useState("");
  const [novaAberta, setNovaAberta] = useState(false);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    let cancelado = false;
    // Pequeno atraso na busca digitada: evita uma requisição por tecla.
    const timeout = setTimeout(async () => {
      try {
        const lista = await listarEmpresasPlataforma({ search: busca, status: status || undefined });
        if (!cancelado) {
          setEmpresas(lista);
          setErro(null);
        }
      } catch (error) {
        if (!cancelado) setErro(error instanceof Error ? error.message : "Não foi possível carregar as empresas.");
      }
    }, busca ? 250 : 0);
    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
  }, [busca, status, versao]);

  function recarregar() {
    setEmpresas(null);
    setErro(null);
    setVersao((atual) => atual + 1);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Buscar</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
              <input
                type="search"
                value={busca}
                onChange={(event) => setBusca(event.target.value)}
                placeholder="Nome, código ou slug"
                className="field w-64 rounded-xl py-2.5 pl-9 pr-3 text-sm"
              />
            </span>
          </label>
          <label className="block text-sm">
            <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Situação</span>
            <select value={status} onChange={(event) => setStatus(event.target.value)} className="field rounded-xl px-3 py-2.5 text-sm">
              <option value="">Todas</option>
              <option value="ativa">Ativas</option>
              <option value="inativa">Inativas</option>
            </select>
          </label>
        </div>
        <Button type="button" onClick={() => setNovaAberta(true)}>
          <Plus size={14} /> Nova empresa
        </Button>
      </div>

      {erro ? (
        <EstadoErro mensagem={erro} onRetry={recarregar} />
      ) : !empresas ? (
        <div className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-sm text-fg-muted shadow-sm">
          <Loader2 className="h-4 w-4 animate-spin" /> Carregando empresas…
        </div>
      ) : empresas.length === 0 ? (
        <EmptyState
          icon={<Building2 size={18} />}
          title="Nenhuma empresa encontrada"
          description={busca || status ? "Ajuste a busca ou o filtro." : "Cadastre a primeira empresa em “Nova empresa”."}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-line bg-surface shadow-sm">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
                <th className="px-4 py-3">Empresa</th>
                <th className="px-4 py-3">Código</th>
                <th className="px-4 py-3">Slug</th>
                <th className="px-4 py-3">Situação</th>
                <th className="px-4 py-3 text-right">Gestores</th>
              </tr>
            </thead>
            <tbody>
              {empresas.map((empresa) => (
                <tr key={empresa.id} className="border-b border-line last:border-0 hover:bg-surface-hover">
                  <td className="px-4 py-3">
                    <Link
                      href={`/plataforma/empresas/${empresa.id}`}
                      className="font-semibold text-fg underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                    >
                      {empresa.nome}
                    </Link>
                    {empresa.nomeFantasia && <p className="text-xs text-fg-muted">{empresa.nomeFantasia}</p>}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-fg-muted">{empresa.codigoInterno}</td>
                  <td className="px-4 py-3 font-mono text-xs text-fg-muted">{empresa.slug}</td>
                  <td className="px-4 py-3">
                    <Badge tone={TOM_STATUS[empresa.status]}>{STATUS_EMPRESA_ROTULO[empresa.status]}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {empresa.gestoresAtivos > 0 ? (
                      empresa.gestoresAtivos
                    ) : (
                      <Badge tone={empresa.status === "ativa" ? "amber" : "neutral"}>Sem Gestor</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <NovaEmpresaModal open={novaAberta} onClose={() => setNovaAberta(false)} onCriada={recarregar} />
    </div>
  );
}
