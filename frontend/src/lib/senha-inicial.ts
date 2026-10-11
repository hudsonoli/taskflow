// Primeiro acesso (Fase 10B.1) — lógica PURA da troca obrigatória da senha temporária (testável com `node --test`).
//
// O Gestor entra em /e/<slug>/login com a senha TEMPORÁRIA e o servidor o obriga a trocá-la em /e/<slug>/trocar-senha-inicial. A tela pede SÓ a nova senha e a
// confirmação (a pessoa já se autenticou no passo anterior): nada de senha atual/temporária, token ou código. O backend revalida tudo (política, confirmação, e a
// nova senha não pode ser a temporária).

export const SENHA_MIN = 8;

export type ErrosTrocaInicial = { novaSenha?: string; confirmacaoSenha?: string };

/** Validação AMIGÁVEL no navegador (o servidor continua sendo a barreira). Vazio = sem erro. */
export function validarTrocaInicial(novaSenha: string, confirmacaoSenha: string): ErrosTrocaInicial {
  const erros: ErrosTrocaInicial = {};
  if (novaSenha.length < SENHA_MIN) erros.novaSenha = `A nova senha deve ter pelo menos ${SENHA_MIN} caracteres.`;
  if (confirmacaoSenha !== novaSenha) erros.confirmacaoSenha = "A confirmação não confere com a nova senha.";
  return erros;
}

/** Corpo ESTRITO enviado ao servidor: somente `novaSenha` e `confirmacaoSenha` — nunca senha atual/temporária. */
export function corpoDaTrocaInicial(novaSenha: string, confirmacaoSenha: string): { novaSenha: string; confirmacaoSenha: string } {
  return { novaSenha, confirmacaoSenha };
}

/** Rota da troca obrigatória de um tenant: `/e/<slug>/trocar-senha-inicial`. */
export function rotaDaTrocaInicial(slug: string): string {
  return `/e/${slug}/trocar-senha-inicial`;
}
