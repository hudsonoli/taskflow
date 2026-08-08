import type { DocumentoTipo } from "@/types/cliente";

/**
 * Consulta de dados por CPF/CNPJ — **stub**, sem integração real.
 *
 * O fluxo de cadastro de cliente previsto (ver CLAUDE.md) é: documento → validação → busca
 * automática → cadastro completo. A busca automática depende de integração externa
 * (Receita Federal ou serviço equivalente), que é trabalho de fase futura.
 *
 * Até lá esta função devolve um nome derivado do próprio documento, só para o formulário
 * ter o que preencher. Vive fora dos mocks de propósito: quando a integração existir, é
 * este arquivo que passa a fazer a chamada real, sem que nenhum componente mude.
 */
export function buscarDadosPorDocumento(
  documento: string,
  tipo: DocumentoTipo,
): { nome: string; razaoSocial: string } {
  const digits = documento.replace(/\D/g, "");
  const sufixo = digits.slice(-4) || "0000";

  if (tipo === "cpf") {
    return { nome: `Cliente ${sufixo}`, razaoSocial: `Cliente ${sufixo}` };
  }
  return { nome: `Empresa ${sufixo}`, razaoSocial: `Empresa ${sufixo} Ltda` };
}
