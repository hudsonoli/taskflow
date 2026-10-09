// Numeração configurável de tarefas (Fase 7D.1) — lógica PURA (testável com `node --test`).
//
// Espelho do formatter do servidor (`backend/app/core/numeracao_formato.py`) SÓ para a PRÉVIA em tempo real da tela. O identificador
// de uma tarefa é emitido e gravado pelo servidor na criação; nenhuma tarefa existente é (re)formatada aqui — a interface exibe
// `demanda.identificador`, nunca recalcula com a configuração atual. O servidor revalida tudo (esta validação é só UX).

export const PREFIXO_MAX = 16;
export const SEPARADOR_MAX = 4;
export const DIGITOS_MIN = 1;
export const DIGITOS_MAX = 10;
export const NUMERO_MAX = 2_147_483_647;

const CARACTERES_SEGUROS = /^[A-Za-z0-9#_./-]*$/;

export type FormatoNumeracao = {
  prefixo: string;
  separador: string;
  incluirAno: boolean;
  digitos: number;
};

export const FORMATO_PADRAO: FormatoNumeracao = { prefixo: "#", separador: "", incluirAno: false, digitos: 1 };

/** Mesma composição do servidor: PREFIXO SEP ANO SEP NÚMERO, sem separador duplicado. */
export function formatarIdentificador(formato: FormatoNumeracao, numero: number, ano: number): string {
  const partes: string[] = [];
  if (formato.prefixo) partes.push(formato.prefixo);
  if (formato.incluirAno) partes.push(String(ano));
  partes.push(String(numero).padStart(formato.digitos, "0"));
  let resultado = "";
  for (const parte of partes) {
    if (resultado && formato.separador && !resultado.endsWith(formato.separador)) resultado += formato.separador;
    resultado += parte;
  }
  return resultado;
}

/** Mensagem de erro do formato (UX imediata) ou `null` se válido. O servidor decide de verdade. */
export function validarFormato(formato: FormatoNumeracao): string | null {
  if (formato.prefixo.length > PREFIXO_MAX) return `O prefixo pode ter no máximo ${PREFIXO_MAX} caracteres.`;
  if (formato.separador.length > SEPARADOR_MAX) return `O separador pode ter no máximo ${SEPARADOR_MAX} caracteres.`;
  if (!CARACTERES_SEGUROS.test(formato.prefixo)) return "O prefixo aceita apenas letras, números e os símbolos # - _ . / (sem espaços).";
  if (!CARACTERES_SEGUROS.test(formato.separador)) return "O separador aceita apenas os símbolos # - _ . / (sem espaços).";
  if (!Number.isInteger(formato.digitos) || formato.digitos < DIGITOS_MIN || formato.digitos > DIGITOS_MAX) {
    return `A quantidade de dígitos deve ficar entre ${DIGITOS_MIN} e ${DIGITOS_MAX}.`;
  }
  if (!formato.prefixo && !formato.separador && !formato.incluirAno && formato.digitos === 1) {
    return "Informe um prefixo, inclua o ano ou use mais de 1 dígito.";
  }
  if (formato.prefixo && /\d$/.test(formato.prefixo) && !formato.separador) {
    return "Um prefixo que termina em número precisa de um separador (ex.: «-») para não confundir com o número da tarefa.";
  }
  return null;
}

/** Mínimo permitido para o próximo número: o maior já emitido + 1 (nunca reutilizar um número emitido). */
export function minimoProximoNumero(maiorNumeroEmitido: number | null): number {
  return (maiorNumeroEmitido ?? 0) + 1;
}

/** `null` se o próximo número é aceitável; senão a mensagem para o usuário. */
export function validarProximoNumero(proximoNumero: number, maiorNumeroEmitido: number | null): string | null {
  if (!Number.isInteger(proximoNumero) || proximoNumero < 1 || proximoNumero > NUMERO_MAX) {
    return `Informe um número inteiro entre 1 e ${NUMERO_MAX}.`;
  }
  const minimo = minimoProximoNumero(maiorNumeroEmitido);
  if (proximoNumero < minimo) {
    return `O próximo número precisa ser pelo menos ${minimo}: já existem tarefas até o número ${maiorNumeroEmitido}.`;
  }
  return null;
}

export type CampoConfiguracaoNumeracao = FormatoNumeracao & { proximoNumero: number };

/** Corpo do PATCH só com o que mudou (campo omitido = não muda). Nunca envia `reinicioAnual` nem `empresaId`. */
export function diferencaParaPatch(
  atual: CampoConfiguracaoNumeracao,
  editado: CampoConfiguracaoNumeracao,
): Partial<CampoConfiguracaoNumeracao> {
  const corpo: Partial<CampoConfiguracaoNumeracao> = {};
  if (editado.prefixo !== atual.prefixo) corpo.prefixo = editado.prefixo;
  if (editado.separador !== atual.separador) corpo.separador = editado.separador;
  if (editado.incluirAno !== atual.incluirAno) corpo.incluirAno = editado.incluirAno;
  if (editado.digitos !== atual.digitos) corpo.digitos = editado.digitos;
  if (editado.proximoNumero !== atual.proximoNumero) corpo.proximoNumero = editado.proximoNumero;
  return corpo;
}

/** Mudanças que merecem confirmação: a consequência (só novas tarefas) fica explícita. */
export function exigeConfirmacao(patch: Partial<CampoConfiguracaoNumeracao>): boolean {
  return patch.proximoNumero !== undefined;
}
