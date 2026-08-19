/**
 * Mock isolado do Modelo de Campanha de Projeto — TipoTarefa e Workflow ainda não têm tabela
 * própria no backend, então o formulário de Projeto (`ProjetoFormSections.tsx`) continua
 * lendo essas duas listas fixas ao montar/editar itens do backlog de campanha.
 *
 * Extraído de `legacy-referencias-mock.ts` na Fase 2E.5F: aquele arquivo reunia as bridges de
 * Cliente/Departamento/Usuário/Projeto (todas migradas para diretório real) e esses dois mocks,
 * que não são bridge nenhuma — são mock legítimo de um domínio ainda não migrado. Sai daqui
 * quando TipoTarefa e Workflow ganharem tabela real.
 */

export const tiposTarefaProjetoDisponiveis = [
  { id: "tipo-post", nome: "Post social" },
  { id: "tipo-landing-page", nome: "Landing page" },
  { id: "tipo-email", nome: "E-mail marketing" },
  { id: "tipo-anuncio", nome: "Anúncio" },
  { id: "tipo-relatorio", nome: "Relatório" },
];

export const workflowsProjetoDisponiveis = [
  { id: "workflow-criacao", nome: "Criação padrão" },
  { id: "workflow-midia", nome: "Mídia paga" },
  { id: "workflow-conteudo", nome: "Conteúdo e revisão" },
];
