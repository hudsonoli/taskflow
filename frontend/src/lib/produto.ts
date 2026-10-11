// Nome comercial do produto e título da aba (Fase 10A). Lógica pura (testável com `node --test`).
//
// O produto é "TaskFlow". No ambiente de uma empresa contratante a identidade PRINCIPAL é a da empresa (nome e logo); o produto é secundário e aparece
// no título da aba (`<Empresa> | TaskFlow`) e discretamente nas telas de acesso. A Gestão da plataforma e as telas neutras usam só o produto.

export const NOME_PRODUTO = "TaskFlow";

/** Título da aba: `<Empresa> | TaskFlow` quando há empresa (nome já vindo do servidor); senão só `TaskFlow`. Nunca um nome fixo de empresa. */
export function tituloDaPagina(nomeEmpresa: string | null | undefined): string {
  const nome = typeof nomeEmpresa === "string" ? nomeEmpresa.trim().replace(/\s+/g, " ").slice(0, 120) : "";
  return nome ? `${nome} | ${NOME_PRODUTO}` : NOME_PRODUTO;
}
