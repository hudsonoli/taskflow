import type { ReactNode } from "react";

type PageHeaderSize = "page" | "section";

type PageHeaderProps = {
  title: string;
  description: string;
  actions?: ReactNode;
  size?: PageHeaderSize;
};

const sizeClassNames: Record<
  PageHeaderSize,
  { wrapper: string; title: string; description: string }
> = {
  page: {
    wrapper: "mb-8",
    title: "text-3xl font-bold",
    description: "mt-2 text-zinc-500",
  },
  section: {
    wrapper: "",
    title: "text-lg font-semibold text-zinc-900",
    description: "mt-0.5 text-sm text-zinc-500",
  },
};

export function PageHeader({
  title,
  description,
  actions,
  size = "page",
}: PageHeaderProps) {
  const classes = sizeClassNames[size];
  const HeadingTag = size === "page" ? "h1" : "h2";

  const titleBlock = (
    <>
      <HeadingTag className={classes.title}>{title}</HeadingTag>

      <p className={classes.description}>{description}</p>
    </>
  );

  if (!actions) {
    return <div className={classes.wrapper}>{titleBlock}</div>;
  }

  const layoutClassName =
    "flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between";

  return (
    <div className={`${layoutClassName} ${classes.wrapper}`.trim()}>
      <div className="min-w-0">{titleBlock}</div>

      <div className="shrink-0">{actions}</div>
    </div>
  );
}
