import type { Metadata } from "next";
import { LoginForm } from "@/components/auth/LoginForm";
import { Card } from "@/components/ui/Card";

export const metadata: Metadata = {
  title: "Entrar | TaskFloww",
};

type LoginPageProps = {
  searchParams: Promise<{
    returnTo?: string | string[];
  }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const returnTo = typeof params.returnTo === "string" ? params.returnTo : null;

  return (
    <div className="fixed inset-0 z-[100] overflow-y-auto bg-[#f4f1ec] px-4 py-10">
      <div className="mx-auto flex min-h-full w-full max-w-md items-center">
        <div className="w-full space-y-6">
          <div className="flex flex-col items-center text-center">
            <div
              className="flex h-12 w-12 items-center justify-center rounded-2xl bg-zinc-900 text-lg font-bold text-white shadow-sm"
              aria-hidden="true"
            >
              T
            </div>
            <h1 className="mt-4 text-2xl font-semibold tracking-tight text-zinc-900">
              Entre no TaskFloww
            </h1>
            <p className="mt-1 text-sm text-zinc-500">
              Acesse sua operação com e-mail e senha.
            </p>
          </div>

          <Card>
            <LoginForm returnTo={returnTo} />
          </Card>
        </div>
      </div>
    </div>
  );
}
