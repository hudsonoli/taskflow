type InputDensity = "compact" | "default";

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  density?: InputDensity;
};

// compact fica menor/mais leve (rótulo e conteúdo) que o default — o
// default permanece byte-a-byte igual ao original, então os consumidores
// que não usam density="compact" não mudam de aparência.
const labelClassNames: Record<InputDensity, string> = {
  compact: "mb-1 block text-[11px] font-normal text-zinc-500",
  default: "mb-1 block font-medium text-zinc-700",
};

const fieldPaddingClassNames: Record<InputDensity, string> = {
  compact: "px-3 py-1.5",
  default: "px-3 py-2",
};

const fieldTextClassNames: Record<InputDensity, string> = {
  compact: "text-[12px]",
  default: "text-sm",
};

// Placeholder nunca mais chamativo que o conteúdo digitado — só relevante
// em compact (default não tem nenhum consumidor com placeholder hoje, mas
// fica igualmente inerte lá por precaução, sem mudar nada visualmente).
const placeholderClassNames: Record<InputDensity, string> = {
  compact: "placeholder:text-zinc-400 placeholder:font-normal",
  default: "",
};

export function Input({
  label,
  className,
  density = "default",
  ...rest
}: InputProps) {
  return (
    <label className="block text-sm">
      <span className={labelClassNames[density]}>{label}</span>

      <input
        className={`w-full rounded-xl border border-zinc-200 bg-white ${fieldPaddingClassNames[density]} ${fieldTextClassNames[density]} ${placeholderClassNames[density]} text-zinc-900 outline-none transition focus:border-zinc-400 ${className ?? ""}`}
        {...rest}
      />
    </label>
  );
}
