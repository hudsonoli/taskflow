// Erro de domínio ao abrir sessão de trabalho: carrega o `code` estável do backend (409 SESSAO_ATIVA_EXISTENTE etc.) para a UI decidir o tratamento SEM depender do
// texto. O backend segue sendo a autoridade — o frontend só traduz.

export const CODIGO_SESSAO_ATIVA_EXISTENTE = "SESSAO_ATIVA_EXISTENTE";

export class SessaoTrabalhoErro extends Error {
  readonly codigo: string | null;
  readonly status: number;

  constructor(mensagem: string, { codigo = null, status = 0 }: { codigo?: string | null; status?: number } = {}) {
    super(mensagem);
    this.name = "SessaoTrabalhoErro";
    this.codigo = codigo;
    this.status = status;
  }
}
