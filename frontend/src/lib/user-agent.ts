// Parser leve de User-Agent — só o suficiente para navegador + sistema operacional.
// Roda 100% local (sem serviço externo), então a ordem dos testes importa: navegadores
// baseados em Chromium (Edge, Opera) incluem "Chrome" na string, então são checados antes.

const BROWSER_PATTERNS: { nome: string; regex: RegExp }[] = [
  { nome: "Edge", regex: /Edg\/([\d.]+)/ },
  { nome: "Opera", regex: /(OPR|Opera)\/([\d.]+)/ },
  { nome: "Chrome", regex: /Chrome\/([\d.]+)/ },
  { nome: "Firefox", regex: /Firefox\/([\d.]+)/ },
  { nome: "Safari", regex: /Version\/([\d.]+).*Safari/ },
];

const OS_PATTERNS: { nome: string; regex: RegExp }[] = [
  { nome: "Windows", regex: /Windows NT ([\d.]+)/ },
  { nome: "macOS", regex: /Mac OS X ([\d_.]+)/ },
  { nome: "iOS", regex: /(iPhone|iPad).*OS ([\d_]+)/ },
  { nome: "Android", regex: /Android ([\d.]+)/ },
  { nome: "Linux", regex: /Linux/ },
];

export function parseNavegador(userAgent: string | null | undefined): string {
  if (!userAgent) return "Desconhecido";
  const match = BROWSER_PATTERNS.find((pattern) => pattern.regex.test(userAgent));
  return match?.nome ?? "Desconhecido";
}

export function parseSistemaOperacional(userAgent: string | null | undefined): string {
  if (!userAgent) return "Desconhecido";
  const match = OS_PATTERNS.find((pattern) => pattern.regex.test(userAgent));
  return match?.nome ?? "Desconhecido";
}
