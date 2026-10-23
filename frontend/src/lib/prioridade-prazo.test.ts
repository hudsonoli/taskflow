// Prioridade como SEMÁFORO (fonte única) e ordenação operacional por prazo decidida no SERVIDOR. `npm run test:prioridade-prazo` (node --test, sem dependências).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { prioridadeBordaClasse, prioridadeTone } from "./prioridade-demanda.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("semáforo: Alta vermelho, Média âmbar, Baixa verde — nos dois mapas da fonte única", () => {
  assert.deepEqual(prioridadeTone, { alta: "red", media: "amber", baixa: "green" });
  assert.match(prioridadeBordaClasse.alta, /border-l-red-/);
  assert.match(prioridadeBordaClasse.media, /border-l-amber-/);
  assert.match(prioridadeBordaClasse.baixa, /border-l-emerald-/);
  assert.deepEqual(Object.keys(prioridadeTone).sort(), ["alta", "baixa", "media"]); // enum real: nada de "urgente"/"crítica"
});

test("a tag sempre mostra o TEXTO (a cor nunca é o único sinal) e vive num componente só", () => {
  const tag = semComentarios(ler("components/demandas/PrioridadeTag.tsx"));
  assert.match(tag, /\{prioridadeDemandaLabels\[prioridade\]\}/);
  assert.match(tag, /<Badge tone=\{prioridadeTone\[prioridade\]\}>/);
  const labels = semComentarios(ler("lib/demandas.ts"));
  assert.match(labels, /alta: "Alta"/);
  assert.match(labels, /media: "Média"/);
  assert.match(labels, /baixa: "Baixa"/);
});

test("tabela, Kanban, lista compacta, prazos da equipe, drawer e seção Dados usam a MESMA tag; nenhum mapa local de cor de prioridade sobrou", () => {
  for (const arquivo of [
    "components/demandas/DemandasTable.tsx",
    "components/demandas/DemandaKanbanCard.tsx",
    "components/operacional/TarefasLista.tsx",
    "components/notificacoes/PrazosEquipeLista.tsx",
    "components/demandas/DemandaDetailsDrawer.tsx",
    "components/demandas/DemandaFormSections.tsx",
  ]) {
    const texto = semComentarios(ler(arquivo));
    assert.match(texto, /<PrioridadeTag prioridade=\{demanda\.prioridade\} \/>/, arquivo);
    assert.doesNotMatch(texto, /prioridadeClassName|prioridadeClassNames|const prioridadeTone/, arquivo);
  }
  // o card do Kanban usa a borda do semáforo (a mesma fonte) e o overlay do arraste também
  const card = semComentarios(ler("components/demandas/DemandaKanbanCard.tsx"));
  assert.equal((card.match(/prioridadeBordaClasse\[demanda\.prioridade\]/g) ?? []).length, 2);
  // nada de hex espalhado nem do azul antigo para prioridade
  const fonte = semComentarios(ler("lib/prioridade-demanda.ts"));
  assert.doesNotMatch(fonte, /#[0-9a-fA-F]{3,8}\b/);
  assert.doesNotMatch(fonte, /blue|sky|indigo/);
});

test("a ordem é do SERVIDOR: a tela pede sort=operacional e lista/Kanban/Solicitadas só PRESERVAM a ordem recebida", () => {
  const view = semComentarios(ler("components/demandas/DemandasView.tsx"));
  assert.match(view, /sort: "operacional" as const/);
  assert.doesNotMatch(view, /\.sort\(/); // nenhuma reordenação local da página
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /DemandaSort = "numero_operacional_desc" \| "prazo_asc" \| "sinalizada_desc" \| "fila_pessoal" \| "operacional"/);
  for (const arquivo of ["components/demandas/DemandasKanban.tsx", "components/demandas/DemandaKanbanColumn.tsx", "components/demandas/DemandasTable.tsx", "components/demandas/DemandasSolicitadasTable.tsx"]) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /\.sort\(|\.toSorted\(|\.reverse\(/, arquivo);
  }
  // o agrupamento por coluna é um filter (preserva a ordem relativa); a mesma consulta alimenta "Solicitadas por mim" (só muda o escopo)
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(kanban, /demandas\.filter\(\(demanda\) => \(column\.statuses as DemandaStatus\[\]\)\.includes\(demanda\.status\)\)/);
});

test("Meu Dia mantém o sort fila_pessoal; a Pauta por etapa tem endpoint próprio (sem sort de Demandas); o novo sort é só das Tarefas", () => {
  assert.doesNotMatch(semComentarios(ler("components/pauta/PautaView.tsx")), /"operacional"|sort:/);
  assert.match(semComentarios(ler("lib/api-backend.ts")), /"fila_pessoal"/);
});
