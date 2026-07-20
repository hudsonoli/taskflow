type ButtonColorScheme = "neutral" | "brand";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
  size?: "sm" | "md";
  colorScheme?: ButtonColorScheme;
};

const sizeClassNames: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "px-3.5 py-1.5",
  md: "px-4 py-2",
};

// neutral continua sendo o default (preto/branco) — decisão revertida
// nesta fase (a generalização do laranja como default de toda ação
// primária foi congelada até uma revisão própria da hierarquia de
// botões). brand (laranja, identidade BOX) é usado explicitamente pelos
// consumidores que já adotaram a ação principal em laranja (ex.: Clientes,
// Usuários, via EntityActions) e continua disponível para os próximos.
const variantClassNamesByColorScheme: Record<
  ButtonColorScheme,
  Record<NonNullable<ButtonProps["variant"]>, string>
> = {
  neutral: {
    primary: "bg-zinc-900 text-white hover:opacity-90",
    secondary: "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50",
  },
  brand: {
    primary: "bg-primary text-white hover:bg-primary-hover",
    secondary:
      "border border-zinc-200 bg-white text-zinc-900 hover:border-primary hover:text-primary",
  },
};

export function Button({
  children,
  variant = "primary",
  size = "md",
  colorScheme = "neutral",
  className,
  ...rest
}: ButtonProps) {
  const variantClassName = variantClassNamesByColorScheme[colorScheme][variant];

  return (
    <button
      className={`rounded-2xl ${sizeClassNames[size]} text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${variantClassName} ${className ?? ""}`}
      {...rest}
    >
      {children}
    </button>
  );
}
