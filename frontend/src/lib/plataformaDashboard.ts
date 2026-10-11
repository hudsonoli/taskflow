// Dashboard da Administração da Plataforma — lógica pura (sem React, sem fetch): proporções, "último acesso" relativo e
// os KPIs do topo. Testável com `node --test`. As definições (já acessaram, ativos 7d/30d, utilizáveis) são do BACKEND;
// aqui só se apresenta. "Ativos" = login recente, NÃO presença em tempo real.

import type { DashboardEmpresa, DashboardResumo } from "../types/plataforma.ts";

/** "7/10 · 70%" (número absoluto sempre presente). Total 0 → "0/0", sem percentual (nada de divisão por zero). */
export function formatarProporcao(parte: number, total: number): string {
  if (total <= 0) return `${parte}/${total}`;
  return `${parte}/${total} · ${Math.round((parte / total) * 100)}%`;
}

const MS_DIA = 24 * 60 * 60 * 1000;

/** Último LOGIN em linguagem curta ("Hoje", "Ontem", "Há 5 dias", "Há 2 meses") ou "Nunca". Datas inválidas viram "—". */
export function rotuloUltimoAcesso(iso: string | null, agora: Date = new Date()): string {
  if (iso === null) return "Nunca";
  const quando = new Date(iso);
  if (Number.isNaN(quando.getTime())) return "—";
  const dias = Math.floor((agora.getTime() - quando.getTime()) / MS_DIA);
  if (dias <= 0) return "Hoje";
  if (dias === 1) return "Ontem";
  if (dias < 30) return `Há ${dias} dias`;
  const meses = Math.floor(dias / 30);
  return meses === 1 ? "Há 1 mês" : meses < 12 ? `Há ${meses} meses` : "Há mais de 1 ano";
}

export type KpiDashboard = { key: string; label: string; value: number; description: string };

/** Os seis indicadores compactos do topo, na ordem pedida. */
export function kpisDoResumo(resumo: DashboardResumo): KpiDashboard[] {
  return [
    { key: "empresas", label: "Empresas ativas", value: resumo.empresasAtivas, description: `${resumo.empresasTotal} cadastradas no total` },
    { key: "usuarios", label: "Usuários", value: resumo.usuarios, description: "Usuários ativos, com acesso, das empresas ativas (sem a conta de sistema)" },
    { key: "acessaram", label: "Já acessaram", value: resumo.jaAcessaram, description: formatarProporcao(resumo.jaAcessaram, resumo.usuarios) },
    { key: "ativos30", label: "Ativos 30 dias", value: resumo.ativos30d, description: `Login nos últimos 30 dias · ${resumo.ativos7d} nos últimos 7. Não indica presença em tempo real.` },
    { key: "nunca", label: "Nunca acessaram", value: resumo.nuncaAcessaram, description: formatarProporcao(resumo.nuncaAcessaram, resumo.usuarios) },
    { key: "gestores", label: "Gestores", value: resumo.gestores, description: "Usuários com perfil Gestor, somando todas as empresas ativas" },
  ];
}

/** Rótulo do botão de uma linha: abre a empresa no console (nunca vira sessão tenant). */
export function hrefDaEmpresa(empresa: Pick<DashboardEmpresa, "id">): string {
  return `/gestao/empresas/${encodeURIComponent(empresa.id)}`;
}
