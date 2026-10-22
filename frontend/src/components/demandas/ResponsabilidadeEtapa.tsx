import { Building2, UserRound } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { ROTULO_ORIGEM, type ResponsabilidadeExibida } from "@/lib/responsabilidade-etapa";

/**
 * Quem executa a etapa, num relance: Departamento, Responsável(is) e DE ONDE vem (definido na etapa, herdado da tarefa ou ninguém). Exibe a resolução do servidor — não
 * decide nada. Herdado aparece como herdado: nunca como se a pessoa estivesse gravada na etapa.
 */
export function ResponsabilidadeEtapa({
  responsabilidade,
  nomeDoUsuario,
  nomeDoDepartamento,
}: {
  responsabilidade: ResponsabilidadeExibida;
  nomeDoUsuario: (id: string) => string;
  nomeDoDepartamento: (id: string) => string;
}) {
  const { origem, usuarioIds, departamentoIds } = responsabilidade;
  const usuarios = usuarioIds.map(nomeDoUsuario);
  const departamentos = departamentoIds.map(nomeDoDepartamento);

  if (origem === "nenhuma") {
    return (
      <p data-origem="nenhuma" className="mt-1 text-xs italic text-amber-700 dark:text-amber-400">
        Responsável ainda não definido
      </p>
    );
  }

  return (
    <div data-origem={origem} className="mt-1.5 flex flex-col gap-1 text-xs text-fg-muted">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={origem === "etapa" ? "blue" : "neutral"}>{ROTULO_ORIGEM[origem]}</Badge>
      </div>
      {departamentos.length > 0 && (
        <p className="flex items-center gap-1.5">
          <Building2 className="h-3.5 w-3.5 shrink-0" aria-hidden />
          <span>
            <span className="font-semibold text-fg-subtle">{departamentos.length > 1 ? "Departamentos" : "Departamento"}:</span> {departamentos.join(", ")}
          </span>
        </p>
      )}
      {usuarios.length > 0 && (
        <p className="flex items-center gap-1.5">
          <UserRound className="h-3.5 w-3.5 shrink-0" aria-hidden />
          <span>
            <span className="font-semibold text-fg-subtle">{usuarios.length > 1 ? "Responsáveis" : "Responsável"}:</span> {usuarios.join(", ")}
          </span>
        </p>
      )}
    </div>
  );
}
