import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE_NAME } from "@/lib/server/backend";
import { COOKIE_TEMA } from "@/lib/tema";

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE_NAME);
  // A preferência pessoal NUNCA sobrevive ao logout (nem aparece na tela pública, nem no próximo login).
  cookieStore.delete(COOKIE_TEMA);
  return NextResponse.json({ ok: true });
}
