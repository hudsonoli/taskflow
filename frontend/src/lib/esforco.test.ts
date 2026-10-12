import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { formatEsforco, parseEsforco, salvarEsforco } from "./esforco.ts";

test("entrada distingue não estimado, zero e horas/minutos", () => {
  for (const [texto, esperado] of [["", null], ["  ", null], ["0", 0], ["0 min", 0], ["30 min", 30], ["1h", 60], ["1h30", 90], ["1h 30min", 90], ["4h", 240]] as const) {
    assert.equal(parseEsforco(texto), esperado);
    if (esperado !== null) assert.equal(parseEsforco(formatEsforco(esperado)), esperado);
  }
  assert.equal(formatEsforco(null), "Não estimado");
  assert.equal(formatEsforco(undefined), "Não estimado");
  assert.equal(formatEsforco(0), "0 min");
});

test("entrada recusa decimais, negativos, dias e overflow", () => {
  for (const texto of ["-1", "1.5h", "1,5", "1.0", "1h60", "3 dias úteis", "abc", "2147483648", "9999999999999999999999999h"]) {
    assert.throws(() => parseEsforco(texto));
  }
});

test("edição envia minutos/null e preserva mensagem de erro backend", async () => {
  const enviados: (number | null)[] = [];
  const salvar = async (n: number | null) => { enviados.push(n); return { esforcoEstimadoMinutos: n }; };
  assert.deepEqual(await salvarEsforco("2h", salvar), { ok: true, valor: { esforcoEstimadoMinutos: 120 } });
  await salvarEsforco("", salvar);
  await salvarEsforco("0", salvar);
  const invalido = await salvarEsforco("1.5", salvar);
  assert.equal(invalido.ok, false);
  assert.deepEqual(enviados, [120, null, 0]);
  assert.deepEqual(await salvarEsforco("1h", async () => { throw new Error("Você não tem autoridade"); }), { ok: false, mensagem: "Você não tem autoridade" });
});

const ler = (p: string) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");
test("template e snapshot usam campo independente, sem derivar prazo", () => {
  const api = ler("lib/api-backend.ts");
  assert.equal((api.match(/esforcoEstimadoMinutos: etapa\.esforcoEstimadoMinutos \?\? null/g) ?? []).length, 3);
  assert.doesNotMatch(api, /esforcoEstimadoMinutos:\s*[^\n]*(quantidadeAntesDeadline|unidadePrazo|\*\s*24)/);
  const template = ler("components/workflows/WorkflowModeloFormModal.tsx");
  assert.match(template, /label="Esforço estimado"/);
  assert.match(template, /parseEsforco\(texto\)/);
  assert.match(template, /draft.etapas.every\(\(etapa\) => !erroEsforco\(etapa\)\)/);
  const detalhe = ler("components/demandas/EsforcoEtapa.tsx");
  assert.match(detalhe, /formatEsforco\(etapa.esforcoEstimadoMinutos\)/);
  assert.match(detalhe, /!somenteLeitura && etapa.podeEditarEsforco/);
  assert.match(detalhe, /setErro\(resultado.mensagem\)/);
  assert.match(detalhe, /Salvar esforço/);
  assert.match(ler("components/demandas/DemandaFormSections.tsx"), /<EsforcoEtapa demandaId=/);
});
