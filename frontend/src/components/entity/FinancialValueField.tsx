import { Input } from "@/components/ui/Input";

type FinancialValueFieldProps = {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  className?: string;
};

/**
 * Campo numérico de valor monetário — o estado permanece number|null,
 * nunca uma string já formatada com moeda (ex.: "R$ 1.234,56"). Formatação
 * de exibição, se necessária no futuro, é responsabilidade de quem lê o
 * valor, não deste campo (entity-component-api.md, seção "Guia
 * Administrativa"). Reutilizável por qualquer entidade com valor
 * financeiro (Fee Mensal em Clientes, Salário em Usuários no futuro).
 */
export function FinancialValueField({
  label,
  value,
  onChange,
  className,
}: FinancialValueFieldProps) {
  return (
    <Input
      label={label}
      type="number"
      inputMode="decimal"
      step="0.01"
      min={0}
      value={value ?? ""}
      density="compact"
      className={className}
      onChange={(event) => {
        const raw = event.target.value;
        onChange(raw === "" ? null : Number(raw));
      }}
    />
  );
}
