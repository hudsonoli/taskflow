import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { EntityForm } from "./EntityForm";

export type BankingFieldsValue = {
  chavePix: string;
  banco: string;
  agencia: string;
  conta: string;
  tipoConta: "Corrente" | "Poupança" | "Pagamento";
};

type BankingFieldsProps = {
  value: BankingFieldsValue;
  onChange: (updater: (current: BankingFieldsValue) => BankingFieldsValue) => void;
  className?: string;
};

const tipoContaOptions = [
  { value: "Corrente", label: "Corrente" },
  { value: "Poupança", label: "Poupança" },
  { value: "Pagamento", label: "Pagamento" },
];

/**
 * Grupo de campos bancários — genérico, sem nome de entidade (evita
 * "ClienteDadosBancarios" aqui). Reutilizável por qualquer entidade com
 * dados bancários (Clientes hoje, Usuários "Dados Bancários" no futuro).
 * Grade de 12 colunas própria: quem usa este componente não precisa
 * conhecer o layout interno.
 */
export function BankingFields({ value, onChange, className }: BankingFieldsProps) {
  function update<K extends keyof BankingFieldsValue>(field: K, fieldValue: BankingFieldsValue[K]) {
    onChange((current) => ({ ...current, [field]: fieldValue }));
  }

  return (
    <EntityForm>
      <div className="col-span-12">
        <Input
          label="Chave PIX"
          value={value.chavePix}
          density="compact"
          className={className}
          onChange={(event) => update("chavePix", event.target.value)}
        />
      </div>

      <div className="col-span-12 md:col-span-6">
        <Input
          label="Banco"
          value={value.banco}
          density="compact"
          className={className}
          onChange={(event) => update("banco", event.target.value)}
        />
      </div>

      <div className="col-span-12 md:col-span-6">
        <Select
          label="Tipo da Conta"
          options={tipoContaOptions}
          value={value.tipoConta}
          density="compact"
          className={className}
          onChange={(event) =>
            update("tipoConta", event.target.value as BankingFieldsValue["tipoConta"])
          }
        />
      </div>

      <div className="col-span-12 md:col-span-6">
        <Input
          label="Agência"
          value={value.agencia}
          density="compact"
          className={className}
          onChange={(event) => update("agencia", event.target.value)}
        />
      </div>

      <div className="col-span-12 md:col-span-6">
        <Input
          label="Conta"
          value={value.conta}
          density="compact"
          className={className}
          onChange={(event) => update("conta", event.target.value)}
        />
      </div>
    </EntityForm>
  );
}
