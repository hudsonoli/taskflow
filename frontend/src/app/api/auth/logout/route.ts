import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { PLATFORM_COOKIE_NAME, PLATFORM_COOKIE_PATH, SESSION_COOKIE_NAME } from "@/lib/server/backend";
import { COOKIE_TEMA } from "@/lib/tema";
import { COOKIE_TENANT_SLUG } from "@/lib/tenant";

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE_NAME);
  // Sair encerra TAMBÉM a sessão de plataforma (cookie de caminho próprio).
  cookieStore.delete({ name: PLATFORM_COOKIE_NAME, path: PLATFORM_COOKIE_PATH });
  // A preferência pessoal NUNCA sobrevive ao logout (nem aparece na tela pública, nem no próximo login).
  cookieStore.delete(COOKIE_TEMA);
  // O contexto visual de empresa também não sobrevive ao logout (o cliente já guardou para onde voltar).
  cookieStore.delete(COOKIE_TENANT_SLUG);
  return NextResponse.json({ ok: true });
}
