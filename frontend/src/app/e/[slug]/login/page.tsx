import { EmpresaIndisponivelView } from "@/components/auth/EmpresaIndisponivelView";
import { LoginView } from "@/components/auth/LoginView";
import { GOOGLE_OAUTH_CLIENT_ID } from "@/lib/server/backend";
import { empresaDisponivelDaRota } from "@/lib/server/tenant-pagina";

// Por requisição: a marca e o client_id do Google vêm do servidor em runtime (não ficam congelados no build).
export const dynamic = "force-dynamic";

export default async function EmpresaLoginPage({ params }: { params: Promise<{ slug: string }> }) {
  const empresa = await empresaDisponivelDaRota((await params).slug);
  if (!empresa) return <EmpresaIndisponivelView />;
  return <LoginView googleClientId={GOOGLE_OAUTH_CLIENT_ID} slug={empresa.slug} nomeEmpresa={empresa.nome} />;
}
