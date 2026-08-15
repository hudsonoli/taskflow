import { Construction } from "lucide-react";

/**
 * Estado vazio para recurso de Demanda que ainda não tem persistência (Fase 2E.1).
 *
 * A regra do contrato transitório: **nenhum controle de escrita é exibido para dado sem
 * persistência**. Não é campo desabilitado com valor fantasma — é affordance ausente com
 * explicação. Um formulário que aceita e descarta é pior que um formulário que não existe,
 * porque parece ter funcionado.
 *
 * A API devolve estas coleções vazias para os componentes não quebrarem, e recusa (422)
 * qualquer tentativa de gravá-las.
 */
export function RecursoIndisponivel({ recurso, fase }: { recurso: string; fase: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-zinc-200 bg-zinc-50/60 px-6 py-8 text-center dark:border-zinc-800 dark:bg-zinc-950/30">
      <Construction className="h-5 w-5 text-zinc-400" />
      <p className="text-sm font-medium text-zinc-700 dark:text-zinc-200">{recurso} ainda não disponível</p>
      <p className="max-w-sm text-xs leading-5 text-zinc-500 dark:text-zinc-400">
        Este recurso entra na {fase} da migração. Até lá não há onde gravar, então o campo não é oferecido — em vez de
        aceitar o conteúdo e perdê-lo.
      </p>
    </div>
  );
}
