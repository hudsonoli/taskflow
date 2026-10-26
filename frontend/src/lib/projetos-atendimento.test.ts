// Projetos para o Atendimento (ver e criar), sem editar/arquivar. `npm run test:projetos-atendimento`.
// O alias `@/` não resolve no node --test: as regras de UX e a fiação são lidas como texto (a decisão real é do servidor, com testes de backend).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (codigo: string) => codigo.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

test("regras de UX: acessa projetos quem é administração OU Atendimento; só a administração gere (editar/arquivar/modelo)", () => {
  const e = semComentarios(ler("lib/escopo-operacional.ts"));
  assert.match(e, /export function podeAcessarProjetos\(usuario: Usuario, departamentos: DepartamentoDiretorioItem\[\]\): boolean \{\s*return podeAcessarAreaAdministrativa\(usuario\) \|\| resolverEhAtendimento\(usuario, departamentos\);\s*\}/);
  assert.match(e, /export function podeGerirProjetos\(usuario: Usuario\): boolean \{\s*return podeAcessarAreaAdministrativa\(usuario\);\s*\}/);
  // o Atendimento é reconhecido pela mesma regra de Minhas Demandas/Pauta (departamento), nunca por perfil
  assert.doesNotMatch(/export function podeAcessarProjetos[\s\S]*?\n\}/.exec(e)?.[0] ?? "", /liderDepartamento|perfil ===|"operador"/);
});

test("o menu mostra Projetos ao Atendimento; Relatórios e Configurações continuam só da administração", () => {
  const nav = semComentarios(ler("components/layout/TopNav.tsx"));
  assert.match(nav, /if \(podeAcessarProjetos\(usuarioAtual, departamentos\)\) \{[\s\S]*?label: "Projetos", href: "\/projetos"/);
  const bloco = /if \(podeAcessarAreaAdministrativa\(usuarioAtual\)\) \{([\s\S]*?)\n  \}/.exec(nav)?.[1] ?? "";
  assert.match(bloco, /label: "Relatórios"/);
  assert.match(bloco, /label: "Configurações"/);
  assert.doesNotMatch(bloco, /label: "Projetos"/);
});

test("a rota de Projetos usa o guarda próprio (admin + Atendimento), que espera sessão/departamentos antes de negar", () => {
  const rota = semComentarios(ler("app/e/[slug]/projetos/page.tsx"));
  assert.match(rota, /<ProjetosAcessoGuard>\s*<ProjetosView \/>\s*<\/ProjetosAcessoGuard>/);
  assert.doesNotMatch(rota, /AreaAdministrativaGuard/);
  const guarda = semComentarios(ler("components/operacional/ProjetosAcessoGuard.tsx"));
  assert.match(guarda, /podeAcessarProjetos\(usuarioAtual, departamentos\)/);
  assert.match(guarda, /if \(sessaoCarregando \|\| !usuarioAtual\) return null;/);
  assert.match(guarda, /if \(carregando && !podeAcessarProjetos\(usuarioAtual, departamentos\)\) return null;/); // não nega enquanto o diretório carrega
  // Relatórios/Configurações seguem protegidos pelo guarda administrativo, que não foi alterado
  assert.match(semComentarios(ler("components/operacional/AreaAdministrativaGuard.tsx")), /podeAcessarAreaAdministrativa\(usuarioAtual\)/);
});

test("a tela de Projetos esconde editar/arquivar/restaurar e a aba Modelo de quem não gere; criar continua disponível", () => {
  const view = semComentarios(ler("components/projetos/ProjetosView.tsx"));
  assert.match(view, /const podeGerir = usuarioAtual \? podeGerirProjetos\(usuarioAtual\) : false;/);
  assert.match(view, /<ProjetosTable[\s\S]*?podeGerir=\{podeGerir\}/);
  assert.match(view, /<ProjetoDetailsDrawer[\s\S]*?podeGerir=\{podeGerir\}/);
  assert.match(view, /onNewProject=\{\(\) => setCreatingProject\(true\)\}/); // "Novo projeto" não depende de podeGerir
  const tabela = semComentarios(ler("components/projetos/ProjetosTable.tsx"));
  assert.match(tabela, /\{!podeGerir \? null : arquivado \? \(/);
  assert.match(tabela, /onClick=\{\(\) => onOpenDetails\(projeto\.id\)\}/); // Detalhes fica para todos
  const drawer = semComentarios(ler("components/projetos/ProjetoDetailsDrawer.tsx"));
  assert.match(drawer, /onEdit=\{projeto && podeGerir \? \(\) => onEdit\(projeto\.id\) : undefined\}/);
  assert.match(drawer, /tabs\.filter\(\(aba\) => aba\.id !== "modelo"\)/);
  assert.match(drawer, /activeTab === "modelo" && podeGerir/);
});

test("o servidor é a autoridade: 403 aos demais, carteira + internos ao Atendimento, editar/arquivar fechados", () => {
  const rota = semComentarios(readFileSync(new URL("../../../backend/app/api/routes/projetos.py", import.meta.url), "utf8"));
  assert.match(rota, /def create_projeto\([\s\S]*?require_permissao_ou_atendimento\("projetos\.criar"\)/);
  assert.match(rota, /def list_projetos\([\s\S]*?require_permissao_ou_atendimento\("projetos\.visualizar"\)/);
  assert.match(rota, /def get_projeto\([\s\S]*?require_permissao_ou_atendimento\("projetos\.visualizar"\)/);
  assert.match(rota, /def update_projeto\([\s\S]*?require_permissao\("projetos\.editar"\)/);
  assert.match(rota, /def arquivar_projeto\([\s\S]*?require_permissao\("projetos\.arquivar"\)/);
  assert.match(rota, /def restaurar_projeto\([\s\S]*?require_permissao\("projetos\.arquivar"\)/);
});
