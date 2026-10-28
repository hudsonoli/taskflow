// P1_PAUTA_COLABORADOR — apresentação da Pauta (source-scan): o que não dá para provar só com a lógica pura. `npm run test:pauta-colaborador`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("Pauta: Colaborador é o padrão e a alternância é compacta (sem item novo na Sidebar/menu)", () => {
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.match(view, /\?\? "colaborador"/);
  const toolbar = semComentarios(ler("components/pauta/PautaToolbar.tsx"));
  assert.match(toolbar, /label: "Colaborador"/);
  assert.match(toolbar, /label: "Projeto"/);
  const nav = semComentarios(ler("components/layout/TopNav.tsx"));
  assert.equal((nav.match(/label: "Pauta"/g) ?? []).length, 1); // o menu segue com UM item Pauta
});

test("as duas visões e os dois modos consomem o MESMO conjunto de itens (uma consulta; agrupar é só apresentação)", () => {
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.equal((view.match(/usePautaOperacional\(/g) ?? []).length, 1);
  assert.equal((view.match(/agruparPorColaborador\(dados\.itens/g) ?? []).length, 1);
  assert.equal((view.match(/agruparPorProjeto\(dados\.itens/g) ?? []).length, 1);
  assert.match(view, /<PautaLista grupos=\{grupos\}/);
  assert.match(view, /<PautaGantt grupos=\{grupos\}/);
  // nenhuma requisição por colaborador/etapa: as únicas chamadas de rede da Pauta são o hook e o selo de execução
  assert.doesNotMatch(view, /\.map\([^)]*=> *(get|list|fetch)/);
  assert.equal((view.match(/listarDemandasEmExecucaoNaPauta\(/g) ?? []).length, 1);
});

test("linhas: identificador emitido pelo servidor, PrioridadeTag compartilhado e nenhuma cor de prioridade recriada", () => {
  for (const arquivo of ["PautaGantt", "PautaLista"]) {
    const codigo = semComentarios(ler(`components/pauta/${arquivo}.tsx`));
    assert.match(codigo, /item\.demandaIdentificador/, arquivo);
    assert.match(codigo, /<PrioridadeTag prioridade=\{item\.prioridade\} \/>/, arquivo);
    assert.doesNotMatch(codigo, /prioridadeTone|prioridadeBordaClasse|prioridade === "alta"/, arquivo);
    assert.doesNotMatch(codigo, /`#\$\{/, arquivo);
  }
});

test("a origem da responsabilidade vai só em tooltip/linha secundária, e só departamento é mostrado como 'Departamento: …' (ninguém é escolhido)", () => {
  const contexto = semComentarios(ler("components/pauta/pautaContexto.ts"));
  assert.match(contexto, /"Herdado da tarefa"/);
  assert.match(contexto, /"Definido na etapa"/);
  assert.match(contexto, /`Departamento: /);
  const gantt = semComentarios(ler("components/pauta/PautaGantt.tsx"));
  assert.match(gantt, /const detalhe = \[[^\]]*origem\]\.filter\(Boolean\)\.join\(" — "\)/); // a origem da responsabilidade vai no tooltip da linha
  assert.match(gantt, /title=\{detalhe\}/);
  const grupos = semComentarios(ler("lib/pauta-operacional.ts"));
  assert.match(grupos, /"Sem responsável individual"/);
  assert.match(grupos, /"Sem responsável"/);
});

test("sem N+1 no cliente: o contexto de nomes vem do catálogo `pessoas` do próprio payload (nada de buscar usuário por colaborador)", () => {
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.match(view, /dados\?\.pessoas/);
  assert.doesNotMatch(view, /useUsuariosComIds|getUsuario|listUsuarios/);
});
