"use client";

import type { ReactNode } from "react";

type EntitySummarySection = {
  title?: string;
  children: ReactNode;
  className?: string;
};

type EntitySummaryPanelProps = {
  badges?: ReactNode;
  sections?: EntitySummarySection[];
  children?: ReactNode;
  className?: string;
};

export function EntitySummaryPanel({
  badges,
  sections = [],
  children,
  className = "",
}: EntitySummaryPanelProps) {
  return (
    <div className={`space-y-5 ${className}`.trim()}>
      {badges && <div className="flex flex-wrap gap-2">{badges}</div>}

      {sections.map((section, index) => (
        <section
          key={`${section.title ?? "section"}-${index}`}
          className={section.className}
        >
          {section.title && (
            <h3 className="text-sm font-semibold text-zinc-900">
              {section.title}
            </h3>
          )}
          <div className={section.title ? "mt-3" : undefined}>
            {section.children}
          </div>
        </section>
      ))}

      {children}
    </div>
  );
}
