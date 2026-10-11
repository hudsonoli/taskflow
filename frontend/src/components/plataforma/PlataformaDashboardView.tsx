"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Activity, AlertTriangle, ArrowRight, Building2, CheckCircle2, Info, Loader2, LogIn, UserCog, UserX, Users } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiStrip, type KpiItem } from "@/components/ui/KpiStrip";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { formatarProporcao, hrefDaEmpresa, kpisDoResumo, rotuloUltimoAcesso } from "@/lib/plataformaDashboard";
import { obterDashboardPlataforma } from "@/lib/plataforma-api";
import { STATUS_EMPRESA_ROTULO } from "@/lib/plataforma";
import type { DashboardAtencao, DashboardEmpresa, PlataformaDashboard, PlataformaEmpresaStatus } from "@/types/plataforma";

const TOM_STATUS: Record<PlataformaEmpresaStatus, BadgeTone> = { ativa: "green", inativa: "amber", arquivada: "neutral" };

const ICONES: Record<string, { icone: React.ReactNode; tone: BadgeTone }> = {
  empresas: { icone: <Building2 size={18} />, tone: "blue" },
  usuarios: { icone: <Users size={18} />, tone: "blue" },
  acessaram: { icone: <LogIn size={18} />, tone: "green" },
  ativos30: { icone: <Activity size={18} />, tone: "green" },
  nunca: { icone: <UserX size={18} />, tone: "amber" },
  gestores: { icone: <UserCog size={18} />, tone: "neutral" },
};

/**
 * Dashboard global da Administração da Plataforma: adoção e uso das empresas por métricas AGREGADAS (nenhum usuário
 * individual, nenhum conteúdo operacional). "Ativos" = login recente, não presença em tempo real. Abrir uma empresa só leva
 * à página dela no console — não existe impersonação nem troca de sessão. O console segue com a identidade neutra.
 */
export function PlataformaDashboardView() {
  const [dados, setDados] = useState<PlataformaDashboard | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      setDados(await obterDashboardPlataforma());
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar a dashboard.");
    }
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => void carregar(), 0);
    return () => clearTimeout(timeout);
  }, [carregar]);

  if (erro) return <EstadoErro mensagem={erro} onRetry={carregar} />;
  if (!dados) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-sm text-fg-muted shadow-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando dashboard…
      </div>
    );
  }

  const kpis: KpiItem[] = kpisDoResumo(dados.resumo).map((k) => ({
    key: k.key,
    label: k.label,
    value: k.value,
    description: k.description,
    icon: ICONES[k.key].icone,
    tone: ICONES[k.key].tone,
  }));
  const agora = new Date();

  return (
    <div className="flex flex-col gap-6">
      <KpiStrip ariaLabel="Indicadores globais da plataforma" itens={kpis} />

      <section aria-labelledby="uso-por-empresa" className="flex flex-col gap-3">
        <h2 id="uso-por-empresa" className="text-sm font-semibold text-fg">
          Uso por empresa
        </h2>
        {dados.empresas.length === 0 ? (
          <EmptyState icon={<Building2 size={18} />} title="Nenhuma empresa cadastrada" description="Cadastre a primeira em Empresas." />
        ) : (
          <>
            {/* Desktop/tablet: tabela */}
            <div className="hidden overflow-x-auto rounded-xl border border-line bg-surface shadow-sm md:block">
              <table className="w-full min-w-[760px] text-left text-sm" aria-label="Uso por empresa">
                <thead>
                  <tr className="border-b border-line text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
                    <th className="px-4 py-3">Empresa</th>
                    <th className="px-3 py-3 text-right">Usuários</th>
                    <th className="px-3 py-3 text-right">Já acessaram</th>
                    <th className="px-3 py-3 text-right">Ativos 30d</th>
                    <th className="px-3 py-3 text-right">Nunca acessaram</th>
                    <th className="px-3 py-3 text-right">Gestores</th>
                    <th className="hidden px-3 py-3 text-right xl:table-cell">Projetos</th>
                    <th className="hidden px-3 py-3 text-right xl:table-cell">Demandas</th>
                    <th className="px-3 py-3">Último acesso</th>
                    <th className="px-4 py-3 text-right">
                      <span className="sr-only">Ação</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {dados.empresas.map((empresa) => (
                    <LinhaEmpresa key={empresa.id} empresa={empresa} agora={agora} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: lista de cartões */}
            <ul className="flex flex-col gap-2 md:hidden" aria-label="Uso por empresa (lista)">
              {dados.empresas.map((empresa) => (
                <CartaoEmpresa key={empresa.id} empresa={empresa} agora={agora} />
              ))}
            </ul>
          </>
        )}
      </section>

      <section aria-labelledby="precisa-atencao" className="flex flex-col gap-3">
        <h2 id="precisa-atencao" className="text-sm font-semibold text-fg">
          Precisa de atenção
        </h2>
        {dados.atencoes.length === 0 ? (
          <p className="flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-3 text-sm text-fg-muted shadow-sm">
            <CheckCircle2 className="h-4 w-4 text-success" /> Nada precisa de atenção agora.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {dados.atencoes.map((atencao) => (
              <ItemAtencao key={`${atencao.empresaId}-${atencao.tipo}`} atencao={atencao} />
            ))}
          </ul>
        )}
      </section>

      <p className="text-xs text-fg-muted">
        “Ativos” = usuários com login nos últimos 30 dias (não indica presença em tempo real). “Usuários” são os ativos, com acesso ao
        sistema, das empresas ativas — a conta de sistema nunca entra. Só o login é rastreado, por isso “Último acesso”.
      </p>
    </div>
  );
}

function LinhaEmpresa({ empresa, agora }: { empresa: DashboardEmpresa; agora: Date }) {
  return (
    <tr className="border-b border-line last:border-0 hover:bg-surface-hover">
      <td className="px-4 py-3">
        <p className="font-semibold text-fg">{empresa.nome}</p>
        <p className="mt-0.5 flex items-center gap-2 text-xs text-fg-muted">
          <Badge tone={TOM_STATUS[empresa.status]}>{STATUS_EMPRESA_ROTULO[empresa.status]}</Badge>
          <span className="font-mono">{empresa.slug}</span>
        </p>
      </td>
      <td className="px-3 py-3 text-right tabular-nums">{empresa.usuarios}</td>
      <td className="px-3 py-3 text-right tabular-nums" title="Absoluto · percentual dos usuários">
        {formatarProporcao(empresa.jaAcessaram, empresa.usuarios)}
      </td>
      <td className="px-3 py-3 text-right tabular-nums">{empresa.ativos30d}</td>
      <td className="px-3 py-3 text-right tabular-nums">{empresa.nuncaAcessaram}</td>
      <td className="px-3 py-3 text-right tabular-nums">
        {empresa.gestores > 0 ? empresa.gestores : <Badge tone={empresa.status === "ativa" ? "amber" : "neutral"}>Sem Gestor</Badge>}
      </td>
      <td className="hidden px-3 py-3 text-right tabular-nums xl:table-cell">{empresa.projetos}</td>
      <td className="hidden px-3 py-3 text-right tabular-nums xl:table-cell">{empresa.demandas}</td>
      <td className="px-3 py-3 text-fg-muted" title={empresa.ultimoAcesso ?? "Nenhum login registrado"}>
        {rotuloUltimoAcesso(empresa.ultimoAcesso, agora)}
      </td>
      <td className="px-4 py-3 text-right">
        <Link
          href={hrefDaEmpresa(empresa)}
          className="inline-flex items-center gap-1 rounded-full text-xs font-semibold text-indigo-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-indigo-400"
          aria-label={`Abrir empresa ${empresa.nome}`}
        >
          Abrir <ArrowRight size={13} />
        </Link>
      </td>
    </tr>
  );
}

function CartaoEmpresa({ empresa, agora }: { empresa: DashboardEmpresa; agora: Date }) {
  return (
    <li className="rounded-xl border border-line bg-surface p-3 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-fg">{empresa.nome}</p>
          <p className="mt-0.5 flex items-center gap-2 text-xs text-fg-muted">
            <Badge tone={TOM_STATUS[empresa.status]}>{STATUS_EMPRESA_ROTULO[empresa.status]}</Badge>
            <span className="font-mono">{empresa.slug}</span>
          </p>
        </div>
        <Link
          href={hrefDaEmpresa(empresa)}
          className="inline-flex shrink-0 items-center gap-1 rounded-full text-xs font-semibold text-indigo-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-indigo-400"
          aria-label={`Abrir empresa ${empresa.nome}`}
        >
          Abrir <ArrowRight size={13} />
        </Link>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <Dado rotulo="Usuários" valor={String(empresa.usuarios)} />
        <Dado rotulo="Gestores" valor={empresa.gestores > 0 ? String(empresa.gestores) : "Sem Gestor"} />
        <Dado rotulo="Já acessaram" valor={formatarProporcao(empresa.jaAcessaram, empresa.usuarios)} />
        <Dado rotulo="Ativos 30d" valor={String(empresa.ativos30d)} />
        <Dado rotulo="Nunca acessaram" valor={String(empresa.nuncaAcessaram)} />
        <Dado rotulo="Último acesso" valor={rotuloUltimoAcesso(empresa.ultimoAcesso, agora)} />
      </dl>
    </li>
  );
}

function Dado({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <dt className="text-fg-subtle">{rotulo}</dt>
      <dd className="font-medium tabular-nums text-fg">{valor}</dd>
    </div>
  );
}

function ItemAtencao({ atencao }: { atencao: DashboardAtencao }) {
  const aviso = atencao.severidade === "aviso";
  return (
    <li className="flex items-center justify-between gap-3 rounded-xl border border-line bg-surface px-4 py-2.5 shadow-sm">
      <div className="flex min-w-0 items-center gap-3">
        {aviso ? (
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-label="Aviso" />
        ) : (
          <Info className="h-4 w-4 shrink-0 text-fg-subtle" aria-label="Informação" />
        )}
        <p className="min-w-0 text-sm text-fg">
          <span className="font-semibold">{atencao.empresaNome}</span> — {atencao.mensagem}
        </p>
      </div>
      <Link
        href={`/gestao/empresas/${encodeURIComponent(atencao.empresaId)}`}
        className="shrink-0 rounded-full text-xs font-semibold text-indigo-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-indigo-400"
      >
        Abrir
      </Link>
    </li>
  );
}
