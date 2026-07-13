"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "taskflow-sidebar";

type SidebarContextValue = {
  isCollapsed: boolean;
  toggleSidebar: () => void;
};

const SidebarContext = createContext<SidebarContextValue | null>(null);

function getStoredSidebarState() {
  if (typeof window === "undefined") {
    return false;
  }

  const value = window.localStorage.getItem(STORAGE_KEY);
  return value === "collapsed";
}

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setIsCollapsed(getStoredSidebarState());
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, []);

  const value = useMemo<SidebarContextValue>(
    () => ({
      isCollapsed,
      toggleSidebar: () => {
        setIsCollapsed((current) => {
          const next = !current;

          if (typeof window !== "undefined") {
            window.localStorage.setItem(
              STORAGE_KEY,
              next ? "collapsed" : "expanded",
            );
          }

          return next;
        });
      },
    }),
    [isCollapsed],
  );

  return (
    <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);

  if (!context) {
    throw new Error("useSidebar must be used within SidebarProvider");
  }

  return context;
}
