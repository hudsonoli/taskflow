import type { ReactNode } from "react";

type DashboardGridProps = {
  children: ReactNode;
  columns?: "auto" | "two" | "three" | "four" | "five";
  className?: string;
};

const columnClassNames: Record<NonNullable<DashboardGridProps["columns"]>, string> = {
  auto: "grid-cols-1 sm:grid-cols-2 xl:grid-cols-4",
  two: "grid-cols-1 xl:grid-cols-2",
  three: "grid-cols-1 md:grid-cols-3",
  four: "grid-cols-1 sm:grid-cols-2 xl:grid-cols-4",
  five: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5",
};

export function DashboardGrid({
  children,
  columns = "auto",
  className,
}: DashboardGridProps) {
  return (
    <div className={`grid gap-4 ${columnClassNames[columns]} ${className ?? ""}`}>
      {children}
    </div>
  );
}
