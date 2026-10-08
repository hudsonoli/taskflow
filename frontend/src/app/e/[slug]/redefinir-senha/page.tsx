import { EmpresaIndisponivelView } from "@/components/auth/EmpresaIndisponivelView";
import { RedefinirSenhaView } from "@/components/auth/RedefinirSenhaView";
import { empresaDisponivelDaRota } from "@/lib/server/tenant-pagina";

export const dynamic = "force-dynamic";

export default async function EmpresaRedefinirSenhaPage({ params }: { params: Promise<{ slug: string }> }) {
  const empresa = await empresaDisponivelDaRota((await params).slug);
  if (!empresa) return <EmpresaIndisponivelView />;
  return <RedefinirSenhaView slug={empresa.slug} />;
}
