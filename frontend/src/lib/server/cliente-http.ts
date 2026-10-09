// IP, região e User-Agent REAIS do cliente, repassados do BFF (Next.js) à API no login (Fases 7E/7E.2). Lógica PURA (testável com `node --test`).
//
// Cadeia: visitante → Cloudflare → Nginx Proxy Manager → BFF → API. O login da interface passa pelo servidor Next.js, que chama a API; sem
// este repasse a API enxergaria só o IP do container do BFF e o User-Agent do Node (auditoria com IP interno e "Desconhecido").
//
// Fonte de cada dado:
// - IP: `CF-Connecting-IP` (a Cloudflare o sobrescreve na borda; o `X-Real-IP` do proxy da origem traz o IP da BORDA, não o do visitante).
//   Sem Cloudflare na frente, cai em `X-Real-IP` e, por último, no ÚLTIMO item do `X-Forwarded-For` (o primeiro é do cliente);
// - região: `CF-IPCity`, `CF-Region`, `CF-Region-Code` e `CF-IPCountry` (Managed Transform "Add visitor location headers" da Cloudflare);
// - navegador/SO: o `User-Agent` do navegador.
//
// O BFF NÃO encaminha `CF-*` do navegador como estão: valida, decodifica e envia à API só cabeçalhos INTERNOS controlados
// (`X-Taskflow-*`, valores em percent-encoding — transporte ASCII). Latitude, longitude, CEP e fuso nunca são lidos. A API só confia
// nesses cabeçalhos quando o peer imediato é um proxy confiável (TRUSTED_PROXY_CIDRS) e os ignora de qualquer outra origem.
import { isIP } from "node:net";

const LIMITE_USER_AGENT = 512;
const LIMITE_TEXTO = 80;

export const CABECALHO_IP = "X-Taskflow-Client-IP";
export const CABECALHO_CIDADE = "X-Taskflow-CF-City";
export const CABECALHO_REGIAO = "X-Taskflow-CF-Region";
export const CABECALHO_CODIGO_REGIAO = "X-Taskflow-CF-Region-Code";
export const CABECALHO_PAIS = "X-Taskflow-CF-Country";

type Cabecalhos = Pick<Headers, "get">;

function ipValido(valor: string | null | undefined): string | null {
  if (!valor) return null;
  const candidato = valor.trim();
  return candidato.length > 0 && candidato.length <= 64 && isIP(candidato) !== 0 ? candidato : null;
}

/** IP do cliente: `CF-Connecting-IP` (UM IP válido; lista ou texto → descartado) > `X-Real-IP` > ÚLTIMO item do `X-Forwarded-For`. */
export function ipDoCliente(cabecalhos: Cabecalhos): string | null {
  const cloudflare = ipValido(cabecalhos.get("cf-connecting-ip"));
  if (cloudflare) return cloudflare;
  const real = ipValido(cabecalhos.get("x-real-ip"));
  if (real) return real;
  const encaminhado = cabecalhos.get("x-forwarded-for");
  if (!encaminhado) return null;
  const itens = encaminhado.split(",");
  return ipValido(itens[itens.length - 1]);
}

/**
 * Texto de localização limpo, ou `null`. O Node lê os bytes do cabeçalho como latin1: um UTF-8 cru ("BrasÃ­lia") é reinterpretado como
 * UTF-8; percent-encoding é decodificado. Sem caracteres de controle nem `<>`, espaços colapsados, limitado.
 */
export function textoDeLocalizacao(bruto: string | null | undefined): string | null {
  if (!bruto) return null;
  let texto = bruto.trim();
  try {
    texto = decodeURIComponent(texto);
  } catch {
    // não era percent-encoding válido: segue com o texto como veio
  }
  if (/[\u0080-\u00ff]/.test(texto) && !/[^\u0000-\u00ff]/.test(texto)) {
    const reinterpretado = Buffer.from(texto, "latin1").toString("utf8");
    if (!reinterpretado.includes("\ufffd")) texto = reinterpretado; // UTF-8 que o Node leu como latin1
  }
  texto = texto.replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029<>]/g, " ").replace(/\s+/g, " ").trim();
  return texto.length > 0 ? texto.slice(0, LIMITE_TEXTO) : null;
}

function codigoDePais(bruto: string | null | undefined): string | null {
  const texto = textoDeLocalizacao(bruto);
  return texto && /^[A-Za-z]{2}$/.test(texto) ? texto.toUpperCase() : null;
}

function codigoDeRegiao(bruto: string | null | undefined): string | null {
  const texto = textoDeLocalizacao(bruto);
  return texto && /^[A-Za-z0-9-]{1,6}$/.test(texto) ? texto.toUpperCase() : null;
}

/** Cabeçalhos internos a enviar à API no login: IP, localização aprovada (só cidade, região, código da região e país) e User-Agent. */
export function cabecalhosDoCliente(cabecalhos: Cabecalhos): Record<string, string> {
  const resultado: Record<string, string> = {};
  const ip = ipDoCliente(cabecalhos);
  if (ip) resultado[CABECALHO_IP] = ip;

  const localizacao: Array<[string, string | null]> = [
    [CABECALHO_CIDADE, textoDeLocalizacao(cabecalhos.get("cf-ipcity"))],
    [CABECALHO_REGIAO, textoDeLocalizacao(cabecalhos.get("cf-region"))],
    [CABECALHO_CODIGO_REGIAO, codigoDeRegiao(cabecalhos.get("cf-region-code"))],
    [CABECALHO_PAIS, codigoDePais(cabecalhos.get("cf-ipcountry"))],
  ];
  for (const [nome, valor] of localizacao) {
    if (valor) resultado[nome] = encodeURIComponent(valor); // ASCII: seguro como valor de cabeçalho (acentos, ç etc.)
  }

  const userAgent = cabecalhos.get("user-agent")?.trim();
  if (userAgent) resultado["User-Agent"] = userAgent.slice(0, LIMITE_USER_AGENT);
  return resultado;
}
