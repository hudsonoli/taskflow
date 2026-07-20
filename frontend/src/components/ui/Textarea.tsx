type TextareaDensity = "compact" | "default";

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  density?: TextareaDensity;
};

// Mesma régua de Input.tsx/Select.tsx: compact menor/mais leve, default
// (usado hoje por Projetos, Equipes, Demandas, Conta, Design System)
// permanece byte-a-byte igual ao original.
const labelClassNames: Record<TextareaDensity, string> = {
  compact: "mb-1 block text-[11px] font-normal text-zinc-500",
  default: "mb-1 block font-medium text-zinc-700",
};

const fieldTextClassNames: Record<TextareaDensity, string> = {
  compact: "text-[12px]",
  default: "text-sm",
};

export function Textarea({ label, className, density = "default", ...rest }: TextareaProps) {
  return (
    <label className="block text-sm">
      <span className={labelClassNames[density]}>{label}</span>

      <textarea
        rows={3}
        className={`w-full rounded-2xl border border-zinc-200 bg-white px-3 py-2 ${fieldTextClassNames[density]} text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-900/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-400 ${className ?? ""}`}
        {...rest}
      />
    </label>
  );
}
