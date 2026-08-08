import { AlertOctagon, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function EstadoErro({
  mensagem = "Não foi possível carregar os dados desta visão.",
  onRetry,
}: {
  mensagem?: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-10 text-center dark:border-red-500/30 dark:bg-red-500/10">
      <AlertOctagon className="h-8 w-8 text-red-500" />
      <p className="max-w-sm text-sm text-red-600 dark:text-red-400">{mensagem}</p>
      <Button type="button" variant="secondary" onClick={onRetry} className="px-3 py-1.5 text-xs">
        <RotateCw className="h-3.5 w-3.5" />
        Tentar novamente
      </Button>
    </div>
  );
}
