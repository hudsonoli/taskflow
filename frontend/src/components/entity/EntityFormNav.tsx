"use client";

import type { LucideIcon } from "lucide-react";
import { useRef, type KeyboardEvent } from "react";
import { Tabs } from "@/components/ui/Tabs";
import { entityFormNavTabId, entitySectionPanelId } from "./entityFormIds";

export type EntitySectionStatus = "default" | "warning" | "error";
export type EntitySectionsStatusMap = Record<string, EntitySectionStatus>;

export type EntityFormNavSection = {
  id: string;
  label: string;
  icon?: LucideIcon;
};

export type EntityFormNavProps = {
  sections: EntityFormNavSection[];
  activeSection: string;
  onSectionChange: (id: string) => void;
  sectionsStatus?: EntitySectionsStatusMap;
};

const statusDotClassNames: Record<EntitySectionStatus, string> = {
  default: "",
  warning: "bg-amber-500",
  error: "bg-red-500",
};

/**
 * Menu de navegação entre seções de um EntityForm em modo edit — substitui
 * Tabs horizontais nesse contexto específico (entity-component-api.md, seção 6).
 * No mobile, reaproveita o componente Tabs já existente (ui/Tabs.tsx) em vez
 * de reimplementar o mesmo padrão de pílula ativa/inativa.
 */
export function EntityFormNav({
  sections,
  activeSection,
  onSectionChange,
  sectionsStatus,
}: EntityFormNavProps) {
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null;

    if (event.key === "ArrowDown" || event.key === "ArrowRight") {
      nextIndex = (index + 1) % sections.length;
    } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
      nextIndex = (index - 1 + sections.length) % sections.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = sections.length - 1;
    }

    if (nextIndex === null) return;

    event.preventDefault();
    onSectionChange(sections[nextIndex].id);
    itemRefs.current[nextIndex]?.focus();
  }

  return (
    <>
      <div className="shrink-0 md:hidden">
        <Tabs
          tabs={sections.map((section) => ({ id: section.id, label: section.label }))}
          activeTab={activeSection}
          onChange={onSectionChange}
          density="compact"
        />
      </div>

      <nav
        role="tablist"
        aria-orientation="vertical"
        aria-label="Seções do formulário"
        className="hidden shrink-0 flex-col gap-0.5 overflow-y-auto border-r border-zinc-100 p-2 md:flex md:w-44"
      >
        {sections.map((section, index) => {
          const active = section.id === activeSection;
          const status = sectionsStatus?.[section.id] ?? "default";
          const Icon = section.icon;

          return (
            <button
              key={section.id}
              ref={(element) => {
                itemRefs.current[index] = element;
              }}
              type="button"
              id={entityFormNavTabId(section.id)}
              role="tab"
              aria-selected={active}
              aria-current={active ? "page" : undefined}
              aria-controls={entitySectionPanelId(section.id)}
              tabIndex={active ? 0 : -1}
              onClick={() => onSectionChange(section.id)}
              onKeyDown={(event) => handleKeyDown(event, index)}
              className={`group relative flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[11px] font-normal transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 ${
                active
                  ? "bg-primary-soft text-text"
                  : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              {active && (
                <span
                  className="absolute left-0 h-4 w-0.5 rounded-r-full bg-primary"
                  aria-hidden="true"
                />
              )}

              {Icon && <Icon className="h-4 w-4 shrink-0" strokeWidth={2} aria-hidden="true" />}
              <span className="min-w-0 flex-1 truncate">{section.label}</span>
              {status !== "default" && (
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${statusDotClassNames[status]}`}
                  aria-hidden="true"
                />
              )}
            </button>
          );
        })}
      </nav>
    </>
  );
}
