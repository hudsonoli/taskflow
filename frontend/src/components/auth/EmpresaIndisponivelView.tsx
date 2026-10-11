import { BrandLogo } from "@/components/branding/BrandLogo";

/**
 * Slug inexistente, reservado, malformado ou de empresa inativa: UMA mensagem só, sem dizer qual dos casos (não
 * enumera empresas nem revela situação interna). A identidade é a neutra do TaskFlow (o layout já usa os padrões).
 */
export function EmpresaIndisponivelView() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 text-center shadow-sm">
        <div className="mb-4 flex justify-center">
          <BrandLogo variant="auth" />
        </div>
        <h1 className="text-lg font-semibold tracking-tight text-fg">Empresa não encontrada ou indisponível</h1>
        <p className="mt-2 text-sm text-fg-muted">
          Confira o endereço de acesso que a sua empresa informou. Se o problema continuar, fale com quem administra o
          TaskFlow na sua empresa.
        </p>
      </div>
    </div>
  );
}
