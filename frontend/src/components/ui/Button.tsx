type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({
  children,
  variant = "primary",
  className,
  ...rest
}: ButtonProps) {
  const variantClassName =
    variant === "secondary"
      ? "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
      : "bg-zinc-900 text-white hover:opacity-90";

  return (
    <button
      className={`rounded-2xl px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${variantClassName} ${className ?? ""}`}
      {...rest}
    >
      {children}
    </button>
  );
}
