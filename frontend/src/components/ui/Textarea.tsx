type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
};

export function Textarea({ label, className, ...rest }: TextareaProps) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-zinc-700">{label}</span>

      <textarea
        rows={3}
        className={`w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-400 ${className ?? ""}`}
        {...rest}
      />
    </label>
  );
}
