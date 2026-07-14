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

// neutral é o default e permanece byte-a-byte igual ao original (preto/
// branco) — os ~25 consumidores atuais de Button não mudam de aparência.
// brand é opt-in, usado hoje só por Clientes (identidade BOX: laranja),
// via os mesmos tokens semânticos já usados em foco/EntityFormNav.
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
