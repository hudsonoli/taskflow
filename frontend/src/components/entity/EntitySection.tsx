import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { entityFormNavTabId, entitySectionPanelId } from "./entityFormIds";

export type EntitySectionProps = {
  id: string;
  title?: string;
  description?: string;
  icon?: LucideIcon;
  children: ReactNode;
};

/**
 * Envelope de uma seção do formulário (título/descrição/ícone opcionais +
 * conteúdo). Não controla navegação global do formulário — quem decide qual
 * EntitySection está visível é a página, via EntityFormNav.onSectionChange
 * (entity-component-api.md, seção 7). id deve corresponder ao id usado em
 * EntityFormNavSection para que os atributos ARIA (tab/tabpanel) se conectem.
 */
export function EntitySection({ id, title, description, icon: Icon, children }: EntitySectionProps) {
  return (
    <section
      id={entitySectionPanelId(id)}
      role="tabpanel"
      aria-labelledby={entityFormNavTabId(id)}
      tabIndex={0}
      className="min-h-0 min-w-0 flex-1 overflow-y-auto px-4 py-3 focus-visible:outline-none"
    >
      {(title || description) && (
        <div className="mb-4">
          {title && (
            <div className="flex items-center gap-2">
              {Icon && (
                <Icon className="h-4 w-4 text-zinc-400" strokeWidth={2} aria-hidden="true" />
              )}
              <h3 className="text-sm font-semibold text-zinc-900">{title}</h3>
            </div>
          )}

          {description && <p className="mt-1 text-sm text-zinc-500">{description}</p>}
        </div>
      )}

      {children}
    </section>
  );
}
