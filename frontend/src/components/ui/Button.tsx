import type { ButtonHTMLAttributes } from "react";
import clsx from "clsx";

type ButtonVariant = "primary" | "secondary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variantClassNames: Record<ButtonVariant, string> = {
  // `inset` de 1px claro no topo dá o relevo do botão sem aumentar a altura; o hover acende e levanta de leve (sem mover o layout).
  primary:
    "bg-brand-gradient shadow-sm shadow-indigo-500/25 inset-shadow-xs inset-shadow-white/25 hover:shadow-md hover:shadow-indigo-500/30 hover:brightness-110",
  secondary:
    "border border-line-strong bg-surface text-fg-muted shadow-xs hover:border-field-line hover:bg-surface-hover hover:text-fg",
  ghost: "text-fg-muted hover:bg-surface-hover hover:text-fg",
};

export function Button({ variant = "primary", className, disabled, ...props }: ButtonProps) {
  return (
    <button
      disabled={disabled}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 rounded-full px-3.5 py-2 text-xs font-semibold transition duration-150 ease-out active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
        variantClassNames[variant],
        className,
      )}
      {...props}
    />
  );
}
