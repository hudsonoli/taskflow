import { EmpresaIndisponivelView } from "@/components/auth/EmpresaIndisponivelView";
import { LoginView } from "@/components/auth/LoginView";
import { GOOGLE_OAUTH_CLIENT_ID } from "@/lib/server/backend";
import { motivoDoLogin, proximoSeguro } from "@/lib/sessao-expirada";
import { empresaDisponivelDaRota } from "@/lib/server/tenant-pagina";

// Por requisição: a marca e o client_id do Google vêm do servidor em runtime (não ficam congelados no build).
export const dynamic = "force-dynamic";

export default async function EmpresaLoginPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ reason?: string | string[]; next?: string | string[] }>;
}) {
  const empresa = await empresaDisponivelDaRota((await params).slug);
  if (!empresa) return <EmpresaIndisponivelView />;
  const consulta = await searchParams;
  // `reason` só liga o aviso (valor conhecido, nunca ecoado); `next` só passa se for caminho interno do PRÓPRIO tenant.
  const sessaoExpirada = motivoDoLogin(consulta.reason) !== null;
  const proximo = proximoSeguro(Array.isArray(consulta.next) ? consulta.next[0] : consulta.next, empresa.slug);
  return (
    <LoginView googleClientId={GOOGLE_OAUTH_CLIENT_ID} slug={empresa.slug} nomeEmpresa={empresa.nome} sessaoExpirada={sessaoExpirada} proximo={proximo} />
  );
}
