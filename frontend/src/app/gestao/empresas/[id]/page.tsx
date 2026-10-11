import { EmpresaPlataformaView } from "@/components/plataforma/EmpresaPlataformaView";

export default async function PlataformaEmpresaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EmpresaPlataformaView empresaId={id} />;
}
