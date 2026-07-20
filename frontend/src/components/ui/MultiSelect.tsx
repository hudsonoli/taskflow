type MultiSelectOption = {
  value: string;
  label: string;
};

type MultiSelectProps = {
  options: MultiSelectOption[];
  values: string[];
  onChange: (values: string[]) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
};

export function MultiSelect({
  options,
  values,
  onChange,
  label,
  placeholder = "Selecione uma ou mais opções",
  disabled = false,
}: MultiSelectProps) {
  const selectedLabels = options
    .filter((option) => values.includes(option.value))
    .map((option) => option.label);

  function toggleValue(value: string) {
    if (disabled) return;

    if (values.includes(value)) {
      onChange(values.filter((currentValue) => currentValue !== value));
      return;
    }

    onChange([...values, value]);
  }

  return (
    <div className="block text-sm">
      {label && (
        <span className="mb-1 block font-medium text-zinc-700">{label}</span>
      )}

      <div
        className={`rounded-2xl border border-zinc-200 bg-white p-3 ${
          disabled ? "opacity-60" : ""
        }`}
      >
        <p className="min-h-5 text-sm text-zinc-500">
          {selectedLabels.length > 0 ? selectedLabels.join(", ") : placeholder}
        </p>

        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {options.map((option) => (
            <label
              key={option.value}
              className={`flex items-center gap-2 rounded-xl border border-zinc-100 px-3 py-2 text-sm text-zinc-700 ${
                disabled
                  ? "cursor-not-allowed"
                  : "cursor-pointer hover:bg-zinc-50"
              }`}
            >
              <input
                type="checkbox"
                checked={values.includes(option.value)}
                disabled={disabled}
                onChange={() => toggleValue(option.value)}
                className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-1"
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
