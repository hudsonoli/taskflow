// Funções PURAS da Central de Notificações e do Perfil (sem React/Next): rodam no `node --test`.

/** Badge: 0 → nada (esconde) · 1..99 → o número · >99 → "99+". */
export function formatarBadge(total: number): string | null {
  if (!Number.isFinite(total) || total <= 0) return null;
  return total > 99 ? "99+" : String(Math.floor(total));
}

/** Telefone BR para exibição (o backend guarda só dígitos, com "+" opcional). Fora do padrão → devolve como veio. */
export function formatarTelefone(valor: string | null | undefined): string {
  if (!valor) return "";
  const mais = valor.trim().startsWith("+");
  const digitos = valor.replace(/\D/g, "");
  let ddi = "";
  let nacional = digitos;
  if (mais && digitos.startsWith("55") && digitos.length >= 12) {
    ddi = "+55 ";
    nacional = digitos.slice(2);
  }
  if (nacional.length === 11) return `${ddi}(${nacional.slice(0, 2)}) ${nacional.slice(2, 7)}-${nacional.slice(7)}`;
  if (nacional.length === 10) return `${ddi}(${nacional.slice(0, 2)}) ${nacional.slice(2, 6)}-${nacional.slice(6)}`;
  return valor;
}

/** Máscara progressiva enquanto digita (DDD + número, 10 ou 11 dígitos); não impõe nada ao banco. */
export function mascararTelefoneDigitando(valor: string): string {
  const mais = valor.trim().startsWith("+");
  if (mais) return "+" + valor.replace(/\D/g, "").slice(0, 15);
  const d = valor.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

export const FOTO_MAX_BYTES = 5 * 1024 * 1024;

/** Pré-validação da foto no navegador (UX; o backend revalida pelos bytes). Mensagem de erro ou `null`. */
export function validarFotoNoNavegador(arquivo: { name: string; size: number; type: string }): string | null {
  if (!/\.(png|jpe?g)$/i.test(arquivo.name)) return "Formato não permitido. Envie uma imagem PNG ou JPG.";
  if (arquivo.type && !["image/png", "image/jpeg"].includes(arquivo.type)) return "Formato não permitido. Envie uma imagem PNG ou JPG.";
  if (arquivo.size === 0) return "O arquivo está vazio.";
  if (arquivo.size > FOTO_MAX_BYTES) return "A foto excede o limite de 5 MB.";
  return null;
}

/** A foto própria vem como caminho da API (`/usuarios/<id>/avatar?v=…`): passa pelo proxy autenticado do BFF.
 * URL externa (foto do Google) ou data URL de pré-visualização ficam como estão. */
export function srcDoAvatar(fotoUrl: string | null | undefined): string | null {
  if (!fotoUrl) return null;
  return fotoUrl.startsWith("/usuarios/") ? `/api/backend${fotoUrl}` : fotoUrl;
}

/** Iniciais para o fallback do avatar: 1ª letra do primeiro e do último nome. */
export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "";
  const primeira = partes[0][0];
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (primeira + ultima).toUpperCase();
}
