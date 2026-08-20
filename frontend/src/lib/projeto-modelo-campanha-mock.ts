/**
 * Mock isolado do Modelo de Campanha de Projeto — TipoTarefa ainda não tem tabela própria no
 * backend, então o formulário de Projeto (`ProjetoFormSections.tsx`) continua lendo esta lista
 * fixa ao montar/editar itens do backlog de campanha.
 *
 * Extraído de `legacy-referencias-mock.ts` na Fase 2E.5F junto com `workflowsProjetoDisponiveis`
 * (removido na Fase 2G.1, quando `ProjetoFormSections` passou a consumir
 * `/workflow-modelos/diretorio`, real). Este arquivo sai quando TipoTarefa ganhar tabela real
 * (Fase 2G.2).
 */

export const tiposTarefaProjetoDisponiveis = [
  { id: "tipo-post", nome: "Post social" },
  { id: "tipo-landing-page", nome: "Landing page" },
  { id: "tipo-email", nome: "E-mail marketing" },
  { id: "tipo-anuncio", nome: "Anúncio" },
  { id: "tipo-relatorio", nome: "Relatório" },
];
