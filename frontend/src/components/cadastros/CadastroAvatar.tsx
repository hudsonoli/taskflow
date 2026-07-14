import type { LucideIcon } from "lucide-react";

type CadastroAvatarDensity = "compact" | "default";

type CadastroAvatarProps = {
  label: string;
  icon?: LucideIcon;
  density?: CadastroAvatarDensity;
};

const densityClassNames: Record<CadastroAvatarDensity, string> = {
  compact: "h-6 w-6",
  default: "h-8 w-8",
};

function getInitials(label: string) {
  const words = label.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) return "--";

  return words
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join("");
}

export function CadastroAvatar({
  label,
  icon: Icon,
  density = "default",
}: CadastroAvatarProps) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full bg-zinc-100 text-[11px] font-semibold text-zinc-700 ring-1 ring-inset ring-zinc-200 ${densityClassNames[density]}`}
    >
      {Icon ? <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" /> : getInitials(label)}
    </span>
  );
}
