"use client";

import { useRef } from "react";
import type { KeyboardEvent } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";

interface Tab {
  id: string;
  label: string;
}

export function Tabs({
  tabs,
  activeTab,
  onChange,
}: {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
}) {
  const buttonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const focusAndSelect = (tabId: string) => {
    onChange(tabId);
    buttonRefs.current[tabId]?.focus();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") {
      nextIndex = (index + 1) % tabs.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + tabs.length) % tabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = tabs.length - 1;
    }
    if (nextIndex !== null) {
      event.preventDefault();
      focusAndSelect(tabs[nextIndex].id);
    }
  };

  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto rounded-xl bg-surface-2 p-1">
      {tabs.map((tab, index) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            ref={(el) => {
              buttonRefs.current[tab.id] = el;
            }}
            type="button"
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className="relative whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium text-fg-muted transition"
          >
            {isActive && (
              <motion.span
                layoutId="tabs-active"
                className="absolute inset-0 rounded-lg bg-surface shadow-sm"
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
              />
            )}
            <span className={clsx("relative z-10", isActive && "text-fg")}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
