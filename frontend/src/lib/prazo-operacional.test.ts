// Fase 7A — prazo operacional com data + horário desde a criação. `npm run test:fase-7a` (node --test, sem dependências).
// Conversões puras exercitadas de verdade (em fusos diferentes); telas e API (.tsx/.ts com alias `@/`) são lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { dataDoInputLocal, inputLocalParaIso, isoParaInputLocal } from "./prazo-operacional.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");

function noFuso<T>(fuso: string, fn: () => T): T {
  const anterior = process.env.TZ;
  process.env.TZ = fuso;
  try {
    return fn();
  } finally {
    if (anterior === undefined) delete process.env.TZ;
    else process.env.TZ = anterior;
  }
}

test("15/10/2026 16:30 em São Paulo vira o instante 19:30Z (o backend lê hora sem fuso como UTC)", () => {
  assert.equal(noFuso("America/Sao_Paulo", () => inputLocalParaIso("2026-10-15T16:30")), "2026-10-15T19:30:00.000Z");
  assert.equal(noFuso("UTC", () => inputLocalParaIso("2026-10-15T16:30")), "2026-10-15T16:30:00.000Z");
});

test("a data planejada é o dia LOCAL escolhido, mesmo quando o instante já é o dia seguinte em UTC", () => {
  noFuso("America/Sao_Paulo", () => {
    assert.equal(inputLocalParaIso("2026-10-15T22:30"), "2026-10-16T01:30:00.000Z"); // dia 16 em UTC
    assert.equal(dataDoInputLocal("2026-10-15T22:30"), "2026-10-15"); // ...mas o dia planejado é 15
    assert.equal(dataDoInputLocal("2026-10-15T00:10"), "2026-10-15");
  });
});

test("ida e volta: o instante da API volta ao mesmo valor do campo local", () => {
  noFuso("America/Sao_Paulo", () => {
    const iso = inputLocalParaIso("2026-10-15T16:30")!;
    assert.equal(isoParaInputLocal(iso), "2026-10-15T16:30");
    assert.equal(isoParaInputLocal("2026-10-16T01:30:00Z"), "2026-10-15T22:30");
    assert.equal(isoParaInputLocal("2026-10-15T19:30:00.123456-00:00"), "2026-10-15T16:30");
  });
});

test("vazio, nulo e inválido não geram valor (nunca lança)", () => {
  for (const ruim of [null, undefined, "", "2026-10-15", "2026-10-15T16", "2026-13-40T10:00", "2026-02-30T10:00", "15/10/2026 16:30", "2026-10-15T25:00"]) {
    assert.equal(inputLocalParaIso(ruim as string | null | undefined), null, String(ruim));
    assert.equal(dataDoInputLocal(ruim as string | null | undefined), "", String(ruim));
  }
  assert.equal(isoParaInputLocal(null), "");
  assert.equal(isoParaInputLocal(undefined), "");
  assert.equal(isoParaInputLocal("não é data"), "");
});

test("criação: a Nova Demanda pede data + horário e envia prazoEtapaAtual E dataFimPrevista no mesmo POST (sem segundo PATCH)", () => {
  const modal = ler("components/demandas/NovaDemandaModal.tsx");
  assert.match(modal, /label="Prazo \(data e horário\)"\s+type="datetime-local"/);
  assert.match(modal, /value=\{draft\.prazoEtapaAtual \?\? ""\}/);
  assert.match(modal, /dataFimPrevista: dataDoInputLocal\(valor\)/);
  assert.doesNotMatch(modal, /label="Prazo previsto"/); // o campo só de data saiu
  const api = ler("lib/api-backend.ts");
  assert.match(api, /prazoEtapaAtual: inputLocalParaIso\(draft\.prazoEtapaAtual\)/);
  assert.match(api, /dataFimPrevista: draft\.dataFimPrevista \|\| null/);
  // um único POST: criarDemandaReal não encadeia PATCH
  const criar = api.slice(api.indexOf("export async function criarDemandaReal"), api.indexOf("export async function atualizarDemandaReal"));
  assert.match(criar, /method: "POST"/);
  assert.doesNotMatch(criar, /PATCH|patchDemandaReal/);
});

test("edição não apaga a data planejada: limpar o horário não zera dataFimPrevista (só preencher a sobrescreve)", () => {
  const modal = ler("components/demandas/NovaDemandaModal.tsx");
  assert.match(modal, /\.\.\.\(valor \? \{ dataFimPrevista: dataDoInputLocal\(valor\) \} : \{\}\)/);
});

test("drawer: o campo datetime-local usa o relógio local e envia o instante com fuso (antes enviava hora sem fuso)", () => {
  const drawer = ler("components/demandas/DemandaFormSections.tsx");
  assert.match(drawer, /useState\(isoParaInputLocal\(demanda\.prazoEtapaAtual\)\)/);
  assert.match(drawer, /\{ prazoEtapaAtual: inputLocalParaIso\(prazo\) \}/);
});

test("as telas mostram prazoEtapaAtual com data + horário (formatPrazo exibe a hora quando o valor é um instante)", () => {
  const demandas = ler("lib/demandas.ts");
  assert.match(demandas, /const hasTime = value\.includes\("T"\)/);
  assert.match(demandas, /\.\.\.\(hasTime \? \{ hour: "2-digit", minute: "2-digit" \} : \{\}\)/);
  for (const tela of [
    "components/demandas/DemandasTable.tsx",
    "components/demandas/DemandaKanbanCard.tsx",
    "components/dashboard/DashboardView.tsx",
    "components/operacional/TarefasLista.tsx",
    "components/demandas/DemandaDetailsDrawer.tsx",
  ]) {
    assert.match(ler(tela), /formatPrazo\(demanda\.prazoEtapaAtual\)/, tela);
  }
  assert.match(ler("components/pauta/PautaLista.tsx"), /formatHora\.format\(prazo\)/); // Pauta: hora na linha do dia
});

test("o seletor de responsáveis e o de departamentos oferecem a empresa toda (o backend decide a regra)", () => {
  const modal = ler("components/demandas/NovaDemandaModal.tsx");
  assert.match(modal, /buscarOpcoes=\{responsaveis\.buscarOpcoes\}/); // busca no servidor, sem restrição por projeto/squad
  assert.match(modal, /departamentos\s+\.filter\(\(departamento\) => departamento\.status === "ativo"\)/);
  assert.doesNotMatch(modal, /equipe|squad/i);
});
