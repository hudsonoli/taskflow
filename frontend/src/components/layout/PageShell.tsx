import type { ReactNode } from "react";

type PageShellDensity = "compact" | "default";

type PageShellProps = {
  children: ReactNode;
  density?: PageShellDensity;
};

const densityClassNames: Record<PageShellDensity, string> = {
  compact: "space-y-2 p-4 sm:p-5",
  default: "space-y-6 p-8",
};

export function PageShell({ children, density = "default" }: PageShellProps) {
  return <div className={densityClassNames[density]}>{children}</div>;
}
