import { LoginView } from "@/components/auth/LoginView";
import { GOOGLE_OAUTH_CLIENT_ID } from "@/lib/server/backend";

// Força renderização por requisição: sem isso, a página (sem dado dinâmico nenhum) seria
// pré-renderizada estática em build time, fixando GOOGLE_OAUTH_CLIENT_ID no bundle — o
// mesmo problema que NEXT_PUBLIC_* teria. Com `force-dynamic`, trocar a variável de
// ambiente do container é o suficiente, sem rebuild.
export const dynamic = "force-dynamic";

export default function LoginPage() {
  return <LoginView googleClientId={GOOGLE_OAUTH_CLIENT_ID} />;
}
