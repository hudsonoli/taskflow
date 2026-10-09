// IP e User-Agent REAIS do cliente, repassados do BFF (Next.js) à API no login (Fase 7E). Lógica PURA (testável com `node --test`).
//
// Por que existe: o login da interface passa pelo servidor Next.js, que chama a API. Sem este repasse, a API enxerga só o IP do
// container do BFF (ex.: 172.18.0.4) e o User-Agent do próprio Node — a auditoria de acesso ficava com IP interno e
// "Desconhecido". O Nginx Proxy Manager à frente do BFF define `X-Real-IP` ($remote_addr: o par real da conexão, que ele
// SOBRESCREVE) e acrescenta o par ao `X-Forwarded-For`. O BFF só é alcançável por esse proxy (não publica porta), então esses
// cabeçalhos são os do proxy.
//
// A API NÃO confia cegamente no que recebe: só aceita `X-Forwarded-For` de um proxy confiável (a rede do BFF) e valida o IP
// (ver backend/app/core/cliente_ip.py). Aqui, só se repassa um IP VÁLIDO; texto arbitrário nunca segue adiante.
import { isIP } from "node:net";

const LIMITE_USER_AGENT = 512;

function ipValido(valor: string | null | undefined): string | null {
  if (!valor) return null;
  const candidato = valor.trim();
  return candidato.length > 0 && candidato.length <= 64 && isIP(candidato) !== 0 ? candidato : null;
}

/** IP do cliente a partir dos cabeçalhos do proxy: `X-Real-IP` (definido pelo proxy) ou o ÚLTIMO item do `X-Forwarded-For`
 *  (o que o próprio proxy acrescentou — o primeiro é controlado pelo cliente). `null` se nada válido. */
export function ipDoCliente(cabecalhos: Pick<Headers, "get">): string | null {
  const real = ipValido(cabecalhos.get("x-real-ip"));
  if (real) return real;
  const encaminhado = cabecalhos.get("x-forwarded-for");
  if (!encaminhado) return null;
  const itens = encaminhado.split(",");
  return ipValido(itens[itens.length - 1]);
}

/** Cabeçalhos a enviar à API no login: `X-Forwarded-For` (só se houver IP válido) e o `User-Agent` do navegador. */
export function cabecalhosDoCliente(cabecalhos: Pick<Headers, "get">): Record<string, string> {
  const resultado: Record<string, string> = {};
  const ip = ipDoCliente(cabecalhos);
  if (ip) resultado["X-Forwarded-For"] = ip;
  const userAgent = cabecalhos.get("user-agent")?.trim();
  if (userAgent) resultado["User-Agent"] = userAgent.slice(0, LIMITE_USER_AGENT);
  return resultado;
}
