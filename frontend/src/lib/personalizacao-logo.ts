// Pré-validação do logo no navegador — SÓ conveniência (feedback imediato, sem ida ao servidor). A autoridade é
// o backend, que revalida tudo pelos bytes. Mesmas regras: PNG ou GIF, exatamente 320×132 px, até 2 MB.

export const LOGO_LARGURA = 320;
export const LOGO_ALTURA = 132;
export const LOGO_MAX_BYTES = 2 * 1024 * 1024;

const ASSINATURA_PNG = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];

function comeca(bytes: Uint8Array, prefixo: number[]): boolean {
  return prefixo.every((valor, i) => bytes[i] === valor);
}

/** Dimensões lidas dos bytes (PNG: IHDR · GIF: logical screen) — `null` se não for PNG/GIF. */
export function dimensoesDoLogo(bytes: Uint8Array): { tipo: "png" | "gif"; largura: number; altura: number } | null {
  if (bytes.length >= 24 && comeca(bytes, ASSINATURA_PNG)) {
    const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    return { tipo: "png", largura: v.getUint32(16), altura: v.getUint32(20) };
  }
  const cabecalho = String.fromCharCode(...bytes.slice(0, 6));
  if (bytes.length >= 10 && (cabecalho === "GIF87a" || cabecalho === "GIF89a")) {
    return { tipo: "gif", largura: bytes[6] | (bytes[7] << 8), altura: bytes[8] | (bytes[9] << 8) };
  }
  return null;
}

/** Mensagem de erro (pt-BR) ou `null` se o arquivo parece válido. */
export async function validarLogoNoNavegador(arquivo: File): Promise<string | null> {
  const nome = arquivo.name.toLowerCase();
  if (!/\.(png|gif)$/.test(nome)) return "Formato não permitido. Envie um arquivo PNG ou GIF.";
  if (arquivo.size === 0) return "O arquivo está vazio.";
  if (arquivo.size > LOGO_MAX_BYTES) return "O arquivo excede o limite de 2 MB.";
  const bytes = new Uint8Array(await arquivo.arrayBuffer());
  const dim = dimensoesDoLogo(bytes);
  if (!dim) return "O conteúdo do arquivo não é um PNG ou GIF válido.";
  if (dim.largura !== LOGO_LARGURA || dim.altura !== LOGO_ALTURA) {
    return `O logo deve ter exatamente ${LOGO_LARGURA}×${LOGO_ALTURA} px (o arquivo tem ${dim.largura}×${dim.altura} px).`;
  }
  return null;
}
