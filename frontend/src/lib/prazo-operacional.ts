// Prazo operacional (`prazoEtapaAtual`) — conversões PURAS entre o campo `datetime-local` do navegador e o instante enviado à API.
//
// - `prazoEtapaAtual` é um INSTANTE (DateTime com fuso). O campo `datetime-local` traz "2026-10-15T16:30" SEM fuso, no relógio do
//   navegador. O backend lê data/hora sem deslocamento como UTC, então o cliente SEMPRE converte para ISO com `Z` ao enviar
//   (16:30 em São Paulo vira 19:30Z) e, ao exibir/editar, converte de volta para o relógio local.
// - `dataFimPrevista` é uma DATA de planejamento (sem hora): é o dia LOCAL escolhido, nunca o dia do instante em UTC
//   (22:30 em São Paulo já é dia seguinte em UTC, mas o dia planejado continua o escolhido).
const RE_LOCAL = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/;

function partes(valor: string): [number, number, number, number, number] | null {
  const m = RE_LOCAL.exec(valor);
  if (!m) return null;
  const [ano, mes, dia, hora, minuto] = [Number(m[1]), Number(m[2]), Number(m[3]), Number(m[4]), Number(m[5])];
  const data = new Date(ano, mes - 1, dia, hora, minuto, 0, 0);
  const existe =
    data.getFullYear() === ano && data.getMonth() === mes - 1 && data.getDate() === dia && data.getHours() === hora && data.getMinutes() === minuto;
  return existe ? [ano, mes, dia, hora, minuto] : null;
}

/** `datetime-local` ("2026-10-15T16:30", relógio local) → ISO com `Z` para a API; vazio ou inválido → `null`. */
export function inputLocalParaIso(valor: string | null | undefined): string | null {
  if (!valor) return null;
  const p = partes(valor);
  if (!p) return null;
  return new Date(p[0], p[1] - 1, p[2], p[3], p[4], 0, 0).toISOString();
}

/** Dia LOCAL escolhido no `datetime-local` ("2026-10-15"), para `dataFimPrevista`; vazio ou inválido → `""`. */
export function dataDoInputLocal(valor: string | null | undefined): string {
  if (!valor) return "";
  const p = partes(valor);
  return p ? valor.slice(0, 10) : "";
}

/** ISO/instante vindo da API → valor para `datetime-local` no relógio local; vazio ou inválido → `""`. */
export function isoParaInputLocal(iso: string | null | undefined): string {
  if (!iso) return "";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}T${pad(data.getHours())}:${pad(data.getMinutes())}`;
}
