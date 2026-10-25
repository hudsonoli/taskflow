// Campo de DATA + HORA (P1_DATETIME_FIELD_UX): regras PURAS (testáveis com `node --test`). O contrato com os formulários NÃO muda: o valor é o MESMO que o `datetime-local` entregava —
// "YYYY-MM-DDTHH:MM" no relógio LOCAL, sem fuso (ou "" = sem valor). A conversão para o instante enviado à API continua em `lib/prazo-operacional.ts`; aqui nada converte fuso.

const RE_VALOR = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/;
const RE_DATA_BR = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
const RE_HORA = /^(\d{1,2}):(\d{2})$/;
const RE_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

const pad = (n: number, tamanho = 2) => String(n).padStart(tamanho, "0");

export const MENSAGEM_HORA_INVALIDA = "Informe um horário válido entre 00:00 e 23:59.";
export const MENSAGEM_DATA_INVALIDA = "Informe uma data válida (DD/MM/AAAA).";
export const MENSAGEM_DATA_OBRIGATORIA = "Informe a data.";
export const MENSAGEM_HORA_OBRIGATORIA = "Informe o horário.";

/** A data existe no calendário (31/02 não existe)? */
export function dataExiste(ano: number, mes: number, dia: number): boolean {
  if (ano < 1900 || ano > 2999 || mes < 1 || mes > 12 || dia < 1) return false;
  const d = new Date(ano, mes - 1, dia);
  return d.getFullYear() === ano && d.getMonth() === mes - 1 && d.getDate() === dia;
}

/** "21/10/2026" (ou "1/2/2026") → "2026-10-21"; qualquer outra coisa → `null`. Não adivinha datas sem barras ("21102026" é inválido). */
export function parseDataBr(texto: string): string | null {
  const m = RE_DATA_BR.exec(texto.trim());
  if (!m) return null;
  const [dia, mes, ano] = [Number(m[1]), Number(m[2]), Number(m[3])];
  return dataExiste(ano, mes, dia) ? `${pad(ano, 4)}-${pad(mes)}-${pad(dia)}` : null;
}

/** "2026-10-21" → "21/10/2026"; vazio/inválido → "". */
export function formatarDataBr(iso: string): string {
  const m = RE_ISO.exec(iso);
  return m && dataExiste(Number(m[1]), Number(m[2]), Number(m[3])) ? `${m[3]}/${m[2]}/${m[1]}` : "";
}

/** "05:49" (ou "5:49") → "05:49"; fora de 00:00–23:59, sem dois-pontos ("549") ou texto → `null`. Nunca converte entradas ambíguas. */
export function parseHora(texto: string): string | null {
  const m = RE_HORA.exec(texto.trim());
  if (!m) return null;
  const [h, min] = [Number(m[1]), Number(m[2])];
  return h <= 23 && min <= 59 ? `${pad(h)}:${pad(min)}` : null;
}

/** Só dígitos e ":" (colar "05:49 " ou digitar letras não quebra nada); no máximo 5 caracteres. */
export function sanitizarHora(texto: string): string {
  return texto.replace(/[^\d:]/g, "").slice(0, 5);
}

/** Só dígitos e "/" (no máximo 10 caracteres). */
export function sanitizarData(texto: string): string {
  return texto.replace(/[^\d/]/g, "").slice(0, 10);
}

export type PartesDoValor = { data: string; hora: string };

/** Valor do formulário ("YYYY-MM-DDTHH:MM") → data ISO + hora ("HH:MM"); vazio ou inválido → vazios. */
export function separarValor(valor: string | null | undefined): PartesDoValor {
  const m = valor ? RE_VALOR.exec(valor) : null;
  if (!m || !dataExiste(Number(m[1]), Number(m[2]), Number(m[3])) || Number(m[4]) > 23 || Number(m[5]) > 59) return { data: "", hora: "" };
  return { data: `${m[1]}-${m[2]}-${m[3]}`, hora: `${m[4]}:${m[5]}` };
}

/** Data ISO + hora → o valor do contrato ("YYYY-MM-DDTHH:MM"). Parcial (falta data ou hora) → `null`: nunca sai uma combinação inválida, nem um 00:00 inventado. */
export function combinarValor(dataIso: string, hora: string): string | null {
  return RE_ISO.test(dataIso) && /^\d{2}:\d{2}$/.test(hora) ? `${dataIso}T${hora}` : null;
}

export type EstadoDosTextos = {
  /** o que sobe para o formulário: o valor completo, "" (campo vazio e anulável) ou `undefined` (parcial/inválido: nada é emitido) */
  valor: string | undefined;
  erroData: string | null;
  erroHora: string | null;
};

/**
 * Interpreta os DOIS textos digitados. Durante a digitação não se bloqueia nada: só o que está completo e válido vira valor; os erros são devolvidos para quem decide QUANDO mostrá-los
 * (ao sair do campo ou no envio). `exigeHora`: data sem horário é pendência (a data não vira prazo sozinha).
 */
export function interpretarTextos(textoData: string, textoHora: string, opcoes: { exigeHora: boolean }): EstadoDosTextos {
  const dataVazia = textoData.trim() === "";
  const horaVazia = textoHora.trim() === "";
  if (dataVazia && horaVazia) return { valor: "", erroData: null, erroHora: null };

  const dataIso = dataVazia ? null : parseDataBr(textoData);
  const hora = horaVazia ? null : parseHora(textoHora);
  const erroData = dataVazia ? MENSAGEM_DATA_OBRIGATORIA : dataIso ? null : MENSAGEM_DATA_INVALIDA;
  const erroHora = horaVazia ? (opcoes.exigeHora ? MENSAGEM_HORA_OBRIGATORIA : null) : hora ? null : MENSAGEM_HORA_INVALIDA;
  const valor = dataIso && hora ? (combinarValor(dataIso, hora) ?? undefined) : undefined;
  return { valor, erroData, erroHora };
}

export type EstadoDaData = {
  /** o valor "YYYY-MM-DD" quando o texto é uma data completa e válida; "" quando está vazio, parcial ou inválido */
  valor: string;
  /** só existe quando há texto que NÃO é uma data válida (vazio não é erro: quem exige a data valida no envio) */
  erro: string | null;
};

/**
 * Campo só de DATA (`DateField`). Mesma semântica do `<input type="date">` nativo que ele substitui: data completa e válida → "YYYY-MM-DD"; vazio, parcial ou inválido → "" — os formulários
 * que já tratavam o valor nativo continuam funcionando sem mudança. Diferente do DateTimeField (que salva ao concluir), aqui nada é salvo por conta própria.
 */
export function interpretarData(texto: string): EstadoDaData {
  if (texto.trim() === "") return { valor: "", erro: null };
  const iso = parseDataBr(texto);
  return iso ? { valor: iso, erro: null } : { valor: "", erro: MENSAGEM_DATA_INVALIDA };
}

/** `min`/`max` ("YYYY-MM-DD", opcionais): o dia está fora do intervalo permitido? (ISO compara em ordem lexicográfica.) */
export function diaForaDoIntervalo(iso: string, min?: string, max?: string): boolean {
  return (Boolean(min) && iso < (min as string)) || (Boolean(max) && iso > (max as string));
}

// ── calendário ────────────────────────────────────────────────────────────────────────────────────────────────────

export function paraIso(data: Date): string {
  return `${pad(data.getFullYear(), 4)}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}`;
}

export function deIso(iso: string): Date | null {
  const m = RE_ISO.exec(iso);
  return m && dataExiste(Number(m[1]), Number(m[2]), Number(m[3])) ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}

export function somarDias(iso: string, dias: number): string {
  const base = deIso(iso) ?? new Date();
  base.setDate(base.getDate() + dias);
  return paraIso(base);
}

/** Soma meses mantendo o dia quando possível (31/01 + 1 mês → 28/02 ou 29/02), sem "pular" para março. */
export function somarMeses(iso: string, meses: number): string {
  const base = deIso(iso) ?? new Date();
  const dia = base.getDate();
  const alvo = new Date(base.getFullYear(), base.getMonth() + meses, 1);
  const ultimo = new Date(alvo.getFullYear(), alvo.getMonth() + 1, 0).getDate();
  alvo.setDate(Math.min(dia, ultimo));
  return paraIso(alvo);
}

export type DiaDaGrade = { iso: string; dia: number; doMes: boolean };

/** Grade mensal (semanas de domingo a sábado — o padrão pt-BR) com 5 ou 6 linhas: dias do mês anterior/seguinte completam as pontas. */
export function montarGrade(ano: number, mes: number): DiaDaGrade[][] {
  const primeiro = new Date(ano, mes - 1, 1);
  const inicio = new Date(ano, mes - 1, 1 - primeiro.getDay());
  const ultimo = new Date(ano, mes, 0);
  const total = Math.ceil((primeiro.getDay() + ultimo.getDate()) / 7);
  return Array.from({ length: total }, (_, semana) =>
    Array.from({ length: 7 }, (_, dow) => {
      const d = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + semana * 7 + dow);
      return { iso: paraIso(d), dia: d.getDate(), doMes: d.getMonth() === mes - 1 };
    }),
  );
}

export const ROTULOS_SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"] as const;
export const NOMES_DOS_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"] as const;
const NOMES_DOS_DIAS = ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"] as const;

/** "quinta-feira, 22 de outubro de 2026" — nome acessível de cada dia. */
export function rotuloDoDia(iso: string): string {
  const d = deIso(iso);
  return d ? `${NOMES_DOS_DIAS[d.getDay()]}, ${d.getDate()} de ${NOMES_DOS_MESES[d.getMonth()]} de ${d.getFullYear()}` : "";
}
