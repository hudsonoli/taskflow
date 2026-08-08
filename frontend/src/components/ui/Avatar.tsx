import { User } from "lucide-react";
import { resolveCorIdentificacaoHex } from "@/lib/cores";

export function Avatar({
  nome,
  corIdentificacao,
  fotoUrl,
  className,
}: {
  nome: string;
  corIdentificacao: string;
  fotoUrl?: string;
  className: string;
}) {
  if (fotoUrl) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={fotoUrl} alt={nome} className={`${className} object-cover`} />;
  }
  return (
    <div
      className={`${className} flex items-center justify-center font-bold text-white`}
      style={{ backgroundColor: resolveCorIdentificacaoHex(corIdentificacao) }}
    >
      {nome.trim().slice(0, 1).toUpperCase() || <User className="h-4 w-4" />}
    </div>
  );
}
