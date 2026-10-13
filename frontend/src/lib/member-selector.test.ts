// MemberSelector canônico — regras puras exercitadas de verdade + estrutura do componente e dos consumidores (payload preservado). `npm run test:member-selector`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  dividirVisiveis,
  filtrarPessoas,
  normalizarBusca,
  podeEscolher,
  posicionarPopover,
  primeiroNome,
  proximaSelecao,
  selecionadosPrimeiro,
} from "./member-selector.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const pessoas = [
  { id: "1", nome: "Hudson de Oliveira", email: "hudson@empresa.com" },
  { id: "2", nome: "João Silva", email: "joao.silva@empresa.com", subtitulo: "Criação" },
  { id: "3", nome: "Maria Souza", email: "maria@empresa.com" },
  { id: "4", nome: "Ana Inativa", inativo: true },
];

// ── busca ────────────────────────────────────────────────────────────────────────────────────────────────────

test("busca por nome, sem acento e sem diferenciar maiúsculas", () => {
  assert.equal(normalizarBusca("  JOÃO "), "joao");
  assert.deepEqual(filtrarPessoas(pessoas, "joao").map((p) => p.id), ["2"]);
  assert.deepEqual(filtrarPessoas(pessoas, "HUDSON").map((p) => p.id), ["1"]);
  assert.deepEqual(filtrarPessoas(pessoas, "olive").map((p) => p.id), ["1"]); // meio do nome
});

test("busca por e-mail (quando a opção o traz) e por subtítulo; opção sem e-mail não quebra", () => {
  assert.deepEqual(filtrarPessoas(pessoas, "maria@").map((p) => p.id), ["3"]);
  assert.deepEqual(filtrarPessoas(pessoas, "EMPRESA.COM").map((p) => p.id), ["1", "2", "3"]);
  assert.deepEqual(filtrarPessoas(pessoas, "criacao").map((p) => p.id), ["2"]); // subtítulo, sem acento
});

test("sem resultados devolve lista vazia; termo vazio devolve todos (cópia)", () => {
  assert.deepEqual(filtrarPessoas(pessoas, "zzzz"), []);
  assert.equal(filtrarPessoas(pessoas, "   ").length, pessoas.length);
});

// ── ordem, nomes, estouro ─────────────────────────────────────────────────────────────────────────────────────

test("selecionados primeiro, preservando a ordem de cada grupo e sem duplicar", () => {
  const ordenado = selecionadosPrimeiro(pessoas, ["3", "1"]);
  assert.deepEqual(ordenado.map((p) => p.id), ["1", "3", "2", "4"]);
  assert.equal(new Set(ordenado.map((p) => p.id)).size, pessoas.length);
});

test("primeiro nome para o rótulo curto", () => {
  assert.equal(primeiroNome("Hudson de Oliveira"), "Hudson");
  assert.equal(primeiroNome("  Maria  "), "Maria");
  assert.equal(primeiroNome(""), "");
});

test("maxVisible: mostra N avatares e o resto vira '+N'; sem limite (ou limite inválido) mostra todos", () => {
  const ids = ["a", "b", "c", "d", "e"];
  assert.deepEqual(dividirVisiveis(ids, 3), { visiveis: ["a", "b", "c"], restantes: ["d", "e"] });
  assert.deepEqual(dividirVisiveis(ids, 5), { visiveis: ids, restantes: [] });
  assert.deepEqual(dividirVisiveis(ids, undefined), { visiveis: ids, restantes: [] });
  assert.deepEqual(dividirVisiveis(ids, 0), { visiveis: ids, restantes: [] });
  assert.deepEqual(dividirVisiveis([], 3), { visiveis: [], restantes: [] });
});

// ── single / multi / limite ──────────────────────────────────────────────────────────────────────────────────

test("SINGLE: escolher outra pessoa SUBSTITUI a anterior (e fecha); clicar na escolhida a remove", () => {
  assert.deepEqual(proximaSelecao({ values: [], id: "1", multiple: false }), { values: ["1"], bloqueadoPorLimite: false, fechar: true });
  assert.deepEqual(proximaSelecao({ values: ["1"], id: "2", multiple: false }), { values: ["2"], bloqueadoPorLimite: false, fechar: true });
  assert.deepEqual(proximaSelecao({ values: ["2"], id: "2", multiple: false }), { values: [], bloqueadoPorLimite: false, fechar: true });
});

test("MULTI: marca e desmarca preservando a ordem dos ids (o payload segue sendo string[])", () => {
  const um = proximaSelecao({ values: [], id: "1", multiple: true });
  const dois = proximaSelecao({ values: um.values, id: "3", multiple: true });
  assert.deepEqual(dois.values, ["1", "3"]);
  assert.equal(dois.fechar, false); // multi continua aberto para escolher mais
  assert.deepEqual(proximaSelecao({ values: ["1", "3"], id: "1", multiple: true }).values, ["3"]);
});

test("MAX: o limite recusa NOVAS escolhas, mas desmarcar continua possível; no single o max é ignorado", () => {
  assert.deepEqual(proximaSelecao({ values: ["1", "2"], id: "3", multiple: true, max: 2 }), { values: ["1", "2"], bloqueadoPorLimite: true, fechar: false });
  assert.deepEqual(proximaSelecao({ values: ["1", "2"], id: "2", multiple: true, max: 2 }).values, ["1"]);
  assert.deepEqual(proximaSelecao({ values: [], id: "1", multiple: false, max: 1 }).values, ["1"]);
  assert.equal(podeEscolher({ selecionado: false, totalSelecionados: 2, max: 2, multiple: true }), false);
  assert.equal(podeEscolher({ selecionado: true, totalSelecionados: 2, max: 2, multiple: true }), true);
  assert.equal(podeEscolher({ selecionado: false, totalSelecionados: 5, max: 1, multiple: false }), true);
});

test("USUÁRIO INATIVO: continua visível se já estava selecionado, mas não é escolhido de novo (a menos que o campo permita)", () => {
  assert.equal(podeEscolher({ selecionado: true, inativo: true, totalSelecionados: 1, multiple: true }), true);
  assert.equal(podeEscolher({ selecionado: false, inativo: true, totalSelecionados: 0, multiple: true }), false);
  assert.equal(podeEscolher({ selecionado: false, inativo: true, permitirInativos: true, totalSelecionados: 0, multiple: true }), true);
});

// ── posição do popover (responsividade) ──────────────────────────────────────────────────────────────────────

test("o popover fica SEMPRE dentro da viewport: largura limitada, deslocamento para dentro e abertura para cima quando falta espaço embaixo", () => {
  const dentro = (r: { largura: number; deslocamentoX: number }, caixaLeft: number, vw: number) => caixaLeft + r.deslocamentoX >= 16 && caixaLeft + r.deslocamentoX + r.largura <= vw - 16;
  // celular: campo recuado (x=41) e popover de 352 -> limitado a 343 e puxado para a esquerda
  const cel = posicionarPopover({ caixa: { left: 41, right: 335, top: 100, bottom: 140 }, larguraPopover: 352, alturaPopover: 320, viewport: { largura: 375, altura: 800 } });
  assert.equal(cel.largura, 343);
  assert.ok(dentro(cel, 41, 375), JSON.stringify(cel));
  // desktop: campo na borda direita -> deslocado para a esquerda
  const dir = posicionarPopover({ caixa: { left: 1100, right: 1400, top: 100, bottom: 140 }, larguraPopover: 352, alturaPopover: 320, viewport: { largura: 1440, altura: 900 } });
  assert.ok(dentro(dir, 1100, 1440) && dir.deslocamentoX < 0, JSON.stringify(dir));
  // campo à esquerda com espaço de sobra: não desloca
  assert.equal(posicionarPopover({ caixa: { left: 40, right: 300, top: 100, bottom: 140 }, larguraPopover: 352, alturaPopover: 320, viewport: { largura: 1440, altura: 900 } }).deslocamentoX, 0);
  // vertical
  assert.equal(posicionarPopover({ caixa: { left: 20, right: 300, top: 700, bottom: 740 }, larguraPopover: 300, alturaPopover: 320, viewport: { largura: 375, altura: 800 } }).vertical, "cima");
  assert.equal(posicionarPopover({ caixa: { left: 20, right: 300, top: 40, bottom: 80 }, larguraPopover: 300, alturaPopover: 320, viewport: { largura: 375, altura: 800 } }).vertical, "baixo");
});

// ── componente canônico ──────────────────────────────────────────────────────────────────────────────────────

test("UM componente canônico evoluído (nada de MemberSelector2): mesmos modos local/servidor e a mesma assinatura de onChange (ids)", () => {
  const comp = semComentarios(ler("components/ui/MemberSelector.tsx"));
  assert.match(comp, /export function MemberSelector\(/);
  assert.match(comp, /onChange: \(values: string\[\], selecionados\?: MemberOption\[\]\) => void;/); // contrato do consumidor intacto
  assert.match(comp, /buscarOpcoes\?: BuscarOpcoesMembros;/); // modo servidor preservado
  assert.match(comp, /resolverSelecionados\?: ResolverSelecionadosMembros;/);
  for (const prop of ["variant?:", "max?: number", "maxVisible?: number", "disabled?: boolean", "permitirInativos?: boolean", "className?: string"]) {
    assert.ok(comp.includes(prop), prop);
  }
  for (const proibido of ["MemberSelector2", "UserPickerNew", "NewMemberSelector"]) assert.ok(!comp.includes(proibido));
});

test("visual: avatares circulares com primeiro nome, botão '+' tracejado, iniciais como fallback (Avatar existente) e SEM dados/imagens externas", () => {
  const comp = semComentarios(ler("components/ui/MemberSelector.tsx"));
  assert.match(comp, /<Avatar /); // foto real ou iniciais: componente único do projeto
  assert.match(comp, /primeiroNome\(pessoa\.nome\)/);
  assert.match(comp, /border-dashed/);
  assert.match(comp, /<Plus /);
  assert.doesNotMatch(comp, /dicebear|unsplash|https?:\/\//i);
});

test("acessibilidade: botões type=button, aria-label, estado selecionado exposto, Esc, foco na busca, listbox/option, focus-visible", () => {
  const comp = semComentarios(ler("components/ui/MemberSelector.tsx"));
  assert.doesNotMatch(comp, /<button(?![^>]*type="button")[^>]*>/); // todo <button> declara type="button"
  assert.match(comp, /role="listbox"/);
  assert.match(comp, /role="option"/);
  assert.match(comp, /aria-selected=\{isSelected\}/);
  assert.match(comp, /aria-multiselectable=\{multiple\}/);
  assert.match(comp, /aria-haspopup/);
  assert.match(comp, /aria-expanded/);
  assert.match(comp, /aria-label=\{`Remover \$\{pessoa\.nome\}`\}/);
  assert.match(comp, /event\.key === "Escape"/);
  assert.match(comp, /autoFocus/); // foco inicial na busca
  assert.match(comp, /ArrowDown/);
  assert.match(comp, /focus-visible:/);
  assert.match(comp, /sr-only">Selecionado/); // não depende só de cor/ícone
});

test("disabled: não abre, não remove, avatares seguem visíveis", () => {
  const comp = semComentarios(ler("components/ui/MemberSelector.tsx"));
  assert.match(comp, /function abrir\(\) \{\s*if \(disabled\) return;/);
  assert.match(comp, /function remove\([^)]*\) \{[\s\S]*?if \(disabled\) return;/);
  assert.match(comp, /\{!disabled && \(\s*<button\s+type="button"\s+onClick=\{\(event\) => remove\(pessoa\.id, event\)\}/); // sem X quando só leitura
});

test("variantes default e compact no MESMO componente; compact é um campo de uma linha com chevron", () => {
  const comp = semComentarios(ler("components/ui/MemberSelector.tsx"));
  assert.match(comp, /variant = "default"/);
  assert.match(comp, /const compacto = variant === "compact";/);
  assert.match(comp, /if \(compacto\) \{/);
  assert.match(comp, /h-7 w-7/); // avatar ~28px no compacto
  assert.match(comp, /h-10 w-10/); // avatar maior no padrão
});

test("popover: largura limitada à viewport, rolagem interna, fecha ao clicar fora e devolve o foco no Esc", () => {
  const comp = semComentarios(ler("components/ui/MemberSelector.tsx"));
  assert.match(comp, /max-w-\[calc\(100vw-2rem\)\]/);
  assert.match(comp, /max-h-60 overflow-y-auto/);
  assert.match(comp, /document\.addEventListener\("mousedown", handleClickOutside\)/);
  assert.match(comp, /gatilhoRef\.current\?\.focus\(\)/);
});

test("nenhuma dependência nova no package.json por causa do seletor", () => {
  const pacote = JSON.parse(readFileSync(new URL("../package.json", SRC), "utf8"));
  const nomes = Object.keys({ ...pacote.dependencies, ...pacote.devDependencies });
  assert.equal(nomes.some((nome) => /headless|radix|downshift|floating|popper|react-select|cmdk/i.test(nome)), false);
});

// ── consumidores: payload (ids) preservado ───────────────────────────────────────────────────────────────────

test("consumidores multi continuam entregando o MESMO string[] de ids (Demanda, Projeto, Equipe, Workflow)", () => {
  const casos: Array<[string, RegExp]> = [
    ["components/demandas/NovaDemandaModal.tsx", /usuarioResponsavelIds/],
    ["components/demandas/DemandaFormSections.tsx", /usuarioResponsavelIds: values/],
    ["components/projetos/NovoProjetoModal.tsx", /responsavelIds/],
    ["components/projetos/ProjetoFormSections.tsx", /responsavelIds/],
    ["components/equipes/EquipeFormModal.tsx", /membroIds/],
    ["components/workflows/WorkflowModeloFormModal.tsx", /usuarioResponsavelIds/],
  ];
  for (const [arquivo, padrao] of casos) {
    const tela = semComentarios(ler(arquivo));
    assert.match(tela, /<MemberSelector/, arquivo);
    assert.match(tela, padrao, arquivo);
    assert.doesNotMatch(tela, /usuarioResponsavelIds:\s*(values|selecionados)\.map\(/, arquivo); // nunca objetos Member no lugar de ids
  }
});

test("Tráfego: single compacto; o usuário escolhido segue sendo só o id enviado a abrirSessaoTrabalho", () => {
  const tela = semComentarios(ler("components/trafego/TrafegoIniciarSessao.tsx"));
  assert.match(tela, /<MemberSelector\s+label="Usuário"\s+variant="compact"\s+multiple=\{false\}/);
  assert.match(tela, /onChange=\{\(values\) => setUsuarioId\(values\[0\] \?\? ""\)\}/);
  assert.match(tela, /await abrirSessaoTrabalho\(\{\s*demandaId,\s*usuarioId,?\s*\}\)/);
});

test("Relatórios (Colaborador) e Definir Gestor passam a usar o seletor canônico, com os mesmos ids", () => {
  const relatorio = semComentarios(ler("components/relatorios/PerformanceColaboradorReport.tsx"));
  assert.match(relatorio, /<MemberSelector\s+label="Colaborador"\s+variant="compact"\s+permitirInativos/);
  assert.match(relatorio, /onChange=\{\(values\) => setColaboradorIdSelecionado\(values\[0\] \?\? ""\)\}/);
  assert.doesNotMatch(relatorio, /<Select\b/);
  const gestor = semComentarios(ler("components/plataforma/DefinirGestorModal.tsx"));
  assert.match(gestor, /<MemberSelector\s+label="Usuário da empresa"/);
  assert.match(gestor, /onChange=\{\(values\) => setEscolhido\(values\[0\] \?\? ""\)\}/);
  assert.match(gestor, /promoverGestorEmpresa\(empresa\.id, escolhido\)/); // payload: o id escolhido
  assert.doesNotMatch(gestor, /<select\b/);
});

test("Permissões: single compacto e permite inativo (consulta histórica); Departamentos NÃO usam o seletor de pessoas", () => {
  assert.match(semComentarios(ler("components/permissoes/PermissoesUsuarioView.tsx")), /variant="compact"\s+permitirInativos/);
  for (const arquivo of ["components/demandas/NovaDemandaModal.tsx", "components/projetos/NovoProjetoModal.tsx", "components/workflows/WorkflowModeloFormModal.tsx"]) {
    const tela = semComentarios(ler(arquivo));
    assert.match(tela, /<MultiSelect/, arquivo); // departamentos: seletor próprio, separado de pessoas
  }
});

test("a fonte das opções marca inativo e usa cargo/departamento como segunda linha — sem inventar e-mail (o diretório do backend não o expõe)", () => {
  const fonte = semComentarios(ler("lib/useResponsaveisSelector.ts"));
  assert.match(fonte, /inativo: usuario\.status !== "ativo"/);
  assert.match(fonte, /\?\? usuario\.cargo/);
  assert.doesNotMatch(fonte, /email/i);
  assert.doesNotMatch(fonte, /marcarIndisponiveis/);
});
