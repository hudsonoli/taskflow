/**
 * Interpretação de datas puras (`"YYYY-MM-DD"`, sem hora nem fuso) como dia de calendário
 * local — nunca como instante UTC.
 *
 * `new Date("2026-08-20")` é interpretado pelo motor JS como meia-noite **UTC**. Formatado ou
 * comparado depois no fuso local do navegador (Brasil, UTC-3 ou mais atrasado), isso pode
 * exibir/posicionar o dia anterior (19/08). Datas puras do backend (`Demanda.dataFimPrevista`
 * e `dataInicio`, coluna `DATE`, sem fuso — decisão confirmada na Fase 2F.1) precisam ser
 * interpretadas como dia de calendário, não como instante — por isso os parsers abaixo
 * constroem a `Date` pelos componentes ano/mês/dia (que o motor JS sempre resolve no fuso
 * local do ambiente onde roda, nunca em UTC), em vez de `new Date(string)`.
 *
 * Não usar para campos que já são timestamp real (`prazoEtapaAtual`, `createdAt`,
 * `updatedAt`, `enviadoClienteEm` etc.) — esses continuam com `new Date(string)` normal,
 * porque a string já carrega instante e fuso (`...Z` ou offset).
 */

const FORMATO_DATA_PURA = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * Interpreta `"YYYY-MM-DD"` como 00:00 do dia de calendário local. `null` se o valor for
 * vazio ou não bater o formato — nunca lança, quem chama decide o fallback (mesmo padrão de
 * `resolverProjetoNome`/`resolverClienteNome` em lib/referencias.ts).
 */
export function parseDataLocal(valor: string | null | undefined): Date | null {
  if (!valor) return null;
  const match = FORMATO_DATA_PURA.exec(valor);
  if (!match) return null;

  const ano = Number(match[1]);
  const mes = Number(match[2]);
  const dia = Number(match[3]);
  const data = new Date(ano, mes - 1, dia, 0, 0, 0, 0);

  // `new Date(ano, mes, dia)` normaliza data inválida (ex.: 31/02 vira 03/03) rolando pro mês
  // seguinte em vez de falhar — conferir que os componentes voltaram exatamente iguais evita
  // aceitar isso em silêncio como se fosse a data pedida.
  if (data.getFullYear() !== ano || data.getMonth() !== mes - 1 || data.getDate() !== dia) {
    return null;
  }
  return data;
}

/**
 * Mesmo dia de `parseDataLocal`, mas às 23:59:59.999 do calendário local — fim do dia.
 *
 * Existe para comparações "dentro do prazo": uma previsão `"2026-08-20"` como data pura não
 * tem hora — o prazo dela só se esgota ao fim do dia 20, não à meia-noite que abre o dia.
 * Comparar um timestamp real (`updatedAt` etc.) contra `parseDataLocal` em vez desta função
 * classificaria erroneamente uma entrega feita de manhã no próprio dia como atrasada.
 */
export function fimDaDataLocal(valor: string | null | undefined): Date | null {
  const inicio = parseDataLocal(valor);
  if (!inicio) return null;
  return new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate(), 23, 59, 59, 999);
}
