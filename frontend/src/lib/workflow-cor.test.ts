// P1_WORKFLOW_COLOR — cor do modelo de workflow. `npm run test:workflow-cor`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { corParaPayload, corParaPintar, estadoDoCampoDeCor, normalizarCorWorkflow, PALETA_WORKFLOW } from "./workflow-cor.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("normalização: só #RRGGBB válido, em maiúsculas; todo o resto é 'sem cor'", () => {
  assert.equal(normalizarCorWorkflow("#8b5cf6"), "#8B5CF6");
  assert.equal(normalizarCorWorkflow("  #f97316 "), "#F97316");
  assert.equal(normalizarCorWorkflow("#8B5CF6"), "#8B5CF6");
  for (const invalida of ["", " ", "#FFF", "#12345", "#1234567", "8B5CF6", "red", "rgb(1,2,3)", "hsl(0,0%,0%)", "bg-red-500", "#GGGGGG", "#8B5CF6;color:red", "<b>", null, undefined]) {
    assert.equal(normalizarCorWorkflow(invalida), null, String(invalida));
  }
});

test("a paleta é só atalho: HEX canônicos distintos, 8 a 12 opções, sem nome persistido", () => {
  assert.ok(PALETA_WORKFLOW.length >= 8 && PALETA_WORKFLOW.length <= 12);
  assert.equal(new Set(PALETA_WORKFLOW.map((cor) => cor.hex)).size, PALETA_WORKFLOW.length);
  for (const cor of PALETA_WORKFLOW) assert.equal(normalizarCorWorkflow(cor.hex), cor.hex);
  assert.equal(corParaPayload("#8b5cf6"), "#8B5CF6"); // vai o HEX, nunca o nome ("Violeta")
});

test("campo HEX: vazio = remover, incompleto/ inválido não é propagado, válido vira cor", () => {
  assert.deepEqual(estadoDoCampoDeCor(""), { texto: "", valida: true, cor: null });
  assert.deepEqual(estadoDoCampoDeCor("#8B5C"), { texto: "#8B5C", valida: false, cor: null });
  assert.deepEqual(estadoDoCampoDeCor("red"), { texto: "red", valida: false, cor: null });
  assert.deepEqual(estadoDoCampoDeCor("#8b5cf6"), { texto: "#8b5cf6", valida: true, cor: "#8B5CF6" });
});

test("o que a interface pinta: HEX válido; sem cor ou valor inválido (dado velho, injeção) = neutro", () => {
  assert.equal(corParaPintar("#06B6D4"), "#06B6D4");
  assert.equal(corParaPintar(null), null);
  assert.equal(corParaPintar(undefined), null);
  assert.equal(corParaPintar("red; background:url(x)"), null);
  assert.equal(corParaPayload(null), null);
  assert.equal(corParaPayload("rgb(0,0,0)"), null);
});

// ── apresentação (source-scan) ─────────────────────────────────────────────────────────────────────────────────────

test("a cor é aplicada em UM só componente (style controlado), sem classe Tailwind dinâmica", () => {
  const componente = semComentarios(ler("components/workflows/WorkflowCor.tsx"));
  assert.match(componente, /style=\{pintar \? \{ backgroundColor: pintar \} : undefined\}/);
  assert.match(componente, /corParaPintar\(cor\)/);
  for (const arquivo of ["components/workflows/WorkflowsGrid.tsx", "components/workflows/WorkflowModeloFormModal.tsx", "components/demandas/NovaDemandaModal.tsx", "components/ui/Combobox.tsx"]) {
    const codigo = semComentarios(ler(arquivo));
    assert.doesNotMatch(codigo, /backgroundColor/, arquivo); // nada de style de cor espalhado
    assert.doesNotMatch(codigo, /bg-\$\{/, arquivo);
  }
});

test("o nome do workflow sempre aparece em texto ao lado da cor e a cor não usa tons de prioridade/status", () => {
  const componente = semComentarios(ler("components/workflows/WorkflowCor.tsx"));
  assert.match(componente, /<span className="min-w-0 truncate">\{nome\}<\/span>/);
  assert.match(componente, /aria-hidden="true"/); // o ponto é decorativo: o nome é o rótulo acessível
  assert.doesNotMatch(componente, /prioridadeTone|statusDemandaTone|bg-red-|bg-emerald-|bg-amber-/);
});

test("cadastro: campo com paleta, seletor nativo, HEX, preview e 'Remover cor' (volta a null)", () => {
  const campo = semComentarios(ler("components/workflows/WorkflowCor.tsx"));
  assert.match(campo, /type="color"/);
  assert.match(campo, /Remover cor/);
  assert.match(campo, /onChange\(null\)/);
  assert.match(campo, /aria-label="Pré-visualização"/);
  assert.match(campo, /PALETA_WORKFLOW\.map/);
  const form = semComentarios(ler("components/workflows/WorkflowModeloFormModal.tsx"));
  assert.match(form, /cor: modelo\?\.cor \?\? null/); // workflow sem cor abre sem cor (nada é sorteado)
  assert.match(form, /<WorkflowCorField valor=\{draft\.cor\} onChange=\{\(cor\) => updateDraft\(\{ cor \}\)\} nomePreview=\{draft\.nome\} \/>/);
});

test("listagem e seletor de workflow mostram a cor ao lado do nome; sem cor = ponto neutro", () => {
  assert.match(semComentarios(ler("components/workflows/WorkflowsGrid.tsx")), /<WorkflowNomeComCor nome=\{modelo\.nome\} cor=\{modelo\.cor\} \/>/);
  const nova = semComentarios(ler("components/demandas/NovaDemandaModal.tsx"));
  assert.match(nova, /leading: <WorkflowCorPonto cor=\{modelo\.cor\} \/>/);
  const combobox = semComentarios(ler("components/ui/Combobox.tsx"));
  assert.match(combobox, /\{option\.leading\}/);
  assert.match(combobox, /<span className="min-w-0 truncate">\{option\.label\}<\/span>/); // o texto da opção continua sendo o rótulo
});

test("contrato com a API: leitura mapeia cor (null por padrão); gravação SEMPRE envia cor (null remove); diretório traz a cor", () => {
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /cor: data\.cor \?\? null,/);
  assert.match(api, /cor: corParaPayload\(draft\.cor\),/);
  assert.match(api, /itens\.map\(\(item\) => \(\{ \.\.\.item, cor: item\.cor \?\? null \}\)\)/);
  const tipos = semComentarios(ler("types/workflow-modelo.ts"));
  assert.match(tipos, /cor: string \| null;/);
});

test("não toca nas semânticas existentes: prioridade, Kanban e Pauta seguem sem a cor do workflow", () => {
  for (const arquivo of ["components/demandas/DemandaKanbanCard.tsx", "components/pauta/PautaGantt.tsx", "components/pauta/PautaLista.tsx", "lib/prioridade-demanda.ts"]) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /workflow-cor|WorkflowCor/, arquivo);
  }
});
