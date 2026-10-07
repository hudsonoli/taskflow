// Partes puras do KpiStrip (faixa de indicadores): texto acessível e posição do tooltip. Sem React, para testar
// com `node --test` (`npm run test:kpi`).

/** Nome acessível do indicador: nome + valor ("Atrasadas: 5"), mesmo quando o rótulo visual está oculto. */
export function rotuloKpi(label: string, value: number | string): string {
  return `${label}: ${value}`;
}

/**
 * Centro horizontal do tooltip, limitado para ele nunca sair da janela. O tooltip é `position: fixed` (a faixa
 * rola na horizontal e um tooltip absoluto seria cortado pelo overflow), então a posição é calculada a partir do
 * retângulo do item.
 */
export function centroTooltip(itemCentro: number, tooltipLargura: number, janelaLargura: number, margem = 8): number {
  const metade = tooltipLargura / 2;
  const minimo = margem + metade;
  const maximo = janelaLargura - margem - metade;
  if (maximo < minimo) return janelaLargura / 2; // janela menor que o tooltip: centraliza
  return Math.min(Math.max(itemCentro, minimo), maximo);
}
