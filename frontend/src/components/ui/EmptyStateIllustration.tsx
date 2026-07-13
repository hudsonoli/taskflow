import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

type EmptyStateIllustrationProps = {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
  size?: "default" | "compact";
};

const sizeClassNames = {
  default: {
    container: "p-6",
    icon: "h-12 w-12 rounded-3xl",
    title: "mt-4 text-base",
    description: "text-sm",
    action: "mt-5",
  },
  compact: {
    container: "p-4",
    icon: "h-10 w-10 rounded-2xl",
    title: "mt-3 text-sm",
    description: "text-xs",
    action: "mt-4",
  },
};

export function EmptyStateIllustration({
  title,
  description,
  icon,
  action,
  size = "default",
}: EmptyStateIllustrationProps) {
  const classes = sizeClassNames[size];

  return (
    <div className={`rounded-3xl border border-dashed border-zinc-200 bg-[#faf8f4] text-center ${classes.container}`}>
      <div className={`mx-auto flex items-center justify-center bg-white text-zinc-500 shadow-sm ring-1 ring-zinc-100 ${classes.icon}`}>
        {icon ?? <Inbox className="h-5 w-5" aria-hidden="true" />}
      </div>
      <h3 className={`${classes.title} font-semibold text-zinc-950`}>{title}</h3>
      <p className={`mx-auto mt-1 max-w-md text-zinc-500 ${classes.description}`}>{description}</p>
      {action && <div className={classes.action}>{action}</div>}
    </div>
  );
}
