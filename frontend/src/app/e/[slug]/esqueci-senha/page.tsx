import { EmpresaIndisponivelView } from "@/components/auth/EmpresaIndisponivelView";
import { EsqueciSenhaView } from "@/components/auth/EsqueciSenhaView";
import { empresaDisponivelDaRota } from "@/lib/server/tenant-pagina";

export const dynamic = "force-dynamic";

export default async function EmpresaEsqueciSenhaPage({ params }: { params: Promise<{ slug: string }> }) {
  const empresa = await empresaDisponivelDaRota((await params).slug);
  if (!empresa) return <EmpresaIndisponivelView />;
  return <EsqueciSenhaView slug={empresa.slug} />;
}
