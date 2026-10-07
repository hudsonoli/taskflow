// KpiStrip: partes puras + garantias estruturais do componente compartilhado e das telas que o usam.
// `npm run test:kpi` (node --test, sem dependências; o componente é .tsx, então é lido como texto).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { centroTooltip, rotuloKpi } from "./kpiStrip.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const componente = ler("components/ui/KpiStrip.tsx");

test("nome acessível: nome + valor", () => {
  assert.equal(rotuloKpi("Atrasadas", 5), "Atrasadas: 5");
  assert.equal(rotuloKpi("Projetos ativos", "…"), "Projetos ativos: …");
  assert.equal(rotuloKpi("Horas estimadas (aprox.)", "12h 30min"), "Horas estimadas (aprox.): 12h 30min");
});

test("tooltip: centraliza no item e nunca sai da janela", () => {
  assert.equal(centroTooltip(500, 100, 1000), 500);
  assert.equal(centroTooltip(10, 100, 1000), 58); // encosta na margem esquerda (8 + 50)
  assert.equal(centroTooltip(995, 100, 1000), 942); // encosta na margem direita (1000 - 8 - 50)
  assert.equal(centroTooltip(50, 400, 300), 150); // janela menor que o tooltip: centraliza
});

test("faixa: uma linha, rolagem horizontal local", () => {
  assert.match(componente, /<ul[\s\S]*?aria-label=\{ariaLabel\}[\s\S]*?flex-nowrap[\s\S]*?overflow-x-auto/);
  assert.match(componente, /w-24 shrink-0/); // chips não encolhem abaixo de lg
  assert.match(componente, /lg:flex-1/); // em lg+ dividem o espaço da mesma linha…
  assert.match(componente, /lg:max-w-60/); // …sem virar cartões enormes quando são poucos
});

test("item: aria-label nome + valor, não é botão, rótulo visual só no mobile, tooltip só no desktop", () => {
  assert.match(componente, /aria-label=\{rotuloKpi\(label, value\)\}/);
  assert.match(componente, /tabIndex=\{0\}/);
  assert.doesNotMatch(componente, /<button|onClick|role="button"/);
  assert.match(componente, /lg:hidden[^"]*">\{label\}/); // rótulo curto visível abaixo de lg, oculto no desktop
  assert.match(componente, /fixed[^"]*hidden[^"]*lg:block/); // tooltip fixo, só em lg+
  assert.match(componente, /aria-hidden\n\s+style=\{\{ left: alvo\.centro/); // tooltip não duplica a leitura
});

test("hover/foco: destaque só com motion-safe; foco do teclado mostra o tooltip", () => {
  assert.match(componente, /motion-safe:group-hover:scale-\[1\.03\]/);
  assert.match(componente, /motion-safe:group-hover:-translate-y-0\.5/);
  assert.match(componente, /group-hover:border-line-strong/);
  assert.match(componente, /matches\(":focus-visible"\)/);
  assert.match(componente, /duration-200/);
  assert.doesNotMatch(componente, /\bbg-(white|black)\b|\btext-black\b/); // só tokens semânticos (text-white só no ícone em gradiente)
});

test("as 4 telas usam o componente compartilhado e não restou cópia local", () => {
  for (const arquivo of [
    "components/dashboard/DashboardView.tsx",
    "components/projetos/ProjetosStats.tsx",
    "components/demandas/DemandasStats.tsx",
    "components/meu-departamento/MeuDepartamentoView.tsx",
  ]) {
    assert.match(ler(arquivo), /<KpiStrip/, `${arquivo} deveria usar KpiStrip`);
  }
  assert.throws(() => ler("components/dashboard/StatCard.tsx"), /ENOENT/);
  // Os cards antigos saíram das telas migradas…
  assert.doesNotMatch(ler("components/projetos/ProjetosStats.tsx"), /MetricCard/);
  assert.doesNotMatch(ler("components/demandas/DemandasStats.tsx"), /MetricCard/);
  assert.doesNotMatch(ler("components/meu-departamento/MeuDepartamentoView.tsx"), /<IndicadoresGrid/);
});

test("telas fora do escopo seguem com o grid antigo", () => {
  assert.match(ler("components/minhas-demandas/MinhasDemandasView.tsx"), /<IndicadoresGrid/);
  assert.match(ler("components/trafego/TrafegoIndicadoresDemandas.tsx"), /<IndicadoresGrid/);
  assert.match(ler("components/trafego/TrafegoResumoCards.tsx"), /MetricCard/);
});
